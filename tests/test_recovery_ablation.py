import csv
from dataclasses import replace
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from test_market_analysis import bullish_structure_sequence, c
from test_mtf_sfp import event, report, BASE
from test_range_engine import c as rc, base_report, bullish_range_events, ev
from crypto_bot.analysis_report import write_event_csv
from crypto_bot.global_report import write_global_opportunities_csv
from crypto_bot.mtf_report import write_mtf_candidates_csv, write_mtf_opportunities_csv
from crypto_bot.range_report import write_ranges_csv
from crypto_bot.strategy.global_opportunity import cluster_cross_pair_opportunities
from crypto_bot.strategy.market_analysis import analyze_market, StructureAnalysisMode as Mode, MarketEventKind as K, TrendState
from crypto_bot.strategy.mtf_sfp import (
    link_sfp_formations_to_ltf_bos,
    MtfSfpError,
    MtfOpportunity,
    MtfOpportunityStatus,
    MtfSfpReport,
)
from crypto_bot.common.models import Direction
from crypto_bot.strategy.range_engine import RangeStatus
from range_test_support import analyze_ranges, augment_market_report_with_range_sfps
from crypto_bot.strategy.recovery_ablation import comparison, range_key, bos_records, market_fingerprint, mtf_records, sfp_records


def recovery_fixture(mirror=False):
    candles=bullish_structure_sequence()+[
        c(10,8.8,12,8,11.5),c(11,11.5,13.8,10.5,13.4),c(12,13.4,14,11,11.5),
        c(13,11.5,12,10,10.5),c(14,10.5,13,10.2,12.5),c(15,12.5,14.5,12,14),
        c(16,14,14.2,12.8,13.2),c(17,13.2,13.5,8.5,9),
        c(18,9,10,8,9.5),c(19,9.5,11,9,10.5),c(20,10.5,10.8,9.2,10),
        c(21,10,10.5,7,7.5),c(22,7.5,9,7.2,8),
    ]
    if mirror:
        candles=[replace(x,open=30-x.open,high=30-x.low,low=30-x.high,close=30-x.close) for x in candles]
    return candles


