import unittest
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone

from crypto_bot.common.models import Candle, Direction
from crypto_bot.strategy.auto_levels import AutoLevelPolicy, derive_automatic_levels
from crypto_bot.strategy.market_analysis import (
    MarketAnalysisReport, MarketEvent, MarketEventKind, OrderBlockReadiness,
    StructuralLevel, StructureAnalysisMode, StructureTransitionDiagnostic, TrendState,
)
from crypto_bot.strategy.mtf_sfp import MtfOpportunity, MtfOpportunityStatus
from crypto_bot.strategy.trade_plan import ote_entry_zone


BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def valid_case(direction=Direction.LONG):
    """OHLC-evidence fixture; returns exact derive_automatic_levels kwargs.

    Explicit structural reports make each causal condition independently mutable;
    they are not a claim that these synthetic candles form a profitable strategy.
    HTF60/LTF5, geometry ready == as_of, no post-formation OB retest.
    """
    htf = []
    ranges = ((140, 141), (140, 141), (130, 131), (130, 131),
              (120, 121), (120, 121), (110, 111), (110, 111),
              (94, 95), (94, 95), (98, 99))
    for index, (low, high) in enumerate(ranges):
        t = BASE + timedelta(hours=index)
        htf.append(Candle(t, t + timedelta(hours=1), low, high, low, high))
    ltf = []
    start = BASE + timedelta(hours=10, minutes=30)
    for index in range(18):
        low = 94 if index == 1 else 96 if index == 4 else 99
        high = 102 if index == 8 else 101
        t = start + timedelta(minutes=5 * index)
        ltf.append(Candle(t, t + timedelta(minutes=5), 100, high, low, 100.5))
    ltf[-1] = replace(ltf[-1], high=105, close=105)
    for o, h, l, c in ((98.5, 99, 94.5, 97), (96.5, 104, 96, 103.5),
                       (104, 110, 100, 109), (106, 108, 101, 105),
                       (103, 106, 100, 102), (104, 109, 101, 108)):
        t = ltf[-1].close_time
        ltf.append(Candle(t, t + timedelta(minutes=5), o, h, l, c))
    if direction == Direction.SHORT:
        def mirror(candle):
            return replace(candle, open=200-candle.open, close=200-candle.close,
                           high=200-candle.low, low=200-candle.high)
        htf, ltf = [mirror(c) for c in htf], [mirror(c) for c in ltf]
    def structural(level_id, side, index, confirmed):
        candle = ltf[index]
        return StructuralLevel(level_id, side, candle.high if side == 'high' else candle.low,
                               index, confirmed, candle.open_time, ltf[confirmed].close_time)
    adverse = 'low' if direction == Direction.LONG else 'high'
    favorable = 'high' if direction == Direction.LONG else 'low'
    levels = (structural(1, adverse, 1, 2), structural(2, adverse, 4, 5),
              structural(3, favorable, 8, 9), structural(4, favorable, 20, 21),
              structural(5, adverse, 22, 23))
    bos_kind = (MarketEventKind.BEARISH_STRUCTURE_BROKEN_BOS if direction == Direction.LONG
                else MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS)
    sweep_kind = (MarketEventKind.LOW_LIQUIDITY_TAKEN if direction == Direction.LONG
                  else MarketEventKind.HIGH_LIQUIDITY_TAKEN)
    bos = MarketEvent(bos_kind, 17, ltf[17].close_time, ltf[17].close,
                      3, levels[2].price, 'fixture exact BOS')
    sweep = MarketEvent(sweep_kind, 18, ltf[18].close_time,
                        ltf[18].low if direction == Direction.LONG else ltf[18].high,
                        2, levels[1].price, 'fixture raw structural sweep')
    trend = TrendState.BULLISH if direction == Direction.LONG else TrendState.BEARISH
    previous_trend = TrendState.BEARISH if direction == Direction.LONG else TrendState.BULLISH
    as_of = ltf[-1].close_time
    transition = StructureTransitionDiagnostic(
        1, bos_kind.value, 17, bos.event_time, previous_trend, trend,
        levels[2].price, levels[0].price, 23, as_of, trend,
        'EXPECTED_OPPOSITE_LOCAL_STRUCTURE', 6, (4,) if direction == Direction.LONG else (5,),
        (5,) if direction == Direction.LONG else (4,), 4, 5, (),
    )
    def report(candles, **kw):
        return MarketAnalysisReport(len(candles), trend, (), (), (),
                                    OrderBlockReadiness(False, 'NOT_AUTOMATIC', ()),
                                    'SOURCE_CONSERVATIVE', 'H1', 'SOURCE', **kw)
    htf_report = report(htf)
    ltf_report = replace(report(ltf), levels=levels, events=(bos, sweep),
                         structure_transition_diagnostics=(transition,))
    zone = ote_entry_zone(direction=direction, impulse_start_price=levels[0].price,
                          impulse_end_price=levels[3].price)
    opportunity = MtfOpportunity(
        1, MtfOpportunityStatus.ENTRY_SEARCH_CANDIDATE, direction,
        bos_kind, bos.event_time, 17, 3, levels[2].price, (1,), (1,), (1,),
        bos.event_time - timedelta(hours=1), bos.event_time - timedelta(hours=1), 1,
        entry_geometry_ready_time=as_of, entry_geometry_transition_id=1,
        impulse_start_price=levels[0].price, impulse_end_price=levels[3].price,
        entry_zone_low=zone.low, entry_zone_high=zone.high, entry_anchor_level_id=4,
        entry_correction_level_id=5, entry_correction_price=levels[4].price,
    )
    return dict(htf_candles=htf, ltf_candles=ltf, htf_report=htf_report, ltf_report=ltf_report,
                opportunity=opportunity, as_of=as_of, policy=AutoLevelPolicy())


