"""Exact venue-cost/book/scoring arithmetic; no strategy or account state."""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from fractions import Fraction

NOTIONALS = ("1000", "5000", "10000", "25000", "50000")


def exact(value):
    if type(value) not in (str, int, Decimal, Fraction):
        raise ValueError("EXACT_DECIMAL_INPUT_REQUIRED")
    if isinstance(value, Fraction):
        return value
    d = Decimal(value)
    if not d.is_finite():
        raise ValueError("FINITE_NUMBER_REQUIRED")
    return Fraction(d)


def display(value):
    """Ranking uses rational values; repeating display rounds at 18 decimals."""
    value = exact(value)
    with localcontext() as ctx:
        ctx.prec = max(
            80, len(str(abs(value.numerator))) + len(str(value.denominator)) + 25
        )
        d = Decimal(value.numerator) / Decimal(value.denominator)
        d = d.quantize(Decimal("1e-18"), rounding=ROUND_HALF_EVEN)
    return format(d, "f").rstrip("0").rstrip(".") if d else "0"


def median(values):
    values = sorted(exact(v) for v in values)
    if not values:
        raise ValueError("NONEMPTY_SAMPLE_REQUIRED")
    n = len(values)
    return values[n // 2] if n % 2 else (values[n // 2 - 1] + values[n // 2]) / 2


def fee_scenarios(maker, taker):
    if maker is None or taker is None:
        return {"available": False, "reason": "BASE_API_FEE_UNVERIFIED"}
    m, t = exact(maker), exact(taker)
    if t < 0 or abs(m) > 1 or t > 1:
        raise ValueError("FEE_FRACTION_REQUIRED")
    rates = {
        "TAKER_TAKER": 2 * t,
        "MAKER_TAKER": m + t,
        "MAKER_MAKER": 2 * m,
        "BLENDED_50_50_TURNOVER": m + t,
    }
    return {
        "available": True,
        "equal_entry_exit_notional_assumption": True,
        "funding_included": False,
        "maker_fill_guaranteed": False,
        "scenarios": {
            name: {
                "fraction": display(rate),
                "percent": display(rate * 100),
                "bps": display(rate * 10000),
                "usd": {n: display(rate * exact(n)) for n in NOTIONALS},
            }
            for name, rate in rates.items()
        },
    }


def levels(rows, side):
    if side not in {"BUY", "SELL"}:
        raise ValueError("BUY_OR_SELL_REQUIRED")
    parsed = [(exact(p), exact(q)) for p, q in rows]
    if not parsed or any(p <= 0 or q < 0 for p, q in parsed):
        raise ValueError("POSITIVE_PRICE_AND_BASE_SIZE_REQUIRED")
    # A zero visible size supplies no liquidity; omission is conservative and
    # avoids inventing a fractional contract behind an integer-size API field.
    parsed = [(p, q) for p, q in parsed if q > 0]
    if not parsed:
        raise ValueError("NONEMPTY_EXECUTABLE_BOOK_REQUIRED")
    if len({p for p, q in parsed}) != len(parsed):
        raise ValueError("DUPLICATE_BOOK_PRICE")
    return sorted(parsed, reverse=side == "SELL")


def market_impact(rows, notional, side, mid):
    """Quote-budget VWAP, exact continuous depth model, no fill guarantee.

    No order is sent. Lot rounding, queue/future exits and realized slippage need
    the later venue-specific execution compatibility gate.
    """
    remaining, quantity = exact(notional), Fraction(0)
    if remaining <= 0 or exact(mid) <= 0:
        raise ValueError("POSITIVE_NOTIONAL_AND_MID_REQUIRED")
    for price, size in levels(rows, side):
        quote = min(remaining, price * size)
        quantity += quote / price
        remaining -= quote
        if remaining == 0:
            break
    if remaining:
        return {
            "filled": False,
            "uncovered_quote": display(remaining),
            "vwap": None,
            "impact_bps": None,
        }
    vwap = exact(notional) / quantity
    impact = (
        (vwap / exact(mid) - 1) * 10000
        if side == "BUY"
        else (1 - vwap / exact(mid)) * 10000
    )
    if impact < 0:
        raise ValueError("CROSSED_OR_INVALID_MID")
    return {
        "filled": True,
        "uncovered_quote": "0",
        "vwap": display(vwap),
        "impact_bps": display(impact),
        "impact_rational": [str(impact.numerator), str(impact.denominator)],
    }


def analyze_book(book):
    bids, asks = levels(book["bids"], "SELL"), levels(book["asks"], "BUY")
    bid, ask = bids[0][0], asks[0][0]
    if bid >= ask:
        raise ValueError("UNCROSSED_BOOK_REQUIRED")
    mid = (bid + ask) / 2
    depths = {}
    for band in (1, 2, 5, 10):
        bound = Fraction(band, 10000)
        depths[str(band)] = {
            "bid_quote": display(
                sum((p * q for p, q in bids if (mid - p) / mid <= bound), Fraction(0))
            ),
            "ask_quote": display(
                sum((p * q for p, q in asks if (p - mid) / mid <= bound), Fraction(0))
            ),
        }
    return {
        "source_id": book["source_id"],
        "time_utc": book["time_utc"],
        "spread_bps": display((ask - bid) / mid * 10000),
        "mid": display(mid),
        "depth_quote_within_bps_from_mid": depths,
        "notionals": {
            n: {
                "BUY": market_impact(book["asks"], n, "BUY", mid),
                "SELL": market_impact(book["bids"], n, "SELL", mid),
            }
            for n in NOTIONALS
        },
        "model": "Exact quote-budget continuous-book estimate; no lot/queue/future-fill guarantee",
    }


def lot_grid_impact(book, notional, side, base_lot):
    """Separate lot-valid model, never substituted for preregistered scoring.

    Target quantity floors the requested USD/mid quantity to a documented base
    lot. Visible residual quantities below a whole lot are conservatively omitted.
    The returned actual reference/cash notional may differ from requested USD.
    """
    if base_lot is None:
        return {"available": False, "reason": "DOCUMENTED_BASE_LOT_REQUIRED"}
    lot = exact(base_lot)
    if lot <= 0:
        raise ValueError("POSITIVE_LOT_REQUIRED")
    bids, asks = levels(book["bids"], "SELL"), levels(book["asks"], "BUY")
    mid = (bids[0][0] + asks[0][0]) / 2
    if bids[0][0] >= asks[0][0]:
        raise ValueError("UNCROSSED_BOOK_REQUIRED")
    target_ratio = exact(notional) / (mid * lot)
    target = (target_ratio.numerator // target_ratio.denominator) * lot
    if target <= 0:
        return {"available": False, "reason": "TARGET_BELOW_ONE_LOT"}
    remaining, quote = target, Fraction(0)
    for price, size in levels(book["asks"] if side == "BUY" else book["bids"], side):
        available_ratio = size / lot
        available = (available_ratio.numerator // available_ratio.denominator) * lot
        take = min(remaining, available)
        quote += take * price
        remaining -= take
        if remaining == 0:
            break
    if remaining:
        return {"available": False, "reason": "INSUFFICIENT_WHOLE_LOT_DEPTH"}
    vwap = quote / target
    impact = (vwap / mid - 1) * 10000 if side == "BUY" else (1 - vwap / mid) * 10000
    return {
        "available": True,
        "base_lot": display(lot),
        "requested_usd": str(notional),
        "target_base_quantity": display(target),
        "actual_reference_notional": display(target * mid),
        "actual_quote_notional": display(quote),
        "vwap": display(vwap),
        "impact_bps": display(impact),
        "source_id": book["source_id"],
        "future_execution_guaranteed": False,
        "scoring_model_replaced": False,
    }


def as_ratio(value):
    return Fraction(int(value[0]), int(value[1]))


def liquidity_summary(books, *, units_confirmed, remove_source=None):
    samples, cells, failures = {}, [], []
    for symbol in ("BTC", "ETH"):
        chosen = [b for b in books.get(symbol, []) if b["source_id"] != remove_source]
        # Repeated cached same source time+same levels is not another independent
        # sample. Retain all original source IDs in evidence, use one assessment.
        unique: dict[tuple, dict] = {}
        for b in chosen:
            key = (
                b["time_utc"],
                tuple(tuple(v) for v in b["bids"]),
                tuple(tuple(v) for v in b["asks"]),
            )
            unique.setdefault(key, b)
        assessed = []
        for b in unique.values():
            try:
                assessed.append(analyze_book(b))
            except ValueError as exc:
                failures.append({"source_id": b["source_id"], "reason": str(exc)})
        samples[symbol] = assessed
        if len(assessed) < 2:
            continue
        for n in NOTIONALS:
            for side in ("BUY", "SELL"):
                results = [s["notionals"][n][side] for s in assessed]
                if not all(r["filled"] for r in results):
                    failures.append(
                        {
                            "symbol": symbol,
                            "notional": n,
                            "side": side,
                            "reason": "INSUFFICIENT_VISIBLE_DEPTH",
                        }
                    )
                    continue
                values = [as_ratio(r["impact_rational"]) for r in results]
                cells.append(
                    {
                        "symbol": symbol,
                        "notional": n,
                        "side": side,
                        "median_bps": display(median(values)),
                        "median_rational": [
                            str(median(values).numerator),
                            str(median(values).denominator),
                        ],
                        "worst_observed_bps": display(max(values)),
                    }
                )
    complete = (
        len(cells) == 20 and not failures and all(len(samples[s]) >= 2 for s in samples)
    )
    eligible = complete and units_confirmed is True
    mean = (
        sum((as_ratio(c["median_rational"]) for c in cells), Fraction(0)) / 20
        if complete
        else None
    )
    return {
        "samples": samples,
        "spread_aggregation": {
            symbol: {
                "median_bps": display(median([row["spread_bps"] for row in rows])),
                "worst_observed_bps": display(
                    max(exact(row["spread_bps"]) for row in rows)
                ),
            }
            for symbol, rows in samples.items()
            if rows
        },
        "cells": cells,
        "invalid_or_incomplete": failures,
        "book_units_confirmed": units_confirmed is True,
        "complete_sizes_and_two_samples": complete,
        "scoring_usable": eligible,
        "mean_impact_bps": display(mean) if mean is not None else None,
        "mean_impact_rational": [str(mean.numerator), str(mean.denominator)]
        if mean is not None
        else None,
        "stablecoin_to_usd_par_normalization": True,
        "not_strategy_results": True,
    }


def band_score(value, bounds, scores):
    if value is None:
        return 0
    for upper, score in zip(bounds, scores, strict=True):
        if exact(value) <= exact(upper):
            return int(score)
    return 0


def evidence_points(indicators):
    if len(indicators) != 5:
        raise ValueError("FIVE_FROZEN_INDICATORS_REQUIRED")
    for item in indicators:
        if item["confirmed"] is not None and type(item["confirmed"]) is not bool:
            raise ValueError("LITERAL_CONFIRMATION_REQUIRED")
        if item["confirmed"] is True and not item["source_ids"]:
            raise ValueError("SOURCE_CITATION_REQUIRED")
    return sum(item["confirmed"] is True for item in indicators)


def weighted_score(points, weights):
    if sum(exact(w) for w in weights.values()) != 100 or set(points) != set(weights):
        raise ValueError("FROZEN_WEIGHTS_AND_CRITERIA_REQUIRED")
    return sum((exact(weights[k]) * exact(points[k]) / 5 for k in weights), Fraction(0))


def shifted_weights(weights, change):
    delta = exact(change)
    if delta not in {Fraction(-5), Fraction(5)}:
        raise ValueError("PREREGISTERED_SHIFT_ONLY")
    prior = exact(weights["cost"])
    return {
        k: prior + delta
        if k == "cost"
        else exact(v) * (100 - prior - delta) / (100 - prior)
        for k, v in weights.items()
    }


def rank(rows):
    return sorted(rows, key=lambda r: (-as_ratio(r["score_rational"]), r["venue"]))
