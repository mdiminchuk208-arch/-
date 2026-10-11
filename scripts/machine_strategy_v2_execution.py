"""Frozen theoretical normalized-R execution; no exchange access, no admission changes."""

from __future__ import annotations

from bisect import bisect_left
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal
from itertools import islice
from statistics import mean, median

from machine_strategy_v2_core import BRANCHES, ident
from original_v1_1_financial_data import END

D = Decimal
FEE = D("0.0006")
SLIPPAGE = D("0.0002")
ACCOUNTING = "NORMALIZED_R_RESEARCH_MODE_UNROUNDED_THEORETICAL_PRICES"
COST_MULTIPLIERS = ("0.5", "1", "2")


def execute(case, market, *, starts=None):
    bars = market[15]
    starts = [b.start for b in bars] if starts is None else starts
    begin = bisect_left(starts, case["decision_at"])
    entry, stop, target = (
        D(case[k])
        for k in ("theoretical_entry", "fixed_initial_stop", "theoretical_target")
    )
    long = case["direction"] == "LONG"
    if not (stop < entry < target if long else target < entry < stop):
        raise ValueError("Invalid frozen price geometry")
    if (
        case["confirmation_known_at"] > case["decision_at"]
        or case["FTA_known_at"] > case["decision_at"]
    ):
        raise ValueError("Future pre-entry evidence")
    result = {
        **case,
        "accounting_mode": ACCOUNTING,
        "status": "UNFILLED_EXPIRED",
        "filled": False,
        "closed": False,
        "fill_at": None,
        "exit_at": None,
        "fill_price": None,
        "exit_price": None,
        "Gross_R": None,
        "Fees_R": None,
        "Slippage_R": None,
        "Funding_R": None,
        "Net_R": None,
        "funding_treatment": "UNAVAILABLE_EXCLUDED_NOT_ASSERTED_ZERO",
        "trade_entry_allowed": False,
    }
    fill = None
    for bar in islice(bars, begin, None):
        if fill is None:
            if bar.start >= case["order_expires_at"]:
                break
            past_stop = bar.open <= stop if long else bar.open >= stop
            past_target = bar.open >= target if long else bar.open <= target
            if past_stop or past_target:
                result["status"] = "GAP_INVALIDATED_BEFORE_FILL"
                break
            at_open = bar.open <= entry if long else bar.open >= entry
            touched = bar.low <= entry if long else bar.high >= entry
            if not touched:
                continue
            fill = bar.open if at_open else entry
            risk = abs(fill - stop)
            if risk <= 0:
                raise ValueError("Nonpositive actual theoretical risk")
            result.update(
                filled=True,
                fill_price=str(fill),
                fill_at=bar.start if at_open else bar.end,
                fill_observation_at=bar.end,
                fill_time_bounds=[bar.start, bar.start if at_open else bar.end],
                initial_price_risk=str(risk),
                first_eligible_touch=ident(
                    "execution_first_touch", case["entry_poi_id"], bar.start
                ),
                consumed_at=bar.end,
                known_entry_fee_R=str(FEE * fill / risk),
                known_entry_slippage_R=str(SLIPPAGE * fill / risk),
            )
            hit_stop = bar.low <= stop if long else bar.high >= stop
            hit_target = bar.high >= target if long else bar.low <= target
            if (hit_stop and hit_target) or (not at_open and hit_target):
                result["status"] = "WAIT_INTRABAR_ORDER"
                break
            if hit_stop:
                return close_result(result, stop, bar.end, "FIXED_INITIAL_STOP")
            if hit_target:
                return close_result(result, target, bar.end, "STRUCTURAL_FTA")
        else:
            # OPEN is a causal ordered event before this completed bar's extrema.
            if bar.open <= stop if long else bar.open >= stop:
                return close_result(result, bar.open, bar.start, "STOP_GAP_OPEN")
            if bar.open >= target if long else bar.open <= target:
                return close_result(result, bar.open, bar.start, "TARGET_GAP_OPEN")
            hit_stop = bar.low <= stop if long else bar.high >= stop
            hit_target = bar.high >= target if long else bar.low <= target
            if hit_stop and hit_target:
                result["status"] = "WAIT_INTRABAR_ORDER"
                break
            if hit_stop:
                return close_result(result, stop, bar.end, "FIXED_INITIAL_STOP")
            if hit_target:
                return close_result(result, target, bar.end, "STRUCTURAL_FTA")
        # Original SFP pattern body invalidation observed only at completed setup TF close.
        if case["branch"] == "SFP" and bar.end % (case["setup_tf"] * 60) == 0:
            invalid = (
                bar.close < D(case["stop_anchor"])
                if long
                else bar.close > D(case["stop_anchor"])
            )
            if invalid:
                return close_result(
                    result, bar.close, bar.end, "SFP_PATTERN_BODY_INVALIDATION"
                )
    if result["status"] != "WAIT_INTRABAR_ORDER" and fill is not None:
        result["status"] = "OPEN_CENSORED_EOF"
        result["censored_at"] = END
    elif result["status"] == "UNFILLED_EXPIRED" and (
        not bars or bars[-1].end < case["order_expires_at"]
    ):
        result["status"] = "ORDER_CENSORED_EOF"
    return result


