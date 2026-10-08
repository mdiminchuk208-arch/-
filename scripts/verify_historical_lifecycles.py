"""Independent reconciliation of actual historical virtual fills and accounting.

Checks retained signals against the original Bybit CSV and every monetary fill.
No signal generation, admission, target or historical OHLC is changed.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime
from hashlib import sha256
import json
from math import isclose
from pathlib import Path

from crypto_bot.data.storage import read_klines_csv


def close(a,b):
    if not isclose(a,b,rel_tol=1e-10,abs_tol=1e-8):
        raise AssertionError(('ACCOUNTING_MISMATCH',a,b))


def verify(root, data_root):
    summary=json.loads((root/'summary.json').read_text())
    trades=[json.loads(line) for line in (root/'trades.jsonl').read_text().splitlines()]
    ready=defaultdict(list)
    for line in (root/'signals.jsonl').read_text().splitlines():
        row=json.loads(line)
        assert row['trade_entry_allowed'] is False
        if row['status']=='READY_FOR_VIRTUAL_ENTRY':ready[row['signal_id']].append(row)
    histories={};checks=[];fee=summary['policy']['fee_fraction'];slip=summary['policy']['slippage_fraction']
    for trade in trades:
        symbol=trade['symbol'];key=trade['signal_id'];sign=1 if trade['direction']=='LONG' else -1
        if symbol not in histories:
            path=data_root/symbol/f"{summary['ltf_minutes']}.csv"
            assert sha256(path.read_bytes()).hexdigest()==summary['input_hashes'][f"{symbol}/{summary['ltf_minutes']}.csv"]
            histories[symbol]={c.open_time.isoformat():c for row in read_klines_csv(path)
                               if (c:=row.to_strategy_candle(summary['ltf_minutes']*60000))}
        candle=histories[symbol][trade['entry_interval_start']]
        signal=max((s for s in ready[key] if datetime.fromisoformat(s['event_time'])<=candle.open_time),key=lambda s:s['event_time'])
        assert datetime.fromisoformat(signal['levels_known_at'])<=datetime.fromisoformat(signal['event_time'])
        assert datetime.fromisoformat(signal['entry_geometry_ready_time'])<=datetime.fromisoformat(signal['event_time'])
        zone=signal['entry_zone'];ob=next(e for e in signal['level_evidence'] if e['kind']=='LTF_OB')
        assert ob['prices'][0]<=zone['low']<=zone['high']<=ob['prices'][1]
        reference=trade['theoretical_entry']
        if trade['fill_model']=='RESTING_LIMIT_TOUCH':
            close(reference,signal['optimal_entry'])
            assert sign*(candle.open-reference)>0 and candle.low<=reference<=candle.high
            assert trade['entry_time']==candle.close_time.isoformat()
        else:
            close(reference,candle.open)
            assert zone['low']<=reference<=zone['high']
            assert sign*(reference-signal['optimal_entry'])<=0
        close(trade['actual_entry_after_slippage'],reference*(1+sign*slip))
        entry=trade['actual_entry_after_slippage'];quantity=trade['quantity']
        close(trade['entry_fee'],quantity*entry*fee)
        close(trade['risk_amount'],trade['initial_equity']*trade['risk_percent'])
        assert trade['aggregate_risk_fraction_after']<=0.06+1e-10
        for fill in trade['fills']:
            q=fill['quantity'];exit_price=fill['price']
            close(exit_price,fill['reference_price']*(1-sign*slip))
            close(fill['gross_pnl'],q*sign*(exit_price-entry))
            close(fill['entry_fee_allocation'],trade['entry_fee']*q/quantity)
            close(fill['exit_fee'],q*exit_price*fee)
            close(fill['net_pnl'],fill['gross_pnl']-fill['entry_fee_allocation']-fill['exit_fee'])
            close(fill['balance_change'],fill['gross_pnl']-fill['exit_fee'])
            assert fill['trade_entry_allowed'] is False
        close(trade['gross_pnl'],sum(f['gross_pnl'] for f in trade['fills']))
        close(trade['net_pnl'],sum(f['net_pnl'] for f in trade['fills']))
        close(trade['fees_total'],trade['entry_fee']+sum(f['exit_fee'] for f in trade['fills']))
        if trade['status']=='CLOSED':
            close(sum(f['quantity'] for f in trade['fills']),quantity)
            close(trade['result_R'],trade['net_pnl']/trade['risk_amount'])
        checks.append(dict(signal_id=key,symbol=symbol,direction=trade['direction'],
            ready_time=signal['event_time'],entry_time=trade['entry_time'],entry_interval_start=trade['entry_interval_start'],
            actual_ohlc=[candle.open,candle.high,candle.low,candle.close],reference=reference,
            status=trade['status'],exit_reason=trade.get('exit_reason'),
            fills=[f['reason'] for f in trade['fills']],net_pnl=trade['net_pnl'],
            exact_source_ohlc_touch=True,risk_and_accounting='PASS'))
    close(summary['portfolio']['balance']-summary['initial_capital'],
          sum(-t['entry_fee']+sum(f['balance_change'] for f in t['fills']) for t in trades))
    close(summary['portfolio']['fees_paid'],sum(t['fees_total'] for t in trades))
    return dict(run=str(root),htf=summary['htf_minutes'],ltf=summary['ltf_minutes'],
        ready=len(ready),entries=len(trades),closed=sum(t['status']=='CLOSED' for t in trades),
        directions=dict(Counter(t['direction'] for t in trades)),
        exit_reasons=dict(Counter(t.get('exit_reason','OPEN') for t in trades)),
        fill_reasons=dict(Counter(f['reason'] for t in trades for f in t['fills'])),
        accounting='PASS',real_ohlc_entry_validation='PASS',trade_entry_allowed=False,checks=checks)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runs',type=Path,nargs='+',required=True)
    p.add_argument('--data-root',type=Path,default=Path('data/history/bybit'))
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();results=[verify(root,args.data_root) for root in args.runs]
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(results,sort_keys=True,indent=2)+'\n')
    for r in results:print(r['htf'],r['ltf'],r['entries'],'actual fills;',r['directions'],'accounting PASS')


if __name__=='__main__':main()
