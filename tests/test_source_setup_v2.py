from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from crypto_bot.common.models import Direction
from crypto_bot.strategy.causal_objects import CausalSourceObject, SourceObjectType
from crypto_bot.strategy.source_ob_breaker_v2 import BosReference, QualitativeEvidence, SourceOrderBlockEvidence
from crypto_bot.strategy.source_range_stb_v2 import RangeDeviationEvidence, RangeDeviationSide, SourceRangeEvidence
from crypto_bot.strategy.source_sfp_v2 import SfpOrigin, SourceSfpEvidence
from crypto_bot.strategy.source_setup_v2 import (
    CausalChainEvidence,
    LowerTimeframePair,
    SetupBranch,
    assemble_ob_conf_strict,
    assemble_ob_conservative_ltf,
    assemble_ob_direct_first_test,
    assemble_range_aggressive,
    assemble_sfp_ltf_bos_new_poi,
)
from crypto_bot.strategy.source_structure_liquidity_v2 import EvidenceStatus


BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def t(minutes: int) -> datetime:
    return BASE + timedelta(minutes=minutes)


def obj(
    object_type: SourceObjectType,
    *,
    direction: Direction | None,
    timeframe: str | int,
    minute: int,
    token: str,
) -> CausalSourceObject:
    at = t(minute)
    return CausalSourceObject.formed(
        object_type=object_type,
        symbol="BTC-USDT-SWAP",
        timeframe=timeframe,
        direction=direction.value if direction is not None else None,
        formation_at=at,
        known_at=at,
        identity_parts={"fixture": token},
        source_rule_ids=("TEST_SOURCE_RULE",),
        provenance="Stage-7 unit fixture",
    )


def ob_evidence(*, timeframe: str | int = 60, direction: Direction = Direction.LONG) -> SourceOrderBlockEvidence:
    context = obj(SourceObjectType.ORDER_BLOCK, direction=direction, timeframe=timeframe, minute=0, token=f"ob-{timeframe}-{direction.value}")
    return SourceOrderBlockEvidence(
        obj=context,
        direction=direction,
        zone_low=99,
        zone_high=101,
        candidate_open_time=t(0),
        candidate_close_time=t(1),
        impulse_close_time=t(2),
        raid_parent_id="liq",
        htf_poi_parent_id="htf",
        structure_parent_id="structure",
        bos_evidence_id="ob-bos",
        imbalance_present=True,
    )


def sfp_evidence(*, timeframe: str | int = 60, direction: Direction = Direction.LONG) -> SourceSfpEvidence:
    context = obj(SourceObjectType.SFP, direction=direction, timeframe=timeframe, minute=0, token=f"sfp-{timeframe}-{direction.value}")
    return SourceSfpEvidence(
        obj=context,
        direction=direction,
        origin=SfpOrigin.STRUCTURAL_LIQUIDITY,
        parent_liquidity_id="liq",
        swept_side="low" if direction == Direction.LONG else "high",
        liquidity_price=98,
        sweep_open_time=t(0),
        sweep_close_time=t(1),
        confirmation_open_time=t(1),
        pattern_extreme=97,
    )


