"""Constructed source lifecycle counterexamples, never performance evidence."""
import unittest
from dataclasses import replace
from datetime import timedelta

from crypto_bot.strategy.source_pdf_native import Raid
from crypto_bot.strategy.source_permitted import Context, SourceContextZone
from crypto_bot.strategy.source_permitted_cases import replay_case
from crypto_bot.strategy.source_sfp_lifecycle import repair_sfp_candidates
from tests.test_source_engine import START, candle
from tests.test_source_permitted import fixture


def ready(minutes=5):
    e,_,_,now=fixture()
    p=SourceContextZone('sfp','SFP','LONG',90,106,START,START,0,
        Raid('LONG',START,96,90,0,('SWING:old',),True),90,130)
    e._conservative(Context(60,5,p,START,1,'sfp'),now)
    r=e.signals[0]
    return replace(r,known_at=START+timedelta(minutes=minutes),
        evidence={**r.evidence,'structural_thesis':{**r.evidence['structural_thesis'],'protected':102}})


def hour(i,close,low=88):
    return replace(candle(i,105,106,low,close),open_time=START+timedelta(hours=i),
                   close_time=START+timedelta(hours=i+1))


class SfpSourceLifecycleTests(unittest.TestCase):
    def test_former_opposite_bos_level_is_not_new_protected_hl(self):
        r=ready();native={('BTCUSDT',5):[candle(1,103,104,97,98.5)],('BTCUSDT',60):[hour(0,101)]}
        valid,_,c=repair_sfp_candidates([r],native)
        self.assertEqual(len(valid),1);self.assertIsNone(valid[0].evidence['structural_thesis'])
        self.assertEqual(c,[])
        self.assertEqual(valid[0].evidence['former_BOS_broken_level_not_new_protected_key']['protected'],102)

    def test_body_invalid_before_ready_rejects_even_after_later_reclaim(self):
        r=ready(65);native={('BTCUSDT',5):[],('BTCUSDT',60):[hour(0,89),hour(1,105)]}
        valid,q,_=repair_sfp_candidates([r],native)
        self.assertEqual(valid,[]);self.assertEqual(q[0]['status'],'REJECT_SFP_INVALID_BEFORE_READY')
        self.assertEqual(q[0]['source_body_invalidation_known_at'],START+timedelta(hours=1))

    def test_future_native_body_cannot_reject_past_ready(self):
        r=ready();native={('BTCUSDT',5):[],('BTCUSDT',60):[hour(0,89)]}
        valid,q,c=repair_sfp_candidates([r],native)
        self.assertEqual(len(valid),1);self.assertIsNone(q[0]['source_body_invalidation_known_at'])
        self.assertEqual(c[0]['known_at'],START+timedelta(hours=1))

    def test_wick_only_does_not_become_pattern_body_failure(self):
        r=ready(65);native={('BTCUSDT',5):[],('BTCUSDT',60):[hour(0,101,85)]}
        valid,_,c=repair_sfp_candidates([r],native)
        self.assertEqual(len(valid),1);self.assertEqual(c,[])

    def test_local_body_known_after_real_quote_fill_cannot_erase_case(self):
        r=ready();cs=[candle(1,103,104,99,103),candle(2,103,104,94,94.5),candle(3,94.5,122,94,121)]
        native={('BTCUSDT',5):cs,('BTCUSDT',60):[hour(0,89)]}
        valid,_,c=repair_sfp_candidates([r],native)
        a=replay_case(valid[0],cs,c)
        self.assertEqual(len(a.trades),1)
        self.assertEqual(a.trades[0]['entry_interval_start'],cs[0].open_time)
        self.assertGreater(c[0]['known_at'],cs[0].open_time)
        self.assertEqual(a.trades[0]['status'],'CLOSED')
