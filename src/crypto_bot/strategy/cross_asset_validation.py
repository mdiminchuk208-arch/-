from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


DEFAULT_CROSS_ASSET_BASKET: tuple[str, ...] = (
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "XRPUSDT",
    "BNBUSDT",
    "DOGEUSDT",
    "ADAUSDT",
    "LINKUSDT",
    "AVAXUSDT",
    "LTCUSDT",
)

REQUIRED_TIMEFRAMES: tuple[int, ...] = (5, 15, 60, 240)


@dataclass(frozen=True)
class SymbolRobustnessChecks:
    symbol: str
    data_qa_passed: bool
    evaluation_span_passed: bool
    source_recovery_free: bool
    suffix_stability_exact: bool
    trade_entry_safety_passed: bool
    mtf_runtime_passed: bool

    @property
    def passed(self) -> bool:
        return all(
            (
                self.data_qa_passed,
                self.evaluation_span_passed,
                self.source_recovery_free,
                self.suffix_stability_exact,
                self.trade_entry_safety_passed,
                self.mtf_runtime_passed,
            )
        )


@dataclass(frozen=True)
class CrossAssetGateDecision:
    required_basket: tuple[str, ...]
    analyzed_symbols: tuple[str, ...]
    missing_required_symbols: tuple[str, ...]
    failed_symbols: tuple[str, ...]
    gate_closed: bool
    note: str


def normalize_symbols(symbols: Sequence[str]) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in symbols:
        symbol = str(raw).strip().upper()
        if not symbol:
            raise ValueError("symbols cannot contain empty values")
        if symbol in seen:
            raise ValueError(f"duplicate symbol: {symbol}")
        seen.add(symbol)
        out.append(symbol)
    if not out:
        raise ValueError("at least one symbol is required")
    return tuple(out)


def decide_cross_asset_gate(
    checks: Mapping[str, SymbolRobustnessChecks],
    *,
    required_basket: Sequence[str] = DEFAULT_CROSS_ASSET_BASKET,
) -> CrossAssetGateDecision:
    """Decide only the project QA gate; never infer a trading edge from event counts.

    TECHNICAL_NORMALIZATION / project QA policy:
    the default pre-entry basket contains ten liquid USDT perpetual symbols. The gate
    closes only when every required symbol is present and all causal/safety invariants
    pass. BOS/SFP/opportunity counts are diagnostics and intentionally do not enter the
    pass/fail decision.
    """
    required = normalize_symbols(required_basket)
    analyzed = normalize_symbols(tuple(checks)) if checks else ()
    missing = tuple(symbol for symbol in required if symbol not in checks)
    failed = tuple(symbol for symbol in required if symbol in checks and not checks[symbol].passed)
    closed = not missing and not failed
    note = (
        "Cross-asset robustness gate is CLOSED: the complete required basket passed data, causal suffix, "
        "source-mode provenance, MTF runtime and trade-entry safety invariants. Event counts were not used "
        "as a quality/profitability threshold."
        if closed
        else "Cross-asset robustness gate remains OPEN until every required symbol is present and passes all "
        "causal/safety invariants. Event counts are diagnostic only."
    )
    return CrossAssetGateDecision(
        required_basket=required,
        analyzed_symbols=analyzed,
        missing_required_symbols=missing,
        failed_symbols=failed,
        gate_closed=closed,
        note=note,
    )
