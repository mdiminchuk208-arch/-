"""Non-vacuous real-data causal prefix/future, determinism and mode checks."""
from __future__ import annotations

import argparse
from contextlib import ExitStack
from dataclasses import asdict, replace
from datetime import datetime, timedelta
import gzip
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from crypto_bot.strategy.auto_levels import AutoLevelPolicy
from crypto_bot.strategy.historical_replay import indexed_signal_updates
from crypto_bot.strategy.replay import EngineMode
from research_support import check_baseline, read_compressed
from run_historical_portfolio import canonical, simulate
from run_research_execution_scenarios import restore_signal
from run_robustness_research import slice_bars
from research_structure_cache import structure_cache, validated_prefix_reuse


def verify(source,output):
    source=source.resolve()
    repo=Path(__file__).resolve().parents[1]
    check_baseline(repo)
    summaries=sorted(source.glob('*/summary.json'))
    selected=None
    # Fixed rule: earliest actual closed trade in a complete canonical run.
    for path in summaries:
        for line in (path.parent/'trades.jsonl').read_text().splitlines():
            trade=json.loads(line)
            if trade['status']=='CLOSED' and (selected is None or trade['entry_time']<selected[1]['entry_time']):
                selected=(path,trade)
    if selected is None:
        raise ValueError('No real closed trade in selected cohort; use a completed cohort with evidence')
    path,trade=selected
    summary=json.loads(path.read_text())
    s=trade['symbol'];htf=summary['htf'];ltf=summary['ltf'];cohort=summary['cohort']
    begin=datetime.fromisoformat(summary['analysis_start'])
    cutoff=datetime.fromisoformat(trade['exit_time'])
    end=min(datetime.fromisoformat(summary['end']),cutoff+timedelta(days=7))
    data={tf:read_compressed(repo/f'data/history/public_research/{cohort}_mirror/{s}/{tf}.csv.gz',tf) for tf in (htf,ltf)}
    sample={tf:slice_bars(cs,begin,end) for tf,cs in data.items()}
    prefix={tf:[c for c in cs if c.close_time<=cutoff] for tf,cs in sample.items()}
    future={tf:[replace(c,open=c.open*1.7,high=c.high*1.7,low=c.low*1.7,close=c.close*1.7)
                    if c.close_time>cutoff else c for c in cs] for tf,cs in sample.items()}
    results=[]
    for name,histories,mode in [('full',sample,'BACKTEST'),('prefix',prefix,'BACKTEST'),
                              ('future_mutation',future,'BACKTEST'),('repeat',sample,'BACKTEST'),('shadow',sample,'SHADOW'),
                              ('accelerated',sample,'BACKTEST'),('accelerated_prefix',prefix,'BACKTEST'),
                              ('accelerated_future',future,'BACKTEST')]:
        with ExitStack() as stack:
            if name.startswith('accelerated'):
                cache=Path(stack.enter_context(TemporaryDirectory()))
                source_hashes={tf:sha256(canonical([asdict(c) for c in cs]).encode()).hexdigest() for tf,cs in histories.items()}
                stack.enter_context(structure_cache(cache,source_hashes,summary['baseline_commit']))
                stack.enter_context(validated_prefix_reuse(histories))
            signals,meta=indexed_signal_updates(histories,symbol=s,htf_minutes=htf,ltf_minutes=ltf,
                                                 mode=mode,auto_level_policy=AutoLevelPolicy())
        normalized=[replace(sig,mode=EngineMode.BACKTEST) for sig in signals if sig.event_time<=cutoff]
        assert normalized, 'Causal evidence must be non-vacuous'
        digest=sha256(canonical([asdict(sig) for sig in normalized]).encode()).hexdigest()
        results.append(dict(case=name,digest=digest,count=len(normalized),signals=normalized))
        print(name,len(normalized),'causal signals',flush=True)
    assert len({r['digest'] for r in results})==1, 'Past signals changed'
    with gzip.open(path.parent/'signals.jsonl.gz','rt') as reader:
        original=[restore_signal(json.loads(line)) for line in reader]
    actual=next(sig for sig in original if sig.signal_id==trade['signal_id'] and sig.status=='READY_FOR_VIRTUAL_ENTRY')
    candidates=[sig for sig in results[0]['signals'] if sig.signal_id==trade['signal_id'] and sig.status=='READY_FOR_VIRTUAL_ENTRY']
    assert any(replace(sig,event_time=actual.event_time)==actual for sig in candidates),'Real canonical READY not reproduced'
    execution={s:slice_bars(sample[ltf],datetime.fromisoformat(summary['start']),end)}
    bt,observed=simulate(execution,results[0]['signals'])
    sh,_=simulate(execution,[replace(sig,mode=EngineMode.SHADOW) for sig in results[0]['signals']],mode='SHADOW')
    assert canonical(bt.trades)==canonical(sh.trades)
    assert canonical([asdict(d) for d in bt.journal])==canonical([asdict(d) for d in sh.journal])
    assert canonical(bt.equity_curve)==canonical(sh.equity_curve)
    receipt=dict(source=str(path.relative_to(repo)),cohort=cohort,symbol=s,htf=htf,ltf=ltf,
        real_closed_trade_id=trade['trade_id'],direction=trade['direction'],analysis_start=begin,
        cutoff=cutoff,end=end,real_canonical_ready_reproduced=True,
        checks=[{k:v for k,v in r.items() if k!='signals'} for r in results],
        prefix_future_mutation_determinism_signal_mode_parity='PASS',
        same_frozen_signals_virtual_trade_decision_equity_mode_parity='PASS',
        single_symbol_verification_is_not_an_independent_performance_claim=True,
        future_mutation_is_a_causality_test_not_market_data=True,trade_entry_allowed=False)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(canonical(receipt)+'\n')
    check_baseline(repo)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    verify(args.source,args.output)


if __name__=='__main__':
    main()
