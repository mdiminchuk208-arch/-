import csv
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from crypto_bot.range_validation_report import (
    write_range_validation_audit_csv,
    write_range_validation_funnel_json,
    write_range_validation_matrix_csv,
)
from crypto_bot.strategy.range_validation import (
    OriginMtfFunnel,
    RangeAuditRow,
    RangeStageFunnel,
    RangeValidationMatrixRow,
)

BASE = datetime(2026, 4, 1, tzinfo=timezone.utc)


class RangeValidationReportTests(unittest.TestCase):
    def test_audit_csv_preserves_manual_clarity_marker_and_iso_times(self):
        row = RangeAuditRow(
            range_id=1, evaluation_context=True, impulse_direction="UP", impulse_bos_time=BASE,
            first_boundary_kind="high", first_boundary_price=110, first_boundary_time=BASE + timedelta(hours=1),
            second_boundary_kind="low", second_boundary_price=100, second_boundary_time=BASE + timedelta(hours=2),
            lower=100, upper=110, width=10, midpoint=105, status="VALIDATED",
            status_time=BASE + timedelta(hours=3), midpoint_reaction_time=BASE + timedelta(hours=3),
            midpoint_reaction_price=105.5, midpoint_distance_fraction=0.05, internal_bos_count=0,
            upper_boundary_state="ACTIVE", lower_boundary_state="ACTIVE", boundary_sweep_episode_count=1,
            sfp_formation_count=1, first_sfp_time=BASE + timedelta(hours=4), last_sfp_time=BASE + timedelta(hours=4),
            boundary_clarity_review_key="UP-fixture",
            manual_boundary_clarity_review="PASS",
            audit_window_start=BASE - timedelta(hours=12), audit_window_end=BASE + timedelta(hours=28),
        )
        with tempfile.TemporaryDirectory() as td:
            path = write_range_validation_audit_csv((row,), Path(td) / "audit.csv")
            with path.open(encoding="utf-8", newline="") as handle:
                data = list(csv.DictReader(handle))
            self.assertEqual(data[0]["boundary_clarity_review_key"], row.boundary_clarity_review_key)
            self.assertEqual(data[0]["manual_boundary_clarity_review"], "PASS")
            self.assertEqual(data[0]["impulse_bos_time"], BASE.isoformat())

    def test_matrix_and_funnel_writers_keep_no_trade_semantics(self):
        matrix = RangeValidationMatrixRow(
            midpoint_tolerance_fraction=0.08, wait_mode="minutes", wait_value=120,
            effective_wait_minutes=120, range_candidate_count_loaded=10,
            ever_validated_range_count_loaded=5, ranges_with_boundary_sweep_loaded=3,
            boundary_sweep_episode_count_loaded=4, ranges_with_sfp_loaded=2,
            range_sfp_formation_count_loaded=2, range_sfp_context_count_evaluation=2,
            range_invalidated_before_bos=1, range_expired=0, range_right_censored=0,
            range_no_bos_available_data=0, range_coverage_missing=0,
            range_bos_confirmed_contexts=1, opportunities_with_range_context=1,
        )
        stage = RangeStageFunnel(10, 5, 2, 1, 3, 4, 2, 2)
        structural = OriginMtfFunnel("STRUCTURAL_SWING", 20, 10, 5, 0, 1, 0, 4, 4)
        range_origin = OriginMtfFunnel("RANGE_BOUNDARY", 2, 1, 0, 0, 0, 0, 1, 1)
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            matrix_path = write_range_validation_matrix_csv([matrix], td / "matrix.csv")
            funnel_path = write_range_validation_funnel_json(
                stage=stage, structural=structural, range_boundary=range_origin,
                midpoint_tolerance_fraction=0.08, wait_mode="minutes", wait_value=120,
                effective_wait_minutes=120, path=td / "funnel.json",
            )
            with matrix_path.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            payload = json.loads(funnel_path.read_text(encoding="utf-8"))
            self.assertEqual(rows[0]["range_bos_confirmed_contexts"], "1")
            self.assertEqual(payload["interpretation"]["trade_entries_created"], 0)
            self.assertTrue(payload["interpretation"]["range_stage_counts_are_not_all_one_to_one"])


if __name__ == "__main__":
    unittest.main()
