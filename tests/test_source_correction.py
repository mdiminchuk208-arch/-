from __future__ import annotations

from dataclasses import asdict, replace
from datetime import timedelta
from hashlib import sha256
import json
from pathlib import Path
import random
import tempfile
import unittest

from crypto_bot.strategy.market_analysis import analyze_market, MarketEvent, MarketEventKind as K, TrendState
from crypto_bot.strategy.source_corrected import (MAPPINGS, Pool, Raid, SourceEngine, SourceSeries, Zone,
                                                  evidence_json, liquidity_roles, poi_entry_policy)
from crypto_bot.strategy.source_cases import deduplicate_cases, replay_case
from crypto_bot.strategy.source_portfolio import SourcePortfolio
from scripts.run_source_cases_bybit import verify_segment
from tests.test_source_engine import START, candle, signal


def zone(kind='DEMAND', direction='LONG', low=95, high=100, name='poi'):
    return Zone(name, kind, direction, low, high, START, START, 0,
                Raid(direction, START, low, low - 1, 0, ('SWING:0',)), low - 1, high + 10)


class SourceCorrectionTests(unittest.TestCase):
    def test_strict_excludes_60m_execution(self):
        self.assertEqual(MAPPINGS, ((15, 5), (60, 5), (60, 15), (240, 5), (240, 15)))

    def test_ds_independent_multicandle_no_fvg(self):
        cs = [candle(0, 103, 104, 101, 102), candle(1, 102, 103, 98, 99),
              candle(2, 99, 105, 98.5, 104.5)]
        event = MarketEvent(K.BULLISH_STRUCTURE_CONFIRMED, 2, cs[2].close_time, 104.5, 1, 98, 'UNIT')
        series = SourceSeries('BTCUSDT', 5, cs, replace(analyze_market(cs), events=(event,)))
        series.pools['old'] = Pool('SWING:old', 'low', 100, START, 'SSL', 'EXTERNAL')
        for i in range(3):
            series.advance(i)
        ds = [z for z in series.zones if z.kind == 'DEMAND']
        self.assertEqual(len(ds), 1)
        self.assertEqual((ds[0].origin_index, ds[0].move_end_index, ds[0].low, ds[0].high), (0, 1, 98, 104))
        self.assertFalse(any(z.kind == 'FVG' for z in series.zones))
        self.assertEqual(ds[0].raid.candle_index, 1)

    def test_failed_ob_does_not_manufacture_ds_without_move_raid(self):
        cs = [candle(0, 105, 106, 102, 104), candle(1, 104, 104.5, 101, 102),
              candle(2, 102, 109, 99, 108), candle(3, 108, 111, 107, 110)]
        event = MarketEvent(K.BULLISH_STRUCTURE_CONFIRMED, 3, cs[3].close_time, 110, 1, 99, 'UNIT')
        series = SourceSeries('BTCUSDT', 5, cs, replace(analyze_market(cs), events=(event,)))
        series.pools['old'] = Pool('SWING:old', 'low', 100, START, 'SSL', 'EXTERNAL')
        for i in range(4):
            series.advance(i)
        self.assertFalse(any(z.kind in ('DEMAND', 'ORDER_BLOCK') for z in series.zones))

    def test_pending_ds_return_is_already_a_test(self):
        cs = [candle(0, 105, 106, 99, 104)]
        series = SourceSeries('BTCUSDT', 5, cs, analyze_market(cs))
        z = zone()
        series.pending = [z]
        series.advance(0)
        self.assertEqual(z.invalidated_at, cs[0].close_time)
        self.assertFalse(any(p.kind == 'DEMAND' for p in series.zones))

    def _range_fixture(self, external):
        cs = [candle(0, 102, 104, 100, 102), candle(1, 102, 103, 94, 102),
              candle(2, 102, 105, 101, 104), candle(3, 104, 106, 102, 105),
              candle(4, 105, 107, 99, 103)]
        series = SourceSeries('BTCUSDT', 5, cs, analyze_market(cs))
        series.range_bounds[1] = (100, 110, START, 'causal-range')
        series.range_events[2] = [MarketEvent(K.BULLISH_SFP_FORMATION_CONFIRMED, 2, cs[2].close_time,
                                             104, 1, 100, 'UNIT', sfp_pattern_extreme_price=94, range_id=1)]
        if external:
            z = zone(low=93, high=96)
            series.zones = [z]
            series.zone_registry[z.zone_id] = z
        return cs, series

    def test_range_sfp_without_external_poi_cannot_create_permission(self):
        cs, series = self._range_fixture(False)
        for i in range(len(cs)):
            series.advance(i)
        self.assertFalse(any(z.kind == 'RANGE_POI' for z in series.zones))
        self.assertEqual(series.counts['range_sfp_without_required_external_poi'], 1)

    def test_range_requires_separate_reclaim_then_boundary_retest(self):
        cs, series = self._range_fixture(True)
        observed = []
        for i in range(len(cs)):
            touched, _ = series.advance(i)
            observed.extend(z for z in touched if z.kind == 'RANGE_POI')
            if i < 4:
                self.assertEqual(observed, [])
        self.assertEqual(len(observed), 1)
        z = observed[0]
        self.assertEqual(z.external_poi['zone_id'], 'poi')
        self.assertEqual(z.range_reclaim_at, cs[3].close_time)
        self.assertEqual(z.range_retest_at, cs[4].close_time)
        self.assertLess(z.external_poi['known_at'], cs[1].open_time)

    def test_external_poi_formed_after_deviation_is_not_causal(self):
        cs, series = self._range_fixture(True)
        z = series.zones[0]
        z.formed_at = z.known_at = cs[1].close_time
        for i in range(len(cs)):
            series.advance(i)
        self.assertEqual(series.counts['zone_RANGE_POI'], 0)

    def test_type_specific_quotes_and_conservative_breaker_stop(self):
        raid = Raid('LONG', START, 93, 90, 0, ('SWING:0',))
        self.assertEqual(poi_entry_policy(zone('ORDER_BLOCK'), raid)[:2], (100, 95))
        self.assertEqual(poi_entry_policy(zone('DEMAND'), raid)[:2], (97.5, 95))
        self.assertEqual(poi_entry_policy(zone('STB'), raid)[:2], (97.5, 94))
        breaker = zone('BREAKER')
        breaker.stop_extreme = 88
        self.assertEqual(poi_entry_policy(breaker, raid)[:2], (100, 88))
        self.assertEqual(poi_entry_policy(zone('FVG'), raid)[:2], (97.5, 90))
        short = zone('BTS', 'SHORT')
        self.assertEqual(poi_entry_policy(short, Raid('SHORT', START, 110, 112, 0, ('SWING:1',)))[0], 97.5)

    def test_liquidity_against_context_is_not_limited_to_stop_band(self):
        cs = [candle(0, 100, 101, 99, 100)]
        h = SourceSeries('BTCUSDT', 60, cs, analyze_market(cs))
        l = SourceSeries('BTCUSDT', 5, cs, analyze_market(cs))
        z = zone()
        z.leg_low = 85
        h.pools = {'below_stop': Pool('a', 'low', 90, START, 'SSL', 'INTERNAL'),
                   'remote_equal': Pool('b', 'low', 80, START, 'EQL', 'EXTERNAL'),
                   'unrelated': Pool('c', 'low', 70, START, 'SSL', 'EXTERNAL')}
        roles = {r['pool_id']: r['role'] for r in liquidity_roles(h, l, z, 'LONG', 100, START)}
        self.assertEqual(roles, {'a': 'AGAINST_SETUP', 'b': 'AGAINST_SETUP', 'c': 'UNRELATED_WITHOUT_CONTEXT'})

    def _flow_fixture(self):
        cs = [candle(0, 100, 103, 99, 102), candle(1, 102, 104, 94, 101), candle(2, 101, 111, 100, 110)]
        series = SourceSeries('BTCUSDT', 60, cs, analyze_market(cs))
        series.index = 2
        series.trend = TrendState.BULLISH
        series.structure = {'direction': 'LONG', 'protected': 100, 'extreme': 110, 'known_at': cs[1].close_time}
        series.swing_history = {'high': [{'price': 103, 'known_at': START, 'level_id': 1},
                                         {'price': 109, 'known_at': cs[1].close_time, 'level_id': 2}],
                                'low': [{'price': 95, 'known_at': START, 'level_id': 3},
                                        {'price': 100, 'known_at': cs[1].close_time, 'level_id': 4}]}
        series.raids = [Raid('LONG', cs[1].close_time, 95, 94, 1, ('SWING:3',))]
        target = zone('SUPPLY', 'SHORT', 115, 120, 'global')
        series.zones = [target]
        series.zone_registry[target.zone_id] = target
        proof = {'kind': K.BULLISH_CONF_CONFIRMED.value, 'direction': 'LONG', 'known_at': cs[2].close_time}
        return cs, series, proof

    def test_flow_requires_liquidity_work_break_and_directional_sequence(self):
        cs, series, proof = self._flow_fixture()
        raids = series.raids
        series.raids = []
        series._update_flow(cs[2], [proof])
        self.assertIsNone(series.flow)  # trend alone is insufficient.
        series.last_flow_conf = None
        series.raids = raids
        series._update_flow(cs[2], [proof])
        self.assertIsNotNone(series.flow)
        self.assertEqual(series.flow['destination_poi']['zone_id'], 'global')
        self.assertLess(series.flow['key_test']['known_at'], series.flow['body_break_at'])

    def test_tested_global_destination_cannot_silently_retarget(self):
        cs, series, proof = self._flow_fixture()
        series._update_flow(cs[2], [proof])
        series.zone_registry['global'].first_test = cs[2].close_time + timedelta(minutes=5)
        future = candle(3, 110, 116, 109, 115)
        series._update_flow(future, [])
        self.assertEqual(series.flow['invalidated_at'], future.close_time)
        self.assertEqual(len(series.flow_history), 1)

    def test_smaller_native_bar_test_invalidates_global_flow(self):
        cs, h, proof = self._flow_fixture()
        h._update_flow(cs[2], [proof])
        future = candle(3, 110, 116, 109, 115)
        l = SourceSeries('BTCUSDT', 5, [future], analyze_market([future]))
        engine = SourceEngine('BTCUSDT', {60: h, 5: l})
        engine.advance(5, 0)
        self.assertEqual(h.flow['invalidated_at'], future.close_time)

    def test_full_prefix_and_future_mutation_preserve_all_corrected_state(self):
        rng, price, cs = random.Random(117), 100., []
        for i in range(140):
            close = price + rng.uniform(-2, 2)
            cs.append(candle(i, price, max(price, close) + .5, min(price, close) - .5, close))
            price = close
        future = [candle(i, 100, 150 + i, 20, 100) for i in range(140, 145)]
        full = SourceSeries('BTCUSDT', 5, cs + future, analyze_market(cs + future))
        for i in range(len(cs)):
            full.advance(i)
            if i % 17:
                continue
            prefix = SourceSeries('BTCUSDT', 5, cs[:i + 1], analyze_market(cs[:i + 1]))
            for n in range(i + 1):
                prefix.advance(n)
            for attr in ('zones', 'pools', 'flow', 'flow_history', 'range_audit', 'counts'):
                a, b = getattr(full, attr), getattr(prefix, attr)
                if attr == 'zones':
                    a, b = [asdict(v) for v in a], [asdict(v) for v in b]
                if attr == 'pools':
                    a, b = {k: asdict(v) for k, v in a.items()}, {k: asdict(v) for k, v in b.items()}
                self.assertEqual(evidence_json(a), evidence_json(b))


