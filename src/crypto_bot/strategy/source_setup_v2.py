from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Sequence

from crypto_bot.common.models import Direction
from crypto_bot.strategy.causal_objects import CausalSourceObject, ObjectStatus, SourceObjectType
from crypto_bot.strategy.source_demand_supply_v2 import (
    SourceDemandSupplyEvidence,
    assess_demand_supply_context,
)
from crypto_bot.strategy.source_imb_ote_pd_v2 import PremiumDiscountEvidence
from crypto_bot.strategy.source_ob_breaker_v2 import (
    BosReference,
    QualitativeEvidence,
    SourceBreakerEvidence,
    SourceOrderBlockEvidence,
)
from crypto_bot.strategy.source_range_stb_v2 import (
    RangeDeviationEvidence,
    RangeDeviationSide,
    SourceRangeEvidence,
    SourceStbBtsEvidence,
)
from crypto_bot.strategy.source_sfp_v2 import SourceSfpEvidence
from crypto_bot.strategy.source_structure_liquidity_v2 import EvidenceStatus


class SetupBranch(str, Enum):
    OB_DIRECT_FIRST_TEST = "OB_DIRECT_FIRST_TEST"
    OB_REPEAT_AFTER_LTF_REACTION = "OB_REPEAT_AFTER_LTF_REACTION"
    OB_CONSERVATIVE_LTF_BOS_NEW_POI = "OB_CONSERVATIVE_LTF_BOS_NEW_POI"
    OB_CONF_STRICT = "OB_CONF_STRICT"
    SFP_LTF_BOS_NEW_POI = "SFP_LTF_BOS_NEW_POI"
    BREAKER_DIRECT = "BREAKER_DIRECT"
    DEMAND_SUPPLY_DIRECT = "DEMAND_SUPPLY_DIRECT"
    STB_BTS_DIRECT = "STB_BTS_DIRECT"
    RANGE_AGGRESSIVE_EXTERNAL_POI = "RANGE_AGGRESSIVE_EXTERNAL_POI"
    RANGE_CONSERVATIVE_RETURN_RETEST = "RANGE_CONSERVATIVE_RETURN_RETEST"


@dataclass(frozen=True)
class LowerTimeframePair:
    context_minutes: int
    refinement_minutes: int

    def __post_init__(self) -> None:
        if type(self.context_minutes) is not int or type(self.refinement_minutes) is not int:
            raise ValueError("timeframes must be integer minutes")
        if self.context_minutes <= 0 or self.refinement_minutes <= 0:
            raise ValueError("timeframes must be positive")
        if self.refinement_minutes >= self.context_minutes:
            raise ValueError("refinement timeframe must be strictly lower than context timeframe")


@dataclass(frozen=True)
class CausalChainEvidence:
    evidence_id: str
    known_at: datetime
    direction: Direction
    provenance: str
    parent_object_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _aware("chain known_at", self.known_at)
        if not self.evidence_id or not self.provenance:
            raise ValueError("chain evidence requires id and provenance")


@dataclass(frozen=True)
class PoiTestReference:
    poi_object_id: str
    test_number: int
    known_at: datetime
    evidence_id: str
    provenance: str

    def __post_init__(self) -> None:
        if self.test_number < 1:
            raise ValueError("test_number must be >= 1")
        _aware("test known_at", self.known_at)
        if not self.poi_object_id or not self.evidence_id or not self.provenance:
            raise ValueError("POI test reference requires provenance")


@dataclass(frozen=True)
class SourceSetupEvidence:
    physical_idea: CausalSourceObject
    setup: CausalSourceObject
    branch: SetupBranch
    direction: Direction
    context_object_id: str
    known_at: datetime
    evidence_ids: tuple[str, ...]
    refinement_timeframe_minutes: int | None = None
    entry_poi_id: str | None = None


@dataclass(frozen=True)
class SetupAssemblyAssessment:
    status: EvidenceStatus
    reason: str
    evidence: SourceSetupEvidence | None = None

    @property
    def assembled(self) -> bool:
        return self.status == EvidenceStatus.PASS


