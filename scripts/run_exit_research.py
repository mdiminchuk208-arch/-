"""Controlled exit variants on identical frozen signals and actual paired fills."""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, replace
from datetime import datetime, timedelta
import gzip
from hashlib import sha256
import json
from pathlib import Path
from statistics import mean

from crypto_bot.data.storage import read_klines_csv
from crypto_bot.strategy.virtual_portfolio import SimulationPolicy, VirtualPortfolio
from research_exit_management import EXIT_VARIANTS, ExitResearchPortfolio
from research_support import check_baseline, performance
from run_historical_portfolio import canonical, simulate
from run_research_execution_scenarios import restore_signal
from run_robustness_research import slice_bars, write_rows
from research_support import read_compressed


def rows(path):
    with (gzip.open(path,'rt') if path.suffix=='.gz' else path.open()) as handle:
        return [json.loads(line) for line in handle]


def artifact(folder,name):
    plain=folder/name
    return plain if plain.exists() else folder/(name+'.gz')


def exit_metrics(p,observed,start,end):
    result=performance(p,observed,start,end)
    closed=[t for t in p.trades.values() if t['status']=='CLOSED']
    wins=[t['net_pnl'] for t in closed if t['net_pnl']>1e-9]
    losses=[-t['net_pnl'] for t in closed if t['net_pnl']< -1e-9]
    avgwin=mean(wins) if wins else None;avgloss=mean(losses) if losses else None
    hits=Counter(reason for t in p.trades.values() for reason in {f['reason'] for f in t['fills']})
    be=sum(any(f['reason']=='TP1' for f in t['fills']) and t['new_breakeven'] is not None
           and t['status']=='CLOSED' and t['exit_reason'] in ('STOP_FIRST_CONSERVATIVE','BREAKEVEN_SAME_BAR_CONSERVATIVE') for t in p.trades.values())
    result.update(average_win=avgwin,average_loss=avgloss,
        descriptive_break_even_win_rate=avgloss/(avgwin+avgloss) if avgwin is not None and avgloss is not None else None,
        tp1_hit_rate=hits['TP1']/len(p.trades) if p.trades else None,
        tp2_hit_rate=hits['TP2']/len(p.trades) if p.trades else None,
        tp3_hit_rate=hits['TP3']/len(p.trades) if p.trades else None,
        post_tp1_be_stops=be,tp_hit_rate_policy='OBSERVED_HITS_PER_ENTRY_CENSORED_OPEN_TRADES_NOT_ASSUMED_FAILED',
        exit_change_evidence='INSUFFICIENT_SAMPLE' if len(closed)<100 or hits['TP1']<30 else 'MINIMUM_GATES_ONLY_NOT_A_RECOMMENDATION')
    return result


def be_follow(trade,history,endpoint):
    if trade['status']!='CLOSED' or trade['new_breakeven'] is None or trade['exit_reason'] not in ('STOP_FIRST_CONSERVATIVE','BREAKEVEN_SAME_BAR_CONSERVATIVE') or not any(f['reason']=='TP1' for f in trade['fills']):
        return None
    after=datetime.fromisoformat(trade['exit_time']) if isinstance(trade['exit_time'],str) else trade['exit_time']
    end=min(endpoint,after+timedelta(days=30));long=trade['direction']=='LONG'
    unconditional=[False,False];before_stop=[False,False];ambiguous=[False,False];stopped=False
    for candle in history:
        if not after<=candle.close_time<=end:
            continue
        first=candle.close_time==after
        stop_hit=candle.low<=trade['stop'] if long else candle.high>=trade['stop']
        for i,target in enumerate(trade['targets'][1:]):
            # Only the closing price proves post-exit movement in the exit bar.
            reached=(candle.close>=target if long else candle.close<=target) if first else (candle.high>=target if long else candle.low<=target)
            touched=candle.high>=target if long else candle.low<=target
            unconditional[i]|=reached
            if not stopped:
                if stop_hit and touched:
                    ambiguous[i]=True
                elif not stop_hit and reached:
                    before_stop[i]=True
            if first and touched and not reached:
                ambiguous[i]=True
        stopped|=stop_hit
    return dict(signal_id=trade['signal_id'],symbol=trade['symbol'],direction=trade['direction'],exit_time=after,
        follow_end=end,follow_right_censored=end<after+timedelta(days=30),
        later_tp2_price_touch=unconditional[0],later_tp3_price_touch=unconditional[1],
        tp2_before_original_sl_stop_first=before_stop[0],tp3_before_original_sl_stop_first=before_stop[1],
        tp2_same_bar_order_ambiguous=ambiguous[0],tp3_same_bar_order_ambiguous=ambiguous[1],
        original_sl_observed=stopped,not_a_counterfactual_profit_claim=True)


