"""Frozen-entry exit diagnostics; never alter production or select an exit."""
from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from collections import defaultdict
from dataclasses import replace
from datetime import datetime
from hashlib import sha256
from pathlib import Path

from crypto_bot.common.models import Direction
from crypto_bot.research.medium_statistics import closed_statistics
from crypto_bot.research.v2_common import write_csv
from crypto_bot.strategy.source_medium_term import portfolio_signal
from crypto_bot.strategy.source_pdf_native import evidence_json
from crypto_bot.strategy.virtual_portfolio import (
    SimulationPolicy,
    VirtualPortfolio,
    VirtualPosition,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_source_fidelity_state import BASE, REPO, ROOT, population
from run_medium_term_research import (
    deserialize_signal,
    digest,
    load_data,
    read_rows,
    resume,
    seal,
    write_json,
    write_rows,
)

MODELS = ('C_CANONICAL', 'D_NO_BE', 'B1_FULL_BASELINE_FIRST_TARGET',
          'B2_FULL_OLD_SOURCE_FTA', 'A_SOURCE_PERMITTED_EXIT_DIAGNOSTIC')


class DiagnosticPortfolio(VirtualPortfolio):
    def __init__(self, *, model, target_prices, fractions, **kwargs):
        super().__init__(**kwargs)
        self.model, self.target_prices, self.fractions = model, target_prices, fractions

    def _manage(self, position, candle):
        if self.model == 'C_CANONICAL':
            return super()._manage(position, candle)
        long = position.signal.direction == Direction.LONG
        if candle.low <= position.stop_loss if long else candle.high >= position.stop_loss:
            reference = min(position.stop_loss, candle.open) if long else max(position.stop_loss, candle.open)
            self._close_fraction(position, position.remaining_fraction, reference,
                                 candle.close_time, 'STOP_FIRST_CONSERVATIVE')
            return
        for stage, (target, fraction) in enumerate(zip(self.target_prices, self.fractions, strict=True)):
            if stage < position.tp_stage:
                continue
            if not (candle.high >= target if long else candle.low <= target):
                break
            self._close_fraction(position, fraction, target, candle.close_time, f'TP{stage+1}')
            position.tp_stage = stage+1


def exit_spec(signal, snapshot, model):
    if model in ('C_CANONICAL', 'D_NO_BE'):
        return tuple(signal.targets), (.4, .3, .3)
    if model == 'B1_FULL_BASELINE_FIRST_TARGET':
        return (signal.targets[0],), (1.,)
    z = snapshot.get('old_source_fta')
    sign = 1 if signal.direction == 'LONG' else -1
    target = (z['low'] if sign == 1 else z['high']) if z else None
    # Missing contextual FTA stays undefined. Never manufacture it from P&L.
    if z is None:
        target = None
    if model == 'A_SOURCE_PERMITTED_EXIT_DIAGNOSTIC' and signal.poi_type == 'RANGE_POI':
        parent = signal.evidence['htf_poi']
        boundary = math.nextafter(parent['high'] if sign == 1 else parent['low'],
                                  parent['low'] if sign == 1 else parent['high'])
        if sign*(boundary-signal.entry) <= 0:
            return None
        # This is the preserved explicit source_permitted._emit alternative,
        # not a claim that the unspecified optional 20% original exit is unique.
        first = min(boundary, target) if target is not None and sign == 1 else (
            max(boundary, target) if target is not None else boundary)
        remainder = target if target is not None and sign*(target-boundary)>0 else boundary
        return (first, remainder), (.8, .2)
    if target is None or sign*(target-signal.entry) <= 0:
        return None
    return (target,), (1.,)


def simulate_fixed_trade(trade, signal, bars, exit_events, *, model,
                         target_prices=None, fractions=None, mode='BACKTEST', cutoff=None):
    """No admission/re-sizing: identical committed entry, quantity and SL."""
    original = copy.deepcopy(trade)
    entry_time = datetime.fromisoformat(trade['entry_time'])
    entry_open = datetime.fromisoformat(trade['entry_interval_start'])
    quantity, entry = trade['quantity'], trade['actual_entry_after_slippage']
    target_prices = tuple(target_prices or signal.targets)
    fractions = tuple(fractions or (.4, .3, .3))
    p = DiagnosticPortfolio(model=model, target_prices=target_prices, fractions=fractions,
        equity=trade['initial_equity'], mode=mode, policy=SimulationPolicy())
    typed = portfolio_signal(signal, 15, p.mode)
    position = VirtualPosition(typed, entry_time, entry, quantity, 1., trade['stop'],
                               entry_fee=trade['entry_fee'])
    p.positions[signal.symbol] = position
    p.balance -= trade['entry_fee']
    p.fees_paid = trade['entry_fee']
    p.slippage_cost = quantity*abs(entry-trade['theoretical_entry'])
    t = copy.deepcopy(trade)
    for key in ('exit_time','exit_reason','balance_after_trade','equity_after_trade'):
        t.pop(key,None)
    t.update(entry_time=entry_time, status='OPEN', fills=[], gross_pnl=0., net_pnl=0.,
             fees_total=trade['entry_fee'], slippage_total=p.slippage_cost,
             result_R=None, MFE=0., MAE=0., new_breakeven=None,
             max_equity_during_trade=trade['initial_equity'], targets=list(target_prices),
             diagnostic_model=model, trade_entry_allowed=False)
    p.trades[signal.signal_id] = t
    s = 1 if signal.direction == 'LONG' else -1
    events = defaultdict(list)
    for e in exit_events:
        at = datetime.fromisoformat(e['known_at'])
        events[at].append(e)
    last = None
    for c in bars:
        if c.open_time < entry_open:
            continue
        if cutoff is not None and c.close_time > cutoff:
            break
        last = c.close_time
        managed = c
        if c.open_time == entry_open and trade['fill_model'] == 'RESTING_LIMIT_TOUCH':
            # Match canonical entry-touch uncertainty exactly.
            managed = replace(c, open=entry,
                high=max(entry,c.close) if s==1 else max(c.high,entry),
                low=min(c.low,entry) if s==1 else min(entry,c.close))
        t['MFE'] = max(t['MFE'], s*((managed.high if s==1 else managed.low)-entry))
        t['MAE'] = max(t['MAE'], -s*((managed.low if s==1 else managed.high)-entry))
        p.marks[signal.symbol] = c.close
        p._manage(position, managed)
        for event in events[c.close_time]:
            if signal.symbol in p.positions:
                p._close_fraction(position, position.remaining_fraction, event['price'],
                                  c.close_time, 'STRUCTURAL_'+event['reason'])
        if signal.symbol not in p.positions:
            break
    assert last is not None
    t['MFE_R'], t['MAE_R'] = t['MFE']*quantity/trade['risk_amount'], t['MAE']*quantity/trade['risk_amount']
    t['observed_until'] = last
    t['matched_entry_quantity_unchanged'] = (quantity==original['quantity'] and entry==original['actual_entry_after_slippage'])
    # This independent matched study has no shared NAV, margin or DD inference.
    for key in ('balance_after_trade','equity_after_trade','max_equity_during_trade'):
        t.pop(key,None)
    return json.loads(evidence_json(t))


def assert_baseline(replayed, original):
    for field in ['status','exit_time','exit_reason','new_breakeven','MFE','MAE',
                  'gross_pnl','net_pnl','fees_total','slippage_total','result_R']:
        a,b=replayed.get(field),original.get(field)
        if isinstance(a,(float,int)) and isinstance(b,(float,int)):
            assert math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-10),(field,a,b)
        else:
            assert a==b,(field,a,b)
    assert len(replayed['fills'])==len(original['fills'])
    for a,b in zip(replayed['fills'],original['fills'],strict=True):
        for key in ['time','reason','quantity','price','reference_price','gross_pnl',
                    'entry_fee_allocation','exit_fee','slippage_cost','net_pnl']:
            if isinstance(a[key],(float,int)):
                assert math.isclose(a[key],b[key],rel_tol=1e-12,abs_tol=1e-10),(key,a[key],b[key])
            else:
                assert a[key]==b[key],(key,a[key],b[key])


