"""Replay frozen observed signals with registered costs/risk, without re-indexing."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime
import gzip
from hashlib import sha256
import json
from pathlib import Path

from crypto_bot.common.models import Direction
from crypto_bot.strategy.auto_levels import LevelEvidence
from crypto_bot.strategy.market_analysis import StructureAnalysisMode
from crypto_bot.strategy.replay import EngineMode, StrategySignal
from crypto_bot.strategy.trade_plan import PriceZone
from crypto_bot.strategy.virtual_portfolio import SimulationPolicy, VirtualPortfolio
from research_support import check_baseline, performance, read_compressed
from run_historical_portfolio import canonical, simulate
from run_robustness_research import slice_bars, write_rows


def restore_signal(row):
    row=dict(row)
    row.pop('trade_entry_allowed',None)
    row['direction']=Direction(row['direction'])
    row['mode']=EngineMode(row['mode'])
    row['analysis_mode']=StructureAnalysisMode(row['analysis_mode'])
    for name in ('event_time','sfp_time','bos_time','entry_geometry_ready_time','levels_known_at'):
        if row[name] is not None:
            row[name]=datetime.fromisoformat(row[name])
    if row['entry_zone'] is not None:
        row['entry_zone']=PriceZone(**row['entry_zone'])
    for name in ('reasons','invalidation_reasons','targets','level_blocking_reasons'):
        row[name]=tuple(row[name])
    evidence=[]
    for item in row['level_evidence']:
        item=dict(item)
        item['known_at']=datetime.fromisoformat(item['known_at'])
        item['source_times']=tuple(datetime.fromisoformat(t) for t in item['source_times'])
        item['prices']=tuple(item['prices'])
        item['details']=tuple(tuple(d) for d in item['details'])
        evidence.append(LevelEvidence(**item))
    row['level_evidence']=tuple(evidence)
    return StrategySignal(**row)


def scenarios(source,output):
    repo=Path(__file__).resolve().parents[1]
    check_baseline(repo)
    folders=sorted(source.glob('*/summary.json'))
    first=json.loads(folders[0].read_text())
    cohort,ltf=first['cohort'],first['ltf']
    split=json.loads((repo/f'data/reports/robustness_research/{cohort}_temporal_split.json').read_text())
    data={s:read_compressed(repo/f'data/history/public_research/{cohort}_mirror/{s}/{ltf}.csv.gz',ltf) for s in split['symbols']}
    policies={'BASE_VERIFY':SimulationPolicy(),'COST_150':SimulationPolicy(fee_fraction=.0009,slippage_fraction=.0003),
              'COST_200':SimulationPolicy(fee_fraction=.0012,slippage_fraction=.0004),
              'RISK_021':SimulationPolicy(risk_fraction=.021),'RISK_025':SimulationPolicy(risk_fraction=.025),
              'REENTRY_SCORE_80':SimulationPolicy(reentry_min_score=80)}
    results=[]
    for summary_path in folders:
        summary=json.loads(summary_path.read_text())
        if summary['window']['name']=='REFERENCE':
            continue
        start,end=(datetime.fromisoformat(summary[k]) for k in ('start','end'))
        execution={s:slice_bars(cs,start,end) for s,cs in data.items()}
        with gzip.open(summary_path.parent/'signals.jsonl.gz','rt') as reader:
            updates=[restore_signal(json.loads(line)) for line in reader]
        for name,policy in policies.items():
            p,observed=simulate(execution,updates,portfolio=VirtualPortfolio(equity=1170,policy=policy),initial_capital=1170)
            if name=='BASE_VERIFY':
                expected_trades=(summary_path.parent/'trades.jsonl').read_text()
                assert expected_trades==''.join(canonical(t)+'\n' for t in p.trades.values()),summary_path
                with gzip.open(summary_path.parent/'decisions.jsonl.gz','rt') as reader:
                    assert reader.read()==''.join(canonical(asdict(d))+'\n' for d in p.journal),summary_path
                with gzip.open(summary_path.parent/'equity_curve.jsonl.gz','rt') as reader:
                    assert reader.read()==''.join(canonical(t)+'\n' for t in p.equity_curve),summary_path
            target=output/name/summary_path.parent.name
            target.mkdir(parents=True,exist_ok=True)
            payload=dict(cohort=cohort,htf=summary['htf'],ltf=ltf,window=summary['window'],segment=summary['segment'],
                start=start,end=end,scenario=name,policy=asdict(policy),
                performance=performance(p,observed,start,end),canonical_parameters=name=='BASE_VERIFY',
                baseline_commit=summary['baseline_commit'],baseline_hash_guard='PASS',
                source_signal_sha256=sha256((summary_path.parent/'signals.jsonl.gz').read_bytes()).hexdigest(),
                source_input_hashes=summary['input_hashes'],signal_generation_unchanged=True,
                baseline_exact_trade_decision_equity_reproduction=name=='BASE_VERIFY',trade_entry_allowed=False)
            (target/'summary.json').write_text(canonical(payload)+'\n')
            write_rows(target/'trades.jsonl',p.trades.values())
            write_rows(target/'decisions.jsonl.gz',(asdict(d) for d in p.journal))
            write_rows(target/'equity_curve.jsonl.gz',p.equity_curve)
            results.append(dict(scenario=name,window=summary['window']['name'],segment=summary['segment'],
                                performance=payload['performance']))
            print(source.name,summary_path.parent.name,name,len(p.trades),'entries',flush=True)
    (output/'results.json').write_text(canonical(results)+'\n')
    check_baseline(repo)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    scenarios(args.source,args.output)


if __name__=='__main__':
    main()
