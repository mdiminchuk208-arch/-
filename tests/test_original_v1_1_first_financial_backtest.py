"""Synthetic accounting / evidence tests; no real-history monetary outcomes."""
from __future__ import annotations

import json
import sys
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from original_v1_1_evidence_adapter import (
    baseline_probe,
    enumerate_series,
    evidence_case,
    inspect_proposal,
)
from original_v1_1_financial_accounting import (
    EQUITY,
    drawdown,
    fixed_risk_quantity,
    metrics,
    money,
)
from original_v1_1_financial_data import START, Bar, compact, daily, validate_bars


def bars(values, tf=15):
    return [Bar(START + i * tf * 60, START + (i + 1) * tf * 60,
                *(Decimal(str(v)) for v in row)) for i, row in enumerate(values)]


def raw():
    return {'candidate_id': 'synthetic-only', 'branch': 'OB_CONSERVATIVE', 'symbol': 'BTCUSDT',
            'direction': 'LONG', 'setup_tf': 60, 'decision_at': START + 3600, 'event': 'CLOSE'}


class OriginalFirstFinancialTests(unittest.TestCase):
    def test_prices_are_completed_contiguous_and_valid(self):
        good = bars([(100, 102, 98, 101), (101, 103, 99, 102)])
        validate_bars(good, 15)
        with self.assertRaises(ValueError):
            validate_bars(good[:1] + bars([(100, 103, 99, 102)]), 15)
        with self.assertRaises(ValueError):
            validate_bars(bars([(100, 103, 99, 105)]), 15)

    def test_unaligned_candles_rejected(self):
        b = bars([(100, 102, 98, 101)])[0]
        with self.assertRaises(ValueError):
            validate_bars([Bar(b.start + 1, b.end + 1, b.open, b.high, b.low, b.close)], 15)

    def test_nonfinite_prices_rejected(self):
        with self.assertRaises(ValueError):
            validate_bars(bars([(100, 'Infinity', 98, 101)]), 15)

    def test_daily_complete_only_no_partial_eof(self):
        rows = bars([(100, 102, 98, 101)] * 97)
        result = daily(rows)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].end, START + 86400)

    def test_no_reference_lookahead_from_unconfirmed_swing(self):
        rows = bars([(100, 102, 98, 101), (100, 101, 95, 99), (99, 102, 97, 101)])
        result = list(enumerate_series('BTCUSDT', 15, rows))
        self.assertEqual(result, [])

    def test_raw_sfp_is_observable_proposal_not_source_validation(self):
        rows = bars([(100, 102, 98, 101), (100, 101, 95, 99), (99, 102, 97, 101), (99, 101, 94, 100)])
        result = [r for r in enumerate_series('BTCUSDT', 15, rows) if r['branch'] == 'SFP']
        self.assertEqual(len(result), 1)
        self.assertFalse(result[0]['source_validated'])
        self.assertTrue(result[0]['raw_only'])
        self.assertEqual(result[0]['decision_at'], rows[-1].end)

    def test_proposal_prefix_consistency_and_future_mutation(self):
        prefix = bars([(100, 102, 98, 101), (100, 101, 95, 99), (99, 102, 97, 101), (99, 101, 94, 100)])
        extended = prefix + bars([(100, 200, 1, 101)])
        last = extended[-1]
        extended[-1] = Bar(prefix[-1].end, prefix[-1].end + 900, last.open, last.high, last.low, last.close)
        before = list(enumerate_series('BTCUSDT', 15, prefix))
        after = [r for r in enumerate_series('BTCUSDT', 15, extended) if r['decision_at'] <= prefix[-1].end]
        self.assertEqual(before, after)

    def test_evidence_absence_is_wait_not_reject(self):
        result = inspect_proposal(raw())
        self.assertEqual(result['SOURCE_STRATEGY_DECISION'], 'WAIT')
        self.assertEqual(result['status'], 'WAIT_UNRESOLVED_INSTRUMENT_METADATA')
        self.assertFalse(result['evidence_complete'])

    def test_missing_qualitative_and_stop_liquidity_explicit(self):
        result = inspect_proposal(raw())
        self.assertIn('SMOOTH_APPROACH', result['missing_evidence'])
        self.assertIn('WAIT_UNRESOLVED_STOP_GEOMETRY', result['parallel_blockers'])
        self.assertIn('WAIT_UNRESOLVED_LIQUIDITY_CONTEXT', result['parallel_blockers'])

    def test_lower_tf_reason_parallel_does_not_override_first_frozen_wait(self):
        case = raw()
        case['setup_tf'] = 15
        result = inspect_proposal(case)
        self.assertIn('WAIT_NO_AVAILABLE_LOWER_TF', result['parallel_blockers'])
        self.assertEqual(result['status'], 'WAIT_UNRESOLVED_INSTRUMENT_METADATA')

    def test_backtest_shadow_parity_and_deterministic_replay(self):
        r = raw()
        expected = inspect_proposal(r)
        self.assertEqual(expected, inspect_proposal(r, mode='SHADOW'))
        self.assertEqual(expected, inspect_proposal(json.loads(compact(r))))

    def test_future_raw_field_does_not_become_source_fact(self):
        r = raw()
        before = evidence_case(r, {})
        r.update(future_return=1000, old_NO_HTF_CONTEXT=False, old_adverse751=False, fitted_prediction=1)
        self.assertEqual(before, evidence_case(r, {}))

    def test_catalog_mutation_cannot_unlock_historical_fills(self):
        r = raw()
        with self.assertRaisesRegex(ValueError, 'empty historical annotation'):
            evidence_case(r, {r['candidate_id']: {'source_validated': True}})

    def test_secondary_legacy_style_reject_is_frozen_profile_selection(self):
        signal = {'signal_id': 'old-fixture', 'symbol': 'BTCUSDT', 'direction': 'LONG',
                  'setup_type': 'OB_DIRECT_FIRST_TEST', 'known_at': '2023-01-01T01:00:00+00:00',
                  'evidence': {'actual_setup_tf': 60}}
        result = baseline_probe(signal)
        self.assertEqual(result['v1_1_decision'], 'REJECT')
        self.assertEqual(result['v1_1_reason'], 'REJECT_INACTIVE_PROFILE_BRANCH')
        signal['setup_type'] = 'OB_CONSERVATIVE_BOS_POI'
        self.assertEqual(baseline_probe(signal)['v1_1_decision'], 'WAIT')

    def test_fixed_risk_sizing_is_accounting_not_admission(self):
        self.assertEqual(fixed_risk_quantity(100, 95), Decimal('4.68'))
        self.assertEqual(fixed_risk_quantity(100, 95, Decimal(2340)), Decimal('9.36'))
        with self.assertRaises(ValueError):
            fixed_risk_quantity(100, 100)

    def test_cost_identity_long_and_short(self):
        for direction, exit_price in [('LONG', 110), ('SHORT', 90)]:
            result = money(direction, 100, exit_price, Decimal('4.68'))
            self.assertAlmostEqual(result['gross_pnl'] - result['fees'] - result['slippage'], result['net_pnl'], places=12)
            self.assertGreater(result['entry_fee'], 0)
            self.assertGreater(result['exit_slippage'], 0)

    def test_symmetric_source_gross_costs_depend_on_notional(self):
        a = money('LONG', 100, 110, 1)
        b = money('SHORT', 110, 100, 1)
        for key in ('gross_pnl', 'fees', 'slippage', 'net_pnl'):
            self.assertEqual(a[key], b[key])

    def test_bad_accounting_direction_and_prices_rejected(self):
        for direction, price in [('FLAT', 100), ('LONG', 0)]:
            with self.assertRaises(ValueError):
                money(direction, price, 101, 1)

    def test_zero_trade_metrics_have_undefined_ratios(self):
        m = metrics([], [{'equity': float(EQUITY)}], 'SHARED_PORTFOLIO')
        for field in ('win_rate_percent', 'profit_factor', 'expectancy', 'average_R', 'median_holding_seconds'):
            self.assertIsNone(m[field])
        self.assertEqual(m['net_pnl'], 0)
        self.assertFalse(m['performance_identifiable'])

    def test_closed_metrics_net_r_and_streak(self):
        rows = []
        for i, exit_price in enumerate((90, 90, 110)):
            rows.append({'candidate_id': str(i), 'status': 'CLOSED', 'entry_at': 10 * i,
                         'exit_at': 10 * i + 5, 'initial_risk': 5, **money('LONG', 100, exit_price, 1)})
        result = metrics(rows, [{'equity': 1170}, {'equity': 1160}], 'INDEPENDENT_SOURCE_CASES')
        self.assertEqual(result['max_loss_streak'], 2)
        self.assertEqual(result['median_holding_seconds'], 5)
        self.assertAlmostEqual(result['expectancy'], result['net_pnl'] / 3)
        self.assertEqual(result['LOSS'], 2)

    def test_open_eof_not_forced_closed(self):
        result = metrics([{'status': 'OPEN'}], [{'equity': 1170}], 'SHARED_PORTFOLIO')
        self.assertEqual(result['open_censored'], 1)
        self.assertEqual(result['closed'], 0)
        self.assertIsNone(result['win_rate_percent'])

    def test_drawdown_uses_chronological_peaks_not_future_equity(self):
        curve = [{'equity': 1170}, {'equity': 1200}, {'equity': 1080}]
        self.assertEqual(drawdown(curve), (120, 0.1))


if __name__ == '__main__':
    unittest.main()
