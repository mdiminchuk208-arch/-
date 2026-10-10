from __future__ import annotations

import inspect
import json
import tempfile
import unittest
from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from crypto_bot.common.models import Candle
from crypto_bot.strategy.anti_scalp import AntiScalpPolicy, check_anti_scalp
from crypto_bot.strategy.source_medium_term import (
    MediumTermEngine,
    MediumTermPortfolio,
    portfolio_signal,
)
from crypto_bot.strategy.source_pdf_native import Raid, Zone

T = datetime(2023, 1, 1, tzinfo=UTC)
REPO = Path(__file__).resolve().parents[1]


class AntiScalpTests(unittest.TestCase):
    def decision(self, **overrides):
        inputs = {'direction': 'LONG', 'entry': 100., 'target': 101., 'setup_tf': 60,
                      'context_tf': 240, 'main_setup_valid': True, 'context_valid': True,
                      'target_known_before_entry': True}
        return check_anti_scalp(**(inputs | overrides))

    def test_four_costs_and_cash_identity_both_directions(self):
        for direction, target, s in [('LONG', 110., 1), ('SHORT', 90., -1)]:
            d = self.decision(direction=direction, target=target)
            self.assertTrue(d.allowed)
            self.assertAlmostEqual(d.estimated_round_trip_cost,
                                   d.entry_fee+d.exit_fee+d.entry_slippage+d.exit_slippage)
            entry_fill, exit_fill = 100*(1+s*.0002), target*(1-s*.0002)
            self.assertAlmostEqual(d.expected_net_move, s*(exit_fill-entry_fill)-.0006*(entry_fill+exit_fill))

    def test_reason_precedence_and_missing_context(self):
        for overrides, reason in [({'setup_tf': 15}, 'NO_HTF_CONTEXT'),
                                  ({'context_tf': 60}, 'NO_HTF_CONTEXT'),
                                  ({'context_valid': False}, 'NO_HTF_CONTEXT'),
                                  ({'target': None}, 'TARGET_TOO_CLOSE'),
                                  ({'target': 100.1}, 'TARGET_TOO_CLOSE'),
                                  ({'target': 100.4}, 'POOR_EDGE_COST_RATIO'),
                                  ({'target_known_before_entry': False}, 'TARGET_TOO_CLOSE')]:
            d = self.decision(**overrides)
            self.assertFalse(d.allowed)
            self.assertEqual(d.status, 'REJECTED_SCALP_RISK')
            self.assertEqual(d.reason, 'REJECTED_SCALP_' + reason)

    def test_threshold_boundary_and_zero_costs(self):
        d = self.decision(target=101.)
        p = AntiScalpPolicy(minimum_edge_cost_ratio=d.edge_cost_ratio)
        self.assertTrue(self.decision(target=101., policy=p).allowed)
        self.assertTrue(self.decision(policy=AntiScalpPolicy(0., 0.)).allowed)

    def test_no_outcome_or_future_duration_inputs(self):
        params = set(inspect.signature(check_anti_scalp).parameters)
        self.assertFalse(params & {'duration', 'holding_time', 'exit_time', 'outcome', 'pnl', 'future'})
        self.assertEqual(asdict(self.decision()), asdict(self.decision()))
        self.assertFalse(self.decision().trade_entry_allowed)

    def test_invalid_costs_and_safety(self):
        for args in [{'fee_fraction': -.1}, {'slippage_fraction': float('nan')},
                     {'minimum_edge_cost_ratio': 1.}]:
            with self.assertRaises(ValueError):
                AntiScalpPolicy(**args)


def fixture():
    policy = json.loads((REPO / 'config/source_medium_term_policy.json').read_text())
    raid = Raid('LONG', T, 94, 90, 0, ('REAL_LOW',))
    proof = {'known_at': T+timedelta(hours=1), 'kind': 'REAL_OB_SOURCE_CONFIRMATION',
             'direction': 'LONG', 'protected': 90., 'extreme': 120.}
    parent = Zone('MAIN_H1_OB', 'ORDER_BLOCK', 'LONG', 90., 100.,
                  T+timedelta(hours=1), T+timedelta(hours=1), 0, raid, 90., 120., structural_proof=proof)
    structure = {'direction': 'LONG', 'protected': 80., 'extreme': 150., 'known_at': T+timedelta(hours=1)}
    target_zones = [Zone('MACRO_TARGET_'+str(p), 'SUPPLY', 'SHORT', p, p+2,
                         T, T, 0, None, 80., 150., structural_proof=proof) for p in [110., 120., 130.]]
    owners = {}
    for tf in [15, 60, 240, 1440]:
        c = Candle(T+timedelta(hours=2), T+timedelta(hours=2, minutes=tf), 102., 104., 101., 103.)
        owners[tf] = SimpleNamespace(index=0, candles=[c], structure=structure if tf >= 240 else proof,
                                     flow={'direction': 'LONG', 'structure': proof, 'known_at': proof['known_at'], 'invalidated_at': None},
                                     zones=target_zones if tf == 240 else [], pools={}, range_bounds={},
                                     range_terminal={}, atr_values=[2.], context_watches={})
    return MediumTermEngine('BTCUSDT', owners, policy), parent, raid


