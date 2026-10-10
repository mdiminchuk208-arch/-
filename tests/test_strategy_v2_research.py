"""Meaningful causal/identity/cost checks using a real saved source snapshot."""
from __future__ import annotations

import copy
import json
import unittest

import numpy as np

from crypto_bot.research.v2_common import (
    BASE,
    numerical_gate,
    read_jsonl,
    seconds,
    wilson,
)
from crypto_bot.research.v2_features import FeatureContext, features, load_native
from crypto_bot.research.v2_rules import LOGISTIC_FEATURES, candidate_mask, design


class StrategyV2CausalityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy=json.loads((BASE/'run_lock.json').read_text())['policy']
        cls.signal=next(read_jsonl(BASE/'segments/SOLUSDT/signals.jsonl.gz'))
        cls.native=load_native('SOLUSDT')
        cls.family={r['path_id']:r['setup_family'] for r in cls.policy['paths']}
        cls.variant={'signal_id':cls.signal['signal_id'],'known_at':cls.signal['known_at'],
            'path_id':cls.signal['evidence']['path_id'],
            'physical_opportunity_id':cls.signal['evidence']['physical_opportunity_id']}
        cls.ctx=FeatureContext(cls.native,[cls.variant],[],[],cls.family)

    def test_real_costs_are_known_target_estimates(self):
        r=features(self.signal,self.ctx,self.policy)
        s=1 if self.signal['direction']=='LONG' else -1
        net=sum(f*(s*(t*(1-s*self.policy['slippage_fraction'])-r['entry_after_slippage'])
                    -self.policy['fee_rate']*(t*(1-s*self.policy['slippage_fraction'])+r['entry_after_slippage']))
                for f,t in zip(self.signal['fractions'],self.signal['targets']))*r['expected_quantity']
        self.assertAlmostEqual(net/r['planned_risk'],r['net_target_R'],places=10)
        self.assertGreater(r['expected_total_friction'],0)

    def test_injected_outcomes_and_fill_extrema_cannot_change_features(self):
        changed=copy.deepcopy(self.signal)
        changed.update({'result':'WIN','net_pnl':1e20,'fees':0,'slippage':0,'holding_seconds':0,
                        'entry_bar_ohlc':{'high':1e20,'low':0},'exit_time':'2099-01-01'})
        self.assertEqual(features(changed,self.ctx,self.policy),features(self.signal,self.ctx,self.policy))

    def test_later_family_is_not_confluence(self):
        later={**self.variant,'signal_id':'TEST_LATER_WITNESS','path_id':'BREAKER_CONSERVATIVE_STOP',
               'known_at':'2099-01-01T00:00:00+00:00'}
        ctx=FeatureContext(self.native,[self.variant,later],[],[],self.family)
        self.assertEqual(features(self.signal,ctx,self.policy),features(self.signal,self.ctx,self.policy))

    def test_independent_families_are_not_quote_variants(self):
        variants=[{**self.variant,'signal_id':str(i),'path_id':path} for i,path in enumerate([
            'OB_DIRECT_FIRST_TEST','OB_DIRECT_INSIDE','OB_CONSERVATIVE_BOS_POI','BREAKER_CONSERVATIVE_STOP'])]
        ctx=FeatureContext(self.native,variants,[],[],self.family)
        r=features(self.signal,ctx,self.policy)
        self.assertEqual(r['physical_family_count'],2)
        self.assertEqual(r['physical_families'],['BREAKER','OB'])

    def test_future_macro_invalidation_not_applied_early(self):
        tf=self.signal['htf'];cutoff=seconds(self.signal['known_at'])
        flow={'tf':tf,'known_at':self.signal['known_at'],'invalidated_at':'2099-01-01T00:00:00+00:00',
              'direction':'LONG','structure':None,'classification':'TEST','destination_poi':None}
        ctx=FeatureContext(self.native,[self.variant],[flow],[],self.family)
        self.assertIsNotNone(ctx.macro(tf,cutoff)[0])
        flow['invalidated_at']=self.signal['known_at']
        ctx=FeatureContext(self.native,[self.variant],[flow],[],self.family)
        self.assertIsNone(ctx.macro(tf,cutoff)[0])

    def test_outcome_and_identity_design_inputs_rejected(self):
        r=features(self.signal,self.ctx,self.policy)
        for field in ['result','fees','month','symbol','signal_id','label_eligible']:
            with self.assertRaises(AssertionError):design([r],[field])
        self.assertEqual(design([r],LOGISTIC_FEATURES).shape,(1,7))

    def test_missing_quality_cannot_pass_rule(self):
        r=features(self.signal,self.ctx,self.policy);r['macro_flow_aligned']=None
        mask=candidate_mask([r],{'kind':'RULE','scope':'ALL','conditions':[['macro_flow_aligned','>=',1]]})
        np.testing.assert_array_equal(mask,[False])

    def test_wilson_and_minimum_sample_gate(self):
        lo,hi=wilson(140,200)
        self.assertAlmostEqual(lo,.633209,places=5)
        self.assertAlmostEqual(hi,.7592525531762859,places=12)
        m={'CLOSED':199,'WR':.99,'PF':100,'Expectancy':10,'AvgR':1,'NetPnL':1000}
        self.assertFalse(numerical_gate(m))


if __name__=='__main__':unittest.main()