def assemble_ob_direct_first_test(
    ob: SourceOrderBlockEvidence,
) -> SetupAssemblyAssessment:
    """Register the source-permitted direct OB plan for its next/first test.

    No future test is required to create the plan. Stage 8 will define the entry
    quote/stop and enforce first-test execution semantics. This prevents future
    interaction from being used as historical setup-formation evidence.
    """
    if not _context_active_at(ob.obj, ob.obj.known_at):
        return _fail("OB_CONTEXT_NOT_ACTIVE_AT_KNOWN_AT")
    return _assemble(
        context=ob.obj,
        direction=ob.direction,
        branch=SetupBranch.OB_DIRECT_FIRST_TEST,
        known_at=ob.obj.known_at,
        evidence_ids=(),
        parent_objects=(),
        source_rule_ids=("OB_FIRST_TEST_001", "SETUP_OB_DIRECT_001"),
        provenance="SW9 p3 direct OB first-test setup; quote and stop deferred to Stage 8",
    )


def assemble_ob_repeat_after_ltf_reaction(
    ob: SourceOrderBlockEvidence,
    *,
    prior_test: PoiTestReference,
    ltf_reaction: CausalChainEvidence,
) -> SetupAssemblyAssessment:
    """Create the exceptional repeated-OB setup only after a causal LTF reaction."""
    if prior_test.poi_object_id != ob.obj.object_id:
        return _fail("PRIOR_TEST_DOES_NOT_BELONG_TO_OB")
    if prior_test.test_number != 1:
        return _fail("REPEAT_OB_EXPECTS_CAUSAL_FIRST_TEST_REFERENCE")
    if prior_test.known_at < ob.obj.known_at:
        return _fail("PRIOR_TEST_PRECEDES_OB_KNOWN_AT")
    if ltf_reaction.direction != ob.direction:
        return _fail("LTF_REACTION_DIRECTION_MISMATCH")
    if ob.obj.object_id not in ltf_reaction.parent_object_ids:
        return _fail("LTF_REACTION_NOT_LINKED_TO_OB")
    if ltf_reaction.known_at <= prior_test.known_at:
        return _fail("LTF_REACTION_NOT_AFTER_FIRST_TEST")
    if not _context_active_at(ob.obj, ltf_reaction.known_at):
        return _fail("OB_NOT_ACTIVE_AT_REPEAT_REACTION")
    return _assemble(
        context=ob.obj,
        direction=ob.direction,
        branch=SetupBranch.OB_REPEAT_AFTER_LTF_REACTION,
        known_at=ltf_reaction.known_at,
        evidence_ids=(prior_test.evidence_id, ltf_reaction.evidence_id),
        parent_objects=(),
        source_rule_ids=("OB_FIRST_TEST_001", "SETUP_OB_REPEAT_REACTION_001"),
        provenance="SW9 p3 repeated OB path after lower-timeframe reaction; future repeat quote deferred",
    )


def assemble_ob_conservative_ltf(
    ob: SourceOrderBlockEvidence,
    *,
    pair: LowerTimeframePair,
    ltf_reaction: CausalChainEvidence,
    ltf_bos: BosReference,
    entry_poi_candidates: Sequence[CausalSourceObject],
) -> SetupAssemblyAssessment:
    """Assemble SW9 conservative HTF-OB -> LTF reaction -> BOS -> new POI chain."""
    if pair.refinement_minutes > 15:
        return _fail("OB_CONSERVATIVE_REFINEMENT_OUTSIDE_SOURCE_1_15M_SCOPE")
    if ltf_reaction.direction != ob.direction or ob.obj.object_id not in ltf_reaction.parent_object_ids:
        return _fail("OB_CONSERVATIVE_REACTION_MISMATCH")
    if ltf_reaction.known_at < ob.obj.known_at:
        return _fail("OB_CONSERVATIVE_REACTION_PRECEDES_OB")
    if ltf_bos.kind != "BOS" or ltf_bos.direction != ob.direction:
        return _fail("OB_CONSERVATIVE_REQUIRES_DIRECTIONAL_LTF_BOS")
    if ltf_bos.known_at < ltf_reaction.known_at:
        return _fail("LTF_BOS_PRECEDES_REACTION")
    selection = _select_unique_new_poi(
        entry_poi_candidates,
        direction=ob.direction,
        min_formation_at=ltf_bos.known_at,
        decision_at=max((p.known_at for p in entry_poi_candidates), default=ltf_bos.known_at),
    )
    if selection.status != EvidenceStatus.PASS:
        return selection
    assert isinstance(selection.evidence, SourceSetupEvidence) is False
    poi = selection_poi(selection)
    assert poi is not None
    if not _context_active_at(ob.obj, poi.known_at):
        return _fail("OB_CONTEXT_NOT_ACTIVE_WHEN_LTF_POI_KNOWN")
    return _assemble(
        context=ob.obj,
        direction=ob.direction,
        branch=SetupBranch.OB_CONSERVATIVE_LTF_BOS_NEW_POI,
        known_at=poi.known_at,
        evidence_ids=(ltf_reaction.evidence_id, ltf_bos.evidence_id, poi.object_id),
        parent_objects=(poi,),
        source_rule_ids=("OB_LTF_ENTRY_001", "SETUP_OB_CONSERVATIVE_LTF_001"),
        provenance="SW9 p4-6 HTF OB reaction -> lower-TF BOS -> newly formed source-valid POI",
        refinement_timeframe_minutes=pair.refinement_minutes,
        entry_poi_id=poi.object_id,
    )


