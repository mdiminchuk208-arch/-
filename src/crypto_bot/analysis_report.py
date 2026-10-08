from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from crypto_bot.strategy.market_analysis import MarketAnalysisReport, TrendState


EVENT_FIELDS = [
    "kind",
    "candle_index",
    "event_time",
    "price",
    "level_id",
    "level_price",
    "episode_id",
    "member_level_ids",
    "sfp_pattern_extreme_price",
    "note",
    "recovery_transition_ids",
]


TREND_STATE_SEGMENT_FIELDS = [
    "state",
    "start_index",
    "end_index",
    "start_time",
    "end_time",
    "candle_count",
]


STRUCTURE_TRANSITION_FIELDS = [
    "transition_id",
    "bos_kind",
    "bos_index",
    "bos_time",
    "from_trend",
    "expected_trend",
    "broken_protected_price",
    "broken_extreme_price",
    "resolved_index",
    "resolved_time",
    "resolved_trend",
    "resolution_mode",
    "broken_candles",
    "post_bos_high_level_ids",
    "post_bos_low_level_ids",
    "selected_anchor_level_id",
    "selected_correction_level_id",
    "rejection_reasons",
]

SWEEP_EPISODE_FIELDS = [
    "episode_id",
    "side",
    "sweep_candle_index",
    "sweep_time",
    "member_level_ids",
    "member_level_prices",
    "status",
    "resolved_index",
    "representative_level_id",
    "representative_level_price",
    "valid_sfp_level_ids",
]


def write_event_csv(report: MarketAnalysisReport, path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=EVENT_FIELDS)
        writer.writeheader()
        for event in report.events:
            writer.writerow(
                {
                    "kind": event.kind.value,
                    "candle_index": event.candle_index,
                    "event_time": event.event_time.isoformat(),
                    "price": event.price,
                    "level_id": event.level_id,
                    "level_price": event.level_price,
                    "episode_id": event.episode_id if event.episode_id is not None else "",
                    "member_level_ids": ";".join(str(x) for x in event.member_level_ids),
                    "sfp_pattern_extreme_price": (
                        event.sfp_pattern_extreme_price if event.sfp_pattern_extreme_price is not None else ""
                    ),
                    "note": event.note,
                    "recovery_transition_ids": ";".join(map(str, event.recovery_transition_ids)),
                }
            )
    return destination


