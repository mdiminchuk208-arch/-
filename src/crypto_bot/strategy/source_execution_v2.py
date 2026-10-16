from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum
from math import isfinite
from typing import Sequence

from crypto_bot.common.models import Direction
from crypto_bot.strategy.causal_objects import CausalSourceObject, ObjectStatus, SourceObjectType
from crypto_bot.strategy.source_demand_supply_v2 import SourceDemandSupplyEvidence
from crypto_bot.strategy.source_ob_breaker_v2 import SourceBreakerEvidence, SourceOrderBlockEvidence
from crypto_bot.strategy.source_range_stb_v2 import (
    RangeDeviationEvidence,
    RangeDeviationSide,
    SourceRangeEvidence,
    SourceStbBtsEvidence,
)
from crypto_bot.strategy.source_sfp_v2 import SourceSfpEvidence
from crypto_bot.strategy.source_setup_v2 import SetupBranch, SourceSetupEvidence
from crypto_bot.strategy.source_structure_liquidity_v2 import EvidenceStatus


class EntryMode(str, Enum):
    OB_BOUNDARY_LIMIT = "OB_BOUNDARY_LIMIT"
    OB_INSIDE_ZONE = "OB_INSIDE_ZONE"
    NEW_POI_ZONE = "NEW_POI_ZONE"
    BREAKER_ZONE = "BREAKER_ZONE"
    DEMAND_SUPPLY_ZONE = "DEMAND_SUPPLY_ZONE"
    STB_BTS_DIRECTIONAL_PART = "STB_BTS_DIRECTIONAL_PART"
    STB_BTS_MIDPOINT = "STB_BTS_MIDPOINT"
    RANGE_DEVIATION_EXTERNAL_POI = "RANGE_DEVIATION_EXTERNAL_POI"
    RANGE_BOUNDARY_RETEST = "RANGE_BOUNDARY_RETEST"


class StopMode(str, Enum):
    OB_BEYOND_ZONE_EXTREME = "OB_BEYOND_ZONE_EXTREME"
    OB_BEYOND_ENGULFING_WICK = "OB_BEYOND_ENGULFING_WICK"
    BREAKER_AGGRESSIVE_BEYOND_ZONE = "BREAKER_AGGRESSIVE_BEYOND_ZONE"
    BREAKER_CONSERVATIVE_BEYOND_SWEEP_IMPULSE = "BREAKER_CONSERVATIVE_BEYOND_SWEEP_IMPULSE"
    SFP_ATR_FROM_PATTERN_EXTREME = "SFP_ATR_FROM_PATTERN_EXTREME"
    UNRESOLVED = "UNRESOLVED"


class ExitMode(str, Enum):
    FTA_FULL_OR_PARTIAL = "FTA_FULL_OR_PARTIAL"
    RANGE_80_20 = "RANGE_80_20"
    WAIT_FTA = "WAIT_FTA"


@dataclass(frozen=True)
class PriceAnchorReference:
    price: float
    known_at: datetime
    evidence_id: str
    provenance: str

    def __post_init__(self) -> None:
        _positive("anchor price", self.price)
        _aware("anchor known_at", self.known_at)
        if not self.evidence_id or not self.provenance:
            raise ValueError("price anchor requires evidence_id and provenance")


@dataclass(frozen=True)
class AtrReference:
    value: float
    period: int
    known_at: datetime
    evidence_id: str
    provenance: str

    def __post_init__(self) -> None:
        if not isfinite(self.value) or self.value <= 0:
            raise ValueError("ATR value must be finite and positive")
        if type(self.period) is not int or self.period <= 0:
            raise ValueError("ATR period must be a positive integer")
        _aware("ATR known_at", self.known_at)
        if not self.evidence_id or not self.provenance:
            raise ValueError("ATR reference requires evidence_id and provenance")


@dataclass(frozen=True)
class SourcePoiTargetReference:
    obj: CausalSourceObject
    zone_low: float
    zone_high: float
    source_kind: str
    consumed_at: datetime | None = None

    def __post_init__(self) -> None:
        _positive("POI zone_low", self.zone_low)
        _positive("POI zone_high", self.zone_high)
        if self.zone_low >= self.zone_high:
            raise ValueError("POI target zone must have positive width")
        if not self.source_kind:
            raise ValueError("source_kind is required")
        if self.consumed_at is not None:
            _aware("POI consumed_at", self.consumed_at)
            if self.consumed_at < self.obj.known_at:
                raise ValueError("POI cannot be consumed before it is known")