def assemble_ob_conf_strict(
    ob: SourceOrderBlockEvidence,
    *,
    conf: BosReference,
) -> SetupAssemblyAssessment:
    """Preserve the general conservative 'after CONF' source-permitted branch."""
    if conf.kind != "CONF" or conf.direction != ob.direction:
        return _fail("OB_CONF_BRANCH_REQUIRES_DIRECTIONAL_CONF")
    if conf.known_at < ob.obj.known_at:
        return _fail("CONF_PRECEDES_OB_KNOWN_AT")
    if not _context_active_at(ob.obj, conf.known_at):
        return _fail("OB_CONTEXT_NOT_ACTIVE_AT_CONF")
    return _assemble(
        context=ob.obj,
        direction=ob.direction,
        branch=SetupBranch.OB_CONF_STRICT,
        known_at=conf.known_at,
        evidence_ids=(conf.evidence_id,),
        parent_objects=(),
        source_rule_ids=("MS_CONF_001", "SETUP_OB_CONF_STRICT_001"),
        provenance="SW5 p6 conservative after-CONF branch applied to an already source-valid OB context",
    )


def assemble_sfp_ltf_bos_new_poi(
    sfp: SourceSfpEvidence,
    *,
    pair: LowerTimeframePair,
    ltf_bos: BosReference,
    entry_poi_candidates: Sequence[CausalSourceObject],
) -> SetupAssemblyAssessment:
    """Assemble completed SFP -> strictly lower-TF BOS -> new source-valid POI."""
    if ltf_bos.kind != "BOS" or ltf_bos.direction != sfp.direction:
        return _fail("SFP_SETUP_REQUIRES_DIRECTIONAL_LTF_BOS")
    if ltf_bos.known_at < sfp.obj.known_at:
        return _fail("LTF_BOS_PRECEDES_SFP_FORMATION")
    selection = _select_unique_new_poi(
        entry_poi_candidates,
        direction=sfp.direction,
        min_formation_at=ltf_bos.known_at,
        decision_at=max((p.known_at for p in entry_poi_candidates), default=ltf_bos.known_at),
    )
    if selection.status != EvidenceStatus.PASS:
        return selection
    poi = selection_poi(selection)
    assert poi is not None
    if not _context_active_at(sfp.obj, poi.known_at):
        return _fail("SFP_CONTEXT_NOT_ACTIVE_WHEN_ENTRY_POI_KNOWN")
    return _assemble(
        context=sfp.obj,
        direction=sfp.direction,
        branch=SetupBranch.SFP_LTF_BOS_NEW_POI,
        known_at=poi.known_at,
        evidence_ids=(ltf_bos.evidence_id, poi.object_id),
        parent_objects=(poi,),
        source_rule_ids=("SFP_LTF_BOS_002", "SETUP_SFP_NEW_POI_001"),
        provenance="SW8/SW9 completed SFP -> lower-TF BOS -> new source-valid POI; no fixed TF mapping",
        refinement_timeframe_minutes=pair.refinement_minutes,
        entry_poi_id=poi.object_id,
    )


def assemble_breaker_direct(
    breaker: SourceBreakerEvidence,
) -> SetupAssemblyAssessment:
    if not _context_active_at(breaker.obj, breaker.obj.known_at):
        return _fail("BREAKER_CONTEXT_NOT_ACTIVE_AT_KNOWN_AT")
    return _assemble(
        context=breaker.obj,
        direction=breaker.direction,
        branch=SetupBranch.BREAKER_DIRECT,
        known_at=breaker.obj.known_at,
        evidence_ids=(),
        parent_objects=(),
        source_rule_ids=("BREAKER_PARENT_OB_001", "SETUP_BREAKER_DIRECT_001"),
        provenance="source-valid Breaker POI setup; quote/stop deferred to Stage 8",
    )


