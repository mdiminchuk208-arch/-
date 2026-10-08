from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from crypto_bot.common.models import Candle, Direction


@dataclass(frozen=True)
class SFPResult:
    valid: bool
    direction: Direction | None
    reason: str


def detect_sfp(sweep: Candle, next_candle: Candle, liquidity_level: float, swept_side: str) -> SFPResult:
    """
    SOURCE RULE implementation from the Base trading-tools material.

    Explicit upper-side example:
    - external liquidity above a structural/range high is swept,
    - the sweep candle closes back below the level,
    - the next candle opens below it,
    - only after formation is complete may the strategy move to LTF and seek BOS.

    Lower-side handling is the deterministic mirrored normalization of the same pattern.
    It is kept explicit in the Source Rule Registry so it is not confused with verbatim
    wording from the source.
    """
    if not isfinite(liquidity_level) or liquidity_level <= 0:
        raise ValueError("liquidity_level must be finite and positive")
    if not sweep.is_closed:
        return SFPResult(False, None, "sweep candle not closed")
    if next_candle.open_time < sweep.close_time:
        return SFPResult(False, None, "next candle is not chronologically after sweep candle")
    if next_candle.open_time != sweep.close_time:
        return SFPResult(False, None, "missing immediate next candle; SFP confirmation is unavailable")

    if swept_side == "high":
        swept = sweep.high > liquidity_level
        closed_back = sweep.close < liquidity_level
        next_open_inside = next_candle.open < liquidity_level
        valid = swept and closed_back and next_open_inside
        return SFPResult(
            valid,
            Direction.SHORT if valid else None,
            "valid bearish SFP" if valid else "bearish SFP conditions not met",
        )

    if swept_side == "low":
        swept = sweep.low < liquidity_level
        closed_back = sweep.close > liquidity_level
        next_open_inside = next_candle.open > liquidity_level
        valid = swept and closed_back and next_open_inside
        return SFPResult(
            valid,
            Direction.LONG if valid else None,
            "valid bullish SFP" if valid else "bullish SFP conditions not met",
        )

    raise ValueError("swept_side must be 'high' or 'low'")
