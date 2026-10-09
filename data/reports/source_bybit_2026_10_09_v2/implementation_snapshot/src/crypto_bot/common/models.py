from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from math import isfinite


@dataclass(frozen=True)
class Candle:
    open_time: datetime
    close_time: datetime
    open: float
    high: float
    low: float
    close: float
    is_closed: bool = True

    def __post_init__(self) -> None:
        if self.open_time.utcoffset() is None or self.close_time.utcoffset() is None:
            raise ValueError("candle timestamps must be timezone-aware")
        if not all(isfinite(v) for v in (self.open, self.high, self.low, self.close)):
            raise ValueError("OHLC values must be finite")
        if self.low > self.high:
            raise ValueError("low cannot exceed high")
        if not (self.low <= self.open <= self.high):
            raise ValueError("open must be within [low, high]")
        if not (self.low <= self.close <= self.high):
            raise ValueError("close must be within [low, high]")
        if self.close_time <= self.open_time:
            raise ValueError("close_time must be after open_time")


class Direction(str, Enum):
    LONG = "long"
    SHORT = "short"


class RuleKind(str, Enum):
    SOURCE = "SOURCE_RULE"
    NORMALIZATION = "TECHNICAL_NORMALIZATION"
    EXPERIMENT = "BACKTEST_PARAMETER"