def assemble_demand_supply_direct(
    zone: SourceDemandSupplyEvidence,
    *,
    premium_discount: PremiumDiscountEvidence | None,
    decision_at: datetime,
    first_test_at: datetime | None = None,
) -> SetupAssemblyAssessment:
    _aware("decision_at", decision_at)
    if first_test_at is not None and first_test_at > decision_at:
        return _fail("FUTURE_FIRST_TEST_FACT_FORBIDDEN")
    context = assess_demand_supply_context(
        zone,
        premium_discount=premium_discount,
        decision_at=decision_at,
        first_test_at=first_test_at,
    )
    if context.status != EvidenceStatus.PASS:
        return SetupAssemblyAssessment(context.status, context.reason)
    if not _context_active_at(zone.obj, decision_at):
        return _fail("DEMAND_SUPPLY_OBJECT_NOT_ACTIVE_AT_DECISION")
    pd_id = premium_discount.dealing_range_evidence_id if premium_discount is not None else ""
    return _assemble(
        context=zone.obj,
        direction=zone.direction,
        branch=SetupBranch.DEMAND_SUPPLY_DIRECT,
        known_at=decision_at,
        evidence_ids=(pd_id,),
        parent_objects=(),
        source_rule_ids=("DS_UNTESTED_001", "DS_PREMIUM_DISCOUNT_001", "SETUP_DS_DIRECT_001"),
        provenance="verified D/S source: fresh zone plus causal Premium/Discount context; entry deferred",
    )


def assemble_stb_bts_direct(
    stb_bts: SourceStbBtsEvidence,
) -> SetupAssemblyAssessment:
    if not _context_active_at(stb_bts.obj, stb_bts.obj.known_at):
        return _fail("STB_BTS_CONTEXT_NOT_ACTIVE_AT_KNOWN_AT")
    return _assemble(
        context=stb_bts.obj,
        direction=stb_bts.direction,
        branch=SetupBranch.STB_BTS_DIRECT,
        known_at=stb_bts.obj.known_at,
        evidence_ids=(),
        parent_objects=(),
        source_rule_ids=("STB_BTS_BOS_CONF_001", "SETUP_STB_BTS_DIRECT_001"),
        provenance="source-valid STB/BTS context; edge/0.5 mitigation choice deferred to Stage 8",
    )


def assemble_range_aggressive(
    range_evidence: SourceRangeEvidence,
    *,
    deviation: RangeDeviationEvidence,
    external_poi: CausalSourceObject,
    external_relation: QualitativeEvidence,
) -> SetupAssemblyAssessment:
    relation = _validate_range_external_context(
        range_evidence,
        deviation=deviation,
        external_poi=external_poi,
        external_relation=external_relation,
    )
    if relation.status != EvidenceStatus.PASS:
        return relation
    direction = _range_direction(deviation.side)
    return _assemble(
        context=range_evidence.obj,
        direction=direction,
        branch=SetupBranch.RANGE_AGGRESSIVE_EXTERNAL_POI,
        known_at=deviation.known_at,
        evidence_ids=(deviation.evidence_id, external_poi.object_id, external_relation.evidence_id or ""),
        parent_objects=(external_poi,),
        source_rule_ids=("RANGE_AGGRESSIVE_ENTRY_001", "SETUP_RANGE_AGGRESSIVE_001"),
        provenance="SW10 aggressive Range branch: deviation at a causally known external POI; quote deferred",
    )