class SourceCaseTests(unittest.TestCase):
    def test_cases_ignore_other_symbol_occupancy_and_portfolio_budget(self):
        s = replace(signal(), stop=99.9, targets=(101.,))
        cs = [candle(0, 100.5, 100.6, 100, 100.2), candle(1, 100.2, 101.5, 100, 101)]
        account = SourcePortfolio()
        account.offer(s)
        account.on_bar('BTCUSDT', cs[0])
        self.assertEqual(account.trades, [])  #3x virtual budget restriction.
        a = replay_case(s, cs, [])
        b = replay_case(replace(s, signal_id='other', symbol='ETHUSDT'), cs, [])
        self.assertEqual([a.trades[0]['status'], b.trades[0]['status']], ['CLOSED', 'CLOSED'])
        self.assertAlmostEqual(a.trades[0]['risk_amount'], 23.4)
        self.assertEqual(a.trades[0]['risk_amount'], b.trades[0]['risk_amount'])
        self.assertFalse(a.trades[0]['trade_entry_allowed'])

    def test_known_cancellation_and_endpoint_censoring(self):
        s = signal()
        cs = [candle(0, 101, 102, 99, 101)]
        a = replay_case(s, cs, [{'known_at': START, 'reason': 'FLOW_TESTED'}])
        self.assertEqual(a.trades, [])
        b = replay_case(s, cs, [])
        self.assertEqual(b.trades[0]['status'], 'OPEN')
        c = replay_case(s, [candle(0, 102, 103, 101, 102)], [])
        self.assertEqual(c.decisions[-1]['reason'], 'PENDING_RIGHT_CENSORED')

    def test_physical_aliases_and_mappings_dedup_before_outcomes(self):
        h = asdict(zone())
        h['first_test'] = START
        l = asdict(zone('ORDER_BLOCK'))
        a = replace(signal(), evidence={'htf_poi': h, 'ltf_poi': l, 'exit_policy': 'FTA'})
        b = replace(a, signal_id='other_mapping', htf=240, ltf=15)
        accepted, duplicates = deduplicate_cases([a, b], ['BTCUSDT'])
        self.assertEqual(len(accepted), 1)
        self.assertEqual(len(duplicates), 1)
        distinct = replace(a, signal_id='next_reaction', evidence={**a.evidence, 'htf_poi': {**h, 'first_test': START + timedelta(days=1)}})
        self.assertEqual(len(deduplicate_cases([a, distinct], ['BTCUSDT'])[0]), 2)

    def test_corrected_resume_requires_every_causal_evidence_artifact(self):
        files = ('signals.jsonl.gz', 'cancellations.jsonl.gz', 'setup_outcomes.jsonl.gz', 'summary.json',
                 'old_loss_audit.json', 'intermediate_audit.json', 'flow_history.jsonl.gz', 'range_audit.jsonl.gz')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in files:
                (root / name).write_bytes(b'causal evidence fixture')
            m = {'status': 'COMPLETE', 'fingerprint': 'exact',
                 'artifacts': {n: sha256((root / n).read_bytes()).hexdigest() for n in files}}
            (root / 'manifest.json').write_text(json.dumps(m))
            self.assertEqual(verify_segment(root, 'exact'), m)
            (root / 'flow_history.jsonl.gz').write_bytes(b'corruption')
            with self.assertRaises(ValueError):
                verify_segment(root, 'exact')


if __name__ == '__main__':
    unittest.main()
