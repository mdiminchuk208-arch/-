"""Offline partial source-evidence checker, not a market strategy or order router.

No price history fetch, financial outcomes, portfolio, or production engine imports.
Timestamps are integer UTC epoch seconds. Qualitative facts are explicit causal
annotations; they do not constitute proof of an automatic OHLC detector.
"""
from __future__ import annotations

import copy
import json
import math
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SPEC = REPO / 'docs/original_strategy_spec_v1'


def load_contract(root=SPEC):
    return json.loads((root / 'ORIGINAL_STRATEGY_DECISION_TREE_v1.json').read_text())


def available(record, now, event, *, completed=True):
    if not isinstance(record, dict) or not record.get('evidence'):
        return False
    known = record.get('known_at')
    if type(known) is not int or known > now:
        return False
    if completed:
        closed = record.get('completed_at')
        if type(closed) is not int or closed > now or closed > known:
            return False
        if event == 'OPEN' and closed == now:
            # The caller must explicitly attest previous-bar CLOSE ordering.
            return record.get('phase') == 'PREVIOUS_CLOSE'
    for dependency in record.get('dependencies',[]):
        if not available(dependency,now,event):
            return False
    return True


def conservative_tf(setup_tf, trigger_tf):
    if (type(setup_tf) not in (int,float) or type(trigger_tf) not in (int,float)
            or not math.isfinite(setup_tf) or not math.isfinite(trigger_tf)):
        return None
    if setup_tf < 15 or trigger_tf < 1 or trigger_tf > 15 or trigger_tf >= setup_tf:
        return False
    if setup_tf > 1440:
        return None  # SW9 "and so on" is not an absolute D1 ceiling.
    return True


def annotation(case, name):
    record = case.get('facts', {}).get(name)
    if not available(record, case['decision_at'], case['event']):
        return None
    return record['value'] if type(record.get('value')) is bool else None


def source_sfp_geometry(case, *, next_open=False):
    geometry = case.get('sfp', {})
    raid = geometry.get('raid')
    if not available(raid, case['decision_at'], case['event']):
        return None
    if not available(geometry.get('old_level'), case['decision_at'], case['event']):
        return None
    level = geometry['old_level']['price']
    if case['direction'] == 'LONG':
        formed = raid['low'] < level and raid['close'] > level
    else:
        formed = raid['high'] > level and raid['close'] < level
    if not next_open:
        return formed
    following = geometry.get('next_open')
    if not available(following, case['decision_at'], case['event'], completed=False):
        return None
    if any(field in following for field in ('high','low','close','completed_at')):
        raise ValueError('next OPEN schema cannot contain future OHLC/completion')
    if following['known_at'] <= raid['completed_at']:
        raise ValueError('next OPEN must follow raid CLOSE')
    return formed and (following['open'] > level if case['direction'] == 'LONG' else following['open'] < level)


def source_fvg_geometry(case):
    bars = case.get('fvg', [])
    if len(bars) != 3 or not all(available(b,case['decision_at'],case['event']) for b in bars):
        return None
    if not bars[0]['completed_at'] < bars[1]['completed_at'] < bars[2]['completed_at']:
        raise ValueError('FVG requires three ordered completed candles')
    return bars[0]['high'] < bars[2]['low'] if case['direction']=='LONG' else bars[0]['low'] > bars[2]['high']


def source_ote_geometry(case):
    impulse = case.get('impulse')
    if not available(impulse,case['decision_at'],case['event']):
        return None
    width = impulse['high'] - impulse['low']
    if width <= 0:
        return False
    retrace = ((impulse['high']-case['entry'])/width if case['direction']=='LONG'
               else (case['entry']-impulse['low'])/width)
    return 0.705 <= retrace <= 0.79


