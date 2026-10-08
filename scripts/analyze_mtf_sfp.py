from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from crypto_bot.analysis_report import write_structure_transition_csv, write_trend_state_csv
from crypto_bot.data.bybit import BybitPublicClient
from crypto_bot.data.qa import audit_klines
from crypto_bot.data.storage import read_klines_csv
from crypto_bot.global_report import (
    write_bos_diagnostic_csv,
    write_bos_inventory_json,
    write_global_opportunities_csv,
    write_global_summary_json,
)
from crypto_bot.mtf_report import (
    write_candidate_quality_audit_csv,
    write_mtf_candidates_csv,
    write_mtf_opportunities_csv,
    write_mtf_summary_json,
)
from crypto_bot.range_report import (
    write_range_sfp_events_csv,
    write_range_sweeps_csv,
    write_range_summary_json,
    write_ranges_csv,
)
from crypto_bot.range_validation_report import (
    write_range_validation_audit_csv,
    write_range_validation_funnel_json,
    write_range_validation_matrix_csv,
)
from crypto_bot.strategy.global_opportunity import cluster_cross_pair_opportunities
from crypto_bot.strategy.market_analysis import MarketAnalysisError, TrendState, StructureAnalysisMode, analyze_market
from crypto_bot.strategy.range_engine import (
    RangeAnalysisError,
    RangeDetectionParams,
    augment_market_report_with_range_sfps,
)
from crypto_bot.strategy.range_validation import (
    build_origin_mtf_funnel,
    build_range_audit_rows,
    build_range_stage_funnel,
    build_range_validation_matrix_row,
    unique_sorted_tolerances,
)
from crypto_bot.strategy.mtf_diagnostics import build_candidate_bos_diagnostics, ltf_bos_inventory
from crypto_bot.strategy.mtf_sfp import MtfSfpError, MtfSfpReport, link_sfp_formations_to_ltf_bos


@dataclass(frozen=True)
class WaitScenario:
    mode: str  # unbounded | bars | minutes
    value: int | None

    @property
    def label(self) -> str:
        if self.mode == "unbounded":
            return "unbounded"
        return f"{self.mode}_{self.value}"


def parse_pair(value: str) -> tuple[str, str]:
    try:
        htf, ltf = value.split(":", 1)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("pair must be HTF:LTF, e.g. 60:5") from exc
    return htf, ltf


