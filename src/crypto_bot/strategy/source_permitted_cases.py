"""Isolated source cases with causal cancellations, honest gaps and ATR exits."""
from __future__ import annotations

import json
from bisect import bisect_left
from datetime import datetime
from math import isfinite

from crypto_bot.strategy.source_pdf_cases import SourceTradeCase
from crypto_bot.strategy.source_pdf_native import evidence_json, sign


class SourcePermittedTradeCase(SourceTradeCase):
    def __init__(self, *args, cancellation_cohort='CANCEL_SOURCE_POI_INVALIDATION', **kwargs):
        super().__init__(*args, **kwargs)
        self.cancellation_cohort=cancellation_cohort

    def _entry(self, signal, c):
        if self.cancellation_cohort=='CANCEL_STRICT_STRUCTURE':
            filled=super()._entry(signal,c)
        else:
            s,p=sign(signal.direction),self.policy
            touched=c.low<=signal.entry if s==1 else c.high>=signal.entry
            if not touched:
                return False
            entry=signal.entry*(1+s*p.slippage_fraction)
            stop_fill=signal.stop*(1-s*p.slippage_fraction)
            unit_risk=s*(entry-stop_fill)+p.fee_rate*(entry+stop_fill)
            if not isfinite(unit_risk) or unit_risk<=0:
                self.cancel(signal.signal_id,c.open_time,'INVALID_FIXED_RISK_GEOMETRY')
                return False
            risk=self.cash*p.risk_fraction
            qty=risk/unit_risk
            fee=qty*entry*p.fee_rate
            trade={'trade_id':signal.signal_id,'signal_id':signal.signal_id,'symbol':signal.symbol,
                   'direction':signal.direction,'htf':signal.htf,'ltf':signal.ltf,
                   'setup_type':signal.setup_type,'poi_type':signal.poi_type,
                   'ready_time':signal.known_at,'entry_time':c.close_time,
                   'entry_interval_start':c.open_time,'entry_interval_end':c.close_time,
                   'entry_time_precision':'REAL_5M_INTERVAL_KNOWN_AT_CLOSE',
                   'entry_reference':signal.entry,'entry':entry,'stop':signal.stop,
                   'targets':list(signal.targets),'fractions':list(signal.fractions),
                   'quantity':qty,'remaining':qty,'risk_amount':risk,'initial_equity':self.cash,
                   'fees':fee,'slippage':qty*abs(entry-signal.entry),'gross_pnl':0.0,
                   'quote_gross_pnl':0.0,'net_pnl':-fee,'fills':[],'status':'OPEN','next_target':0,
                   'evidence':signal.evidence,'exit_policy':signal.evidence['exit_policy'],
                   'trade_entry_allowed':False}
            self.cash-=fee
            self.pending=None
            self.position=trade
            self.trades.append(trade)
            filled=True
        if filled:
            t=self.position
            t['evidence']=json.loads(evidence_json(signal.evidence))
            t['path_id']=signal.evidence['path_id']
            t['physical_opportunity_id']=signal.evidence['physical_opportunity_id']
            t['cancellation_cohort']=self.cancellation_cohort
            t['entry_bar_ohlc']={'open':c.open,'high':c.high,'low':c.low,'close':c.close}
            t['gap_through_original_stop_at_entry']=sign(signal.direction)*(c.open-signal.stop)<=0
            if t['path_id']=='RANGE_AGGRESSIVE_EXTERNAL_POI':
                bounds=signal.evidence['htf_poi']
                actual=c.low<bounds['low'] if signal.direction=='LONG' else c.high>bounds['high']
                if not actual:
                    raise AssertionError('external Range limit filled without actual deviation')
                t['evidence']['actual_range_deviation_at_fill']={'known_at':c.close_time,
                    'interval_start':c.open_time,'low':c.low,'high':c.high,'source':'DOC06 P0111–121'}
        return filled


def instant(value):
    return datetime.fromisoformat(value) if isinstance(value,str) else value


def replay_case(signal,candles,cancellations,exit_events=(),policy=None,
                cancellation_cohort='CANCEL_SOURCE_POI_INVALIDATION'):
    account=SourcePermittedTradeCase(policy,cancellation_cohort=cancellation_cohort)
    account.offer(signal)
    cancels=sorted((r for r in cancellations if r['cohort']==cancellation_cohort),key=lambda r:instant(r['known_at']))
    exits=sorted(exit_events,key=lambda r:instant(r['known_at']))
    cursor=exit_cursor=0
    first=bisect_left(candles,signal.known_at,key=lambda c:c.open_time)
    last=None
    mae=0.0
    for i in range(first,len(candles)):
        c=candles[i]
        while cursor<len(cancels) and instant(cancels[cursor]['known_at'])<=c.open_time:
            r=cancels[cursor]
            account.cancel(signal.signal_id,instant(r['known_at']),r['reason'])
            cursor+=1
        if account.pending is None and account.position is None:
            break
        if account.position:
            t=account.position
            adverse=c.low if signal.direction=='LONG' else c.high
            mae=max(mae,max(0.0,sign(signal.direction)*(t['entry']-adverse))*t['quantity']/t['risk_amount'])
        account.on_bar(signal.symbol,c)
        while exit_cursor<len(exits) and instant(exits[exit_cursor]['known_at'])<=c.close_time:
            r=exits[exit_cursor]
            # Pattern CLOSE proof is usable at this CLOSE, never at its OPEN.
            if account.position and instant(r['known_at'])==c.close_time:
                account._exit(c.close,account.position['remaining']/account.position['quantity'],c.close_time,r['reason'])
            exit_cursor+=1
        last=c.close_time
        if account.trades and account.position is None:
            break
    if account.position:
        account.position['right_censored_at']=last
        account.position['unrealized_pnl']=sign(signal.direction)*(account.last_mark-account.position['entry'])*account.position['remaining']
    if account.pending:
        account.decisions.append({'signal_id':signal.signal_id,'known_at':last or signal.known_at,
                                 'reason':'PENDING_RIGHT_CENSORED','trade_entry_allowed':False})
    for t in account.trades:
        t['max_adverse_excursion_R']=mae if t.get('exit_time')!=t['entry_time'] else None
        t['MAE_method']='POST_ENTRY_BAR_OHLC_UPPER_BOUND; ENTRY_BAR_INTRABAR_ORDER_UNKNOWN'
    return account
