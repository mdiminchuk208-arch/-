from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum


class StrategyProfile(str, Enum):
    PURE_SOURCE = "PURE_SOURCE"
    PROJECT_OVERLAY = "PROJECT_OVERLAY"


class PolicyClass(str, Enum):
    SOURCE_RULE = "SOURCE_RULE"
    TECHNICAL_NORMALIZATION = "TECHNICAL_NORMALIZATION"
    PROJECT_POLICY = "PROJECT_POLICY"


class ProjectPolicyContaminationError(RuntimeError):
    """Raised when PROJECT_POLICY reaches the PURE_SOURCE execution path."""


PROJECT_POLICY_IDS = frozenset({
    "ANTI_SCALP",
    "EDGE_COST_RATIO",
    "COST_VIABILITY",
    "FEE_SLIPPAGE_ADMISSION",
    "PROJECT_HTF_FILTER",
    "PROJECT_MEDIUM_TERM_FILTER",
    "PROJECT_SCORING",
    "PROJECT_RANKING",
    "PORTFOLIO_ADMISSION",
    "CORRELATION_LIMIT",
    "DAILY_LOSS_LIMIT",
    "LEVERAGE_POLICY",
    "TP_40_30_30",
    "COST_ADJUSTED_BREAKEVEN",
    "PROJECT_REENTRY_FILTER",
})


@dataclass(frozen=True)
class StrategyRuntimeConfig:
    """Runtime profile gate. LIVE/private execution is intentionally unsupported."""

    strategy_profile: StrategyProfile = StrategyProfile.PURE_SOURCE
    trade_entry_allowed: bool = False
    project_admission_enabled: bool = False
    project_exits_enabled: bool = False
    project_risk_overlays_enabled: bool = False
    project_ranking_scoring_enabled: bool = False
    applied_policy_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.trade_entry_allowed is not False:
            raise ValueError("trade_entry_allowed must remain false")
        if self.strategy_profile == StrategyProfile.PURE_SOURCE:
            enabled = (
                self.project_admission_enabled,
                self.project_exits_enabled,
                self.project_risk_overlays_enabled,
                self.project_ranking_scoring_enabled,
            )
            if any(enabled):
                raise ProjectPolicyContaminationError(
                    "PROJECT overlay switches are forbidden in PURE_SOURCE"
                )
            contaminated = PROJECT_POLICY_IDS.intersection(self.applied_policy_ids)
            if contaminated:
                raise ProjectPolicyContaminationError(
                    "PROJECT_POLICY reached PURE_SOURCE: " + ",".join(sorted(contaminated))
                )

    def assert_policy_allowed(self, policy_id: str, policy_class: PolicyClass) -> None:
        if (
            self.strategy_profile == StrategyProfile.PURE_SOURCE
            and (policy_class == PolicyClass.PROJECT_POLICY or policy_id in PROJECT_POLICY_IDS)
        ):
            raise ProjectPolicyContaminationError(
                f"PROJECT_POLICY {policy_id!r} is disabled for PURE_SOURCE"
            )

    def record_policy(self, policy_id: str, policy_class: PolicyClass) -> "StrategyRuntimeConfig":
        self.assert_policy_allowed(policy_id, policy_class)
        if policy_id in self.applied_policy_ids:
            return self
        return replace(self, applied_policy_ids=self.applied_policy_ids + (policy_id,))


PURE_SOURCE_CONFIG = StrategyRuntimeConfig()
