from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from crypto_bot.common.models import Direction
from crypto_bot.data.models import MarketCandle
from crypto_bot.strategy.causal_objects import CausalSourceObject, SourceObjectType
from crypto_bot.strategy.pure_source_runtime import PureSourceRuntime
from crypto_bot.strategy.pure_source_replay_v2 import (
    ReplayEvidenceBatch,
    ReplayExecutionAssessment,
    ReplayFrame,
    ReplaySeries,
    StructureLiquidityReplayProvider,
    compare_replay_prefixes,
    run_pure_source_replay,
)
from crypto_bot.strategy.source_execution_v2 import (
    EntryMode,
    EntryOption,
    ExecutionPlanAssessment,
    ExitMode,
    ExitPolicy,
    SourceExecutionPlan,
    StopMode,
    StopOption,
)
from crypto_bot.strategy.source_setup_v2 import (
    SetupAssemblyAssessment,
    SetupBranch,
    SourceSetupEvidence,
)
from crypto_bot.strategy.source_structure_liquidity_v2 import EvidenceStatus

UTC = timezone.utc
BASE = datetime(2026, 1, 1, tzinfo=UTC)
BASE_MS = int(BASE.timestamp() * 1000)
EXCHANGE = "TEST"
SYMBOL = "BTCUSDT"


def market_candle(
    *,
    interval_ms: int,
    index: int,
    interval: str,
    center: float,
    high: float | None = None,
    low: float | None = None,
) -> MarketCandle:
    open_price = center
    close_price = center
    high_price = high if high is not None else center + 1.0
    low_price = low if low is not None else center - 1.0
    return MarketCandle(
        exchange=EXCHANGE,
        symbol=SYMBOL,
        interval=interval,
        open_time_ms=BASE_MS + interval_ms * index,
        open=open_price,
        high=high_price,
        low=low_price,
        close=close_price,
        volume_base=100 + index,
        turnover_quote=1000 + index,
        is_closed=True,
    )


def series(
    timeframe: str,
    interval_ms: int,
    count: int,
    *,
    centers: tuple[float, ...] | None = None,
) -> ReplaySeries:
    if centers is None:
        centers = tuple(100.0 + index for index in range(count))
    candles = tuple(
        market_candle(
            interval_ms=interval_ms,
            index=index,
            interval=timeframe,
            center=centers[index],
        )
        for index in range(count)
    )
    return ReplaySeries(timeframe, interval_ms, candles)


class RecordingProvider:
    provider_id = "TEST_RECORDING_PROVIDER"
    provider_version = "1"

    def __init__(self) -> None:
        self.frames: list[ReplayFrame] = []

    def produce(self, frame: ReplayFrame) -> ReplayEvidenceBatch:
        self.frames.append(frame)
        for item in frame.series:
            self.assert_prefix_safe(frame, item.candles)
        return ReplayEvidenceBatch()

    @staticmethod
    def assert_prefix_safe(frame: ReplayFrame, candles: tuple) -> None:
        if any(candle.close_time > frame.decision_at for candle in candles):
            raise AssertionError("provider received future candle")


class TopologyProvider:
    provider_id = "TEST_TOPOLOGY_PROVIDER"
    provider_version = "1"

    def produce(self, frame: ReplayFrame) -> ReplayEvidenceBatch:
        parent = CausalSourceObject.formed(
            object_type=SourceObjectType.SWING,
            symbol=frame.symbol,
            timeframe="1m",
            direction=Direction.LONG.value,
            formation_at=frame.decision_at,
            known_at=frame.decision_at,
            identity_parts={"kind": "parent", "at": frame.decision_at},
            source_rule_ids=("TEST_PARENT",),
            provenance="Stage-10 topology fixture",
        )
        child = CausalSourceObject.formed(
            object_type=SourceObjectType.LIQUIDITY_POOL,
            symbol=frame.symbol,
            timeframe="1m",
            direction=Direction.LONG.value,
            formation_at=frame.decision_at,
            known_at=frame.decision_at,
            identity_parts={"kind": "child", "parent": parent.object_id},
            source_rule_ids=("TEST_CHILD",),
            parent_object_ids=(parent.object_id,),
            provenance="Stage-10 topology fixture",
        )
        # Intentionally child-first: adapter must topologically register it.
        return ReplayEvidenceBatch(objects=(child, parent))