class RecoveryAblationTests(unittest.TestCase):
    def test_modes_isolate_same_direction_in_both_directions(self):
        for mirror in (False,True):
            with self.subTest(mirror=mirror):
                cs=recovery_fixture(mirror)[:17]
                source=analyze_market(cs,analysis_mode=Mode.SOURCE_CONSERVATIVE)
                tech=analyze_market(cs,analysis_mode=Mode.TECHNICAL_RECOVERY)
                self.assertEqual(source.final_trend,TrendState.BROKEN)
                self.assertEqual(tech.final_trend,TrendState.BEARISH if mirror else TrendState.BULLISH)
                self.assertEqual(tech.structure_transition_diagnostics[0].resolution_mode,'SAME_DIRECTION_POST_BOS_RECOVERY')
                self.assertIn('SAME_DIRECTION_RECOVERY_DISABLED_BY_SOURCE_CONSERVATIVE',source.structure_transition_diagnostics[0].rejection_reasons)

    def test_recovery_is_not_source_conf_and_original_bos_is_untainted(self):
        for mirror in (False,True):
            r=analyze_market(recovery_fixture(mirror),analysis_mode=Mode.TECHNICAL_RECOVERY)
            b=[e for e in r.events if e.kind in (K.BULLISH_STRUCTURE_BROKEN_BOS,K.BEARISH_STRUCTURE_BROKEN_BOS)]
            self.assertEqual(b[0].recovery_transition_ids,())
            self.assertEqual(b[1].recovery_transition_ids,(1,))
            recovery_conf=K.BEARISH_CONF_CONFIRMED if mirror else K.BULLISH_CONF_CONFIRMED
            self.assertFalse([e for e in r.events if e.kind==recovery_conf and e.candle_index<=17])

    def test_ancestry_survives_expected_opposite_transition(self):
        r=analyze_market(recovery_fixture(),analysis_mode=Mode.TECHNICAL_RECOVERY)
        after=[e for e in r.events if e.kind==K.BEARISH_STRUCTURE_CONFIRMED and e.candle_index>=20]
        self.assertTrue(after)
        self.assertTrue(all(e.recovery_transition_ids==(1,) for e in after))

    def test_prefix_events_and_ancestry_are_immutable_for_both_modes(self):
        for mode in Mode:
            for mirror in (False,True):
                cs=recovery_fixture(mirror)
                full=analyze_market(cs,analysis_mode=mode)
                for size in range(3,len(cs)+1):
                    prefix=analyze_market(cs[:size],analysis_mode=mode)
                    self.assertEqual(prefix.events,tuple(e for e in full.events if e.candle_index<size))

    def test_structural_liquidity_and_sfp_are_mode_independent(self):
        cs=recovery_fixture()
        reports=[analyze_market(cs,analysis_mode=m) for m in Mode]
        keys={K.SWING_HIGH_CONFIRMED,K.SWING_LOW_CONFIRMED,K.BEARISH_SFP_FORMATION_CONFIRMED,K.BULLISH_SFP_FORMATION_CONFIRMED,K.HIGH_LIQUIDITY_TAKEN,K.LOW_LIQUIDITY_TAKEN}
        self.assertEqual([e for e in reports[0].events if e.kind in keys],[e for e in reports[1].events if e.kind in keys])

    def test_invalid_mode_fails_and_production_default_is_source_conservative(self):
        with self.assertRaises(ValueError):
            analyze_market([],analysis_mode='unknown')
        self.assertEqual(analyze_market([]).analysis_mode,Mode.SOURCE_CONSERVATIVE)

    def test_v0411_positional_mtf_constructors_keep_legacy_values(self):
        opportunity = MtfOpportunity(
            1, MtfOpportunityStatus.ENTRY_SEARCH_CANDIDATE, Direction.LONG,
            K.BEARISH_STRUCTURE_BROKEN_BOS, BASE, 3, 4, 5.0,
            (1,), (2,), (3,), BASE, BASE, 7, True, False, 'legacy note',
        )
        self.assertTrue(opportunity.entry_search_allowed)
        self.assertFalse(opportunity.trade_entry_allowed)
        self.assertEqual(opportunity.note, 'legacy note')
        self.assertEqual(opportunity.htf_recovery_transition_ids, ())
        legacy_report = MtfSfpReport(
            60, 5, None, (), 's', 'm', 'e', 'entry', 'link', None, None, None,
            (), 'inv', 'opp', 'PAIR_LOCAL_EXACT_LTF_BOS', None, ('OLD_GATE',),
        )
        self.assertEqual(legacy_report.entry_engine_blocking_reasons, ('OLD_GATE',))
        self.assertEqual(legacy_report.analysis_mode, Mode.SOURCE_CONSERVATIVE)

    def test_expected_fast_path_is_identical_without_recovery(self):
        cs=bullish_structure_sequence()+[c(10,8.8,9.3,7.5,8),c(11,8,9,7.8,8.5),c(12,8.5,10.5,8,10),c(13,10,10,8.2,8.8)]
        a,b=[analyze_market(cs,analysis_mode=m) for m in Mode]
        self.assertEqual(a.events,b.events)
        self.assertEqual(a.structure_transition_diagnostics[0].resolution_mode,'EXPECTED_OPPOSITE_FAST_PATH')

    def test_expected_local_path_and_later_conf_survive_in_both_modes(self):
        cs=recovery_fixture()[:15]+[c(15,12.5,13.5,12,13),c(16,13,13.2,10.8,11),
            c(17,11,12,9.5,10),c(18,10,12.5,9.8,12),c(19,12,12.2,8.5,9)]
        for mirror in (False,True):
            fixture=cs if not mirror else [replace(x,open=30-x.open,high=30-x.low,low=30-x.high,close=30-x.close) for x in cs]
            a,b=[analyze_market(fixture,analysis_mode=m) for m in Mode]
            self.assertEqual(a.events,b.events)
            self.assertEqual(a.structure_transition_diagnostics[0].resolution_mode,'EXPECTED_OPPOSITE_LOCAL_STRUCTURE')
            conf=K.BULLISH_CONF_CONFIRMED if mirror else K.BEARISH_CONF_CONFIRMED
            self.assertEqual([e.candle_index for e in a.events if e.kind==conf],[19])

    def test_technical_bos_confirms_analytically_but_never_unlocks_entry(self):
        sfp=event(K.BEARISH_SFP_FORMATION_CONFIRMED,60)
        bos=replace(event(K.BULLISH_STRUCTURE_BROKEN_BOS,75,episode=None),recovery_transition_ids=(7,))
        r=link_sfp_formations_to_ltf_bos(report(sfp),report(bos),htf_minutes=60,ltf_minutes=5)
        self.assertEqual(r.confirmed_count,1)
        self.assertEqual(r.opportunity_count,1)
        self.assertFalse(r.candidates[0].entry_search_allowed)
        self.assertFalse(r.opportunities[0].entry_search_allowed)
        self.assertFalse(r.candidates[0].trade_entry_allowed)
        self.assertEqual(r.opportunities[0].ltf_recovery_transition_ids,(7,))

    def test_htf_recovery_and_mixed_contexts_cannot_be_laundered(self):
        sfp=event(K.BEARISH_SFP_FORMATION_CONFIRMED,60)
        dependent=replace(event(K.BEARISH_SFP_FORMATION_CONFIRMED,65,level_id=2,episode=2),recovery_transition_ids=(2,))
        bos=event(K.BULLISH_STRUCTURE_BROKEN_BOS,75,episode=None)
        r=link_sfp_formations_to_ltf_bos(report(sfp,dependent),report(bos),htf_minutes=60,ltf_minutes=5)
        self.assertTrue(r.candidates[0].entry_search_allowed)
        self.assertFalse(r.candidates[1].entry_search_allowed)
        self.assertEqual(r.opportunity_count,1)
        self.assertFalse(r.opportunities[0].entry_search_allowed)
        g=cluster_cross_pair_opportunities('BTCUSDT',[('60_to_5',r)])
        self.assertEqual(g[0].recovery_context_refs,('60_to_5:HTF:2',))
        self.assertFalse(g[0].entry_search_allowed)
        self.assertFalse(g[0].trade_entry_allowed)

    def test_mixed_analysis_modes_are_rejected(self):
        with self.assertRaises(MtfSfpError):
            link_sfp_formations_to_ltf_bos(replace(report(),analysis_mode=Mode.SOURCE_CONSERVATIVE),replace(report(),analysis_mode=Mode.TECHNICAL_RECOVERY),htf_minutes=60,ltf_minutes=5)

    def test_recovery_seed_flows_through_range_sfp(self):
        cs=[rc(i) for i in range(10)]
        cs[7]=rc(7,106,112,104,109);cs[8]=rc(8,108,109,103,106)
        events=bullish_range_events();events[0]=replace(events[0],recovery_transition_ids=(4,))
        merged,r=augment_market_report_with_range_sfps(cs,base_report(cs,events))
        self.assertEqual(r.ranges[0].recovery_transition_ids,(4,))
        self.assertEqual(r.events[0].recovery_transition_ids,(4,))
        self.assertEqual(r.events[0].liquidity_origin,'RANGE_BOUNDARY')
        for size in range(5,len(cs)+1):
            early=base_report(cs[:size],[e for e in events if e.candle_index<size])
            _,prefix=augment_market_report_with_range_sfps(cs[:size],early)
            self.assertEqual(prefix.events,tuple(e for e in r.events if e.candle_index<size))

    def test_technical_internal_bos_can_remove_validation(self):
        cs=[rc(i) for i in range(9)]
        source=analyze_ranges(cs,base_report(cs,bullish_range_events()))
        internal=replace(ev(K.BULLISH_STRUCTURE_BROKEN_BOS,5,104,20,103),recovery_transition_ids=(9,))
        tech=analyze_ranges(cs,base_report(cs,bullish_range_events()+[internal]))
        self.assertTrue(source.ranges[0].ever_validated)
        self.assertEqual(tech.ranges[0].status,RangeStatus.REJECTED_INTERNAL_STRUCTURE)
        self.assertEqual(tech.ranges[0].invalidating_recovery_transition_ids,(9,))

    def test_postvalidation_internal_bos_has_separate_ancestry(self):
        cs=[rc(i) for i in range(10)]
        internal=replace(ev(K.BULLISH_STRUCTURE_BROKEN_BOS,7,104,20,103),recovery_transition_ids=(9,))
        r=analyze_ranges(cs,base_report(cs,bullish_range_events()+[internal]))
        self.assertEqual(r.ranges[0].status,RangeStatus.INVALIDATED_INTERNAL_STRUCTURE)
        self.assertEqual(r.ranges[0].recovery_transition_ids,())
        self.assertEqual(r.ranges[0].invalidating_recovery_transition_ids,(9,))

    def test_comparison_separates_ancestry_presence_and_behavior(self):
        source={'a':{'status':'ok'},'b':{'status':'ok'},'c':{'status':'ok','entry_search_allowed':True,'analysis_mode':'SOURCE_CONSERVATIVE'}}
        tech={'a':{'status':'ok','recovery_transition_ids':[1]},'b':{'status':'invalid'},
              'c':{'status':'ok','entry_search_allowed':False,'analysis_mode':'TECHNICAL_RECOVERY'},'d':{'status':'ok'}}
        r=comparison(source,tech)
        self.assertEqual(r['common_count'],3)
        self.assertEqual(r['common_changed_count'],1)
        self.assertEqual(r['source_only_count'],0)
        self.assertEqual(r['technical_only_count'],1)
        self.assertEqual(r['technical_with_recovery_ancestry_count'],1)
        self.assertEqual(r['entry_search_changed_count'],1)
        row=next(item for item in r['rows'] if item['key']=='c')
        self.assertEqual(row['category'],'COMMON_ENTRY_SEARCH_CHANGED')
        self.assertEqual(comparison({}, {})['common_count'],0)

    def test_range_identity_is_independent_of_ordinal_ids(self):
        cs=[rc(i) for i in range(9)]
        r=analyze_ranges(cs,base_report(cs,bullish_range_events())).ranges[0]
        self.assertEqual(range_key(r),range_key(replace(r,range_id=99)))

    def test_report_serialization_keeps_ancestry_and_gates(self):
        sfp=replace(event(K.BEARISH_SFP_FORMATION_CONFIRMED,60),recovery_transition_ids=(2,))
        bos=replace(event(K.BULLISH_STRUCTURE_BROKEN_BOS,75,episode=None),recovery_transition_ids=(7,))
        mtf=link_sfp_formations_to_ltf_bos(report(sfp),report(bos),htf_minutes=60,ltf_minutes=5)
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)
            write_event_csv(report(bos),p/'events.csv')
            write_mtf_candidates_csv(mtf,p/'c.csv')
            write_mtf_opportunities_csv(mtf,p/'o.csv')
            write_global_opportunities_csv(cluster_cross_pair_opportunities('BTCUSDT',[('pair',mtf)]),p/'g.csv')
            with (p/'c.csv').open() as f:
                row=next(csv.DictReader(f))
            self.assertEqual(row['htf_recovery_transition_ids'],'2')
            self.assertEqual(row['ltf_recovery_transition_ids'],'7')
            self.assertEqual(row['entry_search_allowed'],'False')
            self.assertIn('pair:HTF:2',(p/'g.csv').read_text())
        structural = sfp_records(report(sfp), range_only=False)
        self.assertEqual(len(structural), 1)
        self.assertEqual(next(iter(structural.values()))['recovery_transition_ids'], [2])

    def test_registry_recovery_rules_remain_normalizations(self):
        data=json.loads((Path(__file__).resolve().parents[1]/'config/source_rules.json').read_text(encoding='utf-8'))
        entries=[r for r in data['rules'] if 'PHASE1412' in r['rule_id']]
        self.assertEqual(len(entries),3)
        self.assertTrue(all(r['kind']=='TECHNICAL_NORMALIZATION' for r in entries))


if __name__=='__main__':
    unittest.main()
