"""Evidence-based source inventory, alignment, rejection and trade traces."""
from __future__ import annotations

import argparse
import copy
import json
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_source_fidelity_state import REPO, ROOT, population
from run_medium_term_research import digest, read_rows, write_json

from crypto_bot.research.v2_common import metrics, write_csv

SOURCES = REPO / 'data/source_materials'
DOC = SOURCES / 'cryptology_2026_10_09'
PDF = SOURCES / 'primary_pdf_2026_10_09'
V2 = REPO / 'data/reports/strategy_v2_2026_10_10'

# File + literal original paragraph/page locator, never current code as source.
MATERIALS = {
    '03': ('ALL; HTF→LTF', 'P0028–34, P0052, P0065',
           'Top-down fractal context, liquidity cause/effect; do not enter with liquidity against setup.',
           'No single complete entry/exit algorithm; only meaningful opposing liquidity prohibition.',
           'Liquidity context, POI, BOS, EQH/EQL, STB/BTS; no H1/H4-owner requirement.'),
    '06': ('ALL (not fixed)', 'P0037–40, P0063–72, P0111–29',
           'Impulse→correction range, midpoint reaction, skip unclear range; deviation + external POI or reclaim/retest.',
           '80% near opposite inside boundary, optional 20% breakout; remainder exit unspecified.',
           'Range clarity, external POI magnet, reaction/acceptance/retest; no daily directional prerequisite.'),
    '11': ('W1/D1 global; H1/H4 local', 'P0076–92, P0113–15',
           'Fractal HH/HL, LL/LH; impulse and correction, momentum.',
           'No executable trade entry, stop, target or lifecycle contract.',
           'Macro/local context; no mandatory four-TF conjunction.'),
    '14': ('ALL, 1 second–1 month', 'P0113–20, P0143–59, P0169–98',
           'Liquidity target/context, structural EQH/EQL, postpone before adverse pool sweep.',
           'Liquidity as target; no fixed partial schedule or stop algorithm.',
           'Internal/external BSL/SSL; tilted equal pools allowed; session/day/week/month context.'),
    '16': ('ALL; SFP H1+ preferred', 'P0033–60, P0075–87, P0102–06',
           'IMB neighbour-wick gap, equilibrium/full fill; external SFP raid, reclaim close, next open, LTF BOS.',
           'No global three-target/BE rule; SFP pattern failure elaborated in SW12.',
           'SFP may occur on any TF; H1+ is preference, not prohibition of all lower-TF POI ideas.'),
    '18': ('HTF single candle / LTF multiple candles', 'P0005–12',
           'Last directional move raids old liquidity; untested Demand/Discount or Supply/Premium.',
           'No universal H1/H4 owner, SL enlargement, target count or exit allocation.',
           'Fresh/untested, liquidity raid, dealing-range P/D.'),
    '19': ('ALL', 'P0088–108, P0122–30, P0138–62',
           'BOS→new structure; OB raid/structural break/IMB; Breaker; range deviation→return/test; OTE 0.705–0.79.',
           'No unique resolver for alternative entry/stop/exit styles.',
           'Structure/CHOCH, POI, FVG/IMB, liquidity, OB+OTE confluence; not a fitted numerical tree.'),
    '20': ('M1/M5 scalp; H1 medium; H4+ long; all mixed', 'P0206–23, P0276–89, P0305–17',
           'Supplementary mixed posts including unrelated classical patterns and financial education.',
           'BE after 10–15% movement conflicts with primary do-not-move-stop; RR>=3 recommendation differs from primary examples.',
           'Volume/levels/engulfing; advertised flag probabilities 67.72%/67.12% lack trade data.'),
    'SW5': ('ALL', 'p2–7', 'Three-candle swings, protected body-close BOS; new structure then conservative CONF.',
            'Body BOS invalidates prior structure; no allocation or fixed TF ladder.', 'Structure/BOS/CONF, fractal analysis.'),
    'SW9': ('ALL; HTF OB M15–D1; conservative LTF M1–M15', 'p2–7, p9, p11–13, p16',
            'OB raid/engulf/BOS/HTF POI/trend; direct and conservative reaction→LTF BOS→new POI; Breaker; FTA.',
            'SL OB/engulf or conservative sweep wick; FTA full OR partial, including countertrend.',
            'First test usually; repeat LTF confirmation; IMB quality and P/D/OTE; no three distinct targets prerequisite.'),
    'SW11': ('No fixed timeframe', 'p2–5, p8', 'Plan entry/stop/target before entry; primary risk 0.25–2%.',
             'Do not move stop; technical/account-risk stop alternatives; no TP1→BE or TP40/30/30.',
             'Risk sizing, stop off liquidity, discipline; not a complete trading tree.'),
    'SW12': ('Multiple; example H3; ATR14 periods', 'p2, p8–13, p15',
             'Indicators are supporting confirmation; completed prior day/week/month liquidity, ATR.',
             'SFP ATR stop not moved; manual close on pattern-TF body beyond SFP extreme.',
             'Structure, RSI/divergence/volume, PDH/PDL, volatility; indicators not standalone signals.'),
    'SW22': ('No fixed timeframe', 'p2–6', 'STB/BTS aligned trend + full absorption + liquidity raid + BOS/CONF; boundary/0.5 mitigation.',
             'Flow delivers to global POI and ends after destination test; no global exit schedule.',
             'Order Flow uses real liquidity and rising/falling structural pairs, P/D.'),
}