class AutomaticLevelTests(unittest.TestCase):
    def test_valid_long_references_and_provenance(self):
        case = valid_case()
        result = derive_automatic_levels(**case)
        self.assertEqual(result.status, 'READY', result.blocked_reasons)
        self.assertEqual(result.stop_loss, 94.5)
        self.assertEqual(result.targets, (111, 121, 131))
        self.assertEqual(result.known_at, case['as_of'])
        self.assertEqual(result.blocked_reasons, ())
        self.assertTrue(all(e.known_at <= result.known_at for e in result.evidence))
        self.assertIn('BACKTEST_PARAMETER', result.target_policy)
        self.assertTrue(any(e.kind == 'SUPPORTING_HTF_POI' for e in result.evidence))
        self.assertEqual(asdict(result)['stop_loss'], 94.5)

    def test_short_is_exact_price_mirror(self):
        long = derive_automatic_levels(**valid_case())
        short = derive_automatic_levels(**valid_case(Direction.SHORT))
        self.assertEqual(short.status, 'READY', short.blocked_reasons)
        self.assertEqual(short.stop_loss, 200-long.stop_loss)
        self.assertEqual(short.targets, tuple(200-target for target in long.targets))
        self.assertEqual(short.known_at, long.known_at)

    def assertBlocked(self, case, reason):
        result = derive_automatic_levels(**case)
        self.assertEqual(result.status, 'BLOCKED')
        self.assertIn(reason, result.blocked_reasons)
        self.assertIsNone(result.stop_loss)
        self.assertEqual(result.targets, ())
        self.assertEqual(result.blocked_reasons, tuple(sorted(set(result.blocked_reasons))))

    def test_full_history_and_prefix_have_identical_causal_results(self):
        case = valid_case()
        expected = derive_automatic_levels(**case)
        t = case['as_of']
        case['ltf_candles'].append(Candle(t, t+timedelta(minutes=5), 80, 200, 70, 90))
        future = BASE + timedelta(hours=13)
        case['htf_candles'].append(Candle(future, future+timedelta(hours=1), 80, 200, 70, 90))
        self.assertEqual(derive_automatic_levels(**case), expected)
        case['ltf_candles'][-1] = replace(case['ltf_candles'][-1], is_closed=False)
        self.assertEqual(derive_automatic_levels(**case), expected)

    def test_future_geometry_cannot_unlock_past_ob(self):
        case = valid_case()
        cutoff = case['ltf_candles'][20].close_time
        report = case['ltf_report']
        case['ltf_report'] = replace(report, candle_count=21,
                                     levels=tuple(l for l in report.levels if l.confirmed_time <= cutoff),
                                     structure_transition_diagnostics=())
        case['as_of'] = cutoff
        self.assertBlocked(case, 'ENTRY_GEOMETRY_NOT_READY')

    def test_aggressive_impulse_thresholds_are_explicit_experiments(self):
        for policy in (AutoLevelPolicy(.95), AutoLevelPolicy(min_engulf_body_ratio=5)):
            with self.subTest(policy=policy):
                case = valid_case()
                case['policy'] = policy
                self.assertBlocked(case, 'AGGRESSIVE_IMPULSE_THRESHOLD_NOT_MET')

    def test_invalid_thresholds_are_rejected(self):
        for value in (0, -1, 1.01, float('nan'), float('inf')):
            with self.subTest(fraction=value), self.assertRaises(ValueError):
                AutoLevelPolicy(min_body_fraction=value)
        for value in (.99, 0, float('nan'), float('inf')):
            with self.subTest(ratio=value), self.assertRaises(ValueError):
                AutoLevelPolicy(min_engulf_body_ratio=value)

    def test_missing_raw_structural_sweep_blocks_ob(self):
        case = valid_case()
        case['ltf_report'] = replace(case['ltf_report'], events=case['ltf_report'].events[:1])
        self.assertBlocked(case, 'RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND')

    def test_missing_preexisting_htf_seed_blocks_ob(self):
        case = valid_case()
        case['htf_candles'][10] = replace(case['htf_candles'][10], open=94, low=94)
        self.assertBlocked(case, 'FRESH_PREEXISTING_HTF_POI_NOT_FOUND')

    def test_supporting_seed_must_be_known_before_initiating_candle(self):
        case = valid_case()
        shift = timedelta(minutes=66)
        case['htf_candles'] = [replace(c, open_time=c.open_time+shift, close_time=c.close_time+shift)
                               for c in case['htf_candles']]
        self.assertBlocked(case, 'FRESH_PREEXISTING_HTF_POI_NOT_FOUND')

    def test_previous_ltf_touch_consumes_supporting_seed(self):
        for direction in (Direction.LONG, Direction.SHORT):
            with self.subTest(direction=direction):
                case = valid_case(direction)
                candle = case['ltf_candles'][10]
                case['ltf_candles'][10] = replace(candle, low=98) if direction == Direction.LONG else replace(candle, high=102)
                self.assertBlocked(case, 'FRESH_PREEXISTING_HTF_POI_NOT_FOUND')

    def test_seed_forming_third_candle_and_initiating_reaction_do_not_expire_context(self):
        case = valid_case()
        result = derive_automatic_levels(**case)
        self.assertEqual(result.status, 'READY')
        support = next(e for e in result.evidence if e.kind == 'SUPPORTING_HTF_POI')
        self.assertEqual(support.prices, (95, 98))
        self.assertEqual(support.known_at, BASE+timedelta(hours=11))

    def test_following_ltf_bar_consumes_ob_first_test_inclusive_of_edge(self):
        for direction in (Direction.LONG, Direction.SHORT):
            with self.subTest(direction=direction):
                case = valid_case(direction)
                t = case['as_of']
                candle = Candle(t, t+timedelta(minutes=5), 101, 102, 99, 100)
                if direction == Direction.SHORT:
                    candle = replace(candle, open=99, high=101, low=98, close=100)
                case['ltf_candles'].append(candle)
                case['as_of'] = candle.close_time
                case['ltf_report'] = replace(case['ltf_report'], candle_count=25)
                self.assertBlocked(case, 'OB_FIRST_TEST_ALREADY_CONSUMED')

    def test_imbalance_confirmation_required(self):
        case = valid_case()
        case['ltf_candles'][20] = replace(case['ltf_candles'][20], low=99)
        self.assertBlocked(case, 'DIRECTIONAL_IMBALANCE_NOT_CONFIRMED')

    def test_body_engulf_requires_both_previous_body_edges(self):
        case = valid_case()
        case['ltf_candles'][19] = replace(case['ltf_candles'][19], open=97.5)
        self.assertBlocked(case, 'NO_OB_PATTERN_IN_STRUCTURAL_IMPULSE')

    def test_opposite_candle_color_required(self):
        case = valid_case()
        case['ltf_candles'][18] = replace(case['ltf_candles'][18], close=98.9)
        self.assertBlocked(case, 'NO_OB_PATTERN_IN_STRUCTURAL_IMPULSE')

    def test_only_two_distinct_opposing_zones_cannot_pad_three_targets(self):
        case = valid_case()
        for index in (0, 1):
            case['htf_candles'][index] = replace(case['htf_candles'][index], open=130, high=131, low=130, close=131)
        self.assertBlocked(case, 'THREE_DISTINCT_FRESH_OPPOSING_POIS_NOT_FOUND')

    def test_ltf_touch_invalidates_opposing_target_seed(self):
        case = valid_case()
        case['ltf_candles'][12] = replace(case['ltf_candles'][12], high=111)
        self.assertBlocked(case, 'THREE_DISTINCT_FRESH_OPPOSING_POIS_NOT_FOUND')

    def test_duplicates_do_not_change_nearest_first_targets(self):
        case = valid_case()
        result = derive_automatic_levels(**case)
        # Plateau pairs produce duplicate HTF seeds. They are not extra targets.
        self.assertEqual(result.targets, (111, 121, 131))
        self.assertEqual(len({e.prices for e in result.evidence if e.kind.startswith('TARGET_POI_')}), 3)

    def test_ote_overlap_is_required(self):
        case = valid_case()
        case['ltf_candles'][18] = replace(case['ltf_candles'][18], open=96.5, high=97, close=95.5)
        case['ltf_candles'][19] = replace(case['ltf_candles'][19], open=95, low=94.5)
        self.assertBlocked(case, 'OB_OUTSIDE_OTE_OR_STRUCTURAL_IMPULSE')

    def test_entire_engulfing_range_must_remain_in_structural_impulse(self):
        case = valid_case()
        case['ltf_candles'][19] = replace(case['ltf_candles'][19], low=93)
        self.assertBlocked(case, 'OB_OUTSIDE_OTE_OR_STRUCTURAL_IMPULSE')

    def test_ob_stop_must_protect_entire_ote(self):
        case = valid_case()
        case['ltf_candles'][4] = replace(case['ltf_candles'][4], low=98)
        case['ltf_candles'][18] = replace(case['ltf_candles'][18], low=97.5, close=97.8)
        report = case['ltf_report']
        levels = list(report.levels)
        levels[1] = replace(levels[1], price=98)
        events = list(report.events)
        events[1] = replace(events[1], level_price=98, price=97.5)
        case['ltf_report'] = replace(report, levels=tuple(levels), events=tuple(events))
        self.assertBlocked(case, 'OB_STOP_DOES_NOT_PROTECT_ENTIRE_OTE')

    def test_missing_or_same_direction_transition_cannot_qualify(self):
        for transitions in ((), (replace(valid_case()['ltf_report'].structure_transition_diagnostics[0],
                                        resolved_trend=TrendState.BEARISH),)):
            with self.subTest(transitions=transitions):
                case = valid_case()
                case['ltf_report'] = replace(case['ltf_report'], structure_transition_diagnostics=transitions)
                self.assertBlocked(case, 'EXPECTED_OPPOSITE_STRUCTURAL_IMPULSE_NOT_FOUND')

    def test_exact_bos_identity_required(self):
        case = valid_case()
        case['opportunity'] = replace(case['opportunity'], ltf_bos_level_price=103)
        self.assertBlocked(case, 'EXACT_SOURCE_BOS_NOT_FOUND')

    def test_recovery_lineage_never_becomes_source_entry(self):
        case = valid_case()
        report = case['ltf_report']
        case['ltf_report'] = replace(report, events=(replace(report.events[0], recovery_transition_ids=(9,)), report.events[1]))
        self.assertBlocked(case, 'TECHNICAL_RECOVERY_LINEAGE_NOT_ENTRY_ELIGIBLE')

    def test_geometry_must_match_source_transition(self):
        case = valid_case()
        case['opportunity'] = replace(case['opportunity'], entry_zone_low=97)
        with self.assertRaises(ValueError):
            derive_automatic_levels(**case)

    def test_structural_confirmation_cannot_follow_claimed_geometry_availability(self):
        case = valid_case()
        earlier = case['ltf_candles'][22].close_time
        case['opportunity'] = replace(case['opportunity'], entry_geometry_ready_time=earlier)
        report = case['ltf_report']
        transition = replace(report.structure_transition_diagnostics[0], resolved_index=22, resolved_time=earlier)
        case['ltf_report'] = replace(report, structure_transition_diagnostics=(transition,))
        with self.assertRaises(ValueError):
            derive_automatic_levels(**case)

    def test_invalid_report_or_history_fails_closed(self):
        for problem in ('count', 'mode', 'level_price', 'event_index', 'duplicate_transition', 'unfinished', 'gap'):
            with self.subTest(problem=problem):
                case = valid_case()
                report = case['ltf_report']
                if problem == 'count':
                    case['ltf_report'] = replace(report, candle_count=25)
                elif problem == 'mode':
                    case['ltf_report'] = replace(report, analysis_mode=StructureAnalysisMode.TECHNICAL_RECOVERY)
                elif problem == 'level_price':
                    case['ltf_report'] = replace(report, levels=(replace(report.levels[0], price=90), *report.levels[1:]))
                elif problem == 'event_index':
                    case['ltf_report'] = replace(report, events=(replace(report.events[0], candle_index=25), report.events[1]))
                elif problem == 'duplicate_transition':
                    case['ltf_report'] = replace(report, structure_transition_diagnostics=report.structure_transition_diagnostics*2)
                elif problem == 'unfinished':
                    case['ltf_candles'][0] = replace(case['ltf_candles'][0], is_closed=False)
                else:
                    del case['ltf_candles'][10]
                with self.assertRaises(ValueError):
                    derive_automatic_levels(**case)

    def test_naive_reference_times_are_rejected(self):
        for key in ('as_of', 'entry_geometry_ready_time', 'ltf_bos_event_time'):
            with self.subTest(key=key):
                case = valid_case()
                if key == 'as_of':
                    case[key] = case[key].replace(tzinfo=None)
                else:
                    case['opportunity'] = replace(case['opportunity'], **{key:getattr(case['opportunity'], key).replace(tzinfo=None)})
                with self.assertRaises(ValueError):
                    derive_automatic_levels(**case)