class MissingParentProvider:
    provider_id = "TEST_MISSING_PARENT_PROVIDER"
    provider_version = "1"

    def produce(self, frame: ReplayFrame) -> ReplayEvidenceBatch:
        child = CausalSourceObject.formed(
            object_type=SourceObjectType.LIQUIDITY_POOL,
            symbol=frame.symbol,
            timeframe="1m",
            direction=None,
            formation_at=frame.decision_at,
            known_at=frame.decision_at,
            identity_parts={"kind": "orphan"},
            source_rule_ids=("TEST_CHILD",),
            parent_object_ids=("missing-parent-id",),
            provenance="Stage-10 orphan fixture",
        )
        return ReplayEvidenceBatch(objects=(child,))


class FutureObjectProvider:
    provider_id = "TEST_FUTURE_OBJECT_PROVIDER"
    provider_version = "1"

    def produce(self, frame: ReplayFrame) -> ReplayEvidenceBatch:
        later_known_at = frame.decision_at + timedelta(minutes=1)
        obj = CausalSourceObject.formed(
            object_type=SourceObjectType.POI,
            symbol=frame.symbol,
            timeframe="1m",
            direction=Direction.LONG.value,
            formation_at=later_known_at,
            known_at=later_known_at,
            identity_parts={"fixture": "later-known-object", "at": later_known_at},
            source_rule_ids=("TEST_FUTURE",),
            provenance="Stage-10 future leakage fixture",
        )
        return ReplayEvidenceBatch(objects=(obj,))


class SetupExecutionProvider:
    provider_id = "TEST_STAGE7_STAGE8_WIRING_PROVIDER"
    provider_version = "1"

    def produce(self, frame: ReplayFrame) -> ReplayEvidenceBatch:
        prefix = frame.series_for("1m")
        context_known = prefix.candles[0].close_time
        context = CausalSourceObject.formed(
            object_type=SourceObjectType.ORDER_BLOCK,
            symbol=frame.symbol,
            timeframe="1m",
            direction=Direction.LONG.value,
            formation_at=context_known,
            known_at=context_known,
            identity_parts={"fixture": "context"},
            source_rule_ids=("TEST_CONTEXT",),
            provenance="Stage-10 synthetic context",
        )
        if len(prefix.candles) < 2:
            return ReplayEvidenceBatch(objects=(context,))

        setup_known = prefix.candles[1].close_time
        physical = CausalSourceObject.formed(
            object_type=SourceObjectType.PHYSICAL_IDEA,
            symbol=frame.symbol,
            timeframe="1m",
            direction=Direction.LONG.value,
            formation_at=context_known,
            known_at=context_known,
            identity_parts={"fixture": "physical", "context": context.object_id},
            source_rule_ids=("TEST_PHYSICAL",),
            parent_object_ids=(context.object_id,),
            provenance="Stage-10 synthetic physical idea",
        )
        setup = CausalSourceObject.formed(
            object_type=SourceObjectType.SETUP,
            symbol=frame.symbol,
            timeframe="1m",
            direction=Direction.LONG.value,
            formation_at=setup_known,
            known_at=setup_known,
            identity_parts={"fixture": "setup", "physical": physical.object_id},
            source_rule_ids=("TEST_SETUP",),
            parent_object_ids=(physical.object_id, context.object_id),
            provenance="Stage-10 synthetic setup",
        )
        evidence = SourceSetupEvidence(
            physical_idea=physical,
            setup=setup,
            branch=SetupBranch.OB_DIRECT_FIRST_TEST,
            direction=Direction.LONG,
            context_object_id=context.object_id,
            known_at=setup_known,
            evidence_ids=(),
        )
        setup_assessment = SetupAssemblyAssessment(
            EvidenceStatus.PASS,
            "TEST_SETUP_ASSEMBLED",
            evidence,
        )
        plan = SourceExecutionPlan(
            setup_id=setup.object_id,
            physical_idea_id=physical.object_id,
            branch=evidence.branch,
            direction=evidence.direction,
            known_at=setup_known,
            entry_options=(
                EntryOption(
                    EntryMode.OB_BOUNDARY_LIMIT,
                    99.0,
                    100.0,
                    100.0,
                    True,
                    ("TEST_ENTRY",),
                    "synthetic exact entry",
                ),
            ),
            stop_options=(
                StopOption(
                    StopMode.OB_BEYOND_ZONE_EXTREME,
                    "BELOW",
                    99.0,
                    98.0,
                    True,
                    ("TEST_STOP",),
                    "synthetic exact stop",
                ),
            ),
            exit_policy=ExitPolicy(
                ExitMode.FTA_FULL_OR_PARTIAL,
                1.0,
                0.0,
                110.0,
                (),
                None,
                ("TEST_TARGET",),
            ),
            invalidation_rules=(),
            unresolved=(),
            source_rule_ids=("TEST_ENTRY", "TEST_STOP", "TEST_TARGET"),
            trade_entry_allowed=False,
        )
        execution = ReplayExecutionAssessment(
            ExecutionPlanAssessment(EvidenceStatus.PASS, "TEST_EXECUTION_READY", plan),
            setup_id=setup.object_id,
        )
        return ReplayEvidenceBatch(
            objects=(context,),
            setup_assessments=(setup_assessment,),
            execution_assessments=(execution,),
        )


