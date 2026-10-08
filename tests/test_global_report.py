from __future__ import annotations

import csv
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from crypto_bot.common.models import Direction
from crypto_bot.global_report import write_global_opportunities_csv, write_global_summary_json
from crypto_bot.strategy.global_opportunity import GlobalOpportunity


class GlobalReportTests(unittest.TestCase):
    def sample(self):
        t = datetime(2026, 1, 1, tzinfo=timezone.utc)
        return (
            GlobalOpportunity(
                global_opportunity_id=1,
                symbol="BTCUSDT",
                expected_direction=Direction.LONG,
                cluster_start_time=t,
                cluster_end_time=t,
                representative_confirmation_time=t,
                pair_labels=("60_to_5", "240_to_15"),
                local_opportunity_ids=("60_to_5#1", "240_to_15#2"),
                context_count=3,
                local_opportunity_count=2,
                cluster_window_minutes=0,
            ),
        )

    def test_global_csv_preserves_pair_references(self):
        with tempfile.TemporaryDirectory() as td:
            path = write_global_opportunities_csv(self.sample(), Path(td) / "g.csv")
            with path.open(encoding="utf-8") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(row["pair_labels"], "60_to_5;240_to_15")
            self.assertEqual(row["trade_entry_allowed"], "False")
            self.assertEqual(row["analysis_mode"], "SOURCE_CONSERVATIVE")

    def test_global_summary_reports_collapsed_count(self):
        with tempfile.TemporaryDirectory() as td:
            path = write_global_summary_json(
                self.sample(), symbol="BTCUSDT", cluster_window_minutes=0,
                pair_local_opportunity_count=2, path=Path(td) / "s.json"
            )
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["global_opportunity_count"], 1)
            self.assertEqual(payload["cross_pair_duplicates_collapsed"], 1)
            self.assertEqual(payload["trade_entry_allowed_count"], 0)
            self.assertEqual(payload["analysis_mode"], "SOURCE_CONSERVATIVE")
