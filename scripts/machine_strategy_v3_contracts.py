"""Pure, non-financial v3 contracts. No historical case adapter or outcome runner.

Every selector here is a machine pre-outcome rule. Raw family events must be
supplied by a separately reviewed causal adapter before a financial run.
"""

from __future__ import annotations

from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal, InvalidOperation
from itertools import pairwise
from re import fullmatch

VERSION = "MACHINE_STRATEGY_v3"
ROLE = "NONFINANCIAL_CONTRACT_CORE"
FAMILIES = ("SFP", "OB", "BREAKER", "STB", "RANGE")
FAMILY_INHERITANCE = {
    "SFP": {"v2": "M2_SFP", "source": "S_SFP_FORMATION", "entry": "M2_ENTRY"},
    "OB": {"v2": "M2_OB", "source": "S_OB_FORMATION", "entry": "M2_ENTRY"},
    "BREAKER": {
        "v2": "M2_BREAKER",
        "source": "S_BREAKER_FORMATION",
        "entry": "M2_ENTRY",
    },
    "STB": {"v2": "M2_STB", "source": "S_STB_FORMATION", "entry": "M2_ENTRY"},
    "RANGE": {"v2": "M2_RANGE", "source": "S_RANGE_FORMATION", "entry": "M2_ENTRY"},
}
FEE_PER_LEG = Decimal("0.0006")
SLIPPAGE_PER_LEG = Decimal("0.0002")
K_PER_LEG = FEE_PER_LEG + SLIPPAGE_PER_LEG
ORDER_LIFETIME_SECONDS = 3600
CONTRACT_TYPE = "USDT_LINEAR_PERPETUAL"
FORBIDDEN_INPUT_FIELDS = frozenset(
    {
        "gross_r",
        "net_r",
        "fees_r",
        "slippage_r",
        "funding_r",
        "pnl",
        "profit",
        "loss",
        "win",
        "pf",
        "expectancy",
        "realized_return",
        "exit_price",
        "exit_reason",
        "closed_trade",
        "outcome",
    }
)


class ContractWait(ValueError):
    """Missing causal observation; never infer a financial outcome."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


class ContractReject(ValueError):
    """Observed evidence contradicts an executable plan."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def decimal(value: object) -> Decimal:
    number = Decimal(str(value))
    if not number.is_finite():
        raise ContractReject("REJECT_NONFINITE_NUMBER")
    return number


def exact_timestamp(value: object) -> int:
    """Only JSON integer timestamps are valid; bool and numeric coercion are unsafe."""
    if type(value) is not int:
        raise ContractReject("REJECT_NONINTEGER_TIMESTAMP")
    return value


def require_known_at(record: dict, decision_at: int) -> None:
    """Recursively validate feature provenance; ban realized outcome inputs."""
    exact_timestamp(decision_at)
    if "known_at" not in record:
        raise ContractReject("REJECT_MISSING_KNOWN_AT")

    def walk(value: object, parent_known_at: int | None) -> None:
        if isinstance(value, dict):
            keys = {str(k).lower() for k in value}
            if keys & FORBIDDEN_INPUT_FIELDS:
                raise ContractReject("REJECT_OUTCOME_INPUT_FIELD")
            for key, field in value.items():
                if field is not None and (
                    str(key).endswith("_at")
                    or key in {"start", "end", "effective_from", "effective_until"}
                ):
                    exact_timestamp(field)
            known = (
                exact_timestamp(value["known_at"])
                if "known_at" in value
                else parent_known_at
            )
            if known is None or known > decision_at:
                raise ContractReject("REJECT_FUTURE_KNOWN_AT")
            if (
                "end_swing_at" in value
                and exact_timestamp(value["end_swing_at"]) > known
            ):
                raise ContractReject("REJECT_FUTURE_SWING_CENTER")
            for child in value.values():
                walk(child, known)
        elif isinstance(value, (list, tuple)):
            for child in value:
                walk(child, parent_known_at)

    walk(record, None)


