from __future__ import annotations

import csv
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from crypto_bot.common.models import Direction
from crypto_bot.mtf_report import (
    write_candidate_quality_audit_csv,
    write_mtf_candidates_csv,
    write_mtf_opportunities_csv,
    write_mtf_summary_json,
)
from crypto_bot.strategy.market_analysis import MarketEventKind
from crypto_bot.strategy.mtf_sfp import (
    MtfOpportunity,
    MtfOpportunityStatus,
    MtfSfpCandidate,
    MtfSfpReport,
    MtfSfpStatus,
)


class MtfReportTests(unittest.TestCase):
    def sample(self) -> MtfSfpReport:
        t = datetime(2026, 1, 1, tzinfo=timezone.utc)
        candidate = MtfSfpCandidate(
            candidate_id=1,
            htf_minutes=60,
            ltf_minutes=5,
            htf_sfp_kind=MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED,
            htf_sfp_event_time=t,
            htf_sfp_candle_index=10,
            htf_episode_id=2,
            htf_level_id=3,
            htf_level_price=100.0,
            expected_direction=Direction.SHORT,
            expected_ltf_bos_kind=MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS,
            status=MtfSfpStatus.LTF_BOS_CONFIRMED,
            ltf_bos_event_time=t,
            ltf_bos_candle_index=20,
            ltf_bos_level_id=4,
            ltf_bos_level_price=99.0,
            elapsed_ltf_bars=0,
            entry_search_allowed=True,
            trade_entry_allowed=False,
            sfp_invalidation_price=101.0,
            opportunity_id=1,
            note="test",
        )
        opportunity = MtfOpportunity(
            opportunity_id=1,
            status=MtfOpportunityStatus.ENTRY_SEARCH_CANDIDATE,
            expected_direction=Direction.SHORT,
            ltf_bos_kind=MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS,
            ltf_bos_event_time=t,
            ltf_bos_candle_index=20,
            ltf_bos_level_id=4,
            ltf_bos_level_price=99.0,
            candidate_ids=(1,),
            htf_episode_ids=(2,),
            htf_level_ids=(3,),
            earliest_sfp_time=t,
            latest_sfp_time=t,
            representative_candidate_id=1,
            note="one opportunity",
        )
        return MtfSfpReport(
            60,
            5,
            None,
            (candidate,),
            "source",
            "mapping",
            "expiry",
            "entry",
            opportunities=(opportunity,),
            invalidation_policy="invalidate",
            opportunity_policy="cluster",
        )

    def test_csv_writes_trade_entry_blocked_and_opportunity_id(self):
        with tempfile.TemporaryDirectory() as td:
            path = write_mtf_candidates_csv(self.sample(), Path(td) / "c.csv")
            with path.open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["entry_search_allowed"], "True")
            self.assertEqual(rows[0]["trade_entry_allowed"], "False")
            self.assertEqual(rows[0]["opportunity_id"], "1")
            self.assertEqual(rows[0]["sfp_invalidation_price"], "101.0")

    def test_opportunity_csv_is_dedicated_output(self):
        with tempfile.TemporaryDirectory() as td:
            path = write_mtf_opportunities_csv(self.sample(), Path(td) / "o.csv")
            with path.open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["status"], "ENTRY_SEARCH_CANDIDATE")
            self.assertEqual(rows[0]["context_count"], "1")
            self.assertEqual(rows[0]["trade_entry_allowed"], "False")

    def test_audit_csv_contains_invalidation_and_bos_columns(self):
        with tempfile.TemporaryDirectory() as td:
            path = write_candidate_quality_audit_csv(self.sample(), Path(td) / "a.csv")
            with path.open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["sfp_extreme"], "101.0")
            self.assertEqual(rows[0]["opportunity_id"], "1")
            self.assertEqual(rows[0]["shared_opportunity_context_count"], "1")

    def test_summary_has_zero_trade_entries_and_one_dedup_opportunity(self):
        with tempfile.TemporaryDirectory() as td:
            path = write_mtf_summary_json(self.sample(), Path(td) / "s.json")
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["candidate_count"], 1)
            self.assertEqual(payload["entry_search_allowed_link_count"], 1)
            self.assertEqual(payload["trade_entry_allowed_count"], 0)
            self.assertEqual(payload["confirmed_link_count"], 1)
            self.assertEqual(payload["unique_ltf_bos_count"], 1)
            self.assertEqual(payload["shared_bos_link_count"], 0)
            self.assertEqual(payload["opportunity_count"], 1)
            self.assertIn("invalidation_policy", payload)
            self.assertIn("opportunity_policy", payload)


if __name__ == "__main__":
    unittest.main()

class Phase143ScopeTests(unittest.TestCase):
    def test_summary_declares_pair_local_dedup_and_entry_blockers(self):
        base = MtfReportTests().sample()
        with tempfile.TemporaryDirectory() as td:
            path = write_mtf_summary_json(base, Path(td) / "s.json")
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["opportunity_dedup_scope"], "PAIR_LOCAL_EXACT_LTF_BOS")
            self.assertNotIn("GLOBAL_CROSS_PAIR_CLUSTER_PARAMETER_NOT_FROZEN", payload["entry_engine_blocking_reasons"])
            self.assertNotIn("CROSS_ASSET_ROBUSTNESS_NOT_VALIDATED", payload["entry_engine_blocking_reasons"])
            self.assertIn("RANGE_BOUNDARY_SFP_NOT_IMPLEMENTED", payload["entry_engine_blocking_reasons"])