# Necessary rule meanings and their separately inspected code implementations.
RULES = [
 ('D1 role','11','P0113–15','Daily/weekly global context; no mandatory D1 object for every H4 idea','source_medium_term._macro_context','INTERPRETATION_CHANGED'),
 ('H4 role','11,SW9','P0113–15; p5–6','Local structure/HTF POI can seed lower-TF trigger','source_medium_term._macro_context/_emit','PARTIAL_MATCH'),
 ('H1 role','11,16,20','P0113–15; P0102–06; P0213–18','Local structure, preferred SFP/medium analysis; not all entry ideas need an owner object','source_medium_term._emit','INTERPRETATION_CHANGED'),
 ('M15 role','SW9','p2,p4–6','Can be HTF OB or actual lower-TF POI trigger','source_medium_term._emit/evaluate','INTERPRETATION_CHANGED'),
 ('Formal H1/H4 owner','SW9,18','p2,p4; P0005–12','No universal named owner requirement; lower-TF formation may be valid with HTF context','source_medium_term._emit main_valid','EXTRA_RULE_NOT_IN_SOURCE'),
 ('Strict extra macro gate','SW5,SW9,SW22','p9; p13; p5–6','Source context/flow is path-specific; no universal strictly-higher H4/D1 structure object','source_medium_term._macro_context/_emit','EXTRA_RULE_NOT_IN_SOURCE'),
 ('Four-TF conjunction','11,03','P0113–15; P0028–30','Top-down analysis without explicit D1→H4→H1→M15 AND contract','source_medium_term._macro_context selects first valid macro','UNCLEAR'),
 ('Direction and flow','SW22,SW9','p5–6; p13','Active flow alignment; explicit countertrend FTA allowed','source_permitted._active_flow/_conservative; source_medium_term._macro_context','PARTIAL_MATCH'),
 ('Swing geometry','SW5','p2','Three consecutive candle high/low inequality; right candle confirmation','market_analysis.analyze_market','EXACT_MATCH'),
 ('BOS','SW5','p4–5','Close body across protected structural point','market_analysis; source_pdf_native.SourceSeries.advance','EXACT_MATCH'),
 ('Conservative CONF','SW5','p6–7','Wait for new structure and its update for selected conservative path','source_permitted._conservative OB_ULTRA_CONSERVATIVE_CONF','PARTIAL_MATCH'),
 ('CHOCH','19','P0092–106','Structural change; supplementary synonym/confluence','source_permitted.SourceSeries._qualify/structural_proof','PARTIAL_MATCH'),
 ('POI taxonomy','SW9','p10–11','Manipulation, OB, Breaker and other qualified tools; not gap alone','source_permitted.SourceSeries + source_pdf_native','PARTIAL_MATCH'),
 ('OB geometry','SW9','p2–3','Raid candle + engulf body/displacement; full engulfed candle wick zone','source_permitted.SourceSeries._order_blocks','EXACT_MATCH'),
 ('OB HTF POI','SW9','p2','OB requires higher-TF POI context','source_permitted._parents/_direct; source_medium_term._emit','PARTIAL_MATCH'),
 ('OB IMB importance','SW9,19','p2,p6–7; P0103–12','IMB important quality; most accurate rather than every OB strictly mandatory','source_permitted.SourceSeries._order_blocks; confluence imbalance','PARTIAL_MATCH'),
 ('OB first/repeated test','SW9','p3','Usually first test; repeated entry requires fresh LTF reaction','source_permitted._direct/_conservative; Zone.test_allowed','PARTIAL_MATCH'),
 ('Conservative lower TF','SW9','p4–6','HTF OB M15–D1 → lower M1–M15 reaction/BOS/new POI','source_medium_term_policy mappings 240/60','INTERPRETATION_CHANGED'),
 ('Smooth approach','SW9','p4','Smooth structural approach before reaction, not objectively quantified','source_permitted._conservative checks reaction/BOS/new POI only','MISSING'),
 ('Demand/Supply','18','P0005–12','Old liquidity raid, last move, untested, P/D','source_pdf_native._demand_supply; source_permitted.SourceSeries.advance','PARTIAL_MATCH'),
 ('Freshness','SW9,18','p3; P0011','Zone-specific first/repeat and untested D/S rules','Zone.fresh/test_allowed and native-touch visit state','PARTIAL_MATCH'),
 ('FVG/IMB geometry','16','P0051–60','Neighbour-wick gap and 0.5/full-fill inefficiency','source_pdf_native.SourceSeries.advance; poi_entry_policy','EXACT_MATCH'),
 ('FVG trigger permission','SW9,16','p11; P0085–87','New POI with independent context/BOS; FVG alone not permission','source_permitted._conservative with parent context','PARTIAL_MATCH'),
 ('OTE geometry','19','P0140–55','0.705–0.79 and confluence; not standalone entry','source_pdf_native.pd_location','EXACT_MATCH'),
 ('P/D applicability','18,SW9,SW22','P0012; p6; p4','D/S mandatory; OB important context; mitigation P/D','source_medium_term._emit gates D/S/STB/BTS, records others','PARTIAL_MATCH'),
 ('Dealing range','06,19','P0037–67; P0125–30','Impulse/correction boundaries and meaningful midpoint reaction','range_engine; source_pdf_native range_bounds','PARTIAL_MATCH'),
 ('Range tolerance 0.08','06','P0063–72','Qualitative meaningful midpoint, no source numeric tolerance','RangeDetectionParams midpoint_tolerance_fraction','EXTRA_RULE_NOT_IN_SOURCE'),
 ('Liquidity sweep','14,16','P0176–98; P0075–83','Actual structural/external pools and raid/reclaim','source_pdf_native advance; source_medium_term._observe_sfp_open','PARTIAL_MATCH'),
 ('EQH/EQL','14','P0143–59','Substructure swings; tilted EQH/EQL allowed, not arbitrary two candle equality','source_pdf_native.advance exact-price equality only','PARTIAL_MATCH'),
 ('Liquidity against setup','03,14','P0065; P0156–59','Do not enter before meaningful opposing liquidity sweep','source_medium_term._emit has NO blocker; source_pdf_native old blocker unused','MISSING'),
 ('SFP causality','16','P0075–87','External raid→reclaim close→next valid OPEN→LTF BOS','source_medium_term._observe_sfp_open; source_permitted._conservative','PARTIAL_MATCH'),
 ('SFP TF preference','16','P0102–06','Any TF, H1+ preferred','source_medium_term._observe_sfp_open only 60/240','INTERPRETATION_CHANGED'),
 ('SFP body invalidation','SW12','p13','Pattern-TF body beyond pattern extreme; ATR protective stop unchanged','source_medium_term._lifecycle MAIN_SFP_BODY_INVALIDATION','EXACT_MATCH'),
 ('Breaker','SW9,19','p7–9; P0113–16','Impulsive pierced OB with structural update; conservative sweep stop permitted','source_pdf_native.SourceSeries.advance; source_permitted._quote_stop','PARTIAL_MATCH'),
 ('STB/BTS','SW22','p2–4','Trend, raid, full absorption, BOS/CONF, boundary or 0.5','source_pdf_native._manipulations; source_permitted._direct','PARTIAL_MATCH'),
 ('Mitigation','SW22','p3–4','Return to origin/0.5 in appropriate P/D','source_permitted._quote_stop','PARTIAL_MATCH'),
 ('FTA','SW9','p11–13,p16','First opposing relevant POI on contextual higher TF','source_medium_term._targets only H4/D1; excludes H1 FTA','INTERPRETATION_CHANGED'),
 ('Three targets prerequisite','SW9','p11,p16','Source permits one FTA full/partial; no exact three-target requirement','source_medium_term._emit len(target_evidence)<3','EXTRA_RULE_NOT_IN_SOURCE'),
 ('TP40/30/30','SW9,06','p11–16; P0119–21','FTA full/partial; explicit Range80/20','VirtualPortfolio._manage','EXTRA_RULE_NOT_IN_SOURCE'),
 ('Range80/20','06','P0119–21','80% inside range near boundary, 20% optional breakout','MediumTermEngine always fractions .4/.3/.3','INTERPRETATION_CHANGED'),
 ('Breakeven','SW11,SW12,20','p8; p13; P0277','Primary do-not-move-stop vs supplementary BE after 10–15%, not TP1','VirtualPortfolio._manage/_breakeven','CONFLICT_BETWEEN_SOURCES'),
 ('Initial stop ownership','SW9','p3,p9','Local OB/engulf or sweep extreme stop alternatives','source_medium_term._emit expands stop to parent invalidator','INTERPRETATION_CHANGED'),
 ('Invalidation/lifecycle','SW5,SW12,SW22','p4–7; p13; p6','Structural/pattern death and destination test; no unified universal life','source_medium_term._lifecycle pending vs main','PARTIAL_MATCH'),
 ('Re-entry','SW9','p3','Repeat OB with LTF confirmation; no universal lifetime one-trade rule','source_medium_term._retained never releases physical ID','EXTRA_RULE_NOT_IN_SOURCE'),
 ('Cooldown','SW9','p3','No fixed cooldown in primary materials','No time cooldown in current MediumTermEngine','EXACT_MATCH'),
 ('No future holding gate','SW11','p4','Only facts present at decision; duration unknown','anti_scalp.check_anti_scalp has no history/outcomes','EXACT_MATCH'),
 ('AntiScalp ratio >=3','SW11','p4','Plan risk; no numeric gross/cost=3 source rule','anti_scalp.AntiScalpPolicy (prior explicit user policy)','EXTRA_RULE_NOT_IN_SOURCE'),
 ('AntiScalp four costs','SW11','p4','Commission/slippage recognised, no fixed fee/slip schedule','anti_scalp.check_anti_scalp (prior explicit user policy)','EXTRA_RULE_NOT_IN_SOURCE'),
 ('Risk 2%','SW11','p3–4','Primary professional default <=2%','SimulationPolicy risk_fraction=.02','EXACT_MATCH'),
 ('Portfolio 6%/daily4%/3x','SW11','p4–5','Sizing/isolated margin principles, not this fixed combined policy','SimulationPolicy caps (prior explicit user policy)','EXTRA_RULE_NOT_IN_SOURCE'),
 ('Indicators','SW12','p2,p15','Context/confirmation, not standalone triggers','No indicator-only current entry; ATR specific SFP stop','PARTIAL_MATCH'),
 ('Original executable tree','03,SW9,06','P0004–8; p3–6,p11–16; P0120–31','Education with alternative styles and further mentoring, not unique executable contract','15 machine paths plus project admission/exit interpretation','UNCLEAR'),
]


