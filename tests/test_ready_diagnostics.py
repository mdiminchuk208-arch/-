from dataclasses import replace
from pathlib import Path
import sys
import json
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'scripts'))
from ready_audit_support import GateInspector
from test_auto_levels import valid_case
from crypto_bot.strategy.auto_levels import AutoLevelPolicy, derive_automatic_levels
from crypto_bot.common.models import Direction
from audit_ready_root_cause import aggregate,STAGES,canonical
from ready_audit_support import CANDIDATE_GATES


class ReadyDiagnosticsTests(unittest.TestCase):
    def inspect(self,case,inspector=None):
        return (inspector or GateInspector()).inspect(
            case['htf_candles'],case['ltf_candles'],case['htf_report'],case['ltf_report'],
            case['opportunity'],as_of=case['as_of'],policy=case['policy'])

    def assertEquivalent(self,case):
        actual=derive_automatic_levels(**case)
        diag=self.inspect(case)
        self.assertEqual(diag['predicted_ready'],actual.status=='READY')
        self.assertEqual(diag['predicted_reasons'],actual.blocked_reasons)
        return diag

    def test_all_rules_are_jointly_satisfiable_in_both_directions(self):
        for direction in (Direction.LONG,Direction.SHORT):
            with self.subTest(direction=direction):
                diag=self.assertEquivalent(valid_case(direction))
                self.assertTrue(diag['predicted_ready'])
                self.assertEqual(diag['qualified_ob_count'],1)
                self.assertEqual(len(diag['selected_targets']),3)
                self.assertTrue(all(diag['candidates'][0]['gates'].values()))

    def test_each_numeric_experiment_matches_unchanged_detector(self):
        for policy in (AutoLevelPolicy(.95),AutoLevelPolicy(min_engulf_body_ratio=5)):
            case=valid_case();case['policy']=policy
            diag=self.assertEquivalent(case)
            self.assertFalse(diag['predicted_ready'])
            self.assertEqual(diag['candidates'][0]['first_failure'],'AGGRESSIVE_IMPULSE_THRESHOLD_NOT_MET')

    def test_missing_raw_sweep_is_not_mislabelled_as_no_pattern(self):
        case=valid_case()
        case['ltf_report']=replace(case['ltf_report'],events=case['ltf_report'].events[:1])
        diag=self.assertEquivalent(case)
        self.assertEqual(len(diag['candidates']),1)
        self.assertFalse(diag['candidates'][0]['gates']['RAW_SWEEP'])

    def test_no_preexisting_supporting_poi_matches_detector(self):
        case=valid_case()
        case['htf_candles'][10]=replace(case['htf_candles'][10],open=94,low=94)
        diag=self.assertEquivalent(case)
        self.assertEqual(diag['candidates'][0]['first_failure'],'FRESH_PREEXISTING_HTF_POI_NOT_FOUND')

    def test_retest_is_a_separate_failure_and_never_reactivates(self):
        case=valid_case()
        case['ltf_candles'][-1]=replace(case['ltf_candles'][-1],low=98)
        diag=self.assertEquivalent(case)
        self.assertFalse(diag['candidates'][0]['gates']['OB_FRESH'])
        self.assertIsNotNone(diag['candidates'][0]['first_retest'])

    def test_later_predicates_do_not_erase_first_failure(self):
        case=valid_case();case['policy']=AutoLevelPolicy(.95)
        diag=self.assertEquivalent(case)
        candidate=diag['candidates'][0]
        self.assertFalse(candidate['gates']['AGGRESSION'])
        self.assertTrue(candidate['gates']['SUPPORTING_POI'])
        self.assertTrue(diag['independent_targets_available'])
        self.assertEqual(diag['qualified_ob_count'],0)

    def test_cache_and_repeat_have_identical_predicates(self):
        case=valid_case(); inspector=GateInspector()
        self.assertEqual(self.inspect(case,inspector),self.inspect(case,inspector))
        self.assertEqual(self.inspect(case,inspector),self.inspect(case))

    def test_future_or_unclosed_input_is_rejected(self):
        for field in ('close_time','is_closed'):
            case=valid_case()
            candle=case['ltf_candles'][-1]
            case['ltf_candles'][-1]=replace(candle,**{field:False if field=='is_closed' else candle.close_time.replace(year=2027)})
            with self.assertRaises(ValueError):self.inspect(case)

    def test_first_blocker_ignores_unreached_ob_before_geometry(self):
        # A waiting geometry state has no OB evaluation. It must not turn an
        # eventual numeric-aggression failure into NO_POST_BOS_OB_PATTERN.
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'audit'; baseline=Path(temp)/'baseline'
            (root/'TEST').mkdir(parents=True);baseline.mkdir()
            rows=[];signals=[]
            times=['2026-01-01T01:00:00+00:00','2026-01-01T01:05:00+00:00']
            for i,time in enumerate(times):
                gates={g:'TRUE' for g in STAGES}
                gates.update({'SFP_ALIVE':'TRUE','READY':'FALSE'})
                for g in STAGES[7:]:gates[g]='UNKNOWN'
                gates['RANGE REVIEW']='NOT_APPLICABLE_STRUCTURAL_SFP';gates['SCORE']='NOT_A_READY_GATE'
                if i==0:
                    for g in STAGES[3:7]:gates[g]='UNKNOWN'
                else:gates['OB']='FALSE'
                state='WAITING_FOR_ENTRY_GEOMETRY' if i==0 else 'WAITING_FOR_AUTO_LEVELS'
                signal=dict(signal_id='one',symbol='TEST',direction='LONG',event_time=time,bos_time=times[0],
                            status=state,entry_zone=dict(low=95,high=96),level_blocking_reasons=[])
                diag=None if i==0 else dict(evaluated_at=time,selected_targets=[],predicted_reasons=['AGGRESSIVE_IMPULSE_THRESHOLD_NOT_MET'],
                      candidates=[dict(gates={g:g!='AGGRESSION' for g,_ in CANDIDATE_GATES},
                          first_failure='AGGRESSIVE_IMPULSE_THRESHOLD_NOT_MET',fresh_supporting_pois=[],supporting_poi_candidates=0,ob_zone=dict(low=94,high=96))])
                rows.append(dict(signal_id='one',symbol='TEST',direction='LONG',timestamp=time,scope='EXECUTION',
                       previous_state='ABSENT' if i==0 else 'WAITING_FOR_ENTRY_GEOMETRY',next_state=state,
                       score=85,gates=gates,signal=signal,automatic_diagnostic=diag,reasons=[],invalidation_reasons=[],opportunity={},sfp_contexts=[]))
                signals.append(signal)
            content=''.join(canonical(s)+'\n' for s in signals)
            (root/'TEST/observed_signals.jsonl').write_text(content)
            (baseline/'signals.jsonl').write_text(content)
            (root/'TEST/evaluations.jsonl').write_text(''.join(canonical(r)+'\n' for r in rows))
            (root/'TEST/sensitivity.json').write_text('[]')
            aggregate(root,baseline,{'symbols':['TEST']})
            first=json.loads((root/'first_blockers.json').read_text())[0]
            self.assertEqual(first['first_gate'],'OB')
            self.assertEqual(first['reason'],'AGGRESSIVE_IMPULSE_THRESHOLD_NOT_MET')
            self.assertEqual(first['timestamp'],times[1])


if __name__=='__main__':unittest.main()
