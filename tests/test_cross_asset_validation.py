from __future__ import annotations

import unittest

from crypto_bot.strategy.cross_asset_validation import (
    DEFAULT_CROSS_ASSET_BASKET,
    SymbolRobustnessChecks,
    decide_cross_asset_gate,
    normalize_symbols,
)


def passing(symbol: str) -> SymbolRobustnessChecks:
    return SymbolRobustnessChecks(
        symbol=symbol,
        data_qa_passed=True,
        evaluation_span_passed=True,
        source_recovery_free=True,
        suffix_stability_exact=True,
        trade_entry_safety_passed=True,
        mtf_runtime_passed=True,
    )


class CrossAssetValidationTests(unittest.TestCase):
    def test_default_basket_is_ten_distinct_symbols(self):
        self.assertEqual(len(DEFAULT_CROSS_ASSET_BASKET), 10)
        self.assertEqual(len(set(DEFAULT_CROSS_ASSET_BASKET)), 10)

    def test_gate_closes_only_with_complete_passing_basket(self):
        checks = {symbol: passing(symbol) for symbol in DEFAULT_CROSS_ASSET_BASKET}
        decision = decide_cross_asset_gate(checks)
        self.assertTrue(decision.gate_closed)
        self.assertEqual(decision.missing_required_symbols, ())
        self.assertEqual(decision.failed_symbols, ())

    def test_gate_stays_open_for_missing_or_failed_symbol(self):
        checks = {symbol: passing(symbol) for symbol in DEFAULT_CROSS_ASSET_BASKET[:-1]}
        decision = decide_cross_asset_gate(checks)
        self.assertFalse(decision.gate_closed)
        self.assertEqual(decision.missing_required_symbols, (DEFAULT_CROSS_ASSET_BASKET[-1],))

        bad_symbol = DEFAULT_CROSS_ASSET_BASKET[0]
        bad = SymbolRobustnessChecks(
            symbol=bad_symbol,
            data_qa_passed=True,
            evaluation_span_passed=True,
            source_recovery_free=True,
            suffix_stability_exact=False,
            trade_entry_safety_passed=True,
            mtf_runtime_passed=True,
        )
        checks = {symbol: passing(symbol) for symbol in DEFAULT_CROSS_ASSET_BASKET}
        checks[bad_symbol] = bad
        decision = decide_cross_asset_gate(checks)
        self.assertFalse(decision.gate_closed)
        self.assertEqual(decision.failed_symbols, (bad_symbol,))

    def test_symbol_normalization_rejects_duplicates(self):
        self.assertEqual(normalize_symbols(['btcusdt', 'ETHUSDT']), ('BTCUSDT', 'ETHUSDT'))
        with self.assertRaises(ValueError):
            normalize_symbols(['BTCUSDT', 'btcusdt'])


if __name__ == '__main__':
    unittest.main()