@dataclass(frozen=True)
class EntryOption:
    mode: EntryMode
    zone_low: float
    zone_high: float
    quote: float | None
    exact_quote: bool
    source_rule_ids: tuple[str, ...]
    note: str


@dataclass(frozen=True)
class StopOption:
    mode: StopMode
    relation: str
    anchor_price: float | None
    stop_price: float | None
    exact_price: bool
    source_rule_ids: tuple[str, ...]
    note: str


@dataclass(frozen=True)
class FtaSelection:
    status: EvidenceStatus
    reason: str
    decision_at: datetime
    direction: Direction
    entry_price: float
    trade_timeframe_minutes: int
    candidates: tuple[SourcePoiTargetReference, ...] = ()
    first_contact_price: float | None = None


@dataclass(frozen=True)
class ExitPolicy:
    mode: ExitMode
    primary_fraction: float | None
    remainder_fraction: float | None
    primary_target_price: float | None
    primary_target_object_ids: tuple[str, ...]
    remainder_target_price: float | None
    source_rule_ids: tuple[str, ...]
    unresolved: tuple[str, ...] = ()


@dataclass(frozen=True)
class SourceExecutionPlan:
    setup_id: str
    physical_idea_id: str
    branch: SetupBranch
    direction: Direction
    known_at: datetime
    entry_options: tuple[EntryOption, ...]
    stop_options: tuple[StopOption, ...]
    exit_policy: ExitPolicy
    invalidation_rules: tuple[str, ...]
    unresolved: tuple[str, ...]
    source_rule_ids: tuple[str, ...]
    technical_normalization_ids: tuple[str, ...] = ()
    trade_entry_allowed: bool = False

    @property
    def execution_ready(self) -> bool:
        if self.trade_entry_allowed or self.unresolved:
            return False
        if len(self.entry_options) != 1 or not self.entry_options[0].exact_quote:
            return False
        if len(self.stop_options) != 1 or not self.stop_options[0].exact_price:
            return False
        return self.exit_policy.primary_target_price is not None


@dataclass(frozen=True)
class ExecutionPlanAssessment:
    status: EvidenceStatus
    reason: str
    plan: SourceExecutionPlan | None = None


