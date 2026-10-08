"""The automatic source POI must remain in the emitted entry reference."""
import unittest
from crypto_bot.common.models import Direction
from crypto_bot.strategy.auto_levels import derive_automatic_levels, ENTRY_POLICY
from test_auto_levels import valid_case
from test_automatic_lifecycle import histories
from crypto_bot.strategy.historical_replay import indexed_signal_updates
from crypto_bot.strategy.auto_levels import AutoLevelPolicy


class ObEntryReferenceTests(unittest.TestCase):
    def test_long_short_reference_is_ob_ote_intersection_near_edge(self):
        for direction in Direction:
            case=valid_case(direction);result=derive_automatic_levels(**case)
            self.assertEqual(result.status,'READY')
            ob=next(e for e in result.evidence if e.kind=='LTF_OB')
            opp=case['opportunity']
            self.assertEqual(result.execution_zone.low,max(ob.prices[0],opp.entry_zone_low))
            self.assertEqual(result.execution_zone.high,min(ob.prices[1],opp.entry_zone_high))
            expected=result.execution_zone.high if direction==Direction.LONG else result.execution_zone.low
            self.assertEqual(result.entry_reference,expected)
            self.assertEqual(result.entry_policy,ENTRY_POLICY)
            self.assertTrue(any(e.kind=='ENTRY_REFERENCE' for e in result.evidence))

    def test_emitted_signal_keeps_ob_quote_and_zone_instead_of_ote_midpoint(self):
        for direction in Direction:
            signals,_=indexed_signal_updates(histories(direction),symbol='E2E',auto_level_policy=AutoLevelPolicy())
            ready=next(s for s in signals if s.status=='READY_FOR_VIRTUAL_ENTRY')
            ref=next(e for e in ready.level_evidence if e.kind=='ENTRY_REFERENCE')
            self.assertEqual((ready.entry_zone.low,ready.entry_zone.high,ready.optimal_entry),ref.prices)
            self.assertEqual(ready.entry_policy,ENTRY_POLICY)


if __name__=='__main__':
    unittest.main()