def proven_tick_epoch(
    epochs: list[dict], symbol: str, contract_type: str, at: int, decision_at: int
) -> dict:
    """Return the unique causally known, verified tick epoch covering an event."""
    exact_timestamp(at)
    exact_timestamp(decision_at)
    if contract_type != CONTRACT_TYPE:
        raise ContractWait("WAIT_HISTORICAL_TICK_METADATA")
    matches = []
    for candidate in epochs:
        if (
            candidate.get("symbol") != symbol
            or candidate.get("contract_type") != contract_type
        ):
            continue
        try:
            catalogue_known_at = exact_timestamp(candidate["known_at"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ContractWait("WAIT_HISTORICAL_TICK_METADATA") from exc
        if catalogue_known_at > decision_at:
            continue
        try:
            effective_from = exact_timestamp(candidate["effective_from"])
            effective_until = exact_timestamp(candidate["effective_until"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ContractWait("WAIT_HISTORICAL_TICK_METADATA") from exc
        if not effective_from < effective_until:
            raise ContractWait("WAIT_HISTORICAL_TICK_METADATA")
        if not effective_from <= at < effective_until:
            continue
        try:
            source_known_at = exact_timestamp(candidate["source_known_at"])
            effective_proof_known_at = exact_timestamp(
                candidate["effective_proof_known_at"]
            )
            source_sha256 = str(candidate["source_sha256"])
            tick = decimal(candidate["tick"])
        except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
            raise ContractWait("WAIT_HISTORICAL_TICK_METADATA") from exc
        if (
            candidate.get("verified") is not True
            or not fullmatch(r"[0-9a-fA-F]{64}", source_sha256)
            or int(source_sha256, 16) == 0
            or tick <= 0
            or source_known_at > decision_at
            or effective_proof_known_at > decision_at
        ):
            raise ContractWait("WAIT_HISTORICAL_TICK_METADATA")
        matches.append(candidate)
    if len(matches) != 1:
        raise ContractWait("WAIT_HISTORICAL_TICK_METADATA")
    return dict(matches[0])


def _valid_leg(leg: dict | None, decision_at: int) -> bool:
    if leg is None:
        return False
    require_known_at(leg, decision_at)
    direction = leg["direction"]
    origin, endpoint = decimal(leg["origin"]), decimal(leg["endpoint"])
    return (direction == "LONG" and origin < endpoint) or (
        direction == "SHORT" and endpoint < origin
    )


def frame_state(
    *,
    current: dict | None,
    previous: dict | None,
    range_event: dict | None,
    latest_close: object,
    latest_close_known_at: int,
    decision_at: int,
) -> dict:
    """State from completed confirmed legs and a causal correction range."""
    exact_timestamp(latest_close_known_at)
    exact_timestamp(decision_at)
    if latest_close_known_at > decision_at:
        raise ContractReject("REJECT_FUTURE_STATE_CLOSE")
    uncertain = {
        "state": "UNCERTAIN",
        "direction": None,
        "known_at": latest_close_known_at,
    }
    if not _valid_leg(current, decision_at):
        return uncertain
    assert current is not None
    if (
        exact_timestamp(current["known_at"]) > latest_close_known_at
        or exact_timestamp(current.get("end_swing_at", current["known_at"]))
        > latest_close_known_at
    ):
        raise ContractReject("REJECT_FUTURE_STATE_STRUCTURE")
    invalidated_at = current.get("invalidated_at")
    if invalidated_at is not None:
        if exact_timestamp(invalidated_at) > latest_close_known_at:
            raise ContractReject("REJECT_FUTURE_STATE_INVALIDATION")
        return uncertain
    direction = current["direction"]
    origin = decimal(current["origin"])
    close = decimal(latest_close)
    if (direction == "LONG" and close < origin) or (
        direction == "SHORT" and close > origin
    ):
        return uncertain
    if previous is not None:
        if not _valid_leg(previous, decision_at):
            return uncertain
        if (
            exact_timestamp(previous["known_at"]) > latest_close_known_at
            or exact_timestamp(previous.get("end_swing_at", previous["known_at"]))
            > latest_close_known_at
        ):
            raise ContractReject("REJECT_FUTURE_STATE_STRUCTURE")
        if exact_timestamp(previous["known_at"]) >= exact_timestamp(
            current["known_at"]
        ):
            return uncertain
    if range_event is not None:
        require_known_at(range_event, decision_at)
        invalidated_at = range_event.get("invalidated_at")
        if (
            invalidated_at is not None
            and exact_timestamp(invalidated_at) > latest_close_known_at
        ):
            raise ContractReject("REJECT_FUTURE_RANGE_INVALIDATION")
        lo, hi = decimal(range_event["low"]), decimal(range_event["high"])
        reacted = range_event.get("eq_reacted_at")
        if (
            range_event["context_id"] == current["id"]
            and reacted is not None
            and exact_timestamp(reacted) <= latest_close_known_at
            and invalidated_at is None
            and not lo < close < hi
        ):
            raise ContractReject("REJECT_MISSING_RANGE_INVALIDATION")
        if (
            lo < hi
            and range_event["context_id"] == current["id"]
            and invalidated_at is None
            and reacted is not None
            and exact_timestamp(range_event["known_at"])
            <= exact_timestamp(reacted)
            <= latest_close_known_at
            and lo < close < hi
        ):
            return {
                "state": "RANGE",
                "direction": direction,
                "context_id": current["id"],
                "range_id": range_event["id"],
                "known_at": max(
                    exact_timestamp(range_event["eq_reacted_at"]), latest_close_known_at
                ),
            }
    if (
        previous
        and _valid_leg(previous, decision_at)
        and previous["direction"] == direction
    ):
        old_origin = decimal(previous["origin"])
        old_end = decimal(previous["endpoint"])
        end = decimal(current["endpoint"])
        advancing = (
            origin > old_origin and end > old_end
            if direction == "LONG"
            else origin < old_origin and end < old_end
        )
        if advancing:
            return {
                "state": "TREND_UP" if direction == "LONG" else "TREND_DOWN",
                "direction": direction,
                "context_id": current["id"],
                "known_at": latest_close_known_at,
            }
    return {
        "state": "TRANSITION_UP" if direction == "LONG" else "TRANSITION_DOWN",
        "direction": direction,
        "context_id": current["id"],
        "known_at": latest_close_known_at,
    }


def admit_context(
    *,
    states: dict[str, dict],
    direction: str,
    formation_bar: dict,
    m15_confirmation: dict,
    parent_pois: list[dict],
    decision_at: int,
    h4_range: dict | None = None,
) -> dict:
    """Symmetric H1/H4/D1 state gate; family signal remains separately required."""
    exact_timestamp(decision_at)
    formation_start = exact_timestamp(formation_bar["start"])
    formation_end = exact_timestamp(formation_bar["end"])
    if formation_end <= formation_start:
        raise ContractReject("REJECT_INVALID_FORMATION_TIME")
    if direction not in ("LONG", "SHORT"):
        raise ContractReject("REJECT_DIRECTION")
    for tf in ("H1", "H4", "D1"):
        if tf not in states:
            raise ContractWait("WAIT_NO_CONFIRMED_STATE")
        require_known_at(states[tf], decision_at)
        if states[tf]["state"] == "UNCERTAIN":
            raise ContractWait("WAIT_NO_CONFIRMED_STATE")
        state_name = states[tf]["state"]
        state_direction = states[tf]["direction"]
        if state_direction not in ("LONG", "SHORT") or state_name not in (
            "RANGE",
            "TREND_UP",
            "TREND_DOWN",
            "TRANSITION_UP",
            "TRANSITION_DOWN",
        ):
            raise ContractReject("REJECT_INCONSISTENT_STATE")
        if (state_name.endswith("_UP") and state_direction != "LONG") or (
            state_name.endswith("_DOWN") and state_direction != "SHORT"
        ):
            raise ContractReject("REJECT_INCONSISTENT_STATE")
    require_known_at(m15_confirmation, decision_at)
    if (
        m15_confirmation["direction"] != direction
        or states["H1"]["direction"] != direction
    ):
        raise ContractWait("WAIT_H1_M15_DIRECTION")
    if formation_end > decision_at:
        raise ContractReject("REJECT_FUTURE_FORMATION")
    if exact_timestamp(m15_confirmation["known_at"]) <= formation_end:
        raise ContractWait("WAIT_SUBSEQUENT_M15_CONFIRMATION")
    if states["H4"]["state"] == "RANGE":
        if h4_range is None:
            raise ContractWait("WAIT_H4_RANGE_OBJECT")
        require_known_at(h4_range, decision_at)
        if (
            h4_range.get("invalidated_at") is not None
            and exact_timestamp(h4_range["invalidated_at"]) > decision_at
        ):
            raise ContractReject("REJECT_FUTURE_RANGE_INVALIDATION")
        if states["H4"].get("range_id") != h4_range["id"]:
            raise ContractWait("WAIT_H4_RANGE_OBJECT")
        if h4_range.get("invalidated_at") is not None or (
            h4_range.get("context_id") != states["H4"].get("context_id")
        ):
            raise ContractWait("WAIT_H4_RANGE_OBJECT")
        if (
            exact_timestamp(h4_range["known_at"]) > formation_start
            or exact_timestamp(h4_range["eq_reacted_at"]) > formation_start
        ):
            raise ContractWait("WAIT_H4_RANGE_OBJECT")
        boundary = decimal(h4_range["low"] if direction == "LONG" else h4_range["high"])
        if (
            not decimal(formation_bar["low"])
            <= boundary
            <= decimal(formation_bar["high"])
        ):
            raise ContractWait("WAIT_RANGE_BOUNDARY_FORMATION")
        return {
            "context": "RANGE_CONTEXT",
            "direction": direction,
            "origin_id": h4_range["id"],
        }
    trend = "TREND_UP" if direction == "LONG" else "TREND_DOWN"
    if states["H4"]["state"] == states["D1"]["state"] == trend:
        return {
            "context": "TREND_CONTEXT",
            "direction": direction,
            "origin_id": states["H4"]["context_id"],
        }
    opposite = "TREND_DOWN" if direction == "LONG" else "TREND_UP"
    if states["H4"]["state"] == states["D1"]["state"] == opposite:
        raise ContractWait("WAIT_H4_D1_TREND_DIRECTION")
    eligible = []
    for poi in parent_pois:
        require_known_at(poi, decision_at)
        if poi.get("tf") not in ("H4", "D1") or poi.get("direction") != direction:
            continue
        if poi.get("consumed_at") is not None or not poi.get("confirmed"):
            continue
        if exact_timestamp(poi["known_at"]) > formation_start:
            continue
        if decimal(formation_bar["low"]) <= decimal(poi["high"]) and decimal(
            formation_bar["high"]
        ) >= decimal(poi["low"]):
            eligible.append(poi)
    if not eligible:
        raise ContractWait("WAIT_TRANSITION_ORIGIN_POI")
    poi = min(eligible, key=lambda p: (exact_timestamp(p["known_at"]), p["id"]))
    return {
        "context": "MIXED_OR_TRANSITION_CONTEXT",
        "direction": direction,
        "origin_id": poi["id"],
    }


def completed_atr14(
    bars: list[dict], decision_at: int, tf_seconds: int, pattern_end: int
) -> Decimal:
    """14 native-TF TRs including the pattern, plus preceding close."""
    exact_timestamp(decision_at)
    exact_timestamp(tf_seconds)
    exact_timestamp(pattern_end)
    if tf_seconds not in (3600, 14400):
        raise ContractReject("REJECT_ATR_NATIVE_TF")
    if pattern_end > decision_at:
        raise ContractReject("REJECT_FUTURE_PATTERN_END")
    prefix = [bar for bar in bars if exact_timestamp(bar["end"]) <= pattern_end]
    if len(prefix) < 15:
        raise ContractWait("WAIT_ATR14_PREFIX")
    window = prefix[-15:]
    if exact_timestamp(window[-1]["end"]) != pattern_end:
        raise ContractWait("WAIT_ATR14_PATTERN_BAR")
    for candle in window:
        start, end = exact_timestamp(candle["start"]), exact_timestamp(candle["end"])
        if end - start != tf_seconds or start % tf_seconds:
            raise ContractReject("REJECT_ATR_NATIVE_BAR_ALIGNMENT")
        opening, high, low, close = (
            decimal(candle[k]) for k in ("open", "high", "low", "close")
        )
        if not (0 < low <= opening <= high and low <= close <= high):
            raise ContractReject("REJECT_INVALID_ATR_BAR")
    if any(
        exact_timestamp(right["start"]) != exact_timestamp(left["end"])
        for left, right in pairwise(window)
    ):
        raise ContractReject("REJECT_ATR_NONCONTIGUOUS_PREFIX")
    trs = []
    for previous, bar in pairwise(window):
        high, low, prev_close = (
            decimal(bar["high"]),
            decimal(bar["low"]),
            decimal(previous["close"]),
        )
        if high < low:
            raise ContractReject("REJECT_INVALID_BAR")
        trs.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))
    return sum(trs, Decimal(0)) / Decimal(14)


def raw_family_prices(
    *,
    family: str,
    direction: str,
    zone_low: object,
    zone_high: object,
    stop_anchor: object,
    atr14: object | None = None,
) -> dict:
    """Price projection only; does not assert that a raw family event is valid."""
    if family not in FAMILIES or direction not in ("LONG", "SHORT"):
        raise ContractReject("REJECT_FAMILY_OR_DIRECTION")
    low, high, anchor = decimal(zone_low), decimal(zone_high), decimal(stop_anchor)
    if low <= 0 or high < low or anchor <= 0:
        raise ContractReject("REJECT_RAW_GEOMETRY")
    entry = (
        (low + high) / 2 if family == "STB" else high if direction == "LONG" else low
    )
    if family == "RANGE":
        entry = low if direction == "LONG" else high
    if family == "SFP":
        if atr14 is None:
            raise ContractWait("WAIT_ATR14_PREFIX")
        atr = decimal(atr14)
        if atr <= 0:
            raise ContractReject("REJECT_NONPOSITIVE_ATR")
        anchor = anchor - atr if direction == "LONG" else anchor + atr
    return {
        "raw_entry": entry,
        "raw_stop_boundary": anchor,
        "family": family,
        "direction": direction,
    }


def _grid_floor(value: Decimal, tick: Decimal) -> Decimal:
    return (value / tick).to_integral_value(rounding=ROUND_FLOOR) * tick


def _grid_ceil(value: Decimal, tick: Decimal) -> Decimal:
    return (value / tick).to_integral_value(rounding=ROUND_CEILING) * tick


def _strict_below(value: Decimal, tick: Decimal) -> Decimal:
    result = _grid_floor(value, tick)
    return result - tick if result == value else result


def _strict_above(value: Decimal, tick: Decimal) -> Decimal:
    result = _grid_ceil(value, tick)
    return result + tick if result == value else result


def cash_stop_identity(
    entry: object, stop: object, exit_price: object, direction: str
) -> dict:
    """Modeled quote-price cash unit; suitable for synthetic algebra tests only."""
    e, s, x = decimal(entry), decimal(stop), decimal(exit_price)
    if min(e, s, x) <= 0 or direction not in ("LONG", "SHORT"):
        raise ContractReject("REJECT_PRICE_OR_DIRECTION")
    q = Decimal(1) if direction == "LONG" else Decimal(-1)
    if q * (e - s) <= 0:
        raise ContractReject("REJECT_STOP_SIDE")
    cost_stop = K_PER_LEG * (e + s)
    unit = abs(e - s) + cost_stop
    gross_cash = q * (x - e)
    fee_cash = FEE_PER_LEG * (e + x)
    slippage_cash = SLIPPAGE_PER_LEG * (e + x)
    cost_exit = fee_cash + slippage_cash
    net_cash = gross_cash - fee_cash - slippage_cash
    return {
        "cash_stop_unit": unit,
        "modeled_gross_cash": gross_cash,
        "modeled_fee_cash": fee_cash,
        "modeled_slippage_cash": slippage_cash,
        "modeled_cost": cost_exit,
        "modeled_net_cash": net_cash,
        "modeled_gross_R": gross_cash / unit,
        "modeled_fee_R": fee_cash / unit,
        "modeled_slippage_R": slippage_cash / unit,
        "modeled_cash_stop_R": net_cash / unit,
        "mode": "MODELED_CASH_STOP_R",
    }


def executable_plan(
    *,
    raw: dict,
    targets: list[dict],
    zone_low: object,
    zone_high: object,
    epochs: list[dict],
    symbol: str,
    contract_type: str,
    decision_at: int,
) -> dict:
    """Tick-rounded stop/limit and nearest FTA, with algebraic cost capacity."""
    require_known_at(raw, decision_at)
    epoch = proven_tick_epoch(epochs, symbol, contract_type, decision_at, decision_at)
    tick = decimal(epoch["tick"])
    if tick <= 0:
        raise ContractWait("WAIT_HISTORICAL_TICK_METADATA")
    direction = raw["direction"]
    if direction not in ("LONG", "SHORT"):
        raise ContractReject("REJECT_DIRECTION")
    e0, a = decimal(raw["raw_entry"]), decimal(raw["raw_stop_boundary"])
    low, high = decimal(zone_low), decimal(zone_high)
    entry = _grid_floor(e0, tick) if direction == "LONG" else _grid_ceil(e0, tick)
    stop = _strict_below(a, tick) if direction == "LONG" else _strict_above(a, tick)
    if not (low <= entry <= high):
        raise ContractReject("REJECT_ROUNDED_ENTRY_OUTSIDE_ZONE")
    if not (0 < stop < entry if direction == "LONG" else entry < stop and entry > 0):
        raise ContractReject("REJECT_ROUNDED_STOP_GEOMETRY")
    forward = []
    for candidate in targets:
        require_known_at(candidate, decision_at)
        if "zone_low" in candidate and "zone_high" in candidate:
            opposing_low = decimal(candidate["zone_low"])
            opposing_high = decimal(candidate["zone_high"])
            if opposing_low > opposing_high:
                raise ContractReject("REJECT_INVALID_FTA_ZONE")
            if opposing_low <= entry <= opposing_high:
                raise ContractReject("REJECT_ENTRY_IN_OPPOSING_POI")
        p = decimal(candidate["price"])
        distance = p - entry if direction == "LONG" else entry - p
        if distance > 0:
            forward.append((distance, candidate["id"], candidate))
    if not forward:
        raise ContractWait("WAIT_NO_CAUSAL_FTA")
    nearest_distance, _, nearest = min(forward, key=lambda row: (row[0], row[1]))
    coincident_ids = tuple(
        sorted(row[1] for row in forward if row[0] == nearest_distance)
    )
    fta = decimal(nearest["price"])
    target = (
        _strict_below(fta, tick) if direction == "LONG" else _strict_above(fta, tick)
    )
    if not (entry < target if direction == "LONG" else target < entry):
        raise ContractReject("REJECT_ROUNDING_COLLISION")
    identity = cash_stop_identity(entry, stop, target, direction)
    if identity["modeled_net_cash"] <= 0:
        raise ContractReject("REJECT_UNECONOMIC_NEAREST_FTA")
    price_risk = abs(entry - stop)
    stop_cost = K_PER_LEG * (entry + stop)
    target_move = abs(target - entry)
    target_cost = identity["modeled_cost"]
    return {
        "entry": entry,
        "stop": stop,
        "target": target,
        "nearest_fta_id": nearest["id"],
        "coincident_fta_ids": coincident_ids,
        "tick_epoch_id": epoch["id"],
        "tick_evidence_scope": "GRID_REPRESENTABILITY_ONLY",
        "modeled_target_cash_margin": identity["modeled_net_cash"],
        "cash_stop_unit": identity["cash_stop_unit"],
        "raw_price_risk_D": price_risk,
        "raw_price_risk_bps": price_risk / entry * Decimal(10000),
        "raw_price_risk_ticks": price_risk / tick,
        "modeled_stop_cost_cash": stop_cost,
        "stop_cost_share_of_unit": stop_cost / identity["cash_stop_unit"],
        "entry_notional_per_cash_stop_unit": entry / identity["cash_stop_unit"],
        "target_move_D": target_move,
        "target_cost_cash": target_cost,
        "target_move_to_cost_ratio": target_move / target_cost,
        "mode": "MODELED_CASH_STOP_R",
    }


def reserve_idea(registry: dict, physical_id: str, poi_id: str) -> dict:
    """Idempotent one-order-per-physical-idea and one-order-per-entry-POI."""
    physical = set(registry.get("physical", ()))
    pois = set(registry.get("pois", ()))
    if physical_id in physical or poi_id in pois:
        raise ContractReject("REJECT_DUPLICATE_PHYSICAL_OR_POI")
    physical.add(physical_id)
    pois.add(poi_id)
    return {"physical": tuple(sorted(physical)), "pois": tuple(sorted(pois))}


def first_test(poi: dict, bar: dict, *, eligibility_at: int) -> dict:
    """A native POI is consumed on first eligible completed intersection."""
    exact_timestamp(eligibility_at)
    start, end = exact_timestamp(bar["start"]), exact_timestamp(bar["end"])
    known_at = exact_timestamp(poi["known_at"])
    if end <= start:
        raise ContractReject("REJECT_INVALID_FIRST_TEST_BAR")
    if poi.get("consumed_at") is not None:
        exact_timestamp(poi["consumed_at"])
        return dict(poi)
    if start < eligibility_at or known_at > start:
        return dict(poi)
    if decimal(bar["low"]) <= decimal(poi["high"]) and decimal(bar["high"]) >= decimal(
        poi["low"]
    ):
        open_touch = decimal(poi["low"]) <= decimal(bar["open"]) <= decimal(poi["high"])
        bounds = (start, start if open_touch else end)
        return {
            **poi,
            "first_touch_time_bounds": bounds,
            "first_touch_observed_at": end,
            "consumed_at": end,
        }
    return dict(poi)


def holding_duration_bounds(
    fill_bounds: tuple[int, int], exit_bounds: tuple[int, int]
) -> dict:
    """Return an interval, never an invented point duration for wick events."""
    fill_low, fill_high = fill_bounds
    exit_low, exit_high = exit_bounds
    for value in (fill_low, fill_high, exit_low, exit_high):
        exact_timestamp(value)
    if fill_low > fill_high or exit_low > exit_high or exit_high < fill_low:
        raise ContractReject("REJECT_INVALID_TIME_BOUNDS")
    minimum = max(0, exit_low - fill_high)
    maximum = exit_high - fill_low
    return {
        "minimum_seconds": minimum,
        "maximum_seconds": maximum,
        "exact_seconds": minimum if minimum == maximum else None,
    }


def observe_m15_bar(order: dict, bar: dict, epochs: list[dict]) -> dict:
    """Causal OHLC event classification only. Never computes per-case P&L."""
    state = dict(order)
    start, end = exact_timestamp(bar["start"]), exact_timestamp(bar["end"])
    decision_at = exact_timestamp(order["decision_at"])
    expires_at = exact_timestamp(order["expires_at"])
    if state["status"] not in ("PENDING", "FILLED"):
        return state
    if start < decision_at or end - start != 900 or start % 900:
        raise ContractReject("REJECT_PREDECISION_OR_INVALID_BAR")
    last_observed_end = exact_timestamp(order.get("last_observed_end", decision_at))
    if start > last_observed_end:
        raise ContractWait("WAIT_DATA_GAP")
    if start < last_observed_end:
        raise ContractReject("REJECT_NONMONOTONIC_M15_BAR")
    if state["status"] == "PENDING" and start >= expires_at:
        return {
            **state,
            "status": "UNFILLED_EXPIRED",
            "observed_at": start,
            "last_observed_end": start,
        }
    start_epoch = proven_tick_epoch(
        epochs, order["symbol"], order["contract_type"], start, decision_at
    )
    end_epoch = proven_tick_epoch(
        epochs, order["symbol"], order["contract_type"], end - 1, decision_at
    )
    if start_epoch != end_epoch or start_epoch["id"] != order["tick_epoch_id"]:
        raise ContractWait("WAIT_HISTORICAL_TICK_METADATA")
    tick = decimal(start_epoch["tick"])
    direction = order["direction"]
    if direction not in ("LONG", "SHORT"):
        raise ContractReject("REJECT_DIRECTION")
    if order.get("branch") == "SFP":
        if "setup_tf_seconds" not in order or "stop_anchor" not in order:
            raise ContractReject("REJECT_MISSING_SFP_NATIVE_INVALIDATION")
        if exact_timestamp(order["setup_tf_seconds"]) not in (3600, 14400):
            raise ContractReject("REJECT_SFP_NATIVE_TF")
        if decimal(order["stop_anchor"]) <= 0:
            raise ContractReject("REJECT_SFP_STOP_ANCHOR")
    e, s, t = (decimal(order[k]) for k in ("entry", "stop", "target"))
    o, high, low, close = (decimal(bar[k]) for k in ("open", "high", "low", "close"))
    if not (
        0 < low <= o <= high
        and low <= close <= high
        and (s < e < t if direction == "LONG" else t < e < s)
    ):
        raise ContractReject("REJECT_EXECUTION_GEOMETRY")
    if any(
        (value / tick) != (value / tick).to_integral_value()
        for value in (o, high, low, close, e, s, t)
    ):
        raise ContractWait("WAIT_HISTORICAL_TICK_METADATA")
    state["last_observed_end"] = end
    stop_open = o <= s if direction == "LONG" else o >= s
    target_open = o >= t if direction == "LONG" else o <= t
    stop_touch = low <= s if direction == "LONG" else high >= s
    target_touch = high >= t if direction == "LONG" else low <= t
    if state["status"] == "PENDING":
        if stop_open or target_open:
            return {
                **state,
                "status": "GAP_INVALIDATED_BEFORE_FILL",
                "observed_at": start,
                "price_evidence_tag": "OBSERVED_BAR_OPEN",
            }
        at_open = o <= e if direction == "LONG" else o >= e
        touched = low <= e if direction == "LONG" else high >= e
        if not touched:
            return state
        state.update(
            status="FILLED",
            fill_price=e,
            fill_price_evidence_tag="TOUCH_IMPLIES_FULL_LIMIT_FILL_AT_E",
            fill_time_bounds=(start, start if at_open else end),
            fill_observed_at=start if at_open else end,
        )
        if not at_open and (stop_touch or target_touch):
            return {
                **state,
                "status": "WAIT_INTRABAR_ORDER",
                "event_time_bounds": (start, end),
                "observed_at": end,
            }
    else:
        if stop_open or target_open:
            return {
                **state,
                "status": "EXIT_OBSERVED",
                "exit_reason": "STOP_GAP_OPEN" if stop_open else "TARGET_GAP_OPEN",
                "exit_price": o,
                "price_evidence_tag": "OBSERVED_BAR_OPEN",
                "event_time_bounds": (start, start),
                "observed_at": start,
            }
    if stop_touch and target_touch:
        return {
            **state,
            "status": "WAIT_INTRABAR_ORDER",
            "event_time_bounds": (start, end),
            "observed_at": end,
        }
    if stop_touch or target_touch:
        return {
            **state,
            "status": "EXIT_OBSERVED",
            "exit_reason": "FIXED_INITIAL_STOP" if stop_touch else "STRUCTURAL_FTA",
            "exit_price": s if stop_touch else t,
            "price_evidence_tag": (
                "MODELED_STOP_TRIGGER_PLUS_SLIPPAGE"
                if stop_touch
                else "MODELED_TARGET_TOUCH_FILL"
            ),
            "event_time_bounds": (start, end),
            "observed_at": end,
        }
    if state["status"] == "FILLED" and order.get("branch") == "SFP":
        native_seconds = exact_timestamp(order["setup_tf_seconds"])
        if end % native_seconds == 0:
            anchor = decimal(order["stop_anchor"])
            invalid = close < anchor if direction == "LONG" else close > anchor
            if invalid:
                return {
                    **state,
                    "status": "EXIT_OBSERVED",
                    "exit_reason": "SFP_PATTERN_BODY_INVALIDATION",
                    "exit_price": close,
                    "price_evidence_tag": "OBSERVED_NATIVE_CLOSE",
                    "event_time_bounds": (end, end),
                    "observed_at": end,
                }
    return state


def censor_eof(order: dict, observed_through: int) -> dict:
    """Pure terminal evidence marker; open positions have no invented exit."""
    exact_timestamp(observed_through)
    state = dict(order)
    if observed_through < exact_timestamp(state["decision_at"]):
        raise ContractReject("REJECT_EOF_BEFORE_DECISION")
    last_observed_end = exact_timestamp(
        state["last_observed_end"]
        if "last_observed_end" in state
        else state["decision_at"]
    )
    if observed_through < last_observed_end:
        raise ContractReject("REJECT_EOF_BEFORE_OBSERVATION")
    if observed_through > last_observed_end and state["status"] in (
        "PENDING",
        "FILLED",
    ):
        raise ContractWait("WAIT_DATA_GAP")
    if state["status"] == "PENDING":
        if observed_through < exact_timestamp(state["expires_at"]):
            return {
                **state,
                "status": "ORDER_CENSORED_EOF",
                "observed_at": observed_through,
            }
        return {
            **state,
            "status": "UNFILLED_EXPIRED",
            "observed_at": exact_timestamp(state["expires_at"]),
        }
    if state["status"] == "FILLED":
        return {**state, "status": "OPEN_CENSORED_EOF", "observed_at": observed_through}
    return state
