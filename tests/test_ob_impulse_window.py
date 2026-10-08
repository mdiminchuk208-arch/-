"""An engulfing displacement can CAUSE BOS; it need not occur after BOS.

Source: retained OB_CORE_001 and MS_BOS_001, advanced tools p.2 / structure p.4.
These fixtures regress the erroneous temporal ordering, not entry profitability.
"""
from dataclasses import replace
import unittest

from crypto_bot.common.models import Direction
from crypto_bot.strategy.auto_levels import derive_automatic_levels, ob_impulse_window
from test_auto_levels import valid_case


def move_bos(case, index):
    report=case['ltf_report']
    candle=case['ltf_candles'][index]
    bos=replace(report.events[0],candle_index=index,event_time=candle.close_time,price=candle.close)
    transition=replace(report.structure_transition_diagnostics[0],bos_index=index,bos_time=bos.event_time)
    case['ltf_report']=replace(report,events=(bos,*report.events[1:]),structure_transition_diagnostics=(transition,))
    case['opportunity']=replace(case['opportunity'],ltf_bos_candle_index=index,ltf_bos_event_time=bos.event_time)


class ObImpulseWindowTests(unittest.TestCase):
    def test_engulf_that_causes_bos_is_not_discarded_long_short(self):
        for direction in (Direction.LONG,Direction.SHORT):
            with self.subTest(direction=direction):
                case=valid_case(direction)
                move_bos(case,19)
                result=derive_automatic_levels(**case)
                self.assertEqual(result.status,'READY',result.blocked_reasons)
                evidence=next(e for e in result.evidence if e.kind=='LTF_OB')
                self.assertEqual(dict(evidence.details)['bos_relation'],'BEFORE_OR_AT_BOS')
                self.assertGreaterEqual(evidence.known_at,case['opportunity'].ltf_bos_event_time)

    def test_ob_can_form_before_subsequent_bos_confirmation(self):
        case=valid_case()
        move_bos(case,21)
        result=derive_automatic_levels(**case)
        self.assertEqual(result.status,'READY',result.blocked_reasons)
        evidence=next(e for e in result.evidence if e.kind=='LTF_OB')
        self.assertEqual(evidence.known_at,case['opportunity'].ltf_bos_event_time)

    def test_engulfing_anchor_candle_is_included_in_window(self):
        case=valid_case()
        case['ltf_candles'][19]=replace(case['ltf_candles'][19],high=110,close=109)
        case['ltf_candles'][20]=replace(case['ltf_candles'][20],open=108,high=109)
        report=case['ltf_report']
        anchor=replace(report.levels[3],swing_index=19,confirmed_index=20,
                       swing_time=case['ltf_candles'][19].open_time,
                       confirmed_time=case['ltf_candles'][20].close_time)
        case['ltf_report']=replace(report,levels=(*report.levels[:3],anchor,report.levels[4]))
        result=derive_automatic_levels(**case)
        self.assertEqual(result.status,'READY',result.blocked_reasons)
        self.assertEqual(ob_impulse_window(case['ltf_report'],case['opportunity'],len(case['ltf_candles'])).stop,20)

    def test_candidate_before_actual_impulse_origin_is_excluded(self):
        case=valid_case()
        window=ob_impulse_window(case['ltf_report'],case['opportunity'],len(case['ltf_candles']))
        self.assertEqual(window.start,2)  # A starts at the frozen LL swing index 1.
        self.assertNotIn(1,window)

    def test_missing_causal_origin_is_explicit_rejection(self):
        case=valid_case()
        case['ltf_report']=replace(case['ltf_report'],levels=case['ltf_report'].levels[1:])
        self.assertEqual(derive_automatic_levels(**case).blocked_reasons,('IMPULSE_ORIGIN_REFERENCE_NOT_FOUND',))


if __name__=='__main__':
    unittest.main()