class SourceSetupStage7Tests(unittest.TestCase):
    def test_direct_and_conf_branches_share_physical_idea_but_not_setup_id(self):
        ob = ob_evidence()
        direct = assemble_ob_direct_first_test(ob)
        strict = assemble_ob_conf_strict(
            ob,
            conf=BosReference(Direction.LONG, t(5), "conf-1", kind="CONF"),
        )
        self.assertEqual(direct.status, EvidenceStatus.PASS)
        self.assertEqual(strict.status, EvidenceStatus.PASS)
        assert direct.evidence is not None and strict.evidence is not None
        self.assertEqual(direct.evidence.physical_idea.object_id, strict.evidence.physical_idea.object_id)
        self.assertNotEqual(direct.evidence.setup.object_id, strict.evidence.setup.object_id)
        self.assertFalse(direct.evidence.setup.trade_eligible)
        self.assertFalse(strict.evidence.setup.trade_eligible)
        self.assertEqual(direct.evidence.branch, SetupBranch.OB_DIRECT_FIRST_TEST)
        self.assertEqual(strict.evidence.branch, SetupBranch.OB_CONF_STRICT)

    def test_ob_ltf_pair_must_match_parent_context_timeframe(self):
        ob = ob_evidence(timeframe=60)
        result = assemble_ob_conservative_ltf(
            ob,
            pair=LowerTimeframePair(240, 5),
            ltf_reaction=CausalChainEvidence("react", t(3), Direction.LONG, "fixture", (ob.obj.object_id,)),
            ltf_bos=BosReference(Direction.LONG, t(4), "bos"),
            entry_poi_candidates=(),
            decision_at=t(5),
        )
        self.assertEqual(result.status, EvidenceStatus.FAIL)
        self.assertEqual(result.reason, "LTF_PAIR_CONTEXT_TIMEFRAME_MISMATCH")

    def test_unparseable_parent_timeframe_stays_unknown_instead_of_inventing_mapping(self):
        ob = ob_evidence(timeframe="CONTEXT")
        result = assemble_ob_conservative_ltf(
            ob,
            pair=LowerTimeframePair(60, 5),
            ltf_reaction=CausalChainEvidence("react", t(3), Direction.LONG, "fixture", (ob.obj.object_id,)),
            ltf_bos=BosReference(Direction.LONG, t(4), "bos"),
            entry_poi_candidates=(),
            decision_at=t(5),
        )
        self.assertEqual(result.status, EvidenceStatus.UNKNOWN)
        self.assertEqual(result.reason, "WAIT_CONTEXT_TIMEFRAME_NORMALIZATION")

    def test_ob_conservative_chain_uses_one_new_causal_poi(self):
        ob = ob_evidence(timeframe="1h")
        poi = obj(SourceObjectType.ORDER_BLOCK, direction=Direction.LONG, timeframe=5, minute=5, token="entry-poi")
        result = assemble_ob_conservative_ltf(
            ob,
            pair=LowerTimeframePair(60, 5),
            ltf_reaction=CausalChainEvidence("react", t(3), Direction.LONG, "fixture", (ob.obj.object_id,)),
            ltf_bos=BosReference(Direction.LONG, t(4), "bos"),
            entry_poi_candidates=(poi,),
            decision_at=t(5),
        )
        self.assertEqual(result.status, EvidenceStatus.PASS)
        assert result.evidence is not None
        self.assertEqual(result.evidence.entry_poi_id, poi.object_id)
        self.assertEqual(result.evidence.refinement_timeframe_minutes, 5)
        self.assertEqual(result.evidence.direction, Direction.LONG)
        self.assertFalse(result.evidence.setup.trade_eligible)

    def test_future_poi_cannot_retroactively_make_prior_unique_poi_nonunique(self):
        ob = ob_evidence(timeframe=60)
        current = obj(SourceObjectType.ORDER_BLOCK, direction=Direction.LONG, timeframe=5, minute=5, token="current")
        future = obj(SourceObjectType.ORDER_BLOCK, direction=Direction.LONG, timeframe=5, minute=9, token="future")
        kwargs = dict(
            ob=ob,
            pair=LowerTimeframePair(60, 5),
            ltf_reaction=CausalChainEvidence("react", t(3), Direction.LONG, "fixture", (ob.obj.object_id,)),
            ltf_bos=BosReference(Direction.LONG, t(4), "bos"),
            decision_at=t(6),
        )
        without_future = assemble_ob_conservative_ltf(entry_poi_candidates=(current,), **kwargs)
        with_future = assemble_ob_conservative_ltf(entry_poi_candidates=(current, future), **kwargs)
        self.assertEqual(without_future.status, EvidenceStatus.PASS)
        self.assertEqual(with_future.status, EvidenceStatus.PASS)
        assert without_future.evidence is not None and with_future.evidence is not None
        self.assertEqual(without_future.evidence.setup.object_id, with_future.evidence.setup.object_id)
        self.assertEqual(without_future.evidence.entry_poi_id, current.object_id)

    def test_multiple_already_known_entry_pois_remain_unresolved_not_ranked(self):
        ob = ob_evidence(timeframe=60)
        a = obj(SourceObjectType.ORDER_BLOCK, direction=Direction.LONG, timeframe=5, minute=5, token="a")
        b = obj(SourceObjectType.FVG, direction=Direction.LONG, timeframe=5, minute=6, token="b")
        result = assemble_ob_conservative_ltf(
            ob,
            pair=LowerTimeframePair(60, 5),
            ltf_reaction=CausalChainEvidence("react", t(3), Direction.LONG, "fixture", (ob.obj.object_id,)),
            ltf_bos=BosReference(Direction.LONG, t(4), "bos"),
            entry_poi_candidates=(a, b),
            decision_at=t(7),
        )
        self.assertEqual(result.status, EvidenceStatus.UNKNOWN)
        self.assertEqual(result.reason, "WAIT_NONUNIQUE_ENTRY_POI")

    def test_sfp_requires_pair_to_reference_its_actual_context_timeframe(self):
        sfp = sfp_evidence(timeframe=240)
        result = assemble_sfp_ltf_bos_new_poi(
            sfp,
            pair=LowerTimeframePair(60, 15),
            ltf_bos=BosReference(Direction.LONG, t(3), "bos"),
            entry_poi_candidates=(),
            decision_at=t(4),
        )
        self.assertEqual(result.status, EvidenceStatus.FAIL)
        self.assertEqual(result.reason, "LTF_PAIR_CONTEXT_TIMEFRAME_MISMATCH")

    def test_range_direction_comes_from_deviation_not_range_forming_impulse(self):
        range_obj = obj(SourceObjectType.RANGE, direction=Direction.LONG, timeframe=60, minute=0, token="range")
        range_evidence = SourceRangeEvidence(
            obj=range_obj,
            impulse_direction=Direction.LONG,
            lower=90,
            upper=110,
            midpoint=100,
            first_boundary_price=110,
            second_boundary_price=90,
            impulse_evidence_id="impulse",
            correction_evidence_id="correction",
        )
        deviation = RangeDeviationEvidence(
            evidence_id="dev-high",
            range_object_id=range_obj.object_id,
            side=RangeDeviationSide.HIGH,
            boundary_price=110,
            extreme_price=112,
            known_at=t(4),
        )
        external = obj(SourceObjectType.ORDER_BLOCK, direction=Direction.SHORT, timeframe=60, minute=1, token="external-short")
        relation = QualitativeEvidence(EvidenceStatus.PASS, "external-relation", t(2))
        result = assemble_range_aggressive(
            range_evidence,
            deviation=deviation,
            external_poi=external,
            external_relation=relation,
        )
        self.assertEqual(result.status, EvidenceStatus.PASS)
        assert result.evidence is not None
        self.assertEqual(result.evidence.direction, Direction.SHORT)
        self.assertIn("TN_RANGE_SETUP_DIRECTION_FROM_DEVIATION", result.evidence.setup.technical_normalization_ids)
        self.assertFalse(result.evidence.setup.trade_eligible)


if __name__ == "__main__":
    unittest.main()
