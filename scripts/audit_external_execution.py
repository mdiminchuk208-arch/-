"""Independent real-candle touch, gap, partial-exit and accounting audit."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
import gzip
import json
from math import isclose
from pathlib import Path

from research_support import check_baseline, read_compressed
from run_historical_portfolio import canonical
from run_research_execution_scenarios import restore_signal


def equal(a,b):
    assert isclose(a,b,rel_tol=1e-9,abs_tol=1e-8),(a,b)


def audit(root):
    repo=Path(__file__).resolve().parents[1]
    check_baseline(repo)
    jobs=defaultdict(list)
    for path in root.glob('*/*/trades.jsonl'):
        summary=json.loads((path.parent/'summary.json').read_text())
        for line in path.read_text().splitlines():
            t=json.loads(line)
            jobs[(summary['cohort'],t['symbol'],summary['ltf'])].append((path,summary,t))
    records=[];counts=Counter()
    for (cohort,symbol,ltf),group in jobs.items():
        data=read_compressed(repo/f'data/history/public_research/{cohort}_mirror/{symbol}/{ltf}.csv.gz',ltf)
        by_open={c.open_time:c for c in data};by_close={c.close_time:c for c in data}
        for path,summary,t in group:
            policy=summary['policy'];sign=1 if t['direction']=='LONG' else -1
            entry=by_open[datetime.fromisoformat(t['entry_interval_start'])]
            available=datetime.fromisoformat(t['signal_time'])
            assert available<=entry.open_time
            assert datetime.fromisoformat(t['ready_time'])<=entry.open_time
            with gzip.open(path.parent/'signals.jsonl.gz','rt') as reader:
                known=[restore_signal(json.loads(line)) for line in reader
                       if json.loads(line)['signal_id']==t['signal_id']]
            ready=max((s for s in known if s.status=='READY_FOR_VIRTUAL_ENTRY' and s.event_time<=entry.open_time),key=lambda s:s.event_time)
            quote=ready.optimal_entry
            if t['fill_model']=='RESTING_LIMIT_TOUCH':
                assert sign*(entry.open-quote)>0 and entry.low<=quote<=entry.high
                equal(t['theoretical_entry'],quote)
            else:
                assert ready.entry_zone.low<=entry.open<=ready.entry_zone.high
                assert sign*(entry.open-quote)<=0
                equal(t['theoretical_entry'],entry.open)
            equal(t['actual_entry_after_slippage'],t['theoretical_entry']*(1+sign*policy['slippage_fraction']))
            equal(t['entry_fee'],t['quantity']*t['actual_entry_after_slippage']*policy['fee_fraction'])
            stop=t['stop'];stage=0;allocated=0.;exit_fee=0.;net=0.;gross=0.;gap=False;samebar=False
            collisions=0
            for f in t['fills']:
                bar=by_close[datetime.fromisoformat(f['time'])]
                reference=f['reference_price'];quantity=f['quantity']
                if f['reason'].startswith('TP'):
                    number=int(f['reason'][-1]);equal(reference,t['targets'][number-1])
                    equal(quantity,t['quantity']*(.4 if number==1 else .3))
                    if bar.open_time==entry.open_time and t['fill_model']=='RESTING_LIMIT_TOUCH':
                        assert sign*(bar.close-reference)>=0,'Entry-bar profit must be proved by post-touch CLOSE'
                    if number==1:
                        stop=t['new_breakeven']
                    stage=number
                elif f['reason']=='STOP_FIRST_CONSERVATIVE':
                    effective_open=t['actual_entry_after_slippage'] if bar.open_time==entry.open_time and t['fill_model']=='RESTING_LIMIT_TOUCH' else bar.open
                    expected=min(stop,effective_open) if sign==1 else max(stop,effective_open)
                    equal(reference,expected);gap=reference!=stop
                    assert bar.low<=stop if sign==1 else bar.high>=stop
                    if stage<3:
                        target=t['targets'][stage]
                        if (bar.high>=target if sign==1 else bar.low<=target):
                            collisions+=1
                else:
                    assert f['reason']=='BREAKEVEN_SAME_BAR_CONSERVATIVE'
                    equal(reference,stop)
                    assert bar.low<=stop<=bar.high
                equal(f['price'],reference*(1-sign*policy['slippage_fraction']))
                equal(f['exit_fee'],quantity*f['price']*policy['fee_fraction'])
                equal(f['gross_pnl'],quantity*sign*(f['price']-t['actual_entry_after_slippage']))
                equal(f['net_pnl'],f['gross_pnl']-f['entry_fee_allocation']-f['exit_fee'])
                allocated+=f['entry_fee_allocation'];exit_fee+=f['exit_fee'];net+=f['net_pnl'];gross+=f['gross_pnl']
                samebar|=bar.open_time==entry.open_time
            equal(t['gross_pnl'],gross);equal(t['net_pnl'],net);equal(t['fees_total'],t['entry_fee']+exit_fee)
            if t['status']=='CLOSED':
                equal(allocated,t['entry_fee']);equal(sum(f['quantity'] for f in t['fills']),t['quantity'])
                equal(net,gross-t['fees_total']);equal(t['result_R'],net/t['risk_amount'])
            counts['trade_records_including_overlapping_research_windows']+=1
            counts['actual_adverse_gap_exit']+=int(gap);counts['entry_bar_exit']+=int(samebar)
            counts['old_stop_wins_stop_target_collision']+=collisions
            records.append(dict(source=str(path.relative_to(repo)),symbol=symbol,direction=t['direction'],
                signal_id=t['signal_id'],entry_time=t['entry_time'],status=t['status'],actual_quote=quote,
                actual_candle_touch='PASS',availability_before_entry_bar='PASS',partial_accounting='PASS',
                adverse_gap=gap,entry_bar_exit=samebar,stop_target_collisions=collisions,trade_entry_allowed=False))
    out=repo/'data/reports/robustness_research/external_execution_audit.json'
    out.write_text(canonical(dict(counts=dict(counts),records=records,
        actual_gaps_are_reported_even_if_none_occurs=True,
        unobserved_gap_cases_remain_covered_by_frozen_regression_tests=True,
        limitations=['OHLC_INTRABAR_ORDER_UNKNOWN','NO_FUNDING_OR_LIQUIDATION','NO_HISTORICAL_LOT_TICK_QUEUE_PARTIAL_LIQUIDITY_MODEL'],
        trade_entry_allowed=False))+'\n')
    print(dict(counts))


if __name__=='__main__':
    audit(Path(__file__).resolve().parents[1]/'data/reports/robustness_research/canonical')
