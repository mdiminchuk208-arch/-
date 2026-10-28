from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from math import isfinite
from typing import Iterable


PROJECT_RISK_SCHEMA = "crypto-bot.project-risk-verdict.v1"


@dataclass(frozen=True)
class ProjectRiskPolicy:
    """Explicit PROJECT_POLICY limits. Never SOURCE truth.

    No defaults are provided on purpose: a caller must supply the policy it
    intends to test/deploy, making the project overlay visible and versionable.
    """

    max_risk_per_trade_fraction: float
    max_total_risk_fraction: float
    max_daily_loss_fraction: float
    max_leverage: float
    max_margin_fraction: float
    max_concurrent_positions: int
    stale_after_seconds: int

    def __post_init__(self) -> None:
        fractions = (
            self.max_risk_per_trade_fraction,
            self.max_total_risk_fraction,
            self.max_daily_loss_fraction,
            self.max_margin_fraction,
        )
        if not all(isfinite(value) and 0 < value <= 1 for value in fractions):
            raise ValueError("risk policy fractions must be finite and within (0, 1]")
        if self.max_risk_per_trade_fraction > self.max_total_risk_fraction:
            raise ValueError("per-trade risk cannot exceed total-risk cap")
        if not isfinite(self.max_leverage) or self.max_leverage < 1:
            raise ValueError("max_leverage must be finite and >= 1")
        if self.max_concurrent_positions <= 0:
            raise ValueError("max_concurrent_positions must be positive")
        if self.stale_after_seconds <= 0:
            raise ValueError("stale_after_seconds must be positive")

    @property
    def policy_id(self) -> str:
        return hashlib.sha256(
            json.dumps(asdict(self), sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()


@dataclass(frozen=True)
class ProjectTradeProposal:
    trade_idea_event_id: str
    symbol: str
    side: str
    entry_price: float
    stop_price: float
    requested_notional: float
    requested_risk_amount: float
    requested_margin: float
    leverage: float
    market_data_at: datetime

    def __post_init__(self) -> None:
        if not self.trade_idea_event_id.strip() or not self.symbol.strip():
            raise ValueError("trade_idea_event_id and symbol must be non-empty")
        side = self.side.upper()
        if side not in {"LONG", "SHORT"}:
            raise ValueError("side must be LONG or SHORT")
        for name in (
            "entry_price",
            "stop_price",
            "requested_notional",
            "requested_risk_amount",
            "requested_margin",
            "leverage",
        ):
            value = float(getattr(self, name))
            if not isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive")
        if side == "LONG" and self.stop_price >= self.entry_price:
            raise ValueError("LONG stop must be below entry")
        if side == "SHORT" and self.stop_price <= self.entry_price:
            raise ValueError("SHORT stop must be above entry")
        if self.market_data_at.tzinfo is None or self.market_data_at.utcoffset() is None:
            raise ValueError("market_data_at must be timezone-aware")

    @property
    def proposal_fingerprint(self) -> str:
        payload = {
            **asdict(self),
            "side": self.side.upper(),
            "market_data_at": self.market_data_at.isoformat(),
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()


@dataclass(frozen=True)
class ProjectPortfolioState:
    equity: float
    day_start_equity: float
    daily_realized_pnl: float
    aggregate_stop_risk: float
    allocated_margin: float
    concurrent_positions: int
    accepted_proposal_fingerprints: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "equity",
            "day_start_equity",
            "daily_realized_pnl",
            "aggregate_stop_risk",
            "allocated_margin",
        ):
            value = float(getattr(self, name))
            if not isfinite(value):
                raise ValueError(f"{name} must be finite")
        if self.equity <= 0 or self.day_start_equity <= 0:
            raise ValueError("equity and day_start_equity must be positive")
        if self.aggregate_stop_risk < 0 or self.allocated_margin < 0:
            raise ValueError("risk and allocated margin cannot be negative")
        if self.concurrent_positions < 0:
            raise ValueError("concurrent_positions cannot be negative")


@dataclass(frozen=True)
class ProjectRiskVerdict:
    schema: str
    verdict_id: str
    proposal_fingerprint: str
    trade_idea_event_id: str
    policy_id: str
    evaluated_at: str
    status: str
    reason_codes: tuple[str, ...]
    trade_entry_allowed: bool

    def __post_init__(self) -> None:
        if self.schema != PROJECT_RISK_SCHEMA:
            raise ValueError(f"unsupported project risk schema: {self.schema!r}")
        if self.status not in {"PASS", "BLOCK"}:
            raise ValueError("status must be PASS or BLOCK")
        if self.trade_entry_allowed:
            raise ValueError("project risk verdict does not grant financial execution authority")
        if self.status == "PASS" and self.reason_codes:
            raise ValueError("PASS verdict cannot contain block reasons")
        if self.status == "BLOCK" and not self.reason_codes:
            raise ValueError("BLOCK verdict requires at least one reason")


def evaluate_project_risk(
    proposal: ProjectTradeProposal,
    portfolio: ProjectPortfolioState,
    policy: ProjectRiskPolicy,
    *,
    evaluated_at: datetime,
    extra_block_reasons: Iterable[str] = (),
) -> ProjectRiskVerdict:
    """Return deterministic PROJECT PASS/BLOCK without mutating the proposal.

    PASS means only that the proposal satisfies the supplied PROJECT policy.
    It never means SOURCE approval and never flips ``trade_entry_allowed``.
    """

    if evaluated_at.tzinfo is None or evaluated_at.utcoffset() is None:
        raise ValueError("evaluated_at must be timezone-aware")
    if evaluated_at < proposal.market_data_at:
        raise ValueError("evaluated_at cannot precede market_data_at")

    reasons: list[str] = []
    max_trade_risk = portfolio.equity * policy.max_risk_per_trade_fraction
    if proposal.requested_risk_amount > max_trade_risk + 1e-12:
        reasons.append("RISK_PER_TRADE_LIMIT")

    max_total_risk = portfolio.equity * policy.max_total_risk_fraction
    if portfolio.aggregate_stop_risk + proposal.requested_risk_amount > max_total_risk + 1e-12:
        reasons.append("TOTAL_PORTFOLIO_RISK_LIMIT")

    daily_loss_amount = max(0.0, -portfolio.daily_realized_pnl)
    if daily_loss_amount >= portfolio.day_start_equity * policy.max_daily_loss_fraction - 1e-12:
        reasons.append("DAILY_LOSS_LIMIT")

    if proposal.leverage > policy.max_leverage + 1e-12:
        reasons.append("LEVERAGE_LIMIT")

    if portfolio.allocated_margin + proposal.requested_margin > portfolio.equity * policy.max_margin_fraction + 1e-12:
        reasons.append("MARGIN_BUDGET_LIMIT")

    if portfolio.concurrent_positions >= policy.max_concurrent_positions:
        reasons.append("CONCURRENT_POSITION_LIMIT")

    age_seconds = (evaluated_at - proposal.market_data_at).total_seconds()
    if age_seconds > policy.stale_after_seconds:
        reasons.append("MARKET_DATA_STALE")

    if proposal.proposal_fingerprint in set(portfolio.accepted_proposal_fingerprints):
        reasons.append("DUPLICATE_PROPOSAL")

    for reason in extra_block_reasons:
        reason = str(reason).strip()
        if reason:
            reasons.append(reason)
    reason_codes = tuple(dict.fromkeys(reasons))
    status = "BLOCK" if reason_codes else "PASS"

    base = {
        "schema": PROJECT_RISK_SCHEMA,
        "proposal_fingerprint": proposal.proposal_fingerprint,
        "trade_idea_event_id": proposal.trade_idea_event_id,
        "policy_id": policy.policy_id,
        "evaluated_at": evaluated_at.isoformat(),
        "status": status,
        "reason_codes": reason_codes,
        # A project policy PASS is not execution authority. SHADOW/PAPER
        # executors consume PASS separately while financial entry remains
        # disabled at the Strategy Engine contract boundary.
        "trade_entry_allowed": False,
    }
    verdict_fingerprint = {
        **base,
        # Make re-evaluation at a later wall-clock time idempotent when the
        # effective proposal/policy/result is unchanged.
        "evaluated_at": None,
    }
    verdict_id = hashlib.sha256(
        json.dumps(verdict_fingerprint, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return ProjectRiskVerdict(verdict_id=verdict_id, **base)
