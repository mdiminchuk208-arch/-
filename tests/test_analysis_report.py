from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from crypto_bot.analysis_report import write_event_csv, write_structure_transition_csv, write_summary_json, write_sweep_episode_csv, write_trend_state_csv
from crypto_bot.common.models import Candle
from crypto_bot.strategy.market_analysis import analyze_market


class AnalysisReportTests(unittest.TestCase):
    def test_summary_and_events_are_written(self):
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        candles = [
            Candle(base, base + timedelta(minutes=1), 10, 11, 9, 10),
            Candle(base + timedelta(minutes=1), base + timedelta(minutes=2), 10, 13, 9.5, 12),
            Candle(base + timedelta(minutes=2), base + timedelta(minutes=3), 12, 12, 10, 11),
            Candle(base + timedelta(minutes=3), base + timedelta(minutes=4), 11, 13.2, 10.5, 12.8),
        ]
        report = analyze_market(candles)
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            event_path = write_event_csv(report, tmp / "events.csv")
            episode_path = write_sweep_episode_csv(report, tmp / "sweep_episodes.csv")
            state_path = write_trend_state_csv(report, tmp / "trend_states.csv")
            transition_path = write_structure_transition_csv(report, tmp / "structure_transitions.csv")
            summary_path = write_summary_json(report, tmp / "summary.json")
            self.assertTrue(event_path.exists())
            self.assertTrue(state_path.exists())
            self.assertTrue(episode_path.exists())
            self.assertTrue(transition_path.exists())
            self.assertTrue(summary_path.exists())
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["candle_count"], 4)
            self.assertIn("structure_policy", payload)
            self.assertIn("sweep_episode_count", payload)
            self.assertIn("sfp_timeframe_preference", payload)
            self.assertIn("trend_state_candle_counts", payload)
            self.assertIn("longest_broken_run_candles", payload)
            self.assertIn("structure_transition_count", payload)
            self.assertIn("structure_transition_resolution_modes", payload)
            self.assertEqual(payload["order_block_readiness"]["enabled"], False)


    def test_transition_csv_writes_resolved_bos_diagnostic(self):
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        def c(i, o, h, l, cl):
            return Candle(
                base + timedelta(minutes=i), base + timedelta(minutes=i + 1),
                o, h, l, cl,
            )
        candles = [
            c(0, 10, 11, 9.5, 10.2), c(1, 10.2, 10.5, 8, 9),
            c(2, 9, 11, 8.5, 10.4), c(3, 10.4, 12, 9, 11.3),
            c(4, 11.3, 11.5, 9.5, 10.2), c(5, 10.2, 11, 9, 9.6),
            c(6, 9.6, 12, 9.3, 11.2), c(7, 11.2, 13, 10, 12.6),
            c(8, 12.6, 12.7, 10.5, 11.6), c(9, 11.6, 11.9, 8.5, 8.8),
            c(10, 8.8, 9.3, 7.5, 8.0), c(11, 8.0, 9.0, 7.8, 8.5),
            c(12, 8.5, 10.5, 8.0, 10.0), c(13, 10.0, 10.0, 8.2, 8.8),
        ]
        report = analyze_market(candles)
        self.assertTrue(report.structure_transition_diagnostics)
        with tempfile.TemporaryDirectory() as tmp:
            path = write_structure_transition_csv(report, Path(tmp) / "transitions.csv")
            text = path.read_text(encoding="utf-8")
            self.assertIn("EXPECTED_OPPOSITE_FAST_PATH", text)
            self.assertIn("post_bos_high_level_ids", text)


if __name__ == "__main__":
    unittest.main()