def adverse_state(case):
    """Use role annotations, not the old union-pool/behind-price classifier."""
    pools = case.get('liquidity')
    if not isinstance(pools,list) or not pools:
        return None
    unknown = False
    for pool in pools:
        if not available(pool,case['decision_at'],case['event']):
            unknown = True
            continue
        role = pool.get('role')
        if role not in ('ADVERSE','TARGET','FTA','IRRELEVANT'):
            unknown = True
            continue
        if role == 'ADVERSE':
            sweep = pool.get('sweep')
            if sweep is None:
                return False
            if not available(sweep,case['decision_at'],case['event']):
                return False  # Pool remains adverse until sweep is causally known.
    return None if unknown else True


def predicate(case, name):
    if name == 'conservative_tf':
        return conservative_tf(case.get('setup_tf'),case.get('trigger_tf'))
    if name == 'sfp_tf':
        value = case.get('setup_tf')
        return (type(value) in (int,float) and math.isfinite(value) and value>0)
    if name in ('sfp_geometry','sfp_next_open'):
        return source_sfp_geometry(case,next_open=name=='sfp_next_open')
    if name == 'fvg_geometry':
        return source_fvg_geometry(case)
    if name == 'ote_geometry':
        return source_ote_geometry(case)
    if name == 'no_adverse_proven':
        return adverse_state(case)
    return annotation(case,name)


def evaluate(case, tree=None):
    tree = copy.deepcopy(tree or load_contract())
    now = case.get('decision_at')
    if type(now) is not int or case.get('event') not in ('OPEN','CLOSE'):
        raise ValueError('Explicit integer decision timestamp and OPEN/CLOSE required')
    if case.get('direction') not in ('LONG','SHORT') or case.get('mode') not in ('BACKTEST','SHADOW'):
        raise ValueError('Only LONG/SHORT offline BACKTEST/SHADOW evidence is accepted')
    branch = case['branch']
    if branch not in tree['branch_start_nodes']:
        raise ValueError('Unsupported branch')
    nodes = {node['node_id']:node for node in tree['nodes']}
    registry = json.loads((SPEC/'original_strategy_rule_registry_v1.json').read_text())
    categories = {r['rule_id']:r['category'] for r in registry['rules']}
    trace = []
    node_id = tree['branch_start_nodes'][branch]
    visited = set()
    while node_id in nodes:
        if node_id in visited:
            raise ValueError('Decision tree cycle')
        visited.add(node_id)
        node = nodes[node_id]
        if categories.get(node['rule_id']) != 'SOURCE_RULE':
            raise ValueError('Extra/project/normalization rule injected into source decision')
        value = predicate(case,node['predicate'])
        status = 'UNKNOWN' if value is None else ('PASS' if value else 'FAIL')
        trace.append({'node_id':node_id,'rule_id':node['rule_id'],'predicate':node['predicate'],
                      'status':status,'decision_at':now,'source_citation':[
                          {'source_id':r['source_id'],'page_or_paragraph':r['page_or_paragraph']}
                          for r in node['source_citation']]})
        node_id = node[status]
    result = {'branch':branch,'source_trace':trace,'terminal':node_id,
              'source_conditions_pass':node_id=='SOURCE_CONDITIONS_PASS',
              'SOURCE_STRATEGY_DECISION':{'SOURCE_REJECT':'REJECT','SOURCE_UNRESOLVED':'UNRESOLVED',
                                         'SOURCE_CONDITIONS_PASS':'CONTRACT_UNRESOLVED'}[node_id],
              'verdict':tree['verdict'],'trade_entry_allowed':False,
              'material_questions':tree['global_material_questions']}
    if result['source_conditions_pass'] and tree['branch_roles'][branch]!='TRADE_SETUP':
        result['SOURCE_STRATEGY_DECISION']='COMPONENT_ONLY'
    if tree.get('ALLOW_enabled') or tree['verdict'] != 'NOT_IDENTIFIABLE':
        raise ValueError('v1 checker is frozen to a NOT_IDENTIFIABLE contract')
    return result


def project_admission(source_result):
    """Boundary probe only; does not implement retained production policies."""
    if source_result.get('SOURCE_STRATEGY_DECISION') != 'ALLOW':
        return {'admission':'SOURCE_NOT_ALLOWED','trade_entry_allowed':False}
    # This stage deliberately cannot produce an executable admission or order.
    return {'admission':'PROJECT_POLICY_EVALUATION_REQUIRED','trade_entry_allowed':False}