class PureSourceReplayTests(unittest.TestCase):
    def test_provider_receives_only_closed_prefixes(self):
        provider = RecordingProvider()
        result = run_pure_source_replay((series("1m", 60_000, 4),), provider)
        self.assertEqual(len(provider.frames), 4)
        self.assertEqual(
            [len(frame.series_for("1m").candles) for frame in provider.frames],
            [1, 2, 3, 4],
        )
        self.assertEqual(result.runtime_summary["trade_entry_allowed"], False)
        self.assertNotIn("dataset_sha256", ReplayFrame.__dataclass_fields__)
        self.assertNotIn("total_candles", ReplayFrame.__dataclass_fields__)

    def test_same_close_multitimeframe_is_visible_together(self):
        provider = RecordingProvider()
        one_minute = series("1m", 60_000, 6)
        five_minute = series("5m", 300_000, 2)
        run_pure_source_replay((five_minute, one_minute), provider)
        five_close = BASE + timedelta(minutes=5)
        frame = next(item for item in provider.frames if item.decision_at == five_close)
        self.assertEqual(len(frame.series_for("1m").candles), 5)
        self.assertEqual(len(frame.series_for("5m").candles), 1)
        self.assertEqual(len(frame.series_for("1m").newly_closed), 1)
        self.assertEqual(len(frame.series_for("5m").newly_closed), 1)
        self.assertEqual([item.timeframe for item in frame.series], ["1m", "5m"])

    def test_manifest_is_deterministic_independent_of_input_series_order(self):
        first = series("1m", 60_000, 5)
        second = series("5m", 300_000, 2)
        left = run_pure_source_replay((first, second), RecordingProvider())
        right = run_pure_source_replay((second, first), RecordingProvider())
        self.assertEqual(left.manifest.dataset_sha256, right.manifest.dataset_sha256)
        self.assertEqual(left.receipts, right.receipts)

    def test_gap_is_rejected_before_provider_runs(self):
        interval_ms = 60_000
        candles = (
            market_candle(interval_ms=interval_ms, index=0, interval="1m", center=100),
            market_candle(interval_ms=interval_ms, index=2, interval="1m", center=102),
        )
        provider = RecordingProvider()
        with self.assertRaisesRegex(ValueError, "unhealthy replay data"):
            run_pure_source_replay(
                (ReplaySeries("1m", interval_ms, candles),), provider
            )
        self.assertEqual(provider.frames, [])

    def test_topological_market_object_registration(self):
        result = run_pure_source_replay((series("1m", 60_000, 1),), TopologyProvider())
        self.assertEqual(result.runtime_summary["causal_object_count"], 2)
        self.assertEqual(result.receipts[-1].causal_object_count, 2)

    def test_missing_parent_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "unresolved/cyclic causal parentage"):
            run_pure_source_replay((series("1m", 60_000, 1),), MissingParentProvider())

    def test_future_object_is_rejected_by_runtime(self):
        runtime = PureSourceRuntime(SYMBOL)
        with patch(
            "crypto_bot.strategy.pure_source_replay_v2.PureSourceRuntime",
            return_value=runtime,
        ):
            with patch.object(
                runtime, "register_object", wraps=runtime.register_object
            ) as register:
                with self.assertRaises(ValueError):
                    run_pure_source_replay(
                        (series("1m", 60_000, 1),), FutureObjectProvider()
                    )
        register.assert_called_once()
        self.assertGreater(
            register.call_args.args[0].known_at,
            register.call_args.kwargs["observed_at"],
        )
        self.assertEqual(runtime.finish()["causal_object_count"], 0)

    def test_interval_metadata_cannot_silently_disagree(self):
        for timeframe, interval_ms, market_interval in (
            ("1m", 60_000, "5m"),
            ("5m", 60_000, "1m"),
            ("5", 60_000, "1"),
            ("H1", 60_000, "M1"),
        ):
            with self.subTest(timeframe=timeframe, market_interval=market_interval):
                candle = market_candle(
                    interval_ms=interval_ms,
                    index=0,
                    interval=market_interval,
                    center=100,
                )
                with self.assertRaisesRegex(ValueError, "does not match"):
                    ReplaySeries(timeframe, interval_ms, (candle,))

    def test_equivalent_exchange_interval_aliases_are_accepted(self):
        for timeframe, interval_ms, market_interval in (
            ("5m", 300_000, "5"),
            ("H1", 3_600_000, "60"),
            ("1d", 86_400_000, "D"),
        ):
            with self.subTest(timeframe=timeframe, market_interval=market_interval):
                candle = market_candle(
                    interval_ms=interval_ms,
                    index=0,
                    interval=market_interval,
                    center=100,
                )
                result = run_pure_source_replay(
                    (ReplaySeries(timeframe, interval_ms, (candle,)),),
                    RecordingProvider(),
                )
                self.assertEqual(len(result.receipts), 1)

    def test_unsupported_or_nonfixed_intervals_fail_closed(self):
        for label in ("W", "M", "1M", "0", "0m", "garbage"):
            for market_interval, timeframe in ((label, "1m"), ("1m", label)):
                with self.subTest(market_interval=market_interval, timeframe=timeframe):
                    candle = market_candle(
                        interval_ms=60_000,
                        index=0,
                        interval=market_interval,
                        center=100,
                    )
                    with self.assertRaisesRegex(ValueError, "unsupported fixed"):
                        ReplaySeries(timeframe, 60_000, (candle,))

    def test_parent_cannot_be_known_later_than_child(self):
        class LateParentProvider:
            provider_id = "TEST_LATE_PARENT"
            provider_version = "1"

            def __init__(self, separate_frames):
                self.separate_frames = separate_frames

            def produce(self, frame):
                first = BASE + timedelta(minutes=1)
                parent = CausalSourceObject.formed(
                    object_type=SourceObjectType.SWING,
                    symbol=SYMBOL,
                    timeframe="1m",
                    direction=None,
                    formation_at=first,
                    known_at=first + timedelta(minutes=1),
                    identity_parts={"fixture": "later-known-parent"},
                    source_rule_ids=("TEST_PARENT",),
                    provenance="Stage-10 parent chronology regression",
                )
                child = CausalSourceObject.formed(
                    object_type=SourceObjectType.LIQUIDITY_POOL,
                    symbol=SYMBOL,
                    timeframe="1m",
                    direction=None,
                    formation_at=first,
                    known_at=first,
                    identity_parts={"fixture": "earlier-known-child"},
                    source_rule_ids=("TEST_CHILD",),
                    parent_object_ids=(parent.object_id,),
                    provenance="Stage-10 child chronology regression",
                )
                if frame.decision_at < parent.known_at:
                    return ReplayEvidenceBatch()
                if self.separate_frames and frame.decision_at == parent.known_at:
                    return ReplayEvidenceBatch(objects=(parent,))
                return ReplayEvidenceBatch(
                    objects=(child,) if self.separate_frames else (child, parent)
                )

        for separate_frames in (False, True):
            with self.subTest(separate_frames=separate_frames):
                with self.assertRaisesRegex(ValueError, "causal parent known_at"):
                    run_pure_source_replay(
                        (series("1m", 60_000, 3),), LateParentProvider(separate_frames)
                    )

    def test_prefix_comparison_rejects_other_provider_or_version(self):
        original = run_pure_source_replay(
            (series("1m", 60_000, 2),), RecordingProvider()
        )
        for field, value, reason in (
            ("provider_id", "OTHER_PROVIDER", "PROVIDER_ID_MISMATCH"),
            ("provider_version", "2", "PROVIDER_VERSION_MISMATCH"),
            ("version", "OTHER_REPLAY_VERSION", "REPLAY_VERSION_MISMATCH"),
        ):
            with self.subTest(field=field):
                comparison = compare_replay_prefixes(
                    original,
                    replace(original, **{field: value}),
                    through=BASE + timedelta(minutes=2),
                )
                self.assertFalse(comparison.equal)
                self.assertEqual(comparison.reason, reason)

    def test_unversioned_provider_is_rejected_before_producing_evidence(self):
        provider = RecordingProvider()
        provider.provider_version = ""
        with self.assertRaisesRegex(ValueError, "provider_version"):
            run_pure_source_replay((series("1m", 60_000, 1),), provider)
        self.assertEqual(provider.frames, [])

    def test_independently_truncated_data_matches_full_replay_prefix(self):
        data = series("1m", 60_000, 8)
        full = run_pure_source_replay((data,), StructureLiquidityReplayProvider())
        truncated = run_pure_source_replay(
            (replace(data, candles=data.candles[:5]),),
            StructureLiquidityReplayProvider(),
        )
        comparison = compare_replay_prefixes(
            full, truncated, through=BASE + timedelta(minutes=5)
        )
        self.assertTrue(comparison.equal)
        self.assertEqual(comparison.compared_steps, 5)
        self.assertNotEqual(
            full.manifest.dataset_sha256, truncated.manifest.dataset_sha256
        )

    def test_stage7_stage8_stage9_wiring_keeps_live_permission_false(self):
        result = run_pure_source_replay(
            (series("1m", 60_000, 4),), SetupExecutionProvider()
        )
        summary = result.runtime_summary
        self.assertEqual(summary["setup_count"], 1)
        self.assertEqual(summary["execution_plan_count"], 1)
        self.assertEqual(len(summary["source_ready_setup_ids"]), 1)
        self.assertFalse(summary["trade_entry_allowed"])
        self.assertEqual(summary["runtime_blockers"], ())

    def test_duplicate_assessment_dedupe_does_not_hide_changed_plan(self):
        class ChangedPlanProvider(SetupExecutionProvider):
            def produce(self, frame):
                batch = super().produce(frame)
                if len(frame.series_for("1m").candles) >= 3:
                    item = batch.execution_assessments[0]
                    changed = replace(
                        item.assessment.plan,
                        technical_normalization_ids=("TEST_CHANGED_PLAN",),
                    )
                    return replace(
                        batch,
                        execution_assessments=(
                            replace(
                                item, assessment=replace(item.assessment, plan=changed)
                            ),
                        ),
                    )
                return batch

        with self.assertRaisesRegex(ValueError, "execution plan changed"):
            run_pure_source_replay((series("1m", 60_000, 3),), ChangedPlanProvider())

    def test_unknown_assessments_remain_observed_at_each_prefix(self):
        class UnknownProvider(RecordingProvider):
            def produce(self, frame):
                return ReplayEvidenceBatch(
                    setup_assessments=(
                        SetupAssemblyAssessment(
                            EvidenceStatus.UNKNOWN, "UNRESOLVED_SOURCE_CONTEXT"
                        ),
                    )
                )

        result = run_pure_source_replay((series("1m", 60_000, 3),), UnknownProvider())
        self.assertEqual(len(result.runtime_summary["runtime_blockers"]), 3)
        self.assertEqual([row.blocker_count for row in result.receipts], [1, 2, 3])

    def test_later_invalidation_preserves_object_and_earlier_prefix(self):
        class LifecycleProvider(RecordingProvider):
            def produce(self, frame):
                obj = CausalSourceObject.formed(
                    object_type=SourceObjectType.POI,
                    symbol=SYMBOL,
                    timeframe="1m",
                    direction=None,
                    formation_at=BASE + timedelta(minutes=1),
                    known_at=BASE + timedelta(minutes=1),
                    identity_parts={"fixture": "later-invalidated"},
                    source_rule_ids=("TEST_LIFECYCLE",),
                    provenance="Stage-10 append-only lifecycle regression",
                )
                if frame.decision_at >= BASE + timedelta(minutes=3):
                    obj = obj.invalidate(
                        BASE + timedelta(minutes=3), "TEST_INVALIDATED"
                    )
                return ReplayEvidenceBatch(objects=(obj,))

        data = series("1m", 60_000, 4)
        full = run_pure_source_replay((data,), LifecycleProvider())
        prefix = run_pure_source_replay(
            (replace(data, candles=data.candles[:2]),), LifecycleProvider()
        )
        comparison = compare_replay_prefixes(
            full, prefix, through=BASE + timedelta(minutes=2)
        )
        self.assertTrue(comparison.equal)
        self.assertEqual(comparison.compared_steps, 2)
        self.assertEqual(
            [row.causal_object_count for row in full.receipts], [1, 1, 1, 1]
        )
        self.assertNotEqual(
            full.receipts[1].runtime_sha256, full.receipts[2].runtime_sha256
        )

    def test_future_market_mutation_cannot_change_earlier_stage2_prefix(self):
        interval_ms = 60_000
        highs = (101, 105, 102, 106, 103, 107, 104, 108)
        lows = (99, 100, 98, 101, 97, 102, 96, 103)
        base_candles = tuple(
            market_candle(
                interval_ms=interval_ms,
                index=index,
                interval="1m",
                center=(highs[index] + lows[index]) / 2,
                high=highs[index],
                low=lows[index],
            )
            for index in range(len(highs))
        )
        mutated = list(base_candles)
        last = mutated[-1]
        mutated[-1] = MarketCandle(
            exchange=last.exchange,
            symbol=last.symbol,
            interval=last.interval,
            open_time_ms=last.open_time_ms,
            open=last.open,
            high=last.high + 20,
            low=last.low,
            close=last.close,
            volume_base=last.volume_base,
            turnover_quote=last.turnover_quote,
            is_closed=True,
        )
        left = run_pure_source_replay(
            (ReplaySeries("1m", interval_ms, base_candles),),
            StructureLiquidityReplayProvider(),
        )
        right = run_pure_source_replay(
            (ReplaySeries("1m", interval_ms, tuple(mutated)),),
            StructureLiquidityReplayProvider(),
        )
        cutoff = BASE + timedelta(minutes=6)
        comparison = compare_replay_prefixes(left, right, through=cutoff)
        self.assertTrue(comparison.equal)
        self.assertGreater(comparison.compared_steps, 0)
        self.assertNotEqual(left.manifest.dataset_sha256, right.manifest.dataset_sha256)

    def test_past_market_mutation_is_detected_at_prefix(self):
        interval_ms = 60_000
        original = series("1m", interval_ms, 4)
        changed = list(original.candles)
        first = changed[0]
        changed[0] = MarketCandle(
            exchange=first.exchange,
            symbol=first.symbol,
            interval=first.interval,
            open_time_ms=first.open_time_ms,
            open=first.open,
            high=first.high + 5,
            low=first.low,
            close=first.close,
            volume_base=first.volume_base,
            turnover_quote=first.turnover_quote,
            is_closed=True,
        )
        left = run_pure_source_replay((original,), RecordingProvider())
        right = run_pure_source_replay(
            (ReplaySeries("1m", interval_ms, tuple(changed)),), RecordingProvider()
        )
        comparison = compare_replay_prefixes(
            left,
            right,
            through=BASE + timedelta(minutes=1),
        )
        self.assertFalse(comparison.equal)
        self.assertEqual(comparison.reason, "PREFIX_DATA_MUTATED")

    def test_cutoff_replay_exposes_no_future_receipts(self):
        cutoff = BASE + timedelta(minutes=3)
        result = run_pure_source_replay(
            (series("1m", 60_000, 6),),
            RecordingProvider(),
            through=cutoff,
        )
        self.assertTrue(result.receipts)
        self.assertLessEqual(result.receipts[-1].decision_at, cutoff)
        self.assertEqual(len(result.receipts), 3)


if __name__ == "__main__":
    unittest.main()