def select_source_fta(
    *,
    direction: Direction,
    entry_price: float,
    trade_timeframe_minutes: int,
    candidates: Sequence[SourcePoiTargetReference],
    decision_at: datetime,
) -> FtaSelection:
    """Select the first causal opposing higher-TF POI by first price contact.

    SOURCE: SW9 p11-16 defines FTA as the first trouble area and says it may be
    any opposing higher-timeframe POI. TECHNICAL_NORMALIZATION: the first contact
    with a zone is its near edge (low edge for LONG, high edge for SHORT).
    Future, consumed, invalid or non-opposing POIs are invisible.
    """
    _positive("entry_price", entry_price)
    _aware("FTA decision_at", decision_at)
    if type(trade_timeframe_minutes) is not int or trade_timeframe_minutes <= 0:
        raise ValueError("trade_timeframe_minutes must be positive integer minutes")

    allowed_types = {
        SourceObjectType.POI,
        SourceObjectType.ORDER_BLOCK,
        SourceObjectType.BREAKER,
        SourceObjectType.FVG,
        SourceObjectType.STB_BTS,
        SourceObjectType.RANGE,
    }
    opposite = Direction.SHORT.value if direction == Direction.LONG else Direction.LONG.value
    visible: list[tuple[float, float, SourcePoiTargetReference]] = []
    unknown_timeframe_ahead = False

    for candidate in candidates:
        obj = candidate.obj
        if obj.known_at > decision_at:
            continue
        if candidate.consumed_at is not None and candidate.consumed_at <= decision_at:
            continue
        if obj.object_type not in allowed_types or obj.direction != opposite:
            continue
        if not _active_at(obj, decision_at):
            continue

        timeframe = _timeframe_minutes(obj.timeframe)
        if timeframe is None:
            if _zone_is_ahead(direction, entry_price, candidate.zone_low, candidate.zone_high):
                unknown_timeframe_ahead = True
            continue
        if timeframe <= trade_timeframe_minutes:
            continue

        if candidate.zone_low <= entry_price <= candidate.zone_high:
            return FtaSelection(
                EvidenceStatus.UNKNOWN,
                "ENTRY_ALREADY_INSIDE_OPPOSING_HTF_POI",
                decision_at,
                direction,
                entry_price,
                trade_timeframe_minutes,
                (candidate,),
                entry_price,
            )
        if not _zone_is_ahead(direction, entry_price, candidate.zone_low, candidate.zone_high):
            continue

        first_contact = candidate.zone_low if direction == Direction.LONG else candidate.zone_high
        distance = abs(first_contact - entry_price)
        visible.append((distance, first_contact, candidate))

    if unknown_timeframe_ahead:
        return FtaSelection(
            EvidenceStatus.UNKNOWN,
            "WAIT_FTA_TIMEFRAME_NORMALIZATION",
            decision_at,
            direction,
            entry_price,
            trade_timeframe_minutes,
        )
    if not visible:
        return FtaSelection(
            EvidenceStatus.UNKNOWN,
            "WAIT_FIRST_TROUBLE_AREA",
            decision_at,
            direction,
            entry_price,
            trade_timeframe_minutes,
        )

    visible.sort(key=lambda row: (row[0], row[1]))
    nearest_distance = visible[0][0]
    nearest_price = visible[0][1]
    nearest = tuple(row[2] for row in visible if row[0] == nearest_distance and row[1] == nearest_price)
    return FtaSelection(
        EvidenceStatus.PASS,
        "SOURCE_FTA_SELECTED_BY_FIRST_CAUSAL_ZONE_CONTACT",
        decision_at,
        direction,
        entry_price,
        trade_timeframe_minutes,
        nearest,
        nearest_price,
    )


