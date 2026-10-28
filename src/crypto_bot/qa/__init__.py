"""Optional QA adapters. Nothing in this package grants trading authority."""

from .tradingview import (
    TradingViewQAPlan,
    TradingViewQARunner,
    TradingViewQAStep,
    build_tradingview_qa_plan,
)

__all__ = [
    "TradingViewQAPlan",
    "TradingViewQARunner",
    "TradingViewQAStep",
    "build_tradingview_qa_plan",
]
