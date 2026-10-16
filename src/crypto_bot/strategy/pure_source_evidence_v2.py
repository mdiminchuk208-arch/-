from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

from crypto_bot.common.models import Candle
from crypto_bot.strategy.causal_objects import CausalSourceObject, SourceObjectType, require_closed_candles
from crypto_bot.strategy.source_structure_liquidity_v2 import (
    SourceSwingEvidence,
    StructuralLiquidityEvidence,
    StructureLeg,
    bos_breaks_active_leg,
    confirmed_source_swings,
    latest_structure_leg,
    structural_liquidity,
)


@dataclass(frozen=True)
class StructureLiquiditySnapshot:
    """Causal evidence available at the end of one closed-candle prefix.

    This is deliberately not a setup/trade engine. It exposes Stage-2 SOURCE
    evidence so prefix replay and future-mutation QA do not need legacy
    SourceEngine labels or PROJECT policy.
    """

    decision_at: datetime | None
    swings: tuple[SourceSwingEvidence, ...]
    liquidity: tuple[StructuralLiquidityEvidence, ...]
    latest_formed_leg: StructureLeg | None
    structure_object: CausalSourceObject | None
    bos_on_last_close: bool


def build_structure_liquidity_snapshot(
    candles: Sequence[Candle],
    *,
    symbol: str,
    timeframe: str | int,
) -> StructureLiquiditySnapshot:
    """Build a deterministic Stage-2 evidence snapshot from a closed prefix.

    The function never reads data outside ``candles``. Re-running it on a longer
    history must leave all prior swing/pool stable IDs unchanged.

    ``latest_formed_leg`` means latest structure geometry identifiable from the
    prefix; it is not a claim that the leg survived every later lifecycle event.
    BOS/CONF lifecycle remains an event layer and must not rewrite object history.
    """

    require_closed_candles(candles)
    if not candles:
        return StructureLiquiditySnapshot(None, (), (), None, None, False)

    swings = confirmed_source_swings(candles, symbol=symbol, timeframe=timeframe)
    pools: list[StructuralLiquidityEvidence] = []
    for index, swing in enumerate(swings):
        # Context may use only swings already known by this swing's known_at.
        causal_leg = latest_structure_leg(swings[: index + 1])
        pools.append(
            structural_liquidity(
                swing,
                symbol=symbol,
                timeframe=timeframe,
                active_leg=causal_leg,
            )
        )

    leg = latest_structure_leg(swings)
    structure_obj = _structure_object(symbol=symbol, timeframe=timeframe, leg=leg) if leg else None

    # BOS on this close must be evaluated against a structure known before the
    # current close. A swing whose right candle is the current candle cannot be
    # used retroactively as the protected point for that same close.
    prior_swings = tuple(s for s in swings if s.obj.known_at < candles[-1].close_time)
    prior_leg = latest_structure_leg(prior_swings)
    bos = bos_breaks_active_leg(candles[-1], prior_leg) if prior_leg is not None else False

    return StructureLiquiditySnapshot(
        decision_at=candles[-1].close_time,
        swings=swings,
        liquidity=tuple(pools),
        latest_formed_leg=leg,
        structure_object=structure_obj,
        bos_on_last_close=bos,
    )


def _structure_object(*, symbol: str, timeframe: str | int, leg: StructureLeg) -> CausalSourceObject:
    direction = "LONG" if leg.direction == "BULLISH" else "SHORT"
    return CausalSourceObject.formed(
        object_type=SourceObjectType.STRUCTURE,
        symbol=symbol,
        timeframe=timeframe,
        direction=direction,
        formation_at=leg.known_at,
        known_at=leg.known_at,
        identity_parts={
            "direction": leg.direction,
            "protected_pivot_id": leg.protected_swing_id,
            "extreme_pivot_id": leg.extreme_swing_id,
            "protected_price": leg.protected_price,
            "extreme_price": leg.extreme_price,
        },
        source_rule_ids=("MS_TREND_001",),
        technical_normalization_ids=("MS_INTERLEAVED_PAIRING_V2",),
        parent_object_ids=(leg.protected_swing_id, leg.extreme_swing_id),
        provenance="SW4/SW5 structure geometry from causally confirmed interleaved swings",
    )
