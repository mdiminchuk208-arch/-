"""Independently trace every unique READY limit against actual native 5m OHLC."""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys

from crypto_bot.data.storage import read_klines_csv
from crypto_bot.strategy.source_engine import SourceSignal, sign
from crypto_bot.strategy.source_pdf_cases import deduplicate_cases

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_source_pdf_native_bybit import read_rows, write_json


def audit(root):
    repo=Path(__file__).resolve().parents[1]
    policy=json.loads((root/'run_lock.json').read_text())['policy']
    signals=[];cancels={}
    for folder in sorted((root/'segments').iterdir()):
        for r in read_rows(folder/'signals.jsonl.gz'):
            if [r['htf'],r['ltf']] in policy['mappings']:
                signals.append(SourceSignal(**{**r,'known_at':datetime.fromisoformat(r['known_at']),
                                               'targets':tuple(r['targets']),'fractions':tuple(r['fractions'])}))
        for r in read_rows(folder/'cancellations.jsonl.gz'):
            cancels[r['signal_id']]=datetime.fromisoformat(r['known_at'])
    unique,_=deduplicate_cases(signals,policy['symbol_priority'])
    cases={r['signal_id']:r for r in read_rows(root/'cases.jsonl.gz')}
    data={};rows=[]
    for signal in unique:
        if signal.symbol not in data:
            data[signal.symbol]=[c.to_strategy_candle(300000) for c in read_klines_csv(repo/f'data/history/bybit/{signal.symbol}/5.csv')]
        trace=[];first=None;why='RIGHT_CENSORED';s=sign(signal.direction)
        for c in data[signal.symbol]:
            if c.open_time<signal.known_at:continue
            if signal.signal_id in cancels and cancels[signal.signal_id]<=c.open_time:
                why='KNOWN_SOURCE_CANCELLATION';break
            invalid=s*(c.open-signal.stop)<=0 or s*(signal.targets[0]-c.open)<=0
            touched=c.low<=signal.entry if s==1 else c.high>=signal.entry
            trace.append({'open_time':c.open_time,'close_time':c.close_time,'open':c.open,'high':c.high,
                          'low':c.low,'close':c.close,'invalid_open':invalid,'quote_touched':touched})
            if invalid:why='OPEN_OUTSIDE_SL_FTA';break
            if touched:first=c;why='FILLED';break
        trade=cases.get(signal.signal_id)
        assert (trade is not None)==(first is not None),(signal.signal_id,why)
        if trade is not None:
            assert datetime.fromisoformat(trade['entry_interval_start'])==first.open_time
            assert trade['entry_reference']==signal.entry and trade['stop']==signal.stop
            assert abs(trade['entry']-signal.entry*(1+s*policy['slippage_fraction']))<max(1,signal.entry)*1e-12
            assert not any(r['quote_touched'] for r in trace[:-1])
        elif why=='KNOWN_SOURCE_CANCELLATION':
            assert not any(r['quote_touched'] for r in trace)
        rows.append({'signal_id':signal.signal_id,'symbol':signal.symbol,'mapping':f'{signal.htf}/{signal.ltf}',
                     'READY':signal.known_at,'entry_quote':signal.entry,'stop':signal.stop,'targets':signal.targets,
                     'independent_trace_result':why,'first_valid_touch':first.open_time if first else None,
                     'all_native_intervals_until_terminal_event':trace,'trade_entry_allowed':False})
    summary=json.loads((root/'case_summary.json').read_text())
    assert len(unique)==summary['unique_opportunities'] and len(cases)==summary['FILLED']
    return {'status':'PASS','all_unique_ready_limits_audited':len(rows),'actual_fill_intervals_verified':len(cases),
            'all_real_5m_bars_before_first_touch_or_cancellation_retained':True,'no_occupancy_or_budget_gate':True,
            'scope':'40_NATIVE_BYBIT_SERIES_993575_CANDLES','rows':rows,'trade_entry_allowed':False}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();result=audit(a.input.resolve());write_json(a.output,result)
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