def plan_ob_execution(
    setup: SourceSetupEvidence,
    ob: SourceOrderBlockEvidence,
    *,
    entry_poi: SourcePoiTargetReference | None = None,
    engulfing_wick_extreme: PriceAnchorReference | None = None,
    fta: FtaSelection | None = None,
) -> ExecutionPlanAssessment:
    allowed = {
        SetupBranch.OB_DIRECT_FIRST_TEST,
        SetupBranch.OB_REPEAT_AFTER_LTF_REACTION,
        SetupBranch.OB_CONSERVATIVE_LTF_BOS_NEW_POI,
        SetupBranch.OB_CONF_STRICT,
    }
    mismatch = _validate_setup_context(setup, ob.obj, ob.direction, allowed)
    if mismatch is not None:
        return mismatch

    unresolved: list[str] = []
    entries: list[EntryOption] = []
    stops: list[StopOption] = []

    if setup.branch == SetupBranch.OB_CONSERVATIVE_LTF_BOS_NEW_POI:
        if entry_poi is None or entry_poi.obj.object_id != setup.entry_poi_id:
            return ExecutionPlanAssessment(EvidenceStatus.UNKNOWN, "WAIT_CAUSAL_ENTRY_POI_GEOMETRY")
        if entry_poi.obj.known_at > setup.known_at:
            return ExecutionPlanAssessment(EvidenceStatus.FAIL, "ENTRY_POI_GEOMETRY_KNOWN_AFTER_SETUP")
        entries.append(_zone_entry(EntryMode.NEW_POI_ZONE, entry_poi.zone_low, entry_poi.zone_high,
                                   ("OB_LTF_ENTRY_001",), "SW9 p4-6: limit order on the new POI; exact quote inside POI unspecified"))
        stops.append(_unresolved_stop("SW9 p4-6 does not uniquely define stop geometry for the refined new POI"))
        unresolved.extend(("OB_CONSERVATIVE_ENTRY_QUOTE_WITHIN_NEW_POI_UNRESOLVED", "WAIT_UNRESOLVED_STOP_GEOMETRY"))
    else:
        boundary = ob.zone_high if ob.direction == Direction.LONG else ob.zone_low
        entries.append(EntryOption(
            EntryMode.OB_BOUNDARY_LIMIT, ob.zone_low, ob.zone_high, boundary, True,
            ("OB_ENTRY_FIRST_VARIANT_001",),
            "SW9 p3: LONG upper OB boundary / SHORT lower OB boundary",
        ))
        entries.append(_zone_entry(
            EntryMode.OB_INSIDE_ZONE, ob.zone_low, ob.zone_high, ("OB_ENTRY_FIRST_VARIANT_001",),
            "SW9 p3 also permits limit orders inside the OB; exact inside-zone quote unspecified",
        ))
        unresolved.append("OB_ENTRY_BOUNDARY_VS_INSIDE_UNRESOLVED")

        ob_anchor = ob.zone_low if ob.direction == Direction.LONG else ob.zone_high
        relation = "BELOW" if ob.direction == Direction.LONG else "ABOVE"
        stops.append(StopOption(
            StopMode.OB_BEYOND_ZONE_EXTREME, relation, ob_anchor, None, False,
            ("OB_STOP_VARIANTS_001",), "SW9 p3: stop beyond OB minimum/maximum; beyond-anchor buffer unspecified",
        ))
        if engulfing_wick_extreme is not None:
            if engulfing_wick_extreme.known_at > setup.known_at:
                return ExecutionPlanAssessment(EvidenceStatus.FAIL, "ENGULFING_WICK_EXTREME_FROM_FUTURE")
            stops.append(StopOption(
                StopMode.OB_BEYOND_ENGULFING_WICK, relation, engulfing_wick_extreme.price, None, False,
                ("OB_STOP_VARIANTS_001",), "SW9 p3: alternative stop beyond wick/extreme of candle that engulfed OB",
            ))
        else:
            unresolved.append("WAIT_OB_ENGULFING_WICK_STOP_EVIDENCE")
        unresolved.append("OB_STOP_VARIANT_AND_EXACT_BUFFER_UNRESOLVED")

    exit_policy, exit_unresolved = _generic_fta_exit(fta)
    unresolved.extend(exit_unresolved)
    return _plan(
        setup, entries, stops, exit_policy,
        invalidation_rules=(),
        unresolved=unresolved,
        source_rule_ids=("OB_ENTRY_FIRST_VARIANT_001", "OB_STOP_VARIANTS_001", "FTA_TARGET_001"),
        technical_ids=("TN_FTA_FIRST_ZONE_CONTACT",),
    )


def plan_breaker_execution(
    setup: SourceSetupEvidence,
    breaker: SourceBreakerEvidence,
    *,
    sweep_impulse_extreme: PriceAnchorReference | None = None,
    fta: FtaSelection | None = None,
) -> ExecutionPlanAssessment:
    mismatch = _validate_setup_context(setup, breaker.obj, breaker.direction, {SetupBranch.BREAKER_DIRECT})
    if mismatch is not None:
        return mismatch

    entries = [
        _zone_entry(EntryMode.BREAKER_ZONE, breaker.zone_low, breaker.zone_high,
                    ("BREAKER_ENTRY_ZONE_001",), "SW9 p7-10: Breaker is tradable POI; exact quote inside zone unspecified")
    ]
    relation = "BELOW" if breaker.direction == Direction.LONG else "ABOVE"
    aggressive_anchor = breaker.zone_low if breaker.direction == Direction.LONG else breaker.zone_high
    stops = [
        StopOption(
            StopMode.BREAKER_AGGRESSIVE_BEYOND_ZONE, relation, aggressive_anchor, None, False,
            ("BREAKER_STOP_VARIANTS_001",), "SW9 p9: aggressive stop immediately beyond Breaker; exact buffer unspecified",
        )
    ]
    unresolved = ["BREAKER_ENTRY_QUOTE_WITHIN_ZONE_UNRESOLVED", "BREAKER_STOP_VARIANT_AND_BUFFER_UNRESOLVED"]
    if sweep_impulse_extreme is not None:
        if sweep_impulse_extreme.known_at > setup.known_at:
            return ExecutionPlanAssessment(EvidenceStatus.FAIL, "BREAKER_SWEEP_IMPULSE_EXTREME_FROM_FUTURE")
        stops.append(StopOption(
            StopMode.BREAKER_CONSERVATIVE_BEYOND_SWEEP_IMPULSE,
            relation,
            sweep_impulse_extreme.price,
            None,
            False,
            ("BREAKER_STOP_VARIANTS_001",),
            "SW9 p9: conservative stop beyond liquidity-sweeping impulse candle min/max",
        ))
    else:
        unresolved.append("WAIT_BREAKER_CONSERVATIVE_STOP_EXTREME_EVIDENCE")

    exit_policy, exit_unresolved = _generic_fta_exit(fta)
    unresolved.extend(exit_unresolved)
    return _plan(
        setup, entries, stops, exit_policy,
        invalidation_rules=(), unresolved=unresolved,
        source_rule_ids=("BREAKER_STOP_VARIANTS_001", "FTA_TARGET_001"),
        technical_ids=("TN_FTA_FIRST_ZONE_CONTACT",),
    )


