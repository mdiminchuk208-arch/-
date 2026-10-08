from __future__ import annotations

from dataclasses import dataclass

from crypto_bot.common.models import Candle, Direction
from crypto_bot.strategy.trade_plan import PriceZone, SourceStopReference


@dataclass(frozen=True)
class OrderBlockEvidence:
    liquidity_swept: bool
    aggressive_impulse: bool
    engulfs_previous_candle: bool
    bos_confirmed: bool
    in_htf_poi: bool
    in_structural_impulse: bool
    aligned_with_trend: bool
    imbalance_present: bool = False
    test_number: int = 1
    ltf_reaction_confirmed: bool = False


@dataclass(frozen=True)
class OrderBlockAssessment:
    formation_valid: bool
    trade_eligible: bool
    quality: str
    reasons: tuple[str, ...]

    @property
    def valid(self) -> bool:
        """Backward-compatible alias: an OB is actionable only when trade_eligible is True."""
        return self.trade_eligible


def assess_order_block(e: OrderBlockEvidence) -> OrderBlockAssessment:
    """
    Conservative source-conformance assessment for an Order Block evidence bundle.

    Source formation elements represented here:
    - liquidity sweep,
    - aggressive impulse that engulfs the prior candle,
    - BOS confirmation,
    - location in an HTF POI,
    - location inside a structural impulse,
    - working with the impulse/trend.

    IMB is intentionally NOT silently resolved. Page 2 says the signal is most accurate
    when IMB appears, while the later violation example warns against ignoring IMB.
    Until this source ambiguity is frozen by explicit project decision/backtest, evidence
    without IMB may be formation-compatible but is not marked trade-eligible.

    Re-tests are NOT treated as invalid Order Block formations. The source says first test
    is preferred in ~90% of cases, while a repeated entry may be considered after LTF
    reaction. Therefore a repeated test is trade-eligible here only when that LTF reaction
    has been separately confirmed.
    """
    if e.test_number < 1:
        raise ValueError("test_number must be >= 1")

    required = {
        "liquidity_swept": e.liquidity_swept,
        "aggressive_impulse": e.aggressive_impulse,
        "engulfs_previous_candle": e.engulfs_previous_candle,
        "bos_confirmed": e.bos_confirmed,
        "in_htf_poi": e.in_htf_poi,
        "in_structural_impulse": e.in_structural_impulse,
        "aligned_with_trend": e.aligned_with_trend,
    }
    failed = tuple(name for name, ok in required.items() if not ok)
    if failed:
        return OrderBlockAssessment(False, False, "INVALID", failed)

    if not e.imbalance_present:
        return OrderBlockAssessment(
            True,
            False,
            "IMB_UNRESOLVED",
            ("imb_hard_vs_soft_rule_unresolved",),
        )

    quality = "A"

    if e.test_number == 1:
        return OrderBlockAssessment(True, True, quality, tuple())

    if not e.ltf_reaction_confirmed:
        return OrderBlockAssessment(
            True,
            False,
            quality,
            ("repeat_test_requires_ltf_reaction",),
        )

    return OrderBlockAssessment(True, True, quality, tuple())


@dataclass(frozen=True)
class QualifiedOrderBlockGeometry:
    zone: PriceZone
    entry_reference_price: float
    stop_reference: SourceStopReference
    policy: str = "SOURCE_CONFIRMED_OB_GEOMETRY"


def derive_qualified_order_block_geometry(*, direction: Direction, engulfed_candle: Candle, engulfing_candle: Candle, assessment: OrderBlockAssessment, stop_policy: str = "SOURCE_OB_EXTREME") -> QualifiedOrderBlockGeometry:
    """Geometry only for an already trade-eligible OB; does not detect an OB."""
    if direction not in (Direction.LONG, Direction.SHORT):
        raise ValueError("direction must be LONG or SHORT")
    if not engulfed_candle.is_closed or not engulfing_candle.is_closed:
        raise ValueError("OB geometry requires closed candles")
    if engulfed_candle.close_time != engulfing_candle.open_time:
        raise ValueError("engulfing candle must immediately follow the engulfed candle")
    if not assessment.trade_eligible:
        raise ValueError("order block must already be source-qualified and trade-eligible")
    zone=PriceZone(engulfed_candle.low, engulfed_candle.high)
    entry=engulfed_candle.high if direction == Direction.LONG else engulfed_candle.low
    if stop_policy == "SOURCE_OB_EXTREME":
        stop=engulfed_candle.low if direction == Direction.LONG else engulfed_candle.high
    elif stop_policy == "SOURCE_ENGULFING_WICK":
        stop=engulfing_candle.low if direction == Direction.LONG else engulfing_candle.high
    else:
        raise ValueError("unsupported source stop policy")
    return QualifiedOrderBlockGeometry(zone=zone,entry_reference_price=entry,stop_reference=SourceStopReference(stop,stop_policy))