def paired_replays(expected,signals,history,policy,end):
    """Condition on actual admitted fills; never manufacture a READY or a quote."""
    results=[];cache={}
    for original in expected:
        symbol=original['symbol'];sid=original['signal_id']
        begin=datetime.fromisoformat(original['entry_interval_start'])
        candidates=[s for s in signals if s.signal_id==sid and s.event_time<=begin
                    and s.status=='READY_FOR_VIRTUAL_ENTRY']
        assert candidates,(sid,'no already-known actual READY')
        signal=max(candidates,key=lambda s:s.event_time)
        assert canonical(asdict(signal.entry_zone))==canonical(original['entry_zone'])
        assert signal.stop_loss==original['stop'] and list(signal.targets)==original['targets']
        observation=next(c for c in history[symbol] if c.close_time==signal.event_time)
        VirtualPortfolio._validate_signal(signal,signal.event_time,{symbol:observation},signal.mode)
        pair=[]
        for variant in EXIT_VARIANTS:
            outputs=[]
            for mode in ('BACKTEST','SHADOW'):
                p=execute_pair(signal,original,variant,history,policy,end,mode,cache)
                assert sid in p.trades and len(p.trades)==1,(sid,variant,'actual fill not reproduced')
                trade=p.trades[sid]
                for key in ('entry_time','entry_interval_start','entry_interval_end','actual_entry_after_slippage',
                            'theoretical_entry','quantity','risk_amount','entry_fee','fill_model'):
                    assert canonical(trade[key])==canonical(original[key]),(sid,variant,key)
                outputs.append(p)
            p,shadow=outputs
            assert canonical(p.trades)==canonical(shadow.trades),(sid,variant,'mode trade mismatch')
            assert canonical(p.equity_curve)==canonical(shadow.equity_curve),(sid,variant,'mode NAV mismatch')
            if variant=='A_40_30_30_BE_TP1':
                for key in ('status','exit_time','exit_reason','net_pnl','gross_pnl','fees_total',
                            'slippage_total','result_R','MFE','MAE','new_breakeven'):
                    assert canonical(p.trades[sid].get(key))==canonical(original.get(key)),(sid,key)
                strip=lambda fills:[{k:v for k,v in f.items() if k!='sequence'} for f in fills]
                assert canonical(strip(p.trades[sid]['fills']))==canonical(strip(original['fills'])),sid
            pair.append(dict(variant=variant,trade=p.trades[sid],
                individual_trade_nav_max_drawdown=p.max_drawdown,baseline_entry_reproduced=True,
                backtest_shadow_trade_nav_match=True,independent_trade_not_a_pooled_portfolio=True))
        results.append(dict(signal_id=sid,actual_ready_observed_at=signal.event_time,
            canonical_entry=original['entry_time'],variants=pair))
    return results


def execute_pair(signal,original,variant,history,policy,end,mode='BACKTEST',cache=None):
    symbol=original['symbol'];begin=datetime.fromisoformat(original['entry_interval_start'])
    p=ExitResearchPortfolio(variant=variant,equity=original['initial_equity'],policy=policy,
        history=history,frame_cache=cache,mode=mode)
    # Actual earlier observed and validated state; inherited admission still runs.
    p.pending[signal.signal_id]=replace(signal,mode=mode)
    for candle in history[symbol]:
        if candle.open_time<begin or candle.close_time>end:
            continue
        p.step({symbol:candle})
        if not p.positions:
            break
    return p


def verify_exit_future(expected,signals,history,policy):
    eligible=[t for t in expected if t['status']=='CLOSED' and any(f['reason']=='TP1' for f in t['fills'])]
    if not eligible:
        return dict(status='NO_CANONICAL_TP1_EVENT_FOR_NONVACUOUS_EXIT_CAUSALITY',trade_entry_allowed=False)
    original=min(eligible,key=lambda t:t['entry_time']);sid=original['signal_id'];symbol=original['symbol']
    begin=datetime.fromisoformat(original['entry_interval_start']);cutoff=datetime.fromisoformat(original['exit_time'])
    signal=max((s for s in signals if s.signal_id==sid and s.event_time<=begin and s.status=='READY_FOR_VIRTUAL_ENTRY'),key=lambda s:s.event_time)
    full={symbol:history[symbol]}
    prefix={symbol:[c for c in history[symbol] if c.close_time<=cutoff]}
    future={symbol:[replace(c,open=c.open*1.7,high=c.high*1.7,low=c.low*1.7,close=c.close*1.7)
                    if c.close_time>cutoff else c for c in history[symbol]]}
    for variant in EXIT_VARIANTS:
        signatures=[]
        for data in (full,prefix,future):
            p=execute_pair(signal,original,variant,data,policy,cutoff)
            signatures.append(canonical(dict(trades=p.trades,journal=[asdict(d) for d in p.journal],equity=p.equity_curve)))
        assert len(set(signatures))==1,(sid,variant,'past exit changed with future prices')
    return dict(status='PASS',actual_tp1_trade=sid,cutoff=cutoff,variants=list(EXIT_VARIANTS),
        full_prefix_future_mutation=True,mutation_is_verification_only=True,trade_entry_allowed=False)