def plan_sfp_execution(
    setup: SourceSetupEvidence,
    sfp: SourceSfpEvidence,
    *,
    entry_poi: SourcePoiTargetReference,
    atr: AtrReference | None,
    fta: FtaSelection | None = None,
) -> ExecutionPlanAssessment:
    mismatch = _validate_setup_context(setup, sfp.obj, sfp.direction, {SetupBranch.SFP_LTF_BOS_NEW_POI})
    if mismatch is not None:
        return mismatch
    if entry_poi.obj.object_id != setup.entry_poi_id:
        return ExecutionPlanAssessment(EvidenceStatus.FAIL, "SFP_ENTRY_POI_ID_MISMATCH")
    if entry_poi.obj.known_at > setup.known_at:
        return ExecutionPlanAssessment(EvidenceStatus.FAIL, "SFP_ENTRY_POI_FROM_FUTURE")

    entries = [_zone_entry(
        EntryMode.NEW_POI_ZONE, entry_poi.zone_low, entry_poi.zone_high,
        ("SFP_LTF_BOS_002",), "SW8 p5: seek entry after LTF BOS; Stage 7 supplies new POI; exact quote unspecified",
    )]
    unresolved = ["SFP_ENTRY_QUOTE_WITHIN_NEW_POI_UNRESOLVED"]
    stops: list[StopOption] = []
    if atr is None:
        stops.append(_unresolved_stop("SW12 p12-13 supports ATR stop, but ATR evidence is missing"))
        unresolved.append("WAIT_SFP_ATR_EVIDENCE")
    elif atr.known_at > setup.known_at:
        return ExecutionPlanAssessment(EvidenceStatus.FAIL, "SFP_ATR_FROM_FUTURE")
    else:
        stop = sfp.pattern_extreme - atr.value if sfp.direction == Direction.LONG else sfp.pattern_extreme + atr.value
        relation = "BELOW" if sfp.direction == Direction.LONG else "ABOVE"
        stops.append(StopOption(
            StopMode.SFP_ATR_FROM_PATTERN_EXTREME,
            relation,
            sfp.pattern_extreme,
            stop,
            True,
            ("SFP_ATR_STOP_001",),
            f"SW12 p12-13: ATR({atr.period}) distance from SFP pattern extreme",
        ))
        if atr.period != 14:
            unresolved.append("SFP_ATR_PERIOD_NOT_FROZEN_BY_SOURCE_STRATEGY")

    exit_policy, exit_unresolved = _generic_fta_exit(fta)
    unresolved.extend(exit_unresolved)
    return _plan(
        setup, entries, stops, exit_policy,
        invalidation_rules=("SFP_BODY_CLOSE_BEYOND_PATTERN_EXTREME_INVALIDATES", "SFP_PROTECTIVE_STOP_NOT_MOVED"),
        unresolved=unresolved,
        source_rule_ids=("SFP_LTF_BOS_002", "SFP_ATR_STOP_001", "SFP_INVALIDATION_CLOSE_001", "FTA_TARGET_001"),
        technical_ids=("TN_SFP_ATR_DIRECTIONAL_MIRROR", "TN_FTA_FIRST_ZONE_CONTACT"),
    )