def protective_stop(initial_stop, *, requested_move=None):
    if requested_move is not None and requested_move != initial_stop:
        raise ValueError('PRIMARY_FIXED_STOP forbids BE/TP1 stop move')
    return initial_stop


def sfp_body_invalid(case, candle):
    """Supplied pattern-TF candle only, no future body or lower-TF substitution."""
    if (candle.get('tf') != case['setup_tf'] or not available(candle,case['decision_at'],case['event'])
            or not available(case['sfp']['raid'],case['decision_at'],case['event'])):
        return None
    extreme = case['sfp']['raid']['low'] if case['direction']=='LONG' else case['sfp']['raid']['high']
    return candle['close'] < extreme if case['direction']=='LONG' else candle['close'] > extreme


def exit_profile(branch, variant=None):
    """Return source-supported component choices, never compute monetary outcomes."""
    if branch.startswith('RANGE'):
        if variant not in (None,'RANGE_80_20'):
            raise ValueError('Range cannot inherit non-Range/canonical schedule')
        return {'type':'RANGE_80_20','first_fraction':0.8,'first_target':'inside opposite boundary',
                'optional_remainder':0.2,'remainder_rule':None,'status':'INCOMPLETE_REMAINDER_AND_NEAR_OFFSET'}
    if variant is None:
        return {'type':'UNRESOLVED_FULL_OR_PARTIAL_FTA','status':'UNRESOLVED'}
    if variant == 'FULL_FTA':
        return {'type':variant,'first_fraction':1.0,'first_target':'nearest contextual FTA',
                'status':'TARGET_OWNER_AND_QUOTE_UNRESOLVED'}
    if variant == 'PARTIAL_FTA':
        return {'type':variant,'first_fraction':None,'first_target':'nearest contextual FTA',
                'remainder_rule':None,'status':'FRACTION_AND_REMAINDER_UNRESOLVED'}
    raise ValueError('Unsupported source exit component')


def synthetic_case(branch, direction, tree=None):
    """Named facts for a logic example, with explicit synthetic provenance."""
    tree = tree or load_contract()
    sign = 1 if direction=='LONG' else -1
    facts = {node['predicate']:{'value':True,'known_at':80,'completed_at':80,
                               'evidence':'SYNTHETIC named source-condition annotation, not detected OHLC'}
             for node in tree['nodes'] if node['branch_id']==branch}
    raid = {'low':96 if sign==1 else 98,'high':102 if sign==1 else 104,
            'close':101 if sign==1 else 99,'known_at':90,'completed_at':90,'evidence':'synthetic raid candle'}
    sfp = {'raid':raid,'old_level':{'price':100,'known_at':50,'completed_at':50,'evidence':'old confirmed structural level'},
           'next_open':{'open':101 if sign==1 else 99,'known_at':91,'evidence':'next native open only'}}
    bars = [{'high':h,'low':l,'known_at':t,'completed_at':t,'evidence':'synthetic FVG candle'}
            for h,l,t in ([(101,98,50),(104,99,60),(106,103,70)] if sign==1
                          else [(102,99,50),(101,96,60),(97,94,70)])]
    return {'case_id':branch+'_'+direction,'branch':branch,'direction':direction,'mode':'BACKTEST',
            'decision_at':100,'event':'CLOSE','setup_tf':60,'trigger_tf':5,'entry':95 if sign==1 else 105,
            'facts':facts,'sfp':sfp,'fvg':bars,
            'impulse':{'high':110,'low':90,'known_at':75,'completed_at':75,'evidence':'selected causal impulse'},
            'liquidity':[{'role':'TARGET','known_at':80,'completed_at':80,
                          'evidence':'synthetic contextual role annotation; not old pool union'}],
            'formal_H1_H4_owner':False,'project_edge_cost_ratio':1,
            'interpretation_limit':'All qualitative facts supplied; no source normalization gap is closed by fixture'}
