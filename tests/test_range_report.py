import csv
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from crypto_bot.common.models import Candle
from crypto_bot.range_report import (
    write_range_sfp_events_csv,
    write_range_summary_json,
    write_ranges_csv,
)
from crypto_bot.strategy.market_analysis import (
    MarketAnalysisReport,
    MarketEvent,
    MarketEventKind,
    OrderBlockReadiness,
    TrendState,
)
from crypto_bot.strategy.range_engine import RangeDetectionParams
from range_test_support import analyze_ranges

BASE = datetime(2026, 2, 1, tzinfo=timezone.utc)


def c(i, o=105, h=108, l=102, cl=105):
    start = BASE + timedelta(hours=i)
    return Candle(start, start + timedelta(hours=1), o, h, l, cl, True)


def event(kind, i, price, lid):
    return MarketEvent(kind, i, BASE + timedelta(hours=i+1), price, lid, price, "fixture")


def fixture():
    candles = [c(i) for i in range(10)]
    candles[7] = c(7, 106, 112, 104, 109)
    candles[8] = c(8, 108, 109, 103, 106)
    events = (
        event(MarketEventKind.BEARISH_STRUCTURE_BROKEN_BOS, 0, 103, 1),
        event(MarketEventKind.SWING_HIGH_CONFIRMED, 2, 110, 2),
        event(MarketEventKind.SWING_LOW_CONFIRMED, 4, 100, 3),
        event(MarketEventKind.SWING_HIGH_CONFIRMED, 6, 105, 4),
    )
    base = MarketAnalysisReport(
        candle_count=len(candles), final_trend=TrendState.UNKNOWN, levels=(), sweep_episodes=(),
        events=events, order_block_readiness=OrderBlockReadiness(False, "BLOCKED", ("fixture",)),
        structure_policy="fixture", sfp_timeframe_preference="fixture", sfp_policy="fixture",
    )
    params = RangeDetectionParams()
    return analyze_ranges(candles, base, params=params), params


class RangeReportTests(unittest.TestCase):
    def test_csv_exposes_range_and_sfp_provenance(self):
        report, _ = fixture()
        with tempfile.TemporaryDirectory() as td:
            rp = write_ranges_csv(report, Path(td) / "ranges.csv")
            ep = write_range_sfp_events_csv(report, Path(td) / "events.csv")
            with rp.open(encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f))
            with ep.open(encoding="utf-8", newline="") as f:
                events = list(csv.DictReader(f))
            self.assertEqual(rows[0]["midpoint"], "105.0")
            self.assertEqual(events[0]["liquidity_origin"], "RANGE_BOUNDARY")
            self.assertEqual(events[0]["range_id"], "1")

    def test_summary_labels_midpoint_tolerance_as_parameter(self):
        report, params = fixture()
        with tempfile.TemporaryDirectory() as td:
            path = write_range_summary_json(report, params, Path(td) / "summary.json")
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["ever_validated_count"], 1)
            self.assertEqual(data["range_sfp_formation_count"], 1)
            self.assertEqual(data["params"]["midpoint_tolerance_fraction"], 0.08)
            self.assertIn("BACKTEST_PARAMETER", data["midpoint_policy"])
            self.assertIn("SOURCE NUANCE", data["boundary_clarity_policy"])
            self.assertIn("defined area", data["boundary_clarity_policy"])
            self.assertIn("smeared", data["boundary_clarity_policy"])


if __name__ == "__main__":
    unittest.main()