def assemble_range_conservative(
    range_evidence: SourceRangeEvidence,
    *,
    deviation: RangeDeviationEvidence,
    external_poi: CausalSourceObject,
    external_relation: QualitativeEvidence,
    return_inside: QualitativeEvidence,
    boundary_retest: QualitativeEvidence,
) -> SetupAssemblyAssessment:
    relation = _validate_range_external_context(
        range_evidence,
        deviation=deviation,
        external_poi=external_poi,
        external_relation=external_relation,
    )
    if relation.status != EvidenceStatus.PASS:
        return relation
    direction = _range_direction(deviation.side)
    for name, evidence in (("RETURN_INSIDE", return_inside), ("BOUNDARY_RETEST", boundary_retest)):
        if evidence.status == EvidenceStatus.FAIL:
            return _fail(f"RANGE_{name}_SOURCE_EVIDENCE_FAILED")
        if not evidence.provenance_ready:
            return SetupAssemblyAssessment(EvidenceStatus.UNKNOWN, f"WAIT_RANGE_{name}_QUALITATIVE_PROVENANCE")
    assert return_inside.known_at is not None and boundary_retest.known_at is not None
    if return_inside.known_at < deviation.known_at:
        return _fail("RANGE_RETURN_PRECEDES_DEVIATION")
    if boundary_retest.known_at < return_inside.known_at:
        return _fail("RANGE_RETEST_PRECEDES_RETURN_INSIDE")
    if not _context_active_at(range_evidence.obj, boundary_retest.known_at):
        return _fail("RANGE_CONTEXT_NOT_ACTIVE_AT_RETEST")
    return _assemble(
        context=range_evidence.obj,
        direction=direction,
        branch=SetupBranch.RANGE_CONSERVATIVE_RETURN_RETEST,
        known_at=boundary_retest.known_at,
        evidence_ids=(
            deviation.evidence_id,
            external_poi.object_id,
            external_relation.evidence_id or "",
            return_inside.evidence_id or "",
            boundary_retest.evidence_id or "",
        ),
        parent_objects=(external_poi,),
        source_rule_ids=("RANGE_CONSERVATIVE_ENTRY_001", "SETUP_RANGE_CONSERVATIVE_001"),
        provenance="SW10 conservative Range branch: external POI -> deviation -> return/acceptance -> boundary retest",
    )


@dataclass(frozen=True)
class _PoiSelection:
    status: EvidenceStatus
    reason: str
    poi: CausalSourceObject | None = None


def _select_unique_new_poi(
    candidates: Sequence[CausalSourceObject],
    *,
    direction: Direction,
    min_formation_at: datetime,
    decision_at: datetime,
) -> _PoiSelection:
    _aware("min_formation_at", min_formation_at)
    _aware("decision_at", decision_at)
    allowed_types = {
        SourceObjectType.POI,
        SourceObjectType.ORDER_BLOCK,
        SourceObjectType.BREAKER,
        SourceObjectType.FVG,
        SourceObjectType.STB_BTS,
    }
    eligible: list[CausalSourceObject] = []
    for candidate in candidates:
        if candidate.object_type not in allowed_types:
            continue
        if candidate.direction != direction.value:
            continue
        if candidate.formation_at < min_formation_at or candidate.known_at < min_formation_at:
            continue
        if candidate.known_at > decision_at:
            continue
        if not _context_active_at(candidate, decision_at):
            continue
        eligible.append(candidate)
    if not eligible:
        return _PoiSelection(EvidenceStatus.UNKNOWN, "WAIT_NEW_SOURCE_VALID_ENTRY_POI")
    if len(eligible) > 1:
        return _PoiSelection(EvidenceStatus.UNKNOWN, "WAIT_NONUNIQUE_ENTRY_POI")
    return _PoiSelection(EvidenceStatus.PASS, "UNIQUE_NEW_SOURCE_VALID_ENTRY_POI", eligible[0])


def selection_poi(selection: _PoiSelection | SetupAssemblyAssessment) -> CausalSourceObject | None:
    return selection.poi if isinstance(selection, _PoiSelection) else None


def _validate_range_external_context(
    range_evidence: SourceRangeEvidence,
    *,
    deviation: RangeDeviationEvidence,
    external_poi: CausalSourceObject,
    external_relation: QualitativeEvidence,
) -> SetupAssemblyAssessment:
    if deviation.range_object_id != range_evidence.obj.object_id:
        return _fail("DEVIATION_DOES_NOT_BELONG_TO_RANGE")
    if deviation.known_at < range_evidence.obj.known_at:
        return _fail("DEVIATION_PRECEDES_RANGE_KNOWN_AT")
    if not _context_active_at(range_evidence.obj, deviation.known_at):
        return _fail("RANGE_NOT_ACTIVE_AT_DEVIATION")
    direction = _range_direction(deviation.side)
    if external_poi.direction != direction.value:
        return _fail("EXTERNAL_POI_DIRECTION_MISMATCH")
    if external_poi.known_at > deviation.known_at:
        return _fail("EXTERNAL_POI_NOT_KNOWN_AT_DEVIATION")
    if not _context_active_at(external_poi, deviation.known_at):
        return _fail("EXTERNAL_POI_NOT_ACTIVE_AT_DEVIATION")
    if external_relation.status == EvidenceStatus.FAIL:
        return _fail("EXTERNAL_POI_RELATION_SOURCE_EVIDENCE_FAILED")
    if not external_relation.provenance_ready:
        return SetupAssemblyAssessment(EvidenceStatus.UNKNOWN, "WAIT_EXTERNAL_POI_RELATION_PROVENANCE")
    assert external_relation.known_at is not None
    if external_relation.known_at > deviation.known_at:
        return _fail("EXTERNAL_POI_RELATION_NOT_KNOWN_AT_DEVIATION")
    return SetupAssemblyAssessment(EvidenceStatus.PASS, "RANGE_EXTERNAL_CONTEXT_VALID")


