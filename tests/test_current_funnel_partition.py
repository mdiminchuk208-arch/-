"""A rejection funnel cannot combine successful predicates from different OBs."""
from dataclasses import replace
import sys
import unittest

sys.path.insert(0,'scripts')
from audit_current_history import first_rejection
from ready_audit_support import CANDIDATE_GATES
from test_virtual_portfolio import signal


class CurrentFunnelTests(unittest.TestCase):
    def candidate(self, **changes):
        gates={name:True for name,_ in CANDIDATE_GATES};gates.update(changes)
        return dict(gates=gates,first_failure=next((reason for gate,reason in CANDIDATE_GATES if not gates[gate]),None),
                    preexisting_supporting_poi_evidence=[],later_supporting_poi_evidence=[],
                    fresh_supporting_pois=[],a_open='2026-01-01T00:00:00+00:00')

    def test_disjoint_candidate_success_never_combines_into_deeper_proof(self):
        no_poi=self.candidate(SUPPORTING_POI=False)
        bad_ob=self.candidate(IMBALANCE=False)
        bad_ob['preexisting_supporting_poi_evidence']=[{}];bad_ob['fresh_supporting_pois']=[{}]
        diag=dict(candidates=[no_poi,bad_ob],independent_targets_available=True)
        waiting=replace(signal(),status='WAITING_FOR_AUTO_LEVELS')
        self.assertEqual(first_rejection(waiting,diag)[0],6)

    def test_invalidated_observation_cannot_reuse_earlier_cached_validity(self):
        invalid=replace(signal(),status='INVALIDATED')
        self.assertEqual(first_rejection(invalid,dict(candidates=[self.candidate()] ))[0],3)


if __name__=='__main__':unittest.main()