def plan_stb_bts_execution(
    setup: SourceSetupEvidence,
    stb_bts: SourceStbBtsEvidence,
    *,
    fta: FtaSelection | None = None,
) -> ExecutionPlanAssessment:
    mismatch = _validate_setup_context(setup, stb_bts.obj, stb_bts.direction, {SetupBranch.STB_BTS_DIRECT})
    if mismatch is not None:
        return mismatch
    if stb_bts.direction == Direction.LONG:
        part_low, part_high = stb_bts.midpoint, stb_bts.zone_high
    else:
        part_low, part_high = stb_bts.zone_low, stb_bts.midpoint
    entries = [
        _zone_entry(
            EntryMode.STB_BTS_DIRECTIONAL_PART, part_low, part_high,
            ("STB_BTS_ENTRY_001",), "SW22 p3: upper part for LONG / lower part for SHORT; no exact quote within that part",
        ),
        EntryOption(
            EntryMode.STB_BTS_MIDPOINT, stb_bts.zone_low, stb_bts.zone_high, stb_bts.midpoint, True,
            ("STB_BTS_ENTRY_001",), "SW22 p3-4: exact 0.5 midpoint is a source-permitted entry/mitigation level",
        ),
    ]
    stops = [_unresolved_stop("SW22 p2-4 does not state a unique protective stop anchor for STB/BTS")]
    unresolved = ["STB_BTS_EDGE_VS_MIDPOINT_ENTRY_PRECEDENCE_UNRESOLVED", "WAIT_UNRESOLVED_STOP_GEOMETRY"]
    exit_policy, exit_unresolved = _generic_fta_exit(fta)
    unresolved.extend(exit_unresolved)
    return _plan(
        setup, entries, stops, exit_policy,
        invalidation_rules=(), unresolved=unresolved,
        source_rule_ids=("STB_BTS_ENTRY_001", "FTA_TARGET_001"),
        technical_ids=("TN_FTA_FIRST_ZONE_CONTACT",),
    )


def plan_range_execution(
    setup: SourceSetupEvidence,
    range_evidence: SourceRangeEvidence,
    *,
    deviation: RangeDeviationEvidence,
    external_poi: SourcePoiTargetReference | None = None,
) -> ExecutionPlanAssessment:
    allowed = {SetupBranch.RANGE_AGGRESSIVE_EXTERNAL_POI, SetupBranch.RANGE_CONSERVATIVE_RETURN_RETEST}
    mismatch = _validate_setup_context(setup, range_evidence.obj, setup.direction, allowed, allow_range_direction=True)
    if mismatch is not None:
        return mismatch
    if deviation.range_object_id != range_evidence.obj.object_id or deviation.known_at > setup.known_at:
        return ExecutionPlanAssessment(EvidenceStatus.FAIL, "RANGE_DEVIATION_NOT_CAUSAL_FOR_SETUP")
    expected_direction = Direction.LONG if deviation.side == RangeDeviationSide.LOW else Direction.SHORT
    if setup.direction != expected_direction:
        return ExecutionPlanAssessment(EvidenceStatus.FAIL, "RANGE_SETUP_DIRECTION_DOES_NOT_MATCH_DEVIATION")

    unresolved = ["WAIT_UNRESOLVED_RANGE_STOP_GEOMETRY"]
    if setup.branch == SetupBranch.RANGE_AGGRESSIVE_EXTERNAL_POI:
        if external_poi is None:
            return ExecutionPlanAssessment(EvidenceStatus.UNKNOWN, "WAIT_RANGE_EXTERNAL_POI_GEOMETRY")
        if external_poi.obj.known_at > deviation.known_at:
            return ExecutionPlanAssessment(EvidenceStatus.FAIL, "RANGE_EXTERNAL_POI_NOT_KNOWN_AT_DEVIATION")
        entries = [_zone_entry(
            EntryMode.RANGE_DEVIATION_EXTERNAL_POI, external_poi.zone_low, external_poi.zone_high,
            ("RANGE_AGGRESSIVE_ENTRY_001",), "SW10 p5: aggressive on deviation with external POI; exact quote unspecified",
        )]
        unresolved.append("RANGE_AGGRESSIVE_EXACT_QUOTE_UNRESOLVED")
    else:
        boundary = range_evidence.lower if setup.direction == Direction.LONG else range_evidence.upper
        entries = [EntryOption(
            EntryMode.RANGE_BOUNDARY_RETEST,
            boundary,
            boundary,
            boundary,
            True,
            ("RANGE_CONSERVATIVE_ENTRY_001",),
            "SW10 p6: after return/acceptance inside range, enter on boundary retest",
        )]

    stops = [_unresolved_stop("SW10 p5-7 does not define a unique protective stop anchor")]
    primary_target = range_evidence.upper if setup.direction == Direction.LONG else range_evidence.lower
    exit_policy = ExitPolicy(
        ExitMode.RANGE_80_20,
        0.8,
        0.2,
        primary_target,
        (range_evidence.obj.object_id,),
        None,
        ("RANGE_EXIT_80_20_001",),
        ("RANGE_REMAINDER_TRUE_BREAKOUT_TARGET_UNRESOLVED",),
    )
    unresolved.append("RANGE_REMAINDER_TRUE_BREAKOUT_TARGET_UNRESOLVED")
    return _plan(
        setup, entries, stops, exit_policy,
        invalidation_rules=(), unresolved=unresolved,
        source_rule_ids=("RANGE_AGGRESSIVE_ENTRY_001", "RANGE_CONSERVATIVE_ENTRY_001", "RANGE_EXIT_80_20_001"),
        technical_ids=("TN_RANGE_PRIMARY_EXIT_OPPOSITE_DIRECTIONAL_BOUNDARY",),
    )