def sources():
    inventory = []
    manifest = json.loads((DOC / 'manifest.json').read_text())
    with zipfile.ZipFile(DOC / 'cryptology.zip') as archive:
        content = {__import__('hashlib').sha256(archive.read(i)).hexdigest(): archive.read(i)
                   for i in archive.infolist() if i.filename.endswith('.docx')}
    original = SOURCES / 'source_fidelity_2026_10_11/unique_docx'
    original.mkdir(parents=True, exist_ok=True)
    for m in manifest['materials']:
        key = str(m['id']).zfill(2)
        entry = next(x for x in manifest['entries'] if x['id'] == m['id'])
        filename = m['name'].split('/')[-1]
        path = original / filename
        if not path.exists():
            path.write_bytes(content[entry['sha256']])
        assert digest(path) == entry['sha256']
        tf, loc, meaning, exits, rules = MATERIALS[key]
        inventory.append({'source_id': key, 'file': filename, 'type': 'DOCX', 'duplicate': False,
            'original': str(path.relative_to(REPO)), 'archive_member': m['name'], 'sha256': entry['sha256'],
            'text': str((DOC / m['text']).relative_to(REPO)), 'location': loc, 'timeframes': tf,
            'entry_confirmation': meaning, 'invalidation_exit': exits, 'filters_structure_liquidity': rules,
            'limitations': 'Not a single deterministic strategy contract'})
    for m in json.loads((PDF / 'manifest.json').read_text()):
        tf, loc, meaning, exits, rules = MATERIALS[m['source']]
        inventory.append({'source_id': m['source'], 'file': m['original_name'], 'type': 'PDF', 'duplicate': False,
            'original': str((PDF / (m['source']+'.pdf')).relative_to(REPO)), 'sha256': m['sha256'],
            'text': str((PDF / (m['source']+'.txt')).relative_to(REPO)), 'location': loc,
            'timeframes': tf, 'entry_confirmation': meaning, 'invalidation_exit': exits,
            'filters_structure_liquidity': rules, 'pages': m['pages'], 'limitations': 'Alternative discretionary choices remain'})
    shortcuts = [x for x in manifest['entries'] if x['kind'] == 'SHORTCUT']
    write_json(ROOT / 'source_inventory.json', {'unique_content_documents': 13, 'materials': inventory,
        'archive_shortcuts': shortcuts, 'standalone_shortcuts': [str(p.relative_to(REPO)) for p in
            (SOURCES / 'correction_2026_10_09').glob('*.lnk')],
        'shortcut_semantics': 'References/duplicates of titles; do not contain target PDF or trading rules',
        'missing_module': 'SW7 Fibonacci: shortcut only; OTE source is DOC19, not a claim to read missing SW7',
        'cross_document_overlap_not_byte_duplicate': 'DOC19/20 overlap selected topics; eight DOCX + five PDF are thirteen distinct contents',
        'source_material_instructions_are_not_operational_authorization': True})
    write_csv(ROOT / 'source_inventory.csv', inventory)
    rows = []
    for rule, source, loc, meaning, code, status in RULES:
        rows.append({'source_rule': rule, 'source_file': source, 'source_location': loc,
                         'original_meaning': meaning, 'current_code': code, 'status': status})
    write_csv(ROOT / 'source_alignment_matrix.csv', rows)
    write_json(ROOT / 'source_alignment_matrix.json', rows)
    contract = [
      {'question':'Global entry branch/priority resolver','evidence':'SW9 p3–6 multiple OB styles; DOC06 aggressive/conservative; SW22 STB/BTS; no total ordering'},
      {'question':'Fixed M15/H1/H4/D1 ladder and countertrend allowance','evidence':'DOC11 P0113–15, SW9 p13, DOC16 P0102–06; qualitative/path-dependent, no universal conjunction'},
      {'question':'Smooth approach / meaningful adverse liquidity / tilted EQH tolerance','evidence':'SW9 p4, DOC03 P0065, DOC14 P0143–59; no unique numerical decision boundary'},
      {'question':'Exact FTA full/partial, later targets and remainder','evidence':'SW9 p11–16 permits full OR partial; DOC06 P0120–21 optional 20% lacks mandatory remainder target'},
      {'question':'Stop model / BE conflict resolver','evidence':'SW9 p3,p9 alternative stops; SW11 p8 no move; DOC20 P0277 BE 10–15%'},
      {'question':'Re-entry and lifecycle resolver','evidence':'SW9 p3 repeated reaction allowed; no universal one-trade-per-lifetime or exit for every typed POI'},
    ]
    write_csv(ROOT / 'original_contract_gaps.csv', contract)
    write_json(ROOT / 'exact_variants_identifiability.json', {'A':'NOT_IDENTIFIABLE_FROM_AVAILABLE_SOURCES',
        'B':'DEPENDENT_ON_UNIDENTIFIABLE_A', 'C':'FROZEN_BASELINE_VERIFIED_RESUME',
        'reason':'Selecting unspecified alternatives would create the new interpretation prohibited by this request',
        'required_contract':contract, 'threshold_search':False, 'production_changes':False,
        'trade_entry_allowed':False})
    print('SOURCE_AUDIT', len(inventory), 'unique documents', len(rows), 'rules', flush=True)


