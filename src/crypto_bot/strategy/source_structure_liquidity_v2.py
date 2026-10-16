from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Sequence

from crypto_bot.common.models import Candle
from crypto_bot.strategy.causal_objects import (
    CausalSourceObject,
    SourceObjectType,
    require_closed_candles,
)
from crypto_bot.strategy.structure import is_swing_high, is_swing_low


class EvidenceStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class LiquidityLocation(str, Enum):
    INTERNAL = "INTERNAL"
    EXTERNAL = "EXTERNAL"


class EqualLiquidityKind(str, Enum):
    EQH = "EQH"
    EQL = "EQL"


@dataclass(frozen=True)
class SourceSwingEvidence:
    obj: CausalSourceObject
    side: str
    price: float
    center_index: int
    confirmed_index: int
    swing_time: datetime

    def __post_init__(self) -> None:
        if self.side not in ("high", "low"):
            raise ValueError("swing side must be high or low")


@dataclass(frozen=True)
class StructuralLiquidityEvidence:
    obj: CausalSourceObject
    swing_object_id: str
    side: str
    price: float
    location: LiquidityLocation


@dataclass(frozen=True)
class EqualLiquidityEvidence:
    kind: EqualLiquidityKind
    status: EvidenceStatus
    left_swing_id: str
    right_swing_id: str
    exact_price: bool
    directional_tilt_valid: bool
    substructure_pair_confirmed: bool | None
    reasonable_tilt_confirmed: bool | None
    reason: str


@dataclass(frozen=True)
class StructureLeg:
    direction: str
    protected_swing_id: str
    extreme_swing_id: str
    protected_price: float
    extreme_price: float
    known_at: datetime

    def __post_init__(self) -> None:
        if self.direction not in ("BULLISH", "BEARISH"):
            raise ValueError("direction must be BULLISH or BEARISH")


def confirmed_source_swings(
    candles: Sequence[Candle],
    *,
    symbol: str,
    timeframe: str | int,
) -> tuple[SourceSwingEvidence, ...]:
    """Emit strict three-candle SOURCE swings causally.

    SOURCE: SW5 p2 defines Swing High/Low using three consecutive candles.
    TECHNICAL_NORMALIZATION: the swing becomes knowable only after the right-hand
    candle closes. No future candle is inspected.
    """
    require_closed_candles(candles)
    out: list[SourceSwingEvidence] = []
    for right_index in range(2, len(candles)):
        left = candles[right_index - 2]
        center = candles[right_index - 1]
        right = candles[right_index]
        if is_swing_high(left, center, right):
            out.append(
                _swing(
                    symbol=symbol,
                    timeframe=timeframe,
                    side="high",
                    price=center.high,
                    center_index=right_index - 1,
                    confirmed_index=right_index,
                    swing_time=center.open_time,
                    known_at=right.close_time,
                )
            )
        if is_swing_low(left, center, right):
            out.append(
                _swing(
                    symbol=symbol,
                    timeframe=timeframe,
                    side="low",
                    price=center.low,
                    center_index=right_index - 1,
                    confirmed_index=right_index,
                    swing_time=center.open_time,
                    known_at=right.close_time,
                )
            )
    return tuple(out)


def latest_structure_leg(swings: Sequence[SourceSwingEvidence]) -> StructureLeg | None:
    """Return the latest causally identifiable interleaved HH/HL or LL/LH leg.

    SOURCE: SW4 p3 and SW5 p2-3 require higher highs + higher lows for bullish
    structure and lower lows + lower highs for bearish structure.
    TECHNICAL_NORMALIZATION: machine pairing is chronological/interleaved; this
    prevents two unrelated same-side points from being paired into a structure.
    """
    bullish: tuple[int, StructureLeg] | None = None
    bearish: tuple[int, StructureLeg] | None = None

    for index, current in enumerate(swings):
        if current.side == "high":
            candidate = _bullish_leg_ending_at(swings, index)
            if candidate is not None:
                bullish = (current.confirmed_index, candidate)
        else:
            candidate = _bearish_leg_ending_at(swings, index)
            if candidate is not None:
                bearish = (current.confirmed_index, candidate)

    if bullish is None:
        return bearish[1] if bearish else None
    if bearish is None:
        return bullish[1]
    return bullish[1] if bullish[0] > bearish[0] else bearish[1]