def normalize_wait_scenarios(args: argparse.Namespace, parser: argparse.ArgumentParser) -> list[WaitScenario]:
    supplied = sum(
        x is not None
        for x in (
            args.wait_windows,
            args.wait_minutes,
        )
    ) + int(args.max_wait_ltf_bars != 0)
    if supplied > 1:
        parser.error("use only one of --wait-windows, --wait-minutes, or --max-wait-ltf-bars")
    if args.max_wait_ltf_bars < 0:
        parser.error("--max-wait-ltf-bars cannot be negative")

    if args.wait_minutes is not None:
        raw = args.wait_minutes
        if any(x <= 0 for x in raw):
            parser.error("--wait-minutes values must be positive")
        return [WaitScenario("minutes", x) for x in dict.fromkeys(raw)]

    raw_bars = args.wait_windows if args.wait_windows is not None else [args.max_wait_ltf_bars]
    if any(x < 0 for x in raw_bars):
        parser.error("wait windows cannot be negative; 0 means unbounded observational mode")
    result: list[WaitScenario] = []
    for value in raw_bars:
        item = WaitScenario("unbounded", None) if value == 0 else WaitScenario("bars", value)
        if item not in result:
            result.append(item)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Phase-1.4.12: structure transition diagnostics/recovery, state audit, range validation, MTF BOS QA and cross-pair de-duplication."
    )
    parser.add_argument("--analysis-mode", choices=[m.value for m in StructureAnalysisMode], default="SOURCE_CONSERVATIVE")
    parser.add_argument("--symbols", nargs="+", default=["BTCUSDT", "ETHUSDT"])
    parser.add_argument(
        "--pairs",
        nargs="+",
        default=["60:5", "240:15"],
        help="HTF:LTF pairs. Defaults are BACKTEST_PARAMETER conveniences, not source rules.",
    )
    parser.add_argument("--data-root", default="data/history/bybit")
    parser.add_argument("--report-root", default="data/reports/phase1_4_16")
    parser.add_argument(
        "--max-wait-ltf-bars",
        type=int,
        default=0,
        help="Legacy single bar window: 0=unbounded; positive values are BACKTEST_PARAMETER.",
    )
    parser.add_argument(
        "--wait-windows",
        nargs="+",
        type=int,
        default=None,
        help="Compare LTF-bar windows, e.g. 12 24 48. Different LTFs imply different real times.",
    )
    parser.add_argument(
        "--wait-minutes",
        nargs="+",
        type=int,
        default=None,
        help="Compare equal real-time BOS budgets across pairs, e.g. 60 120 240. BACKTEST_PARAMETER.",
    )
    parser.add_argument(
        "--global-cluster-windows",
        nargs="+",
        type=int,
        default=[0, 15, 60],
        help="Cross-pair same-direction de-dup windows in minutes. 0=exact timestamp; positive values are BACKTEST_PARAMETER.",
    )
    parser.add_argument(
        "--evaluation-days",
        type=int,
        default=30,
        help="Count/report candidates only from the last N common days. Older loaded candles remain warm-up context.",
    )
    parser.add_argument(
        "--range-midpoint-tolerance",
        type=float,
        default=0.08,
        help=(
            "BACKTEST_PARAMETER: maximum distance from range 0.5 for a confirmed swing reaction, "
            "as fraction of range width. Default 0.08 is diagnostic, not source-defined."
        ),
    )
    parser.add_argument(
        "--range-midpoint-tolerances",
        nargs="+",
        type=float,
        default=[0.04, 0.06, 0.08, 0.10, 0.12],
        help=(
            "Phase-1.4.6 validation grid for the qualitative 0.5 reaction proxy. Values are "
            "BACKTEST_PARAMETER experiments, not source rules. Default: 0.04 0.06 0.08 0.10 0.12."
        ),
    )
    parser.add_argument(
        "--allow-range-internal-structure",
        action="store_true",
        help=(
            "Diagnostic override only. By default an in-range BOS rejects/invalidates a range because "
            "the source says structure should be absent inside range."
        ),
    )
    parser.add_argument("--show-last", type=int, default=10)
    args = parser.parse_args()
    if args.evaluation_days <= 0:
        parser.error("--evaluation-days must be positive")
    if not (0.0 <= args.range_midpoint_tolerance <= 0.5):
        parser.error("--range-midpoint-tolerance must be within [0, 0.5]")
    try:
        range_validation_tolerances = unique_sorted_tolerances(
            [*args.range_midpoint_tolerances, args.range_midpoint_tolerance]
        )
    except ValueError as exc:
        parser.error(str(exc))
    range_params = RangeDetectionParams(
        midpoint_tolerance_fraction=args.range_midpoint_tolerance,
        require_clean_internal_structure=not args.allow_range_internal_structure,
    )
    if any(x < 0 for x in args.global_cluster_windows):
        parser.error("--global-cluster-windows cannot contain negative values")
    global_cluster_windows = list(dict.fromkeys(args.global_cluster_windows))
    scenarios = normalize_wait_scenarios(args, parser)

    try:
        pairs = [parse_pair(p) for p in args.pairs]
        parsed_pairs = []
        for htf, ltf in pairs:
            htf_ms = BybitPublicClient.interval_ms(htf)
            ltf_ms = BybitPublicClient.interval_ms(ltf)
            htf_min = htf_ms // 60_000
            ltf_min = ltf_ms // 60_000
            if ltf_min >= htf_min:
                raise ValueError(f"LTF must be lower than HTF: {htf}:{ltf}")
            parsed_pairs.append((htf, ltf, htf_ms, ltf_ms, htf_min, ltf_min))
    except (ValueError, argparse.ArgumentTypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    overall_ok = True
    for raw_symbol in args.symbols:
        symbol = raw_symbol.upper()
        scenario_pair_reports: dict[str, list[tuple[str, MtfSfpReport]]] = defaultdict(list)

        for htf, ltf, htf_ms, ltf_ms, htf_min, ltf_min in parsed_pairs:
            pair_label = f"{htf}_to_{ltf}"
            print(f"\n[{symbol}] MTF pair HTF={htf} ({htf_min}m) -> LTF={ltf} ({ltf_min}m)")
            print("  SOURCE POLICY: completed SFP -> lower TF -> wait BOS -> then entry may be searched for.")
            print("  SOURCE INVALIDATION: candle close beyond SFP min/max makes the pattern irrelevant.")
            print("  NOTE: exact HTF:LTF mapping and finite wait budgets are BACKTEST_PARAMETER, not source rules.")
            print(
                "  RANGE: boundary #1=end impulse, boundary #2=end correction, 0.5 reaction validates; "
                "strong impulse is conservatively proxied by structural BOS (TECHNICAL_NORMALIZATION)."
            )
            print(
                "  RANGE QA: non-crisp boundaries may define an area; materially ambiguous boundaries should be skipped. No numeric "
                "clarity rule; boundary clarity remains MANUAL REVIEW / NOT FORMALIZED."
            )

            htf_path = Path(args.data_root) / symbol / f"{htf}.csv"
            ltf_path = Path(args.data_root) / symbol / f"{ltf}.csv"
            if not htf_path.exists() or not ltf_path.exists():
                print(f"  MISSING: {htf_path if not htf_path.exists() else ltf_path}")
                print("  Run fetch_bybit_mtf_history.py first.")
                overall_ok = False
                continue

            htf_rows = read_klines_csv(htf_path)
            ltf_rows = read_klines_csv(ltf_path)
            htf_qa = audit_klines(htf_rows, htf_ms)
            ltf_qa = audit_klines(ltf_rows, ltf_ms)
            print(f"  HTF rows/QA: {len(htf_rows)} / {htf_qa.is_healthy}")
            print(f"  LTF rows/QA: {len(ltf_rows)} / {ltf_qa.is_healthy}")
            if not htf_rows or not ltf_rows:
                print("  ANALYSIS BLOCKED: empty HTF/LTF dataset")
                overall_ok = False
                continue
            if not htf_qa.is_healthy or not ltf_qa.is_healthy:
                print("  ANALYSIS BLOCKED: unhealthy HTF/LTF data")
                overall_ok = False
                continue

            try:
                htf_candles = [c.to_strategy_candle(htf_ms) for c in htf_rows]
                ltf_candles = [c.to_strategy_candle(ltf_ms) for c in ltf_rows]
                base_htf_report = analyze_market(htf_candles, timeframe_minutes=htf_min, analysis_mode=args.analysis_mode)
                htf_report, range_report = augment_market_report_with_range_sfps(
                    htf_candles, base_htf_report, params=range_params
                )
                ltf_report = analyze_market(ltf_candles, timeframe_minutes=ltf_min, analysis_mode=args.analysis_mode)
                htf_first = htf_candles[0].open_time
                htf_last = htf_candles[-1].close_time
                ltf_first = ltf_candles[0].open_time
                ltf_last = ltf_candles[-1].close_time
                common_end = min(htf_last, ltf_last)
                evaluation_start = common_end - timedelta(days=args.evaluation_days)
                loaded_common_start = max(htf_first, ltf_first)
                warmup_seconds = max(0.0, (evaluation_start - loaded_common_start).total_seconds())
                warmup_days = warmup_seconds / 86400.0
            except (MarketAnalysisError, RangeAnalysisError, ValueError) as exc:
                print(f"  ANALYSIS ERROR: {exc}")
                overall_ok = False
                continue

            inventory = ltf_bos_inventory(ltf_report)
            htf_states = htf_report.state_candle_counts()
            ltf_states = ltf_report.state_candle_counts()
            state_dir = Path(args.report_root) / symbol / pair_label / "structure_audit"
            htf_state_path = write_trend_state_csv(htf_report, state_dir / "htf_trend_state_segments.csv")
            ltf_state_path = write_trend_state_csv(ltf_report, state_dir / "ltf_trend_state_segments.csv")
            htf_transition_path = write_structure_transition_csv(
                htf_report, state_dir / "htf_structure_transitions.csv"
            )
            ltf_transition_path = write_structure_transition_csv(
                ltf_report, state_dir / "ltf_structure_transitions.csv"
            )
            print(f"  evaluation window:        last {args.evaluation_days} common day(s)")
            print(f"  warm-up loaded before it: {warmup_days:.2f} day(s) (technical context, not a source rule)")
            print(
                "  LTF BOS inventory (loaded data): "
                f"bullish-break={inventory.bullish_structure_broken_bos}, "
                f"bearish-break={inventory.bearish_structure_broken_bos}"
            )
            print(
                "  HTF structure states:          "
                + ", ".join(f"{k}={v}" for k, v in htf_states.items())
                + f"; longest BROKEN={htf_report.longest_state_run(TrendState.BROKEN)} candles"
            )
            print(
                "  LTF structure states:          "
                + ", ".join(f"{k}={v}" for k, v in ltf_states.items())
                + f"; longest BROKEN={ltf_report.longest_state_run(TrendState.BROKEN)} candles"
            )
            htf_unresolved = sum(1 for x in htf_report.structure_transition_diagnostics if x.resolved_trend is None)
            ltf_unresolved = sum(1 for x in ltf_report.structure_transition_diagnostics if x.resolved_trend is None)
            htf_recovery = sum(
                1 for x in htf_report.structure_transition_diagnostics
                if x.resolution_mode == "SAME_DIRECTION_POST_BOS_RECOVERY"
            )
            ltf_recovery = sum(
                1 for x in ltf_report.structure_transition_diagnostics
                if x.resolution_mode == "SAME_DIRECTION_POST_BOS_RECOVERY"
            )
            print(
                f"  HTF transitions: total={len(htf_report.structure_transition_diagnostics)}, "
                f"unresolved={htf_unresolved}, same-direction-recovery={htf_recovery}"
            )
            print(
                f"  LTF transitions: total={len(ltf_report.structure_transition_diagnostics)}, "
                f"unresolved={ltf_unresolved}, same-direction-recovery={ltf_recovery}"
            )
            print(f"  structure states HTF:      {htf_state_path}")
            print(f"  structure states LTF:      {ltf_state_path}")
            print(f"  transition diagnostics HTF:{htf_transition_path}")
            print(f"  transition diagnostics LTF:{ltf_transition_path}")
            if warmup_days <= 0:
                print("  WARMUP WARNING: no pre-evaluation history is loaded; early structure may be boundary-sensitive.")

            range_sfp_in_eval = [
                e for e in range_report.events
                if e.event_time >= evaluation_start
                and e.kind.value.endswith("SFP_FORMATION_CONFIRMED")
            ]
            print(
                f"  RANGE engine (loaded): candidates={len(range_report.ranges)}, "
                f"ever_validated={range_report.validated_count}, boundary_sfp={range_report.sfp_formation_count}"
            )
            print(
                f"  RANGE boundary SFP in evaluation window: {len(range_sfp_in_eval)} | "
                f"midpoint tolerance={range_params.midpoint_tolerance_fraction:.4f} "
                "(BACKTEST_PARAMETER)"
            )
            range_dir = Path(args.report_root) / symbol / pair_label / "range"
            ranges_path = write_ranges_csv(range_report, range_dir / "ranges.csv")
            range_sweeps_path = write_range_sweeps_csv(range_report, range_dir / "range_sweep_episodes.csv")
            range_events_path = write_range_sfp_events_csv(range_report, range_dir / "range_sfp_events.csv")
            range_summary_path = write_range_summary_json(range_report, range_params, range_dir / "summary.json")
            print(f"  range report:             {ranges_path}")
            print(f"  range sweep episodes:     {range_sweeps_path}")
            print(f"  range SFP events:         {range_events_path}")
            print(f"  range summary:            {range_summary_path}")
            validation_dir = Path(args.report_root) / symbol / pair_label / "range_validation"
            range_audit_rows = build_range_audit_rows(
                range_report,
                evaluation_start=evaluation_start,
                htf_minutes=htf_min,
            )
            range_audit_path = write_range_validation_audit_csv(
                range_audit_rows, validation_dir / "range_validation_audit.csv"
            )
            print(f"  range validation audit:   {range_audit_path}")

            comparison_rows: list[dict[str, object]] = []
            baseline_mtf_by_scenario: dict[str, MtfSfpReport] = {}
            for scenario in scenarios:
                if scenario.mode == "unbounded":
                    print("\n  [WAIT unbounded] observational only; source defines no expiry.")
                    link_kwargs: dict[str, int | None] = {"max_wait_ltf_bars": None, "max_wait_minutes": None}
                    effective_minutes = None
                elif scenario.mode == "bars":
                    effective_minutes = scenario.value * ltf_min  # type: ignore[operator]
                    print(
                        f"\n  [WAIT {scenario.value} LTF bars = {effective_minutes} minutes] "
                        "explicit BACKTEST_PARAMETER experiment"
                    )
                    link_kwargs = {"max_wait_ltf_bars": scenario.value, "max_wait_minutes": None}
                else:
                    effective_minutes = scenario.value
                    print(
                        f"\n  [WAIT {scenario.value} minutes] equal-real-time BACKTEST_PARAMETER experiment"
                    )
                    link_kwargs = {"max_wait_ltf_bars": None, "max_wait_minutes": scenario.value}

                try:
                    mtf = link_sfp_formations_to_ltf_bos(
                        htf_report,
                        ltf_report,
                        htf_minutes=htf_min,
                        ltf_minutes=ltf_min,
                        candidate_not_before=evaluation_start,
                        ltf_observation_start=ltf_first,
                        ltf_observation_end=common_end,
                        **link_kwargs,
                    )
                except MtfSfpError as exc:
                    print(f"    MTF ERROR: {exc}")
                    overall_ok = False
                    continue

                scenario_pair_reports[scenario.label].append((pair_label, mtf))
                baseline_mtf_by_scenario[scenario.label] = mtf
                counts = Counter(c.status.value for c in mtf.candidates)
                origin_counts = Counter((c.htf_liquidity_origin or "UNKNOWN") for c in mtf.candidates)
                print(f"    HTF SFP formations:             {len(mtf.candidates)}")
                print(
                    "    HTF SFP origin:                 "
                    + ", ".join(f"{k}={v}" for k, v in sorted(origin_counts.items()))
                )
                print(f"    invalidated before LTF BOS:     {mtf.invalidated_count}")
                print(f"    LTF BOS confirmed context links:{mtf.confirmed_count:>5}")
                print(f"    unique LTF BOS events:          {mtf.unique_ltf_bos_count}")
                print(f"    shared BOS extra links:         {mtf.shared_bos_link_count} (NOT extra trades)")
                print(f"    pair-local ENTRY_SEARCH opps:   {mtf.opportunity_count}")
                print("    actual trade entries:           0 (intentionally blocked)")
                print(f"    pair-local de-dup scope:         {mtf.opportunity_dedup_scope}")
                print("    Entry Engine blockers:           " + "; ".join(mtf.entry_engine_blocking_reasons))
                structural_funnel = build_origin_mtf_funnel(mtf, "STRUCTURAL_SWING")
                range_funnel = build_origin_mtf_funnel(mtf, "RANGE_BOUNDARY")
                stage_funnel = build_range_stage_funnel(range_report)
                print(
                    "    STRUCTURAL_SWING funnel:          "
                    f"SFP={structural_funnel.sfp_context_count}, invalid={structural_funnel.invalidated_before_bos}, "
                    f"expired={structural_funnel.expired}, BOS={structural_funnel.bos_confirmed_contexts}, "
                    f"opps-with-origin={structural_funnel.opportunities_with_origin_context}"
                )
                print(
                    "    RANGE_BOUNDARY funnel:            "
                    f"ranges={stage_funnel.range_candidate_count} -> validated={stage_funnel.ever_validated_range_count} "
                    f"-> ranges_swept={stage_funnel.ranges_with_boundary_sweep} -> ranges_SFP={stage_funnel.ranges_with_sfp}; "
                    f"eval-SFP={range_funnel.sfp_context_count}, invalid={range_funnel.invalidated_before_bos}, "
                    f"expired={range_funnel.expired}, BOS={range_funnel.bos_confirmed_contexts}, "
                    f"opps-with-origin={range_funnel.opportunities_with_origin_context}"
                )
                funnel_path = write_range_validation_funnel_json(
                    stage=stage_funnel,
                    structural=structural_funnel,
                    range_boundary=range_funnel,
                    midpoint_tolerance_fraction=range_params.midpoint_tolerance_fraction,
                    wait_mode=scenario.mode,
                    wait_value=scenario.value,
                    effective_wait_minutes=effective_minutes,
                    path=validation_dir / f"funnel_wait_{scenario.label}.json",
                )
                print(f"    range/origin funnel:             {funnel_path}")
                comparison_rows.append(
                    {
                        "wait_mode": scenario.mode,
                        "wait_value": "" if scenario.value is None else scenario.value,
                        "effective_wait_minutes": "" if effective_minutes is None else effective_minutes,
                        "candidate_count": len(mtf.candidates),
                        "structural_sfp_count": origin_counts.get("STRUCTURAL_SWING", 0),
                        "range_boundary_sfp_count": origin_counts.get("RANGE_BOUNDARY", 0),
                        "invalidated_before_bos": mtf.invalidated_count,
                        "confirmed_context_links": mtf.confirmed_count,
                        "unique_ltf_bos": mtf.unique_ltf_bos_count,
                        "shared_extra_links": mtf.shared_bos_link_count,
                        "pair_local_opportunities": mtf.opportunity_count,
                        "expired": counts.get("EXPIRED_BY_BACKTEST_PARAMETER", 0),
                        "right_censored": counts.get("RIGHT_CENSORED_BEFORE_DEADLINE", 0),
                        "no_bos_available_data": counts.get("NO_LTF_BOS_IN_AVAILABLE_DATA", 0),
                    }
                )
                for key, value in sorted(counts.items()):
                    print(f"      {key:<35} {value}")

                recent = mtf.candidates[-max(0, args.show_last):] if args.show_last > 0 else ()
                print(f"    last {len(recent)} candidate(s):")
                for c in recent:
                    bos_time = c.ltf_bos_event_time.isoformat() if c.ltf_bos_event_time else "-"
                    invalid_time = c.sfp_invalidation_event_time.isoformat() if c.sfp_invalidation_event_time else "-"
                    origin = c.htf_liquidity_origin or "UNKNOWN"
                    print(
                        f"      {c.htf_sfp_event_time.isoformat()} | {c.expected_direction.value.upper():<5} | "
                        f"{origin:<16} | {c.status.value:<31} | BOS={bos_time} | "
                        f"invalid={invalid_time} | opp={c.opportunity_id or '-'}"
                    )

                report_dir = Path(args.report_root) / symbol / pair_label / f"wait_{scenario.label}"
                csv_path = write_mtf_candidates_csv(mtf, report_dir / "mtf_sfp_candidates.csv")
                opportunity_path = write_mtf_opportunities_csv(mtf, report_dir / "mtf_opportunities.csv")
                audit_path = write_candidate_quality_audit_csv(mtf, report_dir / "candidate_quality_audit.csv")
                summary_path = write_mtf_summary_json(mtf, report_dir / "summary.json")
                diagnostic_rows = build_candidate_bos_diagnostics(mtf, ltf_report)
                diagnostic_path = write_bos_diagnostic_csv(diagnostic_rows, report_dir / "bos_diagnostic.csv")
                inventory_path = write_bos_inventory_json(inventory, report_dir / "ltf_bos_inventory.json")
                print(f"    candidates output:   {csv_path}")
                print(f"    opportunities output:{opportunity_path}")
                print(f"    audit output:        {audit_path}")
                print(f"    BOS diagnostic:      {diagnostic_path}")
                print(f"    BOS inventory:       {inventory_path}")
                print(f"    summary output:      {summary_path}")
                if mtf.confirmed_count == 0:
                    expected_after = sum(r.expected_bos_exists_after_sfp for r in diagnostic_rows)
                    before_invalid = sum(r.expected_bos_before_invalidation for r in diagnostic_rows)
                    print(
                        "    ZERO-CONFIRM QA: expected-direction BOS exists later for "
                        f"{expected_after}/{len(diagnostic_rows)} candidates; before invalidation for {before_invalid}."
                    )
                print("    RESULT: OK")

            comparison_dir = Path(args.report_root) / symbol / pair_label
            comparison_path = comparison_dir / "wait_window_comparison.csv"
            comparison_dir.mkdir(parents=True, exist_ok=True)
            if comparison_rows:
                with comparison_path.open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.DictWriter(handle, fieldnames=list(comparison_rows[0].keys()))
                    writer.writeheader()
                    writer.writerows(comparison_rows)
                print(f"\n  wait-window comparison: {comparison_path}")

            # Phase 1.4.7 range validation grid. Re-run only the range augmentation + MTF gate
            # across explicit midpoint tolerances. This is an experiment matrix, not a source rule.
            matrix_rows = []
            for tolerance in range_validation_tolerances:
                sweep_params = RangeDetectionParams(
                    midpoint_tolerance_fraction=tolerance,
                    require_clean_internal_structure=not args.allow_range_internal_structure,
                )
                if tolerance == range_params.midpoint_tolerance_fraction:
                    sweep_htf_report, sweep_range_report = htf_report, range_report
                else:
                    try:
                        sweep_htf_report, sweep_range_report = augment_market_report_with_range_sfps(
                            htf_candles, base_htf_report, params=sweep_params
                        )
                    except (RangeAnalysisError, ValueError) as exc:
                        print(f"  RANGE VALIDATION ERROR tolerance={tolerance}: {exc}")
                        overall_ok = False
                        continue
                for scenario in scenarios:
                    if scenario.mode == "unbounded":
                        sweep_kwargs: dict[str, int | None] = {"max_wait_ltf_bars": None, "max_wait_minutes": None}
                        effective_minutes = None
                    elif scenario.mode == "bars":
                        sweep_kwargs = {"max_wait_ltf_bars": scenario.value, "max_wait_minutes": None}
                        effective_minutes = scenario.value * ltf_min  # type: ignore[operator]
                    else:
                        sweep_kwargs = {"max_wait_ltf_bars": None, "max_wait_minutes": scenario.value}
                        effective_minutes = scenario.value
                    if (
                        tolerance == range_params.midpoint_tolerance_fraction
                        and scenario.label in baseline_mtf_by_scenario
                    ):
                        sweep_mtf = baseline_mtf_by_scenario[scenario.label]
                    else:
                        try:
                            sweep_mtf = link_sfp_formations_to_ltf_bos(
                                sweep_htf_report,
                                ltf_report,
                                htf_minutes=htf_min,
                                ltf_minutes=ltf_min,
                                candidate_not_before=evaluation_start,
                                ltf_observation_start=ltf_first,
                                ltf_observation_end=common_end,
                                **sweep_kwargs,
                            )
                        except MtfSfpError as exc:
                            print(
                                f"  RANGE VALIDATION MTF ERROR tolerance={tolerance} "
                                f"wait={scenario.label}: {exc}"
                            )
                            overall_ok = False
                            continue
                    matrix_rows.append(
                        build_range_validation_matrix_row(
                            midpoint_tolerance_fraction=tolerance,
                            wait_mode=scenario.mode,
                            wait_value=scenario.value,
                            effective_wait_minutes=effective_minutes,
                            range_report=sweep_range_report,
                            mtf_report=sweep_mtf,
                        )
                    )
            matrix_path = write_range_validation_matrix_csv(
                matrix_rows, validation_dir / "midpoint_tolerance_validation_matrix.csv"
            )
            print(
                "\n  RANGE VALIDATION grid: "
                + ", ".join(f"{x:.4f}" for x in range_validation_tolerances)
                + " (BACKTEST_PARAMETER)"
            )
            print(f"  range validation matrix: {matrix_path}")
            print(
                "  VALIDATION NOTE: do not freeze a tolerance from counts alone; Entry Engine remains blocked "
                "until boundary clarity/lifecycle are formalized and later trade outcome metrics exist."
            )

        # Global cross-pair clustering is performed only after every requested pair for the symbol is analyzed.
        for scenario in scenarios:
            pair_reports = scenario_pair_reports.get(scenario.label, [])
            if not pair_reports:
                continue
            pair_local_total = sum(r.opportunity_count for _, r in pair_reports)
            print(f"\n[{symbol}] GLOBAL cross-pair de-dup for wait={scenario.label}")
            print(f"  pair-local opportunities before global clustering: {pair_local_total}")
            for cluster_window in global_cluster_windows:
                global_opps = cluster_cross_pair_opportunities(
                    symbol,
                    pair_reports,
                    cluster_window_minutes=cluster_window,
                )
                collapsed = pair_local_total - len(global_opps)
                print(
                    f"  cluster {cluster_window:>3} min -> global opportunities={len(global_opps)}, "
                    f"collapsed={collapsed}"
                )
                global_dir = (
                    Path(args.report_root)
                    / symbol
                    / "global"
                    / f"wait_{scenario.label}"
                    / f"cluster_{cluster_window}m"
                )
                csv_path = write_global_opportunities_csv(global_opps, global_dir / "global_opportunities.csv")
                summary_path = write_global_summary_json(
                    global_opps,
                    symbol=symbol,
                    cluster_window_minutes=cluster_window,
                    pair_local_opportunity_count=pair_local_total,
                    path=global_dir / "summary.json",
                )
                print(f"    output: {csv_path}")
                print(f"    summary: {summary_path}")

    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
