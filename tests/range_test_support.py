"""Legacy pre-1.4.18 range tests with explicit manual clarity PASS.

Production defaults remain fail-closed: no review means UNREVIEWED.
"""
from crypto_bot.strategy.range_engine import (
    RangeBoundaryClarityReview,
    analyze_ranges as _analyze_ranges,
    augment_market_report_with_range_sfps as _augment_market_report_with_range_sfps,
    range_review_key,
)


def _pass_reviews(report):
    return {
        range_review_key(item): RangeBoundaryClarityReview.PASS
        for item in report.ranges
    }


def analyze_ranges(candles, base_report, *, params=None):
    initial = _analyze_ranges(candles, base_report, params=params)
    return _analyze_ranges(
        candles,
        base_report,
        params=params,
        boundary_clarity_reviews=_pass_reviews(initial),
    )


def augment_market_report_with_range_sfps(candles, base_report, *, params=None):
    initial = _analyze_ranges(candles, base_report, params=params)
    return _augment_market_report_with_range_sfps(
        candles,
        base_report,
        params=params,
        boundary_clarity_reviews=_pass_reviews(initial),
    )
