from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from crypto_bot.common.models import Candle


@dataclass(frozen=True)
class SwingPoint:
    index: int
    kind: str  # "high" | "low"
    price: float


def is_swing_high(left: Candle, center: Candle, right: Candle) -> bool:
    """SOURCE RULE: both side candles have lower highs than the center."""
    return center.high > left.high and center.high > right.high


def is_swing_low(left: Candle, center: Candle, right: Candle) -> bool:
    """SOURCE RULE: both side candles have higher lows than the center."""
    return center.low < left.low and center.low < right.low


def confirmed_swings(candles: Sequence[Candle]) -> list[SwingPoint]:
    """
    TECHNICAL NORMALIZATION:
    A three-candle swing is only emitted after the right-hand candle is closed.
    This avoids using future information before it is available.
    """
    out: list[SwingPoint] = []
    if len(candles) < 3:
        return out
    for i in range(1, len(candles) - 1):
        left, center, right = candles[i - 1], candles[i], candles[i + 1]
        if not (left.is_closed and center.is_closed and right.is_closed):
            continue
        if is_swing_high(left, center, right):
            out.append(SwingPoint(i, "high", center.high))
        if is_swing_low(left, center, right):
            out.append(SwingPoint(i, "low", center.low))
    return out


def bullish_bos(close: float, key_bearish_structure_high: float) -> bool:
    """SOURCE RULE normalization: candle body closes above the key high."""
    return close > key_bearish_structure_high


def bearish_bos(close: float, key_bullish_structure_low: float) -> bool:
    """SOURCE RULE normalization: candle body closes below the key low."""
    return close < key_bullish_structure_low