class MediumEngineTests(unittest.TestCase):
    def emit(self, engine, parent, raid, pid='ONE_IDEA', **kw):
        start = len(engine.signals)
        engine._emit('OB_DIRECT_FIRST_TEST', 60, 15, parent, kw.pop('local', parent),
                     T+timedelta(hours=4), pid, 1, T+timedelta(hours=2), raid,
                     entry_tf=kw.pop('entry_tf', 60), **kw)
        engine._finalize_ready(start, T+timedelta(hours=4))

    def test_main_ownership_targets_cost_and_alias_dedup(self):
        e, parent, raid = fixture()
        self.emit(e, parent, raid)
        self.assertEqual(len(e.signals), 1)
        s = e.signals[0]
        self.assertEqual(s.targets, (110., 120., 130.))
        self.assertEqual(s.fractions, (.4, .3, .3))
        self.assertEqual(s.evidence['macro_context_tf'], 240)
        self.assertTrue(s.evidence['anti_scalp']['allowed'])
        self.emit(e, parent, raid)
        self.assertEqual(len(e.signals), 1)
        self.assertEqual([r['status'] for r in e.lifecycle], ['DISCOVERED', 'QUALIFIED', 'READY'])

    def test_lower_timeframe_cannot_own_idea(self):
        e, parent, raid = fixture()
        self.emit(e, parent, raid, entry_tf=15)
        self.assertFalse(e.signals)
        self.assertEqual(e.rejections[0]['reason'], 'REJECTED_SCALP_NO_HTF_CONTEXT')

    def test_cost_rejection_is_before_ready_and_future_target_excluded(self):
        e, parent, raid = fixture()
        target = e.series[240].zones[0]
        target.low, target.high = 100.2, 100.3
        self.emit(e, parent, raid)
        self.assertFalse(e.signals)
        self.assertEqual(e.rejections[0]['reason'], 'REJECTED_SCALP_POOR_EDGE_COST_RATIO')
        target.known_at = T+timedelta(days=1)
        prices = [r['price'] for r in e._targets('LONG', 100., T+timedelta(hours=4))]
        self.assertNotIn(100.2, prices)

    def test_canonical_partial_be_and_same_clock_mode_determinism(self):
        e, parent, raid = fixture()
        self.emit(e, parent, raid)
        s = e.signals[0]
        records = []
        for mode in ['BACKTEST', 'SHADOW']:
            p = MediumTermPortfolio(equity=1170., mode=mode)
            c = Candle(s.known_at-timedelta(minutes=15), s.known_at, 103., 104., 102., 103.)
            p.source_step({'BTCUSDT': c}, [s])
            c = Candle(s.known_at, s.known_at+timedelta(minutes=15), 100., 104., 99., 103.)
            p.source_step({'BTCUSDT': c})
            c = Candle(c.close_time, c.close_time+timedelta(minutes=15), 105., 111., 104., 110.)
            p.source_step({'BTCUSDT': c})
            trade = next(iter(p.trades.values()))
            self.assertEqual(trade['status'], 'OPEN')
            self.assertAlmostEqual(p.positions['BTCUSDT'].remaining_fraction, .6)
            be = trade['new_breakeven']
            self.assertGreater(be, 100.)
            c = Candle(c.close_time, c.close_time+timedelta(minutes=15), 105., 106., be-1., 104.)
            p.source_step({'BTCUSDT': c})
            self.assertEqual(trade['status'], 'CLOSED')
            self.assertFalse(p.trade_entry_allowed)
            records.append((trade['net_pnl'], trade['fees_total'], trade['slippage_total'], trade['fills']))
        self.assertEqual(records[0], records[1])

    def test_adapter_retains_real_source_confirmation(self):
        e, parent, raid = fixture()
        self.emit(e, parent, raid)
        s = portfolio_signal(e.signals[0], 15)
        self.assertLess(s.sfp_time, s.bos_time)
        self.assertIn('REAL_OB_SOURCE_CONFIRMATION', s.source_qualification_evidence[0])

    def test_refinement_invalidation_withdraws_pending_but_preserves_main_exit_watch(self):
        e, parent, raid = fixture()
        local = Zone('REFINEMENT_M15_OB', 'ORDER_BLOCK', 'LONG', 95., 100.,
                     parent.formed_at, parent.known_at, 0, raid, 90., 120.,
                     structural_proof=parent.structural_proof)
        self.emit(e, parent, raid, local=local, entry_tf=15)
        local.invalidated_at = T+timedelta(hours=5)
        c = Candle(T+timedelta(hours=4, minutes=45), local.invalidated_at, 102., 104., 101., 103.)
        e._lifecycle(15, c)
        self.assertEqual(e.cancellations[0]['reason'], 'REFINEMENT_POI_BODY_INVALIDATED_PENDING_ONLY')
        self.assertFalse(e.exit_events)
        self.assertEqual(len(e._live_signals), 1)
        c = Candle(c.close_time, c.close_time+timedelta(hours=1), 92., 93., 88., 89.)
        e._lifecycle(60, c)
        self.assertEqual(e.exit_events[0]['reason'], 'MAIN_PROTECTED_STRUCTURE_BODY_BREAK')

    def test_sfp_pd_uses_actual_macro_dealing_range(self):
        from crypto_bot.strategy.source_permitted import SourceContextZone
        e, local, raid = fixture()
        parent = SourceContextZone('REAL_MAIN_SFP', 'SFP', 'LONG', 90., 100., T, T, 0,
                                   raid, 90., 100., confluence={'next_open_time': T})
        flow = {'direction': 'LONG', 'known_at': T+timedelta(hours=1), 'invalidated_at': None}
        e._emit('SFP_BOS_POI', 60, 15, parent, local, T+timedelta(hours=4), 'SFP_IDEA', 1,
                T, raid, flow_override=flow)
        e._finalize_ready(0, T+timedelta(hours=4))
        pd = e.signals[0].evidence['premium_discount']
        self.assertEqual((pd['low'], pd['high']), (80., 150.))

    def test_future_range_terminal_metadata_cannot_invalidate_now(self):
        from crypto_bot.strategy.source_permitted import SourceContextZone
        e, local, raid = fixture()
        parent = SourceContextZone('MAIN_RANGE', 'RANGE_POI', 'LONG', 90., 140., T, T, 0,
                                   raid, 90., 140., range_id='ACTUAL_RANGE')
        e._emit('RANGE_AGGRESSIVE_EXTERNAL_POI', 60, 15, parent, local,
                T+timedelta(hours=4), 'RANGE_IDEA', 1, T, raid,
                flow_override={'direction': 'LONG', 'known_at': T}, entry_tf=60)
        e._finalize_ready(0, T+timedelta(hours=4))
        e.series[60].range_terminal['ACTUAL_RANGE'] = T+timedelta(days=10)
        c = Candle(T+timedelta(hours=4), T+timedelta(hours=5), 102., 104., 101., 103.)
        e._lifecycle(60, c)
        self.assertFalse(e.exit_events)
        c = replace(c, open_time=T+timedelta(days=10), close_time=T+timedelta(days=10, hours=1))
        e._lifecycle(60, c)
        self.assertEqual(e.exit_events[0]['reason'], 'MAIN_RANGE_EXHAUSTED')

    def test_target_consumption_expires_pending_without_position_exit(self):
        e, parent, raid = fixture()
        self.emit(e, parent, raid)
        c = Candle(T+timedelta(hours=4), T+timedelta(hours=4, minutes=15), 108., 111., 107., 110.)
        e._lifecycle(15, c)
        self.assertEqual(e.cancellations[0]['reason'], 'MAIN_TARGET_CONSUMED_PENDING_ONLY')
        self.assertFalse(e.exit_events)

    def test_h1_parent_inside_h4_flow_exits_on_h1_observation(self):
        e, parent, raid = fixture()
        e._emit('DEMAND_SUPPLY', 240, 60, parent, parent, T+timedelta(hours=4),
                'ACTUAL_H1_SETUP', 1, T, raid, entry_tf=60)
        e._finalize_ready(0, T+timedelta(hours=4))
        s = e.signals[0]
        self.assertEqual(s.evidence['actual_setup_tf'], 60)
        self.assertEqual(s.evidence['flow_owner_tf'], 240)
        self.assertEqual(portfolio_signal(s, 15).htf_minutes, 60)
        parent.invalidated_at = T+timedelta(hours=5)
        c = Candle(T+timedelta(hours=4), parent.invalidated_at, 92., 93., 88., 89.)
        e._lifecycle(60, c)
        self.assertEqual(e.exit_events[0]['known_at'], parent.invalidated_at)

    def test_resume_checks_artifact_membership_and_bytes(self):
        import sys
        sys.path.insert(0, str(REPO / 'scripts'))
        from run_medium_term_research import resume, seal, write_json
        with tempfile.TemporaryDirectory(dir=REPO / 'data') as temp:
            folder = Path(temp)
            write_json(folder / 'artifact.json', {'safe': True})
            seal(folder, 'fingerprint', {})
            self.assertTrue(resume(folder, 'fingerprint', True))
            with self.assertRaises(ValueError):
                resume(folder, 'changed', True)
            (folder / 'artifact.json').write_text('tampered')
            with self.assertRaises(ValueError):
                resume(folder, 'fingerprint', True)


if __name__ == '__main__':
    unittest.main()