def plan_demand_supply_execution(
    setup: SourceSetupEvidence,
    zone: SourceDemandSupplyEvidence,
    *,
    fta: FtaSelection | None = None,
) -> ExecutionPlanAssessment:
    mismatch = _validate_setup_context(setup, zone.obj, zone.direction, {SetupBranch.DEMAND_SUPPLY_DIRECT})
    if mismatch is not None:
        return mismatch
    entries = [_zone_entry(
        EntryMode.DEMAND_SUPPLY_ZONE, zone.zone_low, zone.zone_high,
        ("DS_ENTRY_ZONE_001",), "SRC_DS_001: zone may be a point for opening position; exact quote inside zone unspecified",
    )]
    stops = [_unresolved_stop("SRC_DS_001 does not define protective stop geometry")]
    unresolved = ["DEMAND_SUPPLY_EXACT_ENTRY_QUOTE_UNRESOLVED", "WAIT_UNRESOLVED_STOP_GEOMETRY"]
    exit_policy, exit_unresolved = _generic_fta_exit(fta)
    unresolved.extend(exit_unresolved)
    return _plan(
        setup, entries, stops, exit_policy,
        invalidation_rules=(), unresolved=unresolved,
        source_rule_ids=("DS_ENTRY_ZONE_001", "FTA_TARGET_001"),
        technical_ids=("TN_FTA_FIRST_ZONE_CONTACT",),
    )


def _generic_fta_exit(fta: FtaSelection | None) -> tuple[ExitPolicy, tuple[str, ...]]:
    if fta is None or fta.status != EvidenceStatus.PASS or fta.first_contact_price is None:
        reason = fta.reason if fta is not None else "WAIT_FIRST_TROUBLE_AREA"
        return (
            ExitPolicy(ExitMode.WAIT_FTA, None, None, None, (), None, ("FTA_TARGET_001",), (reason,)),
            (reason,),
        )
    ids = tuple(candidate.obj.object_id for candidate in fta.candidates)
    return (
        ExitPolicy(
            ExitMode.FTA_FULL_OR_PARTIAL,
            None,
            None,
            fta.first_contact_price,
            ids,
            None,
            ("FTA_TARGET_001",),
            ("FTA_FULL_VS_PARTIAL_FRACTION_UNRESOLVED",),
        ),
        ("FTA_FULL_VS_PARTIAL_FRACTION_UNRESOLVED",),
    )