def _range_direction(side: RangeDeviationSide) -> Direction:
    return Direction.SHORT if side == RangeDeviationSide.HIGH else Direction.LONG


def _assemble(
    *,
    context: CausalSourceObject,
    direction: Direction,
    branch: SetupBranch,
    known_at: datetime,
    evidence_ids: Sequence[str],
    parent_objects: Sequence[CausalSourceObject],
    source_rule_ids: Sequence[str],
    provenance: str,
    refinement_timeframe_minutes: int | None = None,
    entry_poi_id: str | None = None,
) -> SetupAssemblyAssessment:
    _aware("setup known_at", known_at)
    if context.direction != direction.value:
        return _fail("SETUP_DIRECTION_DOES_NOT_MATCH_SOURCE_CONTEXT")
    if known_at < context.known_at:
        return _fail("SETUP_KNOWN_AT_PRECEDES_CONTEXT")
    if not _context_active_at(context, known_at):
        return _fail("SOURCE_CONTEXT_NOT_ACTIVE_AT_SETUP_TIME")
    for parent in parent_objects:
        if parent.known_at > known_at or not _context_active_at(parent, known_at):
            return _fail("SETUP_PARENT_NOT_CAUSALLY_ACTIVE")

    physical = CausalSourceObject.formed(
        object_type=SourceObjectType.PHYSICAL_IDEA,
        symbol=context.symbol,
        timeframe=context.timeframe,
        direction=direction.value,
        formation_at=context.formation_at,
        known_at=context.known_at,
        identity_parts={
            "context_object_id": context.object_id,
            "direction": direction.value,
        },
        source_rule_ids=tuple(context.source_rule_ids),
        technical_normalization_ids=("TN_PHYSICAL_IDEA_BRANCH_INDEPENDENT",),
        parent_object_ids=(context.object_id,),
        provenance="branch-independent physical source idea; no ranking, score or future outcome",
    )
    cleaned_ids = tuple(x for x in evidence_ids if x)
    setup_parent_ids = tuple(dict.fromkeys((physical.object_id, context.object_id) + tuple(p.object_id for p in parent_objects)))
    setup = CausalSourceObject.formed(
        object_type=SourceObjectType.SETUP,
        symbol=context.symbol,
        timeframe=(
            f"{context.timeframe}->{refinement_timeframe_minutes}m"
            if refinement_timeframe_minutes is not None
            else context.timeframe
        ),
        direction=direction.value,
        formation_at=context.known_at,
        known_at=known_at,
        identity_parts={
            "physical_idea_id": physical.object_id,
            "branch": branch.value,
            "evidence_ids": cleaned_ids,
            "refinement_timeframe_minutes": refinement_timeframe_minutes,
            "entry_poi_id": entry_poi_id,
        },
        source_rule_ids=tuple(source_rule_ids),
        technical_normalization_ids=(
            "TN_SETUP_BRANCH_EXPLICIT_NO_PRECEDENCE",
            "TN_SETUP_DIRECTION_FROM_SOURCE_CONTEXT",
        ),
        parent_object_ids=setup_parent_ids,
        provenance=provenance,
    )
    return SetupAssemblyAssessment(
        EvidenceStatus.PASS,
        "SOURCE_SETUP_ASSEMBLED",
        SourceSetupEvidence(
            physical_idea=physical,
            setup=setup,
            branch=branch,
            direction=direction,
            context_object_id=context.object_id,
            known_at=known_at,
            evidence_ids=cleaned_ids,
            refinement_timeframe_minutes=refinement_timeframe_minutes,
            entry_poi_id=entry_poi_id,
        ),
    )


def _context_active_at(obj: CausalSourceObject, at: datetime) -> bool:
    if obj.known_at > at:
        return False
    state = obj.state_at(at)
    return (
        state.formation_valid
        and state.invalidated_at is None
        and state.status not in (ObjectStatus.INVALIDATED, ObjectStatus.CANCELLED)
    )


def _fail(reason: str) -> SetupAssemblyAssessment:
    return SetupAssemblyAssessment(EvidenceStatus.FAIL, reason)


def _aware(name: str, value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