def close_result(result, exit_price, at, reason):
    fill = D(result["fill_price"])
    risk = D(result["initial_price_risk"])
    sign = D(1) if result["direction"] == "LONG" else D(-1)
    gross = sign * (exit_price - fill) / risk
    fee = FEE * (fill + exit_price) / risk
    slip = SLIPPAGE * (fill + exit_price) / risk
    net = gross - fee - slip
    result.update(
        status="CLOSED",
        closed=True,
        exit_price=str(exit_price),
        exit_at=at,
        exit_reason=reason,
        Gross_R=str(gross),
        Fees_R=str(fee),
        Slippage_R=str(slip),
        Net_R=str(net),
        WIN=net > 0,
        LOSS=net < 0,
        FLAT=net == 0,
        hold_hours=(at - result["fill_at"]) / 3600,
        exit_known_at=at,
        exit_time_bounds=[max(result["fill_at"], at - 900), at]
        if reason not in ("STOP_GAP_OPEN", "TARGET_GAP_OPEN")
        else [at, at],
    )
    return result


def stats(rows, *, cost_multiplier="1"):
    closed = sorted(
        (r for r in rows if r["closed"]), key=lambda r: (r["exit_at"], r["case_id"])
    )
    values = [
        float(
            D(r["Gross_R"]) - D(cost_multiplier) * (D(r["Fees_R"]) + D(r["Slippage_R"]))
        )
        for r in closed
    ]
    gains = [v for v in values if v > 0]
    losses = [-v for v in values if v < 0]
    win, loss = len(gains), len(losses)
    n = len(closed)
    gross = sum(float(r["Gross_R"]) for r in closed)
    fees = sum(float(r["Fees_R"]) for r in closed) * float(cost_multiplier)
    slip = sum(float(r["Slippage_R"]) for r in closed) * float(cost_multiplier)
    net = sum(values)
    if abs(gross - fees - slip - net) > 1e-7:
        raise ValueError("Cost accounting mismatch")
    equity = peak = 100.0
    dd = ddpct = 0.0
    streak = maxstreak = 0
    for v in values:
        equity += v
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
        ddpct = max(ddpct, (peak - equity) / peak * 100)
        streak = streak + 1 if v < 0 else 0
        maxstreak = max(maxstreak, streak)
    avgwin = mean(gains) if gains else None
    avgloss = mean(losses) if losses else None
    holds = [r["hold_hours"] for r in closed]
    return {
        "cases": len(rows),
        "orders": len(rows),
        "filled": sum(r["filled"] for r in rows),
        "CLOSED": n,
        "open_censored": sum(r["status"] == "OPEN_CENSORED_EOF" for r in rows),
        "order_censored": sum(r["status"] == "ORDER_CENSORED_EOF" for r in rows),
        "intrabar_unresolved": sum(r["status"] == "WAIT_INTRABAR_ORDER" for r in rows),
        "WIN": win,
        "LOSS": loss,
        "FLAT": n - win - loss,
        "WR_percent": win / n * 100 if n else None,
        "Gross_R": gross,
        "Fees_R": fees,
        "Slippage_R": slip,
        "Funding_R": None,
        "Net_R_ex_funding": net,
        "PF_net": sum(gains) / sum(losses) if losses else None,
        "Expectancy_R": net / n if n else None,
        "AvgR": mean(values) if values else None,
        "MedianR": median(values) if values else None,
        "AvgWin_R": avgwin,
        "AvgLoss_R": -avgloss if avgloss is not None else None,
        "payoff_ratio": avgwin / avgloss
        if avgwin is not None and avgloss is not None
        else None,
        "breakeven_WR_percent": avgloss / (avgwin + avgloss) * 100
        if avgwin is not None and avgloss is not None
        else None,
        "MaxDD_R": dd,
        "MaxDD_percent_closed_case_curve": ddpct,
        "max_loss_streak": maxstreak,
        "average_hold_hours": mean(holds) if holds else None,
        "median_hold_hours": median(holds) if holds else None,
        "equity_curve_convention": "100 initial R units; one unit price risk per independent case; sorted observable exit time then case ID. Diagnostic closed-case curve, no shared margin/portfolio claim.",
        "net_definition": "Closed independent cases only; funding unavailable/excluded. All amounts are normalized risk units, not exchange account currency.",
        "status_counts": dict(Counter(r["status"] for r in rows)),
        "known_entry_fees_all_filled_R": sum(
            float(r.get("known_entry_fee_R", 0)) for r in rows
        ),
        "cost_multiplier": cost_multiplier,
        "trade_entry_allowed": False,
    }


def calendar(stamp):
    return datetime.fromtimestamp(stamp, UTC)


def breakdowns(rows):
    groups = {
        "symbol": ("BTCUSDT", "ETHUSDT"),
        "direction": ("LONG", "SHORT"),
        "branch": BRANCHES,
        "setup_tf": (15, 60, 240, 1440),
        "year": (2023, 2024, 2025),
        "month": tuple(
            f"{y}-{m:02d}" for y in (2023, 2024, 2025) for m in range(1, 13)
        ),
    }
    out = {}
    for key, values in groups.items():
        out[key] = {}
        for value in values:
            subset = []
            for r in rows:
                date = calendar(r["decision_at"])
                actual = (
                    date.year
                    if key == "year"
                    else date.strftime("%Y-%m")
                    if key == "month"
                    else r[key]
                )
                if actual == value:
                    subset.append(r)
            out[key][str(value)] = stats(subset)
    return out