def write_summary_json(report: MarketAnalysisReport, path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    counts = Counter(event.kind.value for event in report.events)
    active_high_liquidity = sum(1 for level in report.levels if level.side == "high" and level.liquidity_active)
    active_low_liquidity = sum(1 for level in report.levels if level.side == "low" and level.liquidity_active)
    liquidity_states = Counter(level.liquidity_state.value for level in report.levels)
    episode_statuses = Counter(ep.status.value for ep in report.sweep_episodes)

    payload = {
        "analysis_mode": report.analysis_mode.value,
        "candle_count": report.candle_count,
        "level_count": len(report.levels),
        "event_count": len(report.events),
        "event_counts": dict(sorted(counts.items())),
        "active_structural_liquidity": {
            "highs": active_high_liquidity,
            "lows": active_low_liquidity,
        },
        "liquidity_state_counts": dict(sorted(liquidity_states.items())),
        "sweep_episode_count": len(report.sweep_episodes),
        "sweep_episode_status_counts": dict(sorted(episode_statuses.items())),
        "sfp_timeframe_preference": report.sfp_timeframe_preference,
        "sfp_policy": report.sfp_policy,
        "sfp_liquidity_scope": report.sfp_liquidity_scope,
        "final_trend": report.final_trend.value,
        "trend_state_candle_counts": report.state_candle_counts(),
        "longest_broken_run_candles": report.longest_state_run(TrendState.BROKEN),
        "trend_state_segment_count": len(report.trend_state_segments),
        "structure_transition_count": len(report.structure_transition_diagnostics),
        "unresolved_structure_transition_count": sum(
            1 for item in report.structure_transition_diagnostics if item.resolved_trend is None
        ),
        "max_transition_broken_candles": max(
            (item.broken_candles for item in report.structure_transition_diagnostics), default=0
        ),
        "structure_transition_resolution_modes": dict(
            sorted(Counter(item.resolution_mode for item in report.structure_transition_diagnostics).items())
        ),
        "structure_policy": report.structure_policy,
        "order_block_readiness": {
            "enabled": report.order_block_readiness.enabled,
            "status": report.order_block_readiness.status,
            "blocking_reasons": list(report.order_block_readiness.blocking_reasons),
        },
    }
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return destination


def write_trend_state_csv(report: MarketAnalysisReport, path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=TREND_STATE_SEGMENT_FIELDS)
        writer.writeheader()
        for segment in report.trend_state_segments:
            writer.writerow(
                {
                    "state": segment.state.value,
                    "start_index": segment.start_index,
                    "end_index": segment.end_index,
                    "start_time": segment.start_time.isoformat(),
                    "end_time": segment.end_time.isoformat(),
                    "candle_count": segment.candle_count,
                }
            )
    return destination


def write_sweep_episode_csv(report: MarketAnalysisReport, path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SWEEP_EPISODE_FIELDS)
        writer.writeheader()
        for episode in report.sweep_episodes:
            writer.writerow(
                {
                    "episode_id": episode.episode_id,
                    "side": episode.side,
                    "sweep_candle_index": episode.sweep_candle_index,
                    "sweep_time": episode.sweep_time.isoformat(),
                    "member_level_ids": ";".join(str(x) for x in episode.member_level_ids),
                    "member_level_prices": ";".join(str(x) for x in episode.member_level_prices),
                    "status": episode.status.value,
                    "resolved_index": episode.resolved_index if episode.resolved_index is not None else "",
                    "representative_level_id": (
                        episode.representative_level_id if episode.representative_level_id is not None else ""
                    ),
                    "representative_level_price": (
                        episode.representative_level_price if episode.representative_level_price is not None else ""
                    ),
                    "valid_sfp_level_ids": ";".join(str(x) for x in episode.valid_sfp_level_ids),
                }
            )
    return destination


def write_structure_transition_csv(report: MarketAnalysisReport, path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=STRUCTURE_TRANSITION_FIELDS)
        writer.writeheader()
        for item in report.structure_transition_diagnostics:
            writer.writerow(
                {
                    "transition_id": item.transition_id,
                    "bos_kind": item.bos_kind,
                    "bos_index": item.bos_index,
                    "bos_time": item.bos_time.isoformat(),
                    "from_trend": item.from_trend.value,
                    "expected_trend": item.expected_trend.value,
                    "broken_protected_price": item.broken_protected_price,
                    "broken_extreme_price": (
                        item.broken_extreme_price if item.broken_extreme_price is not None else ""
                    ),
                    "resolved_index": item.resolved_index if item.resolved_index is not None else "",
                    "resolved_time": item.resolved_time.isoformat() if item.resolved_time is not None else "",
                    "resolved_trend": item.resolved_trend.value if item.resolved_trend is not None else "",
                    "resolution_mode": item.resolution_mode,
                    "broken_candles": item.broken_candles,
                    "post_bos_high_level_ids": ";".join(str(x) for x in item.post_bos_high_level_ids),
                    "post_bos_low_level_ids": ";".join(str(x) for x in item.post_bos_low_level_ids),
                    "selected_anchor_level_id": (
                        item.selected_anchor_level_id if item.selected_anchor_level_id is not None else ""
                    ),
                    "selected_correction_level_id": (
                        item.selected_correction_level_id if item.selected_correction_level_id is not None else ""
                    ),
                    "rejection_reasons": ";".join(item.rejection_reasons),
                }
            )
    return destination