def structural_liquidity(
    swing: SourceSwingEvidence,
    *,
    symbol: str,
    timeframe: str | int,
    active_leg: StructureLeg | None,
) -> StructuralLiquidityEvidence:
    """Map a confirmed structural swing into causal liquidity evidence.

    SOURCE: SW6 p12 places external liquidity at structural highs/lows and
    internal liquidity inside a formed impulse between its structural endpoints.
    No significance/ranking threshold is introduced here.

    Pool identity is the physical swing/side/price only. INTERNAL/EXTERNAL is a
    causal context label and is deliberately excluded from the stable ID so a
    later context interpretation cannot create a second physical pool identity.
    """
    if active_leg is None:
        location = LiquidityLocation.EXTERNAL
    else:
        low = min(active_leg.protected_price, active_leg.extreme_price)
        high = max(active_leg.protected_price, active_leg.extreme_price)
        location = LiquidityLocation.INTERNAL if low < swing.price < high else LiquidityLocation.EXTERNAL

    obj = CausalSourceObject.formed(
        object_type=SourceObjectType.LIQUIDITY_POOL,
        symbol=symbol,
        timeframe=timeframe,
        direction=None,
        formation_at=swing.obj.formation_at,
        known_at=swing.obj.known_at,
        identity_parts={
            "swing_object_id": swing.obj.object_id,
            "side": swing.side,
            "price": swing.price,
        },
        source_rule_ids=("LIQ_STRUCTURAL_001",),
        technical_normalization_ids=("TN_LIQUIDITY_LOCATION_FROM_ACTIVE_STRUCTURE_LEG",),
        parent_object_ids=(swing.obj.object_id,),
        provenance="SW6 p12 structural liquidity; location is a causal context label, not physical pool identity",
    )
    return StructuralLiquidityEvidence(obj, swing.obj.object_id, swing.side, swing.price, location)


def assess_equal_liquidity(
    left: SourceSwingEvidence,
    right: SourceSwingEvidence,
    *,
    kind: EqualLiquidityKind,
    substructure_pair_confirmed: bool | None,
    reasonable_tilt_confirmed: bool | None,
) -> EqualLiquidityEvidence:
    """Assess EQH/EQL without inventing a numeric price tolerance.

    SOURCE: SW6 p7-10 says EQH/EQL are formed between substructure swings;
    they need not be ruler-flat. A reasonable tilt is allowed, with EQH left
    maximum above right and EQL left minimum below right. The source gives no
    numeric definition of "reasonable", therefore non-exact tilted geometry
    remains UNKNOWN until qualitative evidence is supplied.
    """
    expected_side = "high" if kind == EqualLiquidityKind.EQH else "low"
    if left.side != expected_side or right.side != expected_side:
        return _equal_result(kind, EvidenceStatus.FAIL, left, right, False, False,
                             substructure_pair_confirmed, reasonable_tilt_confirmed,
                             "WRONG_SWING_SIDE")
    if right.confirmed_index <= left.confirmed_index:
        return _equal_result(kind, EvidenceStatus.FAIL, left, right, False, False,
                             substructure_pair_confirmed, reasonable_tilt_confirmed,
                             "NON_CAUSAL_ORDER")

    exact = left.price == right.price
    directional_tilt_valid = (
        exact
        or (kind == EqualLiquidityKind.EQH and left.price > right.price)
        or (kind == EqualLiquidityKind.EQL and left.price < right.price)
    )
    if not directional_tilt_valid:
        return _equal_result(kind, EvidenceStatus.FAIL, left, right, exact, False,
                             substructure_pair_confirmed, reasonable_tilt_confirmed,
                             "SOURCE_TILT_DIRECTION_VIOLATION")
    if substructure_pair_confirmed is False:
        return _equal_result(kind, EvidenceStatus.FAIL, left, right, exact, True,
                             substructure_pair_confirmed, reasonable_tilt_confirmed,
                             "NOT_SUBSTRUCTURE_SWINGS")
    if substructure_pair_confirmed is None:
        return _equal_result(kind, EvidenceStatus.UNKNOWN, left, right, exact, True,
                             substructure_pair_confirmed, reasonable_tilt_confirmed,
                             "WAIT_SUBSTRUCTURE_EVIDENCE")
    if exact:
        return _equal_result(kind, EvidenceStatus.PASS, left, right, True, True,
                             substructure_pair_confirmed, reasonable_tilt_confirmed,
                             "EXACT_EQUAL_SUBSTRUCTURE_SWINGS")
    if reasonable_tilt_confirmed is True:
        return _equal_result(kind, EvidenceStatus.PASS, left, right, False, True,
                             substructure_pair_confirmed, reasonable_tilt_confirmed,
                             "QUALITATIVE_REASONABLE_TILT_CONFIRMED")
    if reasonable_tilt_confirmed is False:
        return _equal_result(kind, EvidenceStatus.FAIL, left, right, False, True,
                             substructure_pair_confirmed, reasonable_tilt_confirmed,
                             "TILT_NOT_REASONABLE")
    return _equal_result(kind, EvidenceStatus.UNKNOWN, left, right, False, True,
                         substructure_pair_confirmed, reasonable_tilt_confirmed,
                         "WAIT_QUALITATIVE_REASONABLE_TILT")