def tree():
    rules = json.loads((V2 / 'strategy_v2_final_rules.json').read_text())
    model = next(m for m in rules['models'] if m['model_id'] == 'TREE_D3_L200')
    features = read_rows(V2 / 'features_TEST.jsonl.gz')
    labels = {r['signal_id']: r for r in read_rows(V2 / 'labels_TEST.jsonl.gz')}
    predictions = {r['signal_id']: r for r in read_rows(V2 / 'frozen_TEST_predictions.jsonl.gz')
                   if r['candidate_name'] == 'BEST_META'}
    rows = []
    for r in features:
        node, path = 0, []
        while model['children_left'][node] != -1:
            i = model['feature'][node]
            name = model['features'][i]
            v = r.get(name)
            v = model['impute'][i] if v is None else v
            # sklearn exported tree uses float32 for prediction inputs.
            import struct
            v = struct.unpack('f', struct.pack('f', v))[0]
            left = v <= model['threshold'][node]
            path.append({'feature':name, 'value':v, 'threshold':model['threshold'][node],
                         'branch':'<=' if left else '>'})
            node = model['children_left'][node] if left else model['children_right'][node]
        admitted = model['probability_WIN'][node] >= .55
        assert admitted == predictions[r['signal_id']]['admitted']
        l = labels[r['signal_id']]
        rows.append({'signal_id': r['signal_id'], 'physical_opportunity_id': r['physical_opportunity_id'],
            'symbol': r['symbol'], 'direction': r['direction'], 'READY': r['READY'], 'HTF': r['HTF'], 'LTF': r['LTF'],
            'path_id': r['path_id'], 'leaf': node, 'probability': model['probability_WIN'][node],
            'admitted': admitted, 'conditions': path, 'status': l['status'], 'result': l.get('result'),
            'entry': l.get('entry'), 'original_SL': r['original_SL'], 'targets': r['targets'],
            'target_fractions': r['target_fractions'], 'FTA_kind': r['FTA_kind'],
            'gross': l.get('quote_gross_pnl'), 'fees': l.get('fees'), 'slippage': l.get('slippage'),
            'net': l.get('net_pnl'), 'result_R': l.get('result_R'),
            'entry_time': l.get('entry_interval_start'), 'exit_time': l.get('exit_time')})
    selected = [labels[r['signal_id']] for r in rows if r['admitted'] and r['status']=='CLOSED']
    assert len(selected)==297 and sum(r['result']=='WIN' for r in selected)==201
    write_csv(ROOT / 'old_tree_TEST_all_leaf_trace.csv', rows)
    write_csv(ROOT / 'old_tree_297_closed.csv', [r for r in rows if r['admitted'] and r['status']=='CLOSED'])
    rejected = [labels[r['signal_id']] for r in rows if not r['admitted'] and r['status']=='CLOSED']
    groups = {}
    for dim in ['symbol','direction','path_id','mapping','month']:
        buckets=defaultdict(list)
        for r in features:
            if predictions[r['signal_id']]['admitted'] and labels[r['signal_id']]['status']=='CLOSED':
                buckets[str(r[dim])].append(labels[r['signal_id']])
        groups[dim] = {k: metrics(v) for k,v in sorted(buckets.items())}
    write_json(ROOT / 'old_tree_reconstruction.json', {'model':model, 'threshold':.55,
        'baseline_TEST':metrics([r for r in labels.values() if r['status']=='CLOSED']),
        'admitted_TEST':metrics(selected), 'rejected_TEST':metrics(rejected),
        'admitted_OPEN':sum(r['admitted'] and r['status']=='OPEN' for r in rows),
        'groups':groups, 'selected_exit_allocations':dict(Counter(str(r['target_fractions']) for r in rows if r['admitted'])),
        'split':json.loads((V2 / 'split.json').read_text()),
        'freeze':json.loads((V2 / 'TEST_opening_receipt.json').read_text()),
        'leakage_receipt':json.loads((V2 / 'strategy_v2_final_leakage_audit.json').read_text()),
        'artifact_hashes':{str(p.relative_to(REPO)):digest(p) for p in [V2/'strategy_v2_final_rules.json',
            V2/'features_TEST.jsonl.gz',V2/'labels_TEST.jsonl.gz',V2/'frozen_TEST_predictions.jsonl.gz',
            V2/'strategy_v2_oos_results.csv']},
        'interpretation':'TRAIN-fitted single admitted leaf, selected VALIDATION; development TEST, not original methodology or untouched market OOS',
        'future_leakage_demonstrated':False, 'trade_entry_allowed':False})
    print('OLD_TREE_VERIFIED', len(features), 'predictions', len(selected), 'closed', flush=True)


