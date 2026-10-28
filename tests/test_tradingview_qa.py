import unittest
from dataclasses import replace
from datetime import datetime, timezone

from crypto_bot.qa.tradingview import (
    TradingViewQAPlan,
    TradingViewQARunner,
    TradingViewQAStep,
    build_tradingview_qa_plan,
)


NOW = datetime(2026, 10, 28, 10, 0, tzinfo=timezone.utc)


class TradingViewQATests(unittest.TestCase):
    def test_plan_is_deterministic_explicit_and_fail_closed(self):
        left = build_tradingview_qa_plan(
            case_id="case-9",
            chart_symbol="OKX:BTCUSDT.P",
            replay_at=NOW,
            timeframes=("D", "240", "60", "15"),
        )
        right = build_tradingview_qa_plan(
            case_id="case-9",
            chart_symbol="OKX:BTCUSDT.P",
            replay_at=NOW,
            timeframes=("D", "240", "60", "15"),
        )
        self.assertEqual(left.plan_id, right.plan_id)
        self.assertEqual(left.chart_symbol, "OKX:BTCUSDT.P")
        self.assertTrue(left.qa_only)
        self.assertFalse(left.trade_entry_allowed)
        self.assertEqual(left.steps[0].command, ("status",))
        self.assertEqual(left.steps[1].command, ("symbol", "OKX:BTCUSDT.P"))
        self.assertFalse(any("trade" in step.command for step in left.steps))

    def test_plan_identity_changes_with_market_timeframe_or_replay_boundary(self):
        base = build_tradingview_qa_plan(
            case_id="case-9",
            chart_symbol="OKX:BTCUSDT.P",
            replay_at=NOW,
            timeframes=("60", "15"),
        )
        changed_symbol = build_tradingview_qa_plan(
            case_id="case-9",
            chart_symbol="BINANCE:BTCUSDT",
            replay_at=NOW,
            timeframes=("60", "15"),
        )
        changed_tf = build_tradingview_qa_plan(
            case_id="case-9",
            chart_symbol="OKX:BTCUSDT.P",
            replay_at=NOW,
            timeframes=("240", "15"),
        )
        changed_time = build_tradingview_qa_plan(
            case_id="case-9",
            chart_symbol="OKX:BTCUSDT.P",
            replay_at=datetime(2026, 10, 28, 10, 15, tzinfo=timezone.utc),
            timeframes=("60", "15"),
        )
        self.assertNotEqual(base.plan_id, changed_symbol.plan_id)
        self.assertNotEqual(base.plan_id, changed_tf.plan_id)
        self.assertNotEqual(base.plan_id, changed_time.plan_id)

    def test_runner_executes_only_plan_steps_and_returns_fail_closed_receipt(self):
        calls = []

        def transport(command, timeout):
            calls.append((command, timeout))
            return {"ok": True, "command": list(command)}

        plan = build_tradingview_qa_plan(
            case_id="case-9",
            chart_symbol="OKX:BTCUSDT.P",
            replay_at=NOW,
            timeframes=("15",),
        )
        result = TradingViewQARunner(transport=transport, timeout_seconds=5).run(plan)
        self.assertEqual(len(calls), len(plan.steps))
        self.assertEqual(len(result.completed_steps), len(plan.steps))
        self.assertEqual(result.plan_id, plan.plan_id)
        self.assertTrue(result.qa_only)
        self.assertFalse(result.trade_entry_allowed)

    def test_trade_and_unsafe_replay_actions_are_forbidden(self):
        with self.assertRaises(ValueError):
            TradingViewQAStep("x", ("replay", "trade", "buy"), "unsafe")
        with self.assertRaises(ValueError):
            TradingViewQAStep("x", ("alert", "create"), "not part of QA adapter")

    def test_plan_cannot_be_flipped_into_execution_authority(self):
        plan = build_tradingview_qa_plan(
            case_id="case-9",
            chart_symbol="OKX:BTCUSDT.P",
            replay_at=NOW,
            timeframes=("15",),
        )
        with self.assertRaises(ValueError):
            replace(plan, trade_entry_allowed=True)
        with self.assertRaises(ValueError):
            replace(plan, qa_only=False)

    def test_naive_time_empty_or_duplicate_timeframes_are_rejected(self):
        with self.assertRaises(ValueError):
            build_tradingview_qa_plan(
                case_id="case",
                chart_symbol="OKX:BTCUSDT.P",
                replay_at=datetime(2026, 10, 28, 10, 0),
            )
        with self.assertRaises(ValueError):
            build_tradingview_qa_plan(
                case_id="case",
                chart_symbol="OKX:BTCUSDT.P",
                replay_at=NOW,
                timeframes=("15", "15"),
            )
        with self.assertRaises(ValueError):
            build_tradingview_qa_plan(
                case_id="",
                chart_symbol="OKX:BTCUSDT.P",
                replay_at=NOW,
                timeframes=("15",),
            )

    def test_to_dict_is_json_native(self):
        plan = build_tradingview_qa_plan(
            case_id="case-9",
            chart_symbol="OKX:BTCUSDT.P",
            replay_at=NOW,
            timeframes=("15",),
        )
        payload = plan.to_dict()
        self.assertIsInstance(payload["timeframes"], list)
        self.assertIsInstance(payload["steps"], list)
        self.assertIsInstance(payload["steps"][0]["command"], list)


if __name__ == "__main__":
    unittest.main()
