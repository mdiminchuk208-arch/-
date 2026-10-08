"""Isolated exit research. Frozen entry/admission/accounting code is inherited."""
from __future__ import annotations

from bisect import bisect_right

from crypto_bot.common.models import Direction
from crypto_bot.strategy.market_analysis import analyze_market
from crypto_bot.strategy.virtual_portfolio import VirtualPortfolio

EXIT_VARIANTS = {
    'A_40_30_30_BE_TP1': ((.4,.3,.3),'TP1'),
    'B_30_30_40_BE_TP1': ((.3,.3,.4),'TP1'),
    'C_25_25_50_BE_TP1': ((.25,.25,.5),'TP1'),
    'D_25_35_40_BE_TP1': ((.25,.35,.4),'TP1'),
    'A_BE_LATER_CLOSE': ((.4,.3,.3),'LATER_CLOSE'),
    'A_ORIGINAL_SL_UNTIL_TP2': ((.4,.3,.3),'TP2'),
    'A_STRUCTURAL_AFTER_TP1': ((.4,.3,.3),'STRUCTURAL'),
}


class ExitResearchPortfolio(VirtualPortfolio):
    """Changes only exit fractions/timing, never permissions or signal generation."""
    def __init__(self,*,variant,history=None,frame_cache=None,**kwargs):
        super().__init__(**kwargs)
        self.variant=variant
        self.allocation,self.be_policy=EXIT_VARIANTS[variant]
        assert abs(sum(self.allocation)-1)<1e-12 and all(f>0 for f in self.allocation)
        self.history=history or {}
        self.clocks={s:[c.close_time for c in cs] for s,cs in self.history.items()}
        self.frame_cache=frame_cache if frame_cache is not None else {}
        self.tp1_times={}

    def _set_be(self,position,candle,reason):
        position.stop_loss=self._breakeven(position)  # unchanged per-unit cost formula
        self.trades[position.signal.signal_id]['new_breakeven']=position.stop_loss
        self._log(candle.close_time,position.signal,'VIRTUAL_STOP_UPDATE',reason,price=position.stop_loss)

    def _structural_ratchet(self,position,candle):
        symbol=position.signal.symbol
        history=self.history[symbol]
        end=bisect_right(self.clocks[symbol],candle.close_time)
        begin=max(0,end-576)
        key=(id(history),begin,end)
        if key not in self.frame_cache:
            self.frame_cache[key]=analyze_market(history[begin:end],timeframe_minutes=position.signal.ltf_minutes)
        report=self.frame_cache[key]
        long=position.signal.direction==Direction.LONG
        candidates=[level for level in report.levels
                    if level.side==('low' if long else 'high')
                    and level.swing_time>self.tp1_times[position.signal.signal_id]
                    and level.confirmed_time<=candle.close_time
                    and level.liquidity_active and level.structure_unbroken
                    and (position.stop_loss<level.price<candle.close if long else candle.close<level.price<position.stop_loss)]
        if candidates:
            level=max(candidates,key=lambda lev:(lev.confirmed_time,lev.swing_time,lev.level_id))
            position.stop_loss=level.price
            self._log(candle.close_time,position.signal,'VIRTUAL_STOP_UPDATE','RESEARCH_STRUCTURAL_TRAIL_NEXT_BAR',price=level.price)

    def _manage(self,position,candle):
        long=position.signal.direction==Direction.LONG
        stop_hit=candle.low<=position.stop_loss if long else candle.high>=position.stop_loss
        if stop_hit:
            reference=min(position.stop_loss,candle.open) if long else max(position.stop_loss,candle.open)
            self._close_fraction(position,position.remaining_fraction,reference,candle.close_time,'STOP_FIRST_CONSERVATIVE')
            return
        for stage,fraction in enumerate(self.allocation):
            if stage<position.tp_stage:
                continue
            target=position.signal.targets[stage]
            hit=candle.high>=target if long else candle.low<=target
            if not hit:
                break
            self._close_fraction(position,fraction,target,candle.close_time,f'TP{stage+1}')
            position.tp_stage=stage+1
            if stage==0:
                self.tp1_times[position.signal.signal_id]=candle.close_time
            transfer=(stage==0 and self.be_policy=='TP1') or (stage==1 and self.be_policy=='TP2')
            if transfer:
                reason='BREAKEVEN_WITH_FEES_AND_SLIPPAGE' if self.be_policy=='TP1' else 'RESEARCH_BREAKEVEN_AFTER_TP2'
                self._set_be(position,candle,reason)
                be_hit=candle.low<=position.stop_loss if long else candle.high>=position.stop_loss
                if be_hit:
                    self._close_fraction(position,position.remaining_fraction,position.stop_loss,candle.close_time,'BREAKEVEN_SAME_BAR_CONSERVATIVE')
                    return
        if position.signal.symbol not in self.positions or position.tp_stage<1:
            return
        if self.be_policy=='LATER_CLOSE' and self.trades[position.signal.signal_id]['new_breakeven'] is None:
            price=self._breakeven(position)
            if self.tp1_times[position.signal.signal_id]<candle.close_time and (candle.close>price if long else candle.close<price):
                self._set_be(position,candle,'RESEARCH_BREAKEVEN_LATER_CLOSE_NEXT_BAR')
        elif self.be_policy=='STRUCTURAL':
            self._structural_ratchet(position,candle)