def statistics(rows):
    m=closed_statistics(rows)
    closed=[r for r in rows if r['status']=='CLOSED']
    m.update(defined_entries=len(rows),OPEN=sum(r['status']=='OPEN' for r in rows),
        average_winner=math.fsum(r['net_pnl'] for r in closed if r['net_pnl']>0)/m['wins'] if m['wins'] else None,
        average_loser=-math.fsum(r['net_pnl'] for r in closed if r['net_pnl']<0)/m['losses'] if m['losses'] else None,
        mean_MFE_R=math.fsum(r['MFE_R'] for r in closed)/len(closed) if closed else None,
        mean_MAE_R=math.fsum(r['MAE_R'] for r in closed)/len(closed) if closed else None,
        basis='SAME_FROZEN_ENTRIES_AND_QUANTITIES_INDEPENDENT_EXIT_CASES_NOT_REBALANCED_NAV')
    return m


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--resume-existing',action='store_true')
    args=parser.parse_args()
    policy=json.loads((REPO/'config/source_medium_term_policy.json').read_text())
    paths=[Path(__file__),REPO/'SOURCE_FIDELITY_AUDIT_PROTOCOL.md',
        ROOT/'source_alignment_matrix.json',ROOT/'exact_variants_identifiability.json',
        BASE/'simulation/enabled/manifest.json',REPO/'scripts/run_medium_term_research.py',
        REPO/'scripts/research_support.py',REPO/'scripts/audit_source_fidelity_state.py']
    paths+=list((REPO/'src').rglob('*.py'))
    paths+=[ROOT/'state'/s/'manifest.json' for s in ('BTCUSDT','ETHUSDT')]
    lock={'dependencies':{str(p.relative_to(REPO)):digest(p) for p in sorted(set(paths))},
          'models':MODELS,'frozen_entries':880,'production_changes':False,'trade_entry_allowed':False}
    fp=sha256(evidence_json(lock).encode()).hexdigest()
    folder=ROOT/'matched_exits'
    if resume(folder,fp,args.resume_existing):
        return
    signals,trades,_=population()
    snapshots={r['id']:r for s in ('BTCUSDT','ETHUSDT') for r in
        read_rows(ROOT/'state'/s/'snapshots.jsonl.gz') if r['stage']=='PRE_ENTRY'}
    clocks={s:load_data('bybit_2023_2025',s,policy)[0][15] for s in ('BTCUSDT','ETHUSDT')}
    bar_indices={s:{c.open_time:i for i,c in enumerate(cs)} for s,cs in clocks.items()}
    exits=defaultdict(list)
    for s in clocks:
        for e in read_rows(BASE/'detection'/s/'enabled/exit_events.jsonl.gz'):
            exits[e['signal_id']].append(e)
    result={model:[] for model in MODELS};undefined=[];checked=0
    for t in sorted(trades,key=lambda r:(r['entry_interval_start'],r['signal_id'])):
        source=deserialize_signal(signals[t['signal_id']])
        start=bar_indices[t['symbol']][datetime.fromisoformat(t['entry_interval_start'])]
        bars=clocks[t['symbol']][start:]
        for model in MODELS:
            spec=exit_spec(source,snapshots[t['signal_id']],model)
            if spec is None:
                undefined.append({'signal_id':t['signal_id'],'model':model,
                    'reason':'NO_DEFINED_CAUSAL_CONTEXTUAL_FTA_OR_RANGE_EXIT', 'trade_entry_allowed':False})
                continue
            prices,fractions=spec
            kwargs={'model': model,'target_prices': prices,'fractions': fractions}
            a=simulate_fixed_trade(t,source,bars,exits[t['signal_id']],**kwargs)
            b=simulate_fixed_trade(t,source,bars,exits[t['signal_id']],mode='SHADOW',**kwargs)
            assert a==b,'Matched exit BACKTEST/SHADOW mismatch'
            if model=='C_CANONICAL':
                assert_baseline(a,t)
            result[model].append(a);checked+=1
        if checked%200<5:
            print('MATCHED_EXIT',t['entry_interval_start'],checked,flush=True)
    folder.mkdir(parents=True)
    write_json(folder/'run_lock.json',lock)
    for model,rows in result.items():
        write_rows(folder/(model+'.jsonl.gz'),rows)
        write_csv(folder/(model+'.csv'),rows)
    write_csv(folder/'undefined_cases.csv',undefined)
    common=set.intersection(*[{r['signal_id'] for r in rs if r['status']=='CLOSED'} for rs in result.values()])
    summary={'models':{name:statistics(rows) for name,rows in result.items()},
        'common_defined_closed_entries':len(common),
        'common_closed_models':{name:statistics([r for r in rows if r['signal_id'] in common]) for name,rows in result.items()},
        'undefined_counts':dict(__import__('collections').Counter(r['model'] for r in undefined)),
        'C_all_880_per_trade_and_fill_baseline_equality':'PASS',
        'BACKTEST_SHADOW_all_models_exact_parity':'PASS','mode_pairs_checked':checked,
        'MODEL_A_EXACT_ORIGINAL':'NOT_IDENTIFIABLE; A diagnostic is one preserved source-permitted alternative',
        'portfolio_limits':'FROZEN_ACTUAL_BASELINE_ADMISSIONS; no reallocation from counterfactual exit outcomes',
        'trade_entry_allowed':False}
    write_json(folder/'summary.json',summary)
    write_csv(folder/'summary.csv',[dict(model=k,**v) for k,v in summary['models'].items()])
    write_json(ROOT/'qa/matched_exit_receipt.json',{k:v for k,v in summary.items() if k not in ['models','common_closed_models']})
    seal(folder,fp,{'cases':checked,'frozen_entries':880,'models':MODELS})
    print('MATCHED_EXITS_COMPLETE',checked,len(common),flush=True)


if __name__=='__main__':
    main()