def run_case(folder,output,role,verify_only=False):
    repo=Path(__file__).resolve().parents[1];check_baseline(repo)
    source=json.loads((folder/'summary.json').read_text())
    old='execution_start' in source
    start=datetime.fromisoformat(source['execution_start'] if old else source['start'])
    end=datetime.fromisoformat(source['execution_end'] if old else source['end'])
    analysis_start=datetime.fromisoformat(source['warmup_start'] if old else source['analysis_start'])
    ltf=source['ltf_minutes'] if old else source['ltf'];htf=source['htf_minutes'] if old else source['htf']
    symbols=source['symbols'] if old else sorted({Path(name).parts[-2] for name in source['input_hashes']})
    history={}
    for s in symbols:
        p=repo/f'data/history/bybit/{s}/{ltf}.csv' if old else repo/f"data/history/public_research/{source['cohort']}_mirror/{s}/{ltf}.csv.gz"
        digest=sha256(p.read_bytes()).hexdigest()
        assert digest==source['input_hashes'][f'{s}/{ltf}.csv' if old else str(p.relative_to(repo))],p
        history[s]=[c.to_strategy_candle(ltf*60000) for c in read_klines_csv(p)] if old else read_compressed(p,ltf,begin=analysis_start,end=end)
    execution={s:slice_bars(cs,start,end) for s,cs in history.items()}
    signals=[restore_signal(row) for row in rows(artifact(folder,'signals.jsonl'))]
    expected=rows(artifact(folder,'trades.jsonl'));policy=SimulationPolicy(**source['policy'])
    if verify_only:
        assert (output/'results.json').exists() and (output/'paired_actual_entries.json').exists(),output
        (output/'exit_real_causality.json').write_text(canonical(verify_exit_future(expected,signals,history,policy))+'\n')
        check_baseline(repo)
        return
    capital=source['initial_capital'] if old else 1170
    results=[];base=None;cache={}
    for variant,(allocation,timing) in EXIT_VARIANTS.items():
        inactive=base is not None and not any(f['reason']=='TP1' for t in base.trades.values() for f in t['fills'])
        if inactive:
            p=base;observed=signals
        else:
            p,observed=simulate(execution,signals,initial_capital=capital,
                portfolio=ExitResearchPortfolio(variant=variant,equity=capital,policy=policy,history=history,frame_cache=cache))
        if base is None:
            assert canonical(sorted(p.trades.values(),key=lambda t:t['trade_id']))==canonical(sorted(expected,key=lambda t:t['trade_id'])),folder
            assert canonical([asdict(d) for d in p.journal])==canonical(rows(artifact(folder,'decisions.jsonl'))),folder
            assert canonical(p.equity_curve)==canonical(rows(artifact(folder,'equity_curve.jsonl'))),folder
            base=p
        destination=output/variant;destination.mkdir(parents=True,exist_ok=True)
        receipt=dict(source=str(folder.relative_to(repo)),role=role,cohort='BYBIT_2026_DEVELOPMENT' if old else source['cohort'],
            symbols=symbols,htf=htf,ltf=ltf,start=start,end=end,variant=variant,allocation=allocation,stop_policy=timing,
            performance=exit_metrics(p,observed,start,end),source_signal_sha256=sha256(artifact(folder,'signals.jsonl').read_bytes()).hexdigest(),
            identical_frozen_incoming_signals=True,entry_and_risk_rules_unchanged=True,
            later_admissions_can_change_due_to_exit_cash_occupancy=True,
            equivalence_before_any_tp1_used=inactive,
            baseline_a_exact_trade_decision_equity_match=variant=='A_40_30_30_BE_TP1',
            baseline_commit=check_baseline(repo)['baseline_commit'],trade_entry_allowed=False)
        (destination/'summary.json').write_text(canonical(receipt)+'\n')
        write_rows(destination/'trades.jsonl',p.trades.values())
        write_rows(destination/'decisions.jsonl.gz',(asdict(d) for d in p.journal))
        write_rows(destination/'equity_curve.jsonl.gz',p.equity_curve)
        results.append(receipt)
        print(folder.name,variant,len(p.trades),'entries',len([t for t in p.trades.values() if t['status']=='CLOSED']),'closed',flush=True)
    assert base is not None
    follow=[row for t in base.trades.values() if (row:=be_follow(t,history[t['symbol']],end)) is not None]
    (output/'post_be_follow.json').write_text(canonical(follow)+'\n')
    (output/'paired_actual_entries.json').write_text(canonical(paired_replays(expected,signals,history,policy,end))+'\n')
    (output/'exit_real_causality.json').write_text(canonical(verify_exit_future(expected,signals,history,policy))+'\n')
    (output/'results.json').write_text(canonical(results)+'\n')
    check_baseline(repo)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--role',choices=['DEVELOPMENT','EXTERNAL','EXIT_UNTOUCHED_RESERVE'],required=True)
    parser.add_argument('--verify-only',action='store_true',help='Add real exit causal checks to already completed identical-entry experiments.')
    args=parser.parse_args();source=args.source.resolve()
    folders=[source] if (source/'summary.json').exists() else [p.parent for p in sorted(source.glob('*/summary.json'))
        if json.loads(p.read_text())['window']['name'] in ('REFERENCE','VALIDATION','HOLDOUT','EXIT_HOLDOUT')]
    for folder in folders:
        run_case(folder,args.output/folder.name,args.role,args.verify_only)


if __name__=='__main__':
    main()
