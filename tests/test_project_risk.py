import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from crypto_bot.project_risk import (
    ProjectPortfolioState,
    ProjectRiskPolicy,
    ProjectTradeProposal,
    evaluate_project_risk,
)


UTC = timezone.utc
NOW = datetime(2026, 10, 28, 10, 0, tzinfo=UTC)


def policy():
    return ProjectRiskPolicy(
        max_risk_per_trade_fraction=0.02,
        max_total_risk_fraction=0.06,
        max_daily_loss_fraction=0.04,
        max_leverage=3.0,
        max_margin_fraction=0.50,
        max_concurrent_positions=4,
        stale_after_seconds=120,
    )


def proposal():
    return ProjectTradeProposal(
        trade_idea_event_id="idea-event-1",
        symbol="BTC-USDT-SWAP",
        side="LONG",
        entry_price=81_250.0,
        stop_price=80_640.0,
        requested_notional=3_000.0,
        requested_risk_amount=100.0,
        requested_margin=1_000.0,
        leverage=3.0,
        market_data_at=NOW - timedelta(seconds=30),
    )


def portfolio(**overrides):
    base = dict(
        equity=10_000.0,
        day_start_equity=10_000.0,
        daily_realized_pnl=0.0,
        aggregate_stop_risk=200.0,
        allocated_margin=1_000.0,
        concurrent_positions=1,
        accepted_proposal_fingerprints=(),
    )
    base.update(overrides)
    return ProjectPortfolioState(**base)


class ProjectRiskTests(unittest.TestCase):
    def test_clean_proposal_passes_but_does_not_grant_execution(self):
        verdict = evaluate_project_risk(proposal(), portfolio(), policy(), evaluated_at=NOW)
        self.assertEqual(verdict.status, "PASS")
        self.assertEqual(verdict.reason_codes, ())
        self.assertFalse(verdict.trade_entry_allowed)

    def test_changed_proposal_requires_a_new_fingerprint_and_verdict(self):
        first = proposal()
        changed = replace(first, entry_price=81_300.0)
        self.assertNotEqual(first.proposal_fingerprint, changed.proposal_fingerprint)
        a = evaluate_project_risk(first, portfolio(), policy(), evaluated_at=NOW)
        b = evaluate_project_risk(changed, portfolio(), policy(), evaluated_at=NOW)
        self.assertNotEqual(a.verdict_id, b.verdict_id)

    def test_same_effective_verdict_is_idempotent_across_evaluation_time(self):
        p = proposal()
        a = evaluate_project_risk(p, portfolio(), policy(), evaluated_at=NOW)
        b = evaluate_project_risk(p, portfolio(), policy(), evaluated_at=NOW + timedelta(seconds=20))
        self.assertEqual(a.verdict_id, b.verdict_id)
        self.assertNotEqual(a.evaluated_at, b.evaluated_at)

    def test_each_core_policy_guard_blocks_with_machine_reason(self):
        cases = [
            (replace(proposal(), requested_risk_amount=250.0), portfolio(), "RISK_PER_TRADE_LIMIT"),
            (proposal(), portfolio(aggregate_stop_risk=550.0), "TOTAL_PORTFOLIO_RISK_LIMIT"),
            (proposal(), portfolio(daily_realized_pnl=-400.0), "DAILY_LOSS_LIMIT"),
            (replace(proposal(), leverage=4.0), portfolio(), "LEVERAGE_LIMIT"),
            (proposal(), portfolio(allocated_margin=4_500.0), "MARGIN_BUDGET_LIMIT"),
            (proposal(), portfolio(concurrent_positions=4), "CONCURRENT_POSITION_LIMIT"),
        ]
        for p, state, expected in cases:
            with self.subTest(expected=expected):
                verdict = evaluate_project_risk(p, state, policy(), evaluated_at=NOW)
                self.assertEqual(verdict.status, "BLOCK")
                self.assertIn(expected, verdict.reason_codes)

    def test_stale_market_data_blocks(self):
        p = replace(proposal(), market_data_at=NOW - timedelta(seconds=121))
        verdict = evaluate_project_risk(p, portfolio(), policy(), evaluated_at=NOW)
        self.assertIn("MARKET_DATA_STALE", verdict.reason_codes)

    def test_duplicate_exact_proposal_blocks(self):
        p = proposal()
        state = portfolio(accepted_proposal_fingerprints=(p.proposal_fingerprint,))
        verdict = evaluate_project_risk(p, state, policy(), evaluated_at=NOW)
        self.assertIn("DUPLICATE_PROPOSAL", verdict.reason_codes)

    def test_external_project_guard_can_add_reason_without_mutating_proposal(self):
        p = proposal()
        original = p.proposal_fingerprint
        verdict = evaluate_project_risk(
            p,
            portfolio(),
            policy(),
            evaluated_at=NOW,
            extra_block_reasons=("CORRELATION_LIMIT",),
        )
        self.assertEqual(p.proposal_fingerprint, original)
        self.assertEqual(verdict.status, "BLOCK")
        self.assertEqual(verdict.reason_codes, ("CORRELATION_LIMIT",))

    def test_policy_identity_changes_when_limits_change(self):
        a = policy()
        b = replace(a, max_leverage=2.0)
        self.assertNotEqual(a.policy_id, b.policy_id)

    def test_bad_geometry_rejected_before_policy_evaluation(self):
        with self.assertRaises(ValueError):
            replace(proposal(), stop_price=82_000.0)

    def test_evaluation_cannot_precede_market_data(self):
        p = replace(proposal(), market_data_at=NOW + timedelta(seconds=1))
        with self.assertRaises(ValueError):
            evaluate_project_risk(p, portfolio(), policy(), evaluated_at=NOW)


if __name__ == "__main__":
    unittest.main()
