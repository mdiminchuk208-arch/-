from __future__ import annotations

from math import isfinite


def source_aligned_risk_fraction(value: float) -> bool:
    """SOURCE RULE range from the specialized risk-management material: 0.25%-2%."""
    return isfinite(value) and 0.0025 <= value <= 0.02


def risk_budget(equity: float, risk_fraction: float) -> float:
    if not isfinite(equity) or equity <= 0:
        raise ValueError("equity must be finite and positive")
    if not isfinite(risk_fraction) or risk_fraction <= 0:
        raise ValueError("risk_fraction must be finite and positive")
    return equity * risk_fraction


def position_quantity_simple(
    *,
    equity: float,
    risk_fraction: float,
    entry_price: float,
    stop_price: float,
    enforce_source_range: bool = True,
) -> float:
    """
    Phase-1 sizing skeleton: risk budget divided by price distance to stop.

    By default it enforces the source-aligned 0.25%-2% risk range because Phase 1 is the
    conservative baseline. Later execution-aware sizing will also include entry/exit fees,
    both-side slippage, contract specifics and portfolio/venue caps.
    """
    if not all(isfinite(v) and v > 0 for v in (entry_price, stop_price)):
        raise ValueError("prices must be finite and positive")
    if enforce_source_range and not source_aligned_risk_fraction(risk_fraction):
        raise ValueError("risk_fraction is outside the source-aligned 0.25%-2% range")
    loss_per_unit = abs(entry_price - stop_price)
    if loss_per_unit == 0:
        raise ValueError("stop price cannot equal entry price")
    return risk_budget(equity, risk_fraction) / loss_per_unit
