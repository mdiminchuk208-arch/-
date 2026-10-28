"""Integration contracts between Strategy Engine and external platform layers.

This package transports engine facts. It does not define or modify PURE SOURCE
trading semantics.
"""

from .events import STRATEGY_EVENT_SCHEMA, StrategyObjectSnapshot

__all__ = ["STRATEGY_EVENT_SCHEMA", "StrategyObjectSnapshot"]