def _plan(
    setup: SourceSetupEvidence,
    entries: Sequence[EntryOption],
    stops: Sequence[StopOption],
    exit_policy: ExitPolicy,
    *,
    invalidation_rules: Sequence[str],
    unresolved: Sequence[str],
    source_rule_ids: Sequence[str],
    technical_ids: Sequence[str],
) -> ExecutionPlanAssessment:
    if setup.setup.known_at != setup.known_at:
        return ExecutionPlanAssessment(EvidenceStatus.FAIL, "SETUP_KNOWN_AT_CONTRACT_MISMATCH")
    dedup_unresolved = tuple(dict.fromkeys(reason for reason in unresolved if reason))
    plan = SourceExecutionPlan(
        setup_id=setup.setup.object_id,
        physical_idea_id=setup.physical_idea.object_id,
        branch=setup.branch,
        direction=setup.direction,
        known_at=setup.known_at,
        entry_options=tuple(entries),
        stop_options=tuple(stops),
        exit_policy=exit_policy,
        invalidation_rules=tuple(invalidation_rules),
        unresolved=dedup_unresolved,
        source_rule_ids=tuple(dict.fromkeys(source_rule_ids)),
        technical_normalization_ids=tuple(dict.fromkeys(technical_ids)),
        trade_entry_allowed=False,
    )
    return ExecutionPlanAssessment(EvidenceStatus.PASS, "SOURCE_EXECUTION_SEMANTICS_CAPTURED", plan)


def _zone_entry(mode: EntryMode, low: float, high: float, source_ids: tuple[str, ...], note: str) -> EntryOption:
    _positive("entry zone low", low)
    _positive("entry zone high", high)
    if low >= high:
        raise ValueError("entry zone must have positive width")
    return EntryOption(mode, low, high, None, False, source_ids, note)


def _unresolved_stop(note: str) -> StopOption:
    return StopOption(StopMode.UNRESOLVED, "UNRESOLVED", None, None, False, (), note)


def _validate_setup_context(
    setup: SourceSetupEvidence,
    context: CausalSourceObject,
    direction: Direction,
    allowed_branches: set[SetupBranch],
    *,
    allow_range_direction: bool = False,
) -> ExecutionPlanAssessment | None:
    if setup.branch not in allowed_branches:
        return ExecutionPlanAssessment(EvidenceStatus.FAIL, "SETUP_BRANCH_CONTEXT_TYPE_MISMATCH")
    if setup.context_object_id != context.object_id:
        return ExecutionPlanAssessment(EvidenceStatus.FAIL, "SETUP_CONTEXT_OBJECT_ID_MISMATCH")
    if setup.direction != direction and not allow_range_direction:
        return ExecutionPlanAssessment(EvidenceStatus.FAIL, "SETUP_DIRECTION_CONTEXT_MISMATCH")
    if context.known_at > setup.known_at:
        return ExecutionPlanAssessment(EvidenceStatus.FAIL, "SETUP_PRECEDES_CONTEXT")
    if not _active_at(context, setup.known_at):
        return ExecutionPlanAssessment(EvidenceStatus.FAIL, "SOURCE_CONTEXT_NOT_ACTIVE_AT_SETUP")
    return None


def _active_at(obj: CausalSourceObject, at: datetime) -> bool:
    if obj.known_at > at:
        return False
    state = obj.state_at(at)
    return (
        state.formation_valid
        and state.invalidated_at is None
        and state.status not in (ObjectStatus.INVALIDATED, ObjectStatus.CANCELLED)
    )


def _zone_is_ahead(direction: Direction, entry: float, low: float, high: float) -> bool:
    return low > entry if direction == Direction.LONG else high < entry


def _timeframe_minutes(value: str) -> int | None:
    text = str(value).strip().lower()
    multiplier = 1
    if text.endswith("m"):
        text = text[:-1]
    elif text.endswith("h"):
        text = text[:-1]
        multiplier = 60
    elif text.endswith("d"):
        text = text[:-1]
        multiplier = 1440
    try:
        number = int(text)
    except ValueError:
        return None
    return number * multiplier if number > 0 else None


def _positive(name: str, value: float) -> None:
    if not isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and positive")


def _aware(name: str, value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
