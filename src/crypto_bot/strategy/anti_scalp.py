"""Pre-entry structural edge/cost check. No price history or outcomes are inputs."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from math import inf, isfinite


@dataclass(frozen=True)
class AntiScalpPolicy:
    fee_fraction: float = 0.0006
    slippage_fraction: float = 0.0002
    minimum_edge_cost_ratio: float = 3.0

    def __post_init__(self):
        if not all(isfinite(x) for x in (self.fee_fraction, self.slippage_fraction,
                                        self.minimum_edge_cost_ratio)):
            raise ValueError("finite costs and threshold required")
        if not 0 <= self.fee_fraction < .1 or not 0 <= self.slippage_fraction < .1:
            raise ValueError("invalid trading costs")
        if self.minimum_edge_cost_ratio <= 1:
            raise ValueError("edge buffer must exceed full round-trip costs")


@dataclass(frozen=True)
class AntiScalpDecision:
    allowed: bool
    status: str
    reason: str
    expected_gross_move: float
    entry_fee: float
    exit_fee: float
    entry_slippage: float
    exit_slippage: float
    estimated_round_trip_cost: float
    edge_cost_ratio: float | None
    expected_net_move: float
    minimum_edge_cost_ratio: float
    classification: str = "DECLARED_PRE_ENTRY_RISK_POLICY_NOT_PDF_RULE"
    trade_entry_allowed: bool = False

    def evidence(self):
        return asdict(self)


def check_anti_scalp(*, direction: str, entry: float, target: float | None,
                     setup_tf: int, context_tf: int | None,
                     main_setup_valid: bool, context_valid: bool,
                     target_known_before_entry: bool,
                     policy: AntiScalpPolicy | None = None) -> AntiScalpDecision:
    """Unit-notional costs at real first structural target, before READY/entry.

    The buffer of three is a frozen engineering policy, not a fitted threshold.
    Nearest FTA is checked even when later structural targets are much farther.
    Slippage is charged on both references; fees use both slipped fills.
    """
    policy = policy or AntiScalpPolicy()
    if direction not in ("LONG", "SHORT") or not isfinite(entry) or entry <= 0:
        raise ValueError("positive entry and LONG/SHORT required")
    s = 1 if direction == "LONG" else -1
    valid_target = target is not None and isfinite(target) and target > 0
    target_price = target if target is not None else 0.0
    gross = s * (target_price - entry) if valid_target else 0.0
    entry_slip = entry * policy.slippage_fraction
    exit_slip = target_price * policy.slippage_fraction if valid_target else 0.0
    entry_fee = entry * (1 + s * policy.slippage_fraction) * policy.fee_fraction
    exit_fee = target_price * (1 - s * policy.slippage_fraction) * policy.fee_fraction if valid_target else 0.0
    cost = entry_fee + exit_fee + entry_slip + exit_slip
    ratio = gross / cost if cost > 0 else inf if gross > 0 else 0.0
    reason = "ANTI_SCALP_PASSED"
    if setup_tf not in (60, 240) or context_tf not in (240, 1440) or not main_setup_valid or not context_valid:
        reason = "REJECTED_SCALP_NO_HTF_CONTEXT"
    elif not valid_target or not target_known_before_entry or gross <= cost:
        reason = "REJECTED_SCALP_TARGET_TOO_CLOSE"
    elif ratio < policy.minimum_edge_cost_ratio:
        reason = "REJECTED_SCALP_POOR_EDGE_COST_RATIO"
    allowed = reason == "ANTI_SCALP_PASSED"
    return AntiScalpDecision(allowed, "QUALIFIED" if allowed else "REJECTED_SCALP_RISK",
                             reason, gross, entry_fee, exit_fee, entry_slip, exit_slip,
                             cost, ratio if isfinite(ratio) else None, gross - cost,
                             policy.minimum_edge_cost_ratio)