def bos_breaks_active_leg(candle: Candle, leg: StructureLeg) -> bool:
    """SOURCE BOS acceptance: body close beyond the protected point (SW5 p4-5)."""
    if not candle.is_closed:
        raise ValueError("BOS cannot use an unfinished candle")
    if leg.direction == "BULLISH":
        return candle.close < leg.protected_price
    return candle.close > leg.protected_price


def strict_liquidity_take(candle: Candle, pool: StructuralLiquidityEvidence) -> bool:
    """Causal strict-wick representation of a liquidity raid.

    This is explicitly TECHNICAL_NORMALIZATION, not a SOURCE numeric rule.
    SOURCE defines removal/sweep but does not specify a close-vs-wick machine
    threshold. The legacy strict penetration rule is preserved only as a named
    deterministic representation pending further SOURCE evidence.
    """
    if not candle.is_closed:
        raise ValueError("liquidity take cannot use an unfinished candle")
    return candle.high > pool.price if pool.side == "high" else candle.low < pool.price


def _swing(
    *,
    symbol: str,
    timeframe: str | int,
    side: str,
    price: float,
    center_index: int,
    confirmed_index: int,
    swing_time: datetime,
    known_at: datetime,
) -> SourceSwingEvidence:
    rule_id = "MS_SWING_HIGH_001" if side == "high" else "MS_SWING_LOW_001"
    obj = CausalSourceObject.formed(
        object_type=SourceObjectType.SWING,
        symbol=symbol,
        timeframe=timeframe,
        direction=None,
        formation_at=known_at,
        known_at=known_at,
        identity_parts={
            "side": side,
            "price": price,
            "center_index": center_index,
            "confirmed_index": confirmed_index,
            "swing_time": swing_time,
        },
        source_rule_ids=(rule_id,),
        technical_normalization_ids=("SWING_CONFIRM_001",),
        provenance="SW5 p2 strict three-candle swing; known after right candle close",
    )
    return SourceSwingEvidence(obj, side, price, center_index, confirmed_index, swing_time)


def _bullish_leg_ending_at(swings: Sequence[SourceSwingEvidence], end_index: int) -> StructureLeg | None:
    new_high = swings[end_index]
    if new_high.side != "high":
        return None
    lows = [s for s in swings[:end_index] if s.side == "low" and s.center_index < new_high.center_index]
    if not lows:
        return None
    candidate_low = lows[-1]
    previous_highs = [s for s in swings[:end_index] if s.side == "high" and s.center_index < candidate_low.center_index]
    if not previous_highs:
        return None
    previous_high = previous_highs[-1]
    previous_lows = [s for s in swings[:end_index] if s.side == "low" and s.center_index < previous_high.center_index]
    if not previous_lows:
        return None
    previous_low = previous_lows[-1]
    if new_high.price <= previous_high.price or candidate_low.price <= previous_low.price:
        return None
    return StructureLeg(
        "BULLISH",
        candidate_low.obj.object_id,
        new_high.obj.object_id,
        candidate_low.price,
        new_high.price,
        new_high.obj.known_at,
    )


def _bearish_leg_ending_at(swings: Sequence[SourceSwingEvidence], end_index: int) -> StructureLeg | None:
    new_low = swings[end_index]
    if new_low.side != "low":
        return None
    highs = [s for s in swings[:end_index] if s.side == "high" and s.center_index < new_low.center_index]
    if not highs:
        return None
    candidate_high = highs[-1]
    previous_lows = [s for s in swings[:end_index] if s.side == "low" and s.center_index < candidate_high.center_index]
    if not previous_lows:
        return None
    previous_low = previous_lows[-1]
    previous_highs = [s for s in swings[:end_index] if s.side == "high" and s.center_index < previous_low.center_index]
    if not previous_highs:
        return None
    previous_high = previous_highs[-1]
    if new_low.price >= previous_low.price or candidate_high.price >= previous_high.price:
        return None
    return StructureLeg(
        "BEARISH",
        candidate_high.obj.object_id,
        new_low.obj.object_id,
        candidate_high.price,
        new_low.price,
        new_low.obj.known_at,
    )


def _equal_result(
    kind: EqualLiquidityKind,
    status: EvidenceStatus,
    left: SourceSwingEvidence,
    right: SourceSwingEvidence,
    exact: bool,
    directional_tilt_valid: bool,
    substructure_pair_confirmed: bool | None,
    reasonable_tilt_confirmed: bool | None,
    reason: str,
) -> EqualLiquidityEvidence:
    return EqualLiquidityEvidence(
        kind,
        status,
        left.obj.object_id,
        right.obj.object_id,
        exact,
        directional_tilt_valid,
        substructure_pair_confirmed,
        reasonable_tilt_confirmed,
        reason,
    )
