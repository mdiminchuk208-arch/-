"""Physical cases cannot be multiplied by parent patterns, mappings or ranges."""
import unittest
from dataclasses import replace
from datetime import timedelta

from crypto_bot.strategy.source_permitted import select_union
from crypto_bot.strategy.source_physical import canonical_physical_signals
from tests.test_source_permitted import fixture, policy


def ready(context='a', zone_id='local', path='OB_DIRECT_FIRST_TEST', offset=0, tf=5):
    e,p,q,now=fixture();q.zone_id=zone_id
    e._emit(path,60,5,p,q,now,context,1,now,q.raid)
    r=e.signals[0]
    return replace(r,signal_id=context+zone_id+path,known_at=r.known_at+timedelta(minutes=offset),
                   evidence={**r.evidence,'entry_zone_tf':tf})


class PhysicalSourceTests(unittest.TestCase):
    def test_two_parent_patterns_same_local_zone_are_one_physical_entry(self):
        rows,claims=canonical_physical_signals([ready('a'),ready('b')],policy())
        self.assertEqual(rows[0].evidence['physical_opportunity_id'],rows[1].evidence['physical_opportunity_id'])
        self.assertEqual(claims[1]['reason'],'SAME_NATIVE_LOCAL_ZONE_FIRST_TEST')
        self.assertEqual(len(select_union(rows,policy())[0]),1)

    def test_range_and_direct_on_same_external_first_test_share_identity(self):
        a=ready('direct');b=ready('range',path='OB_DIRECT_INSIDE',offset=20)
        b=replace(b,evidence={**b.evidence,'path_id':'RANGE_AGGRESSIVE_EXTERNAL_POI'})
        rows,_=canonical_physical_signals([b,a],policy())
        self.assertEqual(len(select_union(rows,policy())[0]),1)
        self.assertEqual(rows[0].signal_id,a.signal_id)

    def test_native_formation_aliases_share_identity_without_future_fill(self):
        rows,claims=canonical_physical_signals([ready('a','five'),ready('b','fifteen',tf=15)],policy())
        self.assertEqual(rows[0].evidence['physical_opportunity_id'],rows[1].evidence['physical_opportunity_id'])
        self.assertEqual(claims[1]['reason'],'KNOWN_NATIVE_FORMATION_TIME_PRICE_ALIAS')

    def test_future_ready_cannot_rewrite_prefix_ids_or_choose_later_quote(self):
        a=ready('a');b=ready('b',path='OB_DIRECT_INSIDE',offset=20)
        prefix,_=canonical_physical_signals([a],policy())
        full,_=canonical_physical_signals([b,a],policy())
        self.assertEqual(prefix[0],full[0])
        selected,_=select_union(full,policy());self.assertEqual(selected[0].signal_id,a.signal_id)

    def test_identity_pass_never_changes_quotes_stops_times_or_raw_input(self):
        original=ready();rows,_=canonical_physical_signals([original],policy())
        r=rows[0]
        for field in ('signal_id','setup_id','known_at','entry','stop','targets','fractions'):
            self.assertEqual(getattr(r,field),getattr(original,field))
        self.assertNotIn('physical_context_id',original.evidence)

    def test_family_cohorts_reuse_global_ids(self):
        a,b=ready('a'),ready('b',path='OB_DIRECT_INSIDE')
        rows,_=canonical_physical_signals([a,b],policy())
        family=[r for r in rows if r.evidence['path_id']=='OB_DIRECT_INSIDE']
        self.assertEqual(family[0].evidence['physical_opportunity_id'],rows[0].evidence['physical_opportunity_id'])

    def test_three_candle_fvg_geometry_aliases_across_native_tfs(self):
        a,b=ready('a','five'),ready('b','fifteen',offset=10,tf=15)
        def gap(r,formed):
            q={**r.evidence['ltf_poi'],'kind':'FVG','raid':None,'formed_at':formed}
            return replace(r,evidence={**r.evidence,'ltf_poi':q})
        a=gap(a,a.known_at);b=gap(b,b.known_at)
        rows,_=canonical_physical_signals([a,b],policy())
        self.assertEqual(rows[0].evidence['physical_opportunity_id'],rows[1].evidence['physical_opportunity_id'])

    def test_symbol_namespaces_do_not_share_native_formation_alias(self):
        a,b=ready('a'),replace(ready('b'),symbol='ETHUSDT')
        rows,_=canonical_physical_signals([a,b],policy())
        self.assertNotEqual(rows[0].evidence['physical_opportunity_id'],rows[1].evidence['physical_opportunity_id'])