def traces():
    signals, trades, rejected = population()
    snapshots = {}
    for s in ('BTCUSDT','ETHUSDT'):
        for r in read_rows(ROOT / 'state' / s / 'snapshots.jsonl.gz'):
            snapshots[(r['id'],r['stage'])] = r
    rejection_rows=[]
    for r in sorted(rejected, key=lambda r:(r['known_at'],r['signal_id'])):
        snap = snapshots[(r['physical_opportunity_id'],'NO_HTF_CONTEXT')]
        rejection_rows.append({'physical_opportunity_id': r['physical_opportunity_id'], 'symbol': r['symbol'],
            'known_at': r['known_at'], 'path_id': r['path_id'], 'logged_setup_tf': r['setup_tf'],
            'actual_setup_tf': 'NOT_LOGGED_IN_ORIGINAL_REJECTION', 'context_tf': r['context_tf'],
            'category': 'ENGINE_EXTRA_REJECTION', 'original_source_rule_violated': 'NONE_DEMONSTRATED_BY_THIS_REASON',
            'engine_cause': ('FORMAL_MAIN_SETUP_OR_SETUP_TF_GATE' if r['context_tf'] is not None
                          else 'FORMAL_HIGHER_MACRO_STRUCTURE_GATE_POSSIBLY_PLUS_MAIN_GATE'),
            'genuine_context_absence': (False if r['context_tf'] is not None else 'UNPROVEN: missing machine structure is not absence of all source context'),
            'causal_active_flow_passed_before_this_gate': True,
            'original_tree_decision': 'UNCLEAR_REMAINING_SOURCE_CONDITIONS_NOT_ALL_EVALUATED',
            'first_discovery_parent_matches': [{'tf':m['tf'],'kind':m['zone']['kind'],
                'zone_id':m['zone']['zone_id']} for m in snap['first_discovery_parent_matches']],
            'evidence_ref': f"state/{r['symbol']}/snapshots.jsonl.gz:{r['physical_opportunity_id']}:NO_HTF_CONTEXT",
            'source_locations': 'SW9 p2,p4; DOC18 P0005–12; DOC16 P0102–06', 'trade_entry_allowed': False})
    write_csv(ROOT / 'no_htf_3680_rule_trace.csv', rejection_rows)
    rows=[]; detailed=[]
    for t in sorted(trades,key=lambda t:(t['entry_interval_start'],t['signal_id'])):
        s=signals[t['signal_id']];e=s['evidence'];p=e['htf_poi'];q=e['ltf_poi']
        ready=snapshots[(s['signal_id'],'READY')];entry=snapshots[(s['signal_id'],'PRE_ENTRY')]
        violations=[]; uncertain=['Original full branch/exit resolver not supplied',
            'Meaningful liquidity/smooth approach require interpretation']
        is_ob=s['setup_type'].startswith('OB_')
        if is_ob and 'CONSERVATIVE' in s['setup_type'] and e['refinement_tf']>15:
            violations.append('SW9_P4_CONSERVATIVE_LTF_OUTSIDE_1_15M')
        # The restored contextual pool rule is retained as an interpreted
        # necessary rejection, never promoted to exact human methodology.
        adverse=entry['adverse_liquidity']
        if adverse:
            violations.append('DOC03_P0065_ADVERSE_LIQUIDITY_UNDER_EXISTING_CONTEXTUAL_POOL_INTERPRETATION')
        sfp=s['setup_type'].startswith('SFP')
        liquidity={'status':'FAIL' if adverse else 'PASS_UNDER_CONTEXTUAL_POOL_INTERPRETATION',
                   'source':'DOC03 P0065; DOC14 P0156–59','adverse_at_READY':ready['adverse_liquidity'],
                   'adverse_at_PRE_ENTRY':adverse,'raid':e['liquidity_sweep']}
        timeframe_trace={}
        for tf,label in [(1440,'D1'),(240,'H4'),(60,'H1'),(15,'M15')]:
            st=entry['timeframe_states'][str(tf)]
            roles=[]
            if e['macro_context_tf']==tf:roles.append('ENGINE_MACRO_CONTEXT')
            if e['actual_setup_tf']==tf:roles.append('ENGINE_MAIN_SETUP')
            if e['flow_owner_tf']==tf:roles.append('FLOW_OWNER')
            if e['refinement_tf']==tf:roles.append('SOURCE_REFINEMENT')
            timeframe_trace[label]={'status':'UNCLEAR_ORIGINAL_ROLE_NOT_UNIQUELY_SPECIFIED',
                'completed_state_check':'PASS' if st['completed_at'] else 'FAIL',
                'current_engine_applicable_role_check':'PASS_SAVED_READY_PROOF' if roles else 'NOT_APPLICABLE',
                'evidence':st,'roles':roles,'original_required_every_trade':False,
                'note':'State availability is not proof of an unspecified four-TF original AND gate'}
        decision='ORIGINAL_TREE_REJECT_UNDER_STATED_INTERPRETATION' if violations else 'UNCLEAR_ORIGINAL_TREE'
        source_checks={'liquidity':liquidity,
            'structure':{'status':'PASS','proof':e['source_confirmation']},
            'POI':{'status':'PARTIAL_MATCH','parent':p,'local':q},
            'OB':{'status':'PASS_FORMATION' if q['kind']=='ORDER_BLOCK' else 'NOT_APPLICABLE',
                  'imbalance':q['confluence'].get('imbalance'), 'repeat_visit':e['htf_visit_number']},
            'FVG_IMB':{'status':'RECORDED_CONFLUENCE_NOT_UNIVERSAL_GATE','local_kind':q['kind']},
            'OTE':{'status':'OPTIONAL_CONFLUENCE','present':e['premium_discount']['ote_confluence']},
            'BOS_CHOCH':{'status':'PASS_TYPED_SOURCE_CONFIRMATION','proof':e['source_confirmation']},
            'Premium_Discount':{'status':'PASS' if e['premium_discount']['allowed'] else 'NOT_APPLICABLE_OR_UNRESOLVED_PATH',
                                'evidence':e['premium_discount']},
            'FTA':{'status':'INTERPRETATION_CHANGED','baseline_targets':e['targets'],
                   'nearest_old_source_FTA_READY':ready['old_source_fta'],
                   'nearest_old_source_FTA_PRE_ENTRY':entry['old_source_fta']},
            'invalidation':{'status':'PARTIAL_MATCH','source_body_exit_events_preserved':True,
                            'actual_exit_reason':t['exit_reason']},
            'entry_trigger':{'status':'PASS_ACTUAL_RESTING_TOUCH','fill_model':t['fill_model'],
                             'source_refinement_tf':e['refinement_tf'],'pattern_SFP':sfp},
            'branch':{'status':'CURRENT_MACHINE_PATH_NOT_ORIGINAL_META_TREE','path':s['setup_type']}}
        r={'trade_id': t['trade_id'],'symbol': t['symbol'],'direction': t['direction'],
            'entry_timestamp': t['entry_interval_start'],'entry_known_at': t['entry_time'],
            'entry_Yekaterinburg': datetime.fromisoformat(t['entry_interval_start']).astimezone(ZoneInfo('Asia/Yekaterinburg')).isoformat(),
            'source_branch': s['setup_type'],'actual_setup_tf': e['actual_setup_tf'],
            'flow_owner_tf': e['flow_owner_tf'],'refinement_tf': e['refinement_tf'],'macro_context_tf': e['macro_context_tf'],
            'result': 'WIN' if t['net_pnl']>0 else 'LOSS','net_pnl': t['net_pnl'],
            'D1': timeframe_trace['D1'],'H4': timeframe_trace['H4'],'H1': timeframe_trace['H1'],'M15': timeframe_trace['M15'],
            'liquidity': liquidity,'structure': source_checks['structure'],'POI': source_checks['POI'],'OB': source_checks['OB'],
            'FVG_IMB': source_checks['FVG_IMB'],'OTE': source_checks['OTE'],'BOS_CHOCH': source_checks['BOS_CHOCH'],
            'Premium_Discount': source_checks['Premium_Discount'],'FTA': source_checks['FTA'],
            'invalidation': source_checks['invalidation'],'entry_trigger': source_checks['entry_trigger'],
            'trading_tree_branch': source_checks['branch'],'final_original_strategy_decision': decision,
            'violated_rules': violations,'uncertain_rules': uncertain,'trade_entry_allowed': False}
        # Store full evidence compressed, compact evidence paths in CSV.
        detailed.append(r)
        compact=copy.deepcopy(r)
        for tf in ['D1','H4','H1','M15']:
            st=compact[tf]['evidence']
            compact[tf]['evidence']={k:st[k] for k in ['completed_at','structure']}
        compact['POI']={'status':'PARTIAL_MATCH','parent_kind':p['kind'],'local_kind':q['kind'],
                        'parent_id':p['zone_id'],'local_id':q['zone_id']}
        compact['FTA']={k:v for k,v in source_checks['FTA'].items() if k=='status'}
        compact['FTA'].update(baseline_targets=list(s['targets']),old_FTA_READY=(
            ready['old_source_fta']['zone_id'] if ready['old_source_fta'] else None),old_FTA_PRE_ENTRY=(
            entry['old_source_fta']['zone_id'] if entry['old_source_fta'] else None))
        compact['evidence_ref']=f"trade_rule_evidence.jsonl.gz:{t['trade_id']}"
        rows.append(compact)
    from run_medium_term_research import write_rows
    write_rows(ROOT / 'trade_rule_evidence.jsonl.gz',detailed)
    write_csv(ROOT / 'rule_trace_880.csv',rows)
    write_csv(ROOT / 'rule_trace_542_losses.csv',[r for r in rows if r['result']=='LOSS'])
    stats={'trades':880,'losses':542,'NO_HTF_population':3680,
        'rejection_categories':dict(Counter(r['category'] for r in rejection_rows)),
        'NO_HTF_engine_causes':dict(Counter(r['engine_cause'] for r in rejection_rows)),
        'original_trade_decisions':dict(Counter(r['final_original_strategy_decision'] for r in rows)),
        'loss_original_trade_decisions':dict(Counter(r['final_original_strategy_decision'] for r in rows if r['result']=='LOSS')),
        'violations_counts':dict(Counter(v for r in rows for v in r['violated_rules'])),
        'loss_violations_counts':dict(Counter(v for r in rows if r['result']=='LOSS' for v in r['violated_rules'])),
        'TRUE_SOURCE_REJECTION_demonstrated_by_NO_HTF_reason':0,
        'TRUE_SOURCE_REJECTION_remaining_conditions':'UNDETERMINED; no full source admission replay from this reason alone',
        'source_valid_missed_trades_proven_by_rejection_reason_alone':0,
        'binary_original_allow_count':'UNIDENTIFIABLE; absence of demonstrated violation is not original-tree proof',
        'trade_entry_allowed':False}
    write_json(ROOT / 'rule_trace_summary.json',stats)
    print(json.dumps(stats,ensure_ascii=False),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['sources','tree','traces'])
    args=parser.parse_args()
    {'sources':sources,'tree':tree,'traces':traces}[args.stage]()


if __name__=='__main__':
    main()
