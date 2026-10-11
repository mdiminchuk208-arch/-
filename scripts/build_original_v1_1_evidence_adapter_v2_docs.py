"""Register evidence-adapter contracts before objective run. Never alters strategy."""
from __future__ import annotations

import json

from original_v1_1_evidence_adapter_v2 import QUALITATIVE
from original_v1_1_financial_data import END, ROOT, START, checksum, save, write_csv

D=ROOT/'docs/original_v1_1_evidence_adapter_v2'
S=ROOT/'docs/original_strategy_spec_v1_1'
A='DETERMINISTIC_FROM_OHLC'
B='DETERMINISTIC_FROM_EXCHANGE_METADATA'
C='DERIVABLE_FROM_EXPLICIT_SOURCE_GEOMETRY'
Q='QUALITATIVE_REQUIRES_ANNOTATION'
E='NOT_RECONSTRUCTABLE'
ALL='SFP|OB_CONSERVATIVE|BREAKER|STB_BTS|RANGE_CONSERVATIVE|RANGE_RETURN_CHOCH'


def text(name,body):
    (D/name).write_text(body.strip()+'\n')


def build():
    if (D/'freeze_manifest.json').exists():
        raise ValueError('Frozen adapter namespace cannot be rebuilt')
    rows=[]
    def field(name,branches,category,rules,producer,inputs,wait,ambiguity='',notes=''):
        rows.append({'evidence_field':name,'required_by_branch':branches,'category':category,
            'source_rule_ids':rules,'input_data':inputs,'causal_known_at':'max completion/known_at of exact cited dependencies <= decision_at',
            'exact_producer':producer,'automatic_possible':category in (A,B,C),
            'ambiguity':ambiguity,'WAIT reason if missing':wait,'notes':notes})
    for name in ('branch','symbol','direction','setup_tf','trigger_tf','decision_at','event','mode','trade_entry_allowed'):
        field(name,ALL,C,'','build_case','explicit candidate/event contract','WAIT_EXPLICIT_EVENT',
              notes='Candidate direction/branch is a hypothesis, not inferred SOURCE truth; mode offline; U/N are not SOURCE_RULE')
    for name in ('tick_size','price_precision','qty_step','quantity_precision','minimum_qty','contract_type','linear_perpetual','base_asset','quote_asset'):
        field('instrument_metadata.'+name,ALL,B,'','metadata_at','authoritative effective-date snapshot/proof','WAIT_UNRESOLVED_INSTRUMENT_METADATA',
              'Current sample/price decimal precision does not prove historical filters')
    field('tick_size',ALL,B,'','metadata_at','same verified instrument record','WAIT_UNRESOLVED_INSTRUMENT_METADATA')
    tree=json.loads((S/'ORIGINAL_STRATEGY_EXECUTABLE_DECISION_TREE_v1.json').read_text())
    for node in tree['source_nodes']:
        p=node['predicate']; branch=node['branch_id']
        field(('geometry.' if p in ('sfp_geometry','sfp_next_open','sfp_tf','conservative_tf') else 'facts.')+p,
            branch,A if p.startswith('sfp_') and p not in ('sfp_tf',) else C if p in ('sfp_tf','conservative_tf') else Q,
            node['rule_id'],'sfp_valid/predicate' if p.startswith('sfp_') or p=='conservative_tf' else 'annotation_fact',
            'completed candles + explicit level/TF' if p.startswith('sfp_') else 'audited source selection + blinded annotation',
            'WAIT_UNRESOLVED_SOURCE_GEOMETRY','Source selection/qualitative relations remain unresolved' if p in QUALITATIVE else '')
    for name,branch in [('ltf_bos_source_entry','SFP'),('range_reclaim_retest','RANGE_CONSERVATIVE|RANGE_RETURN_CHOCH'),('breaker_confirmation','BREAKER')]:
        field('facts.'+name,branch,Q,'|'.join(QUALITATIVE[name]),'annotation_fact','exact geometry + contextual validation','WAIT_UNRESOLVED_SOURCE_GEOMETRY')
    field('facts.sl_off_liquidity.checked_price',ALL,C,'S_SL_OFF_POOL','stop_price + exact-price annotation','verified tick + source anchor + classified pool inventory','WAIT_UNRESOLVED_STOP_LIQUIDITY')
    for name in ('low','high','id','formation_known_at','parent_poi_id'):
        field('entry_poi.'+name,ALL,C,'S_POI|S_OB_CONS_TRIGGER|S_SFP_REFINE|S_STB_ENTRY|S_RANGE_CONSERVATIVE',
              'source_entry_poi','unique source-selected POI + branch chronology','WAIT_UNRESOLVED_ENTRY_GEOMETRY','Nonunique source choices WAIT; no nearest POI selection for entry')
    for name in ('kind','price','unique'):
        field('stop_anchor.'+name,ALL,C,'S_OB_DIRECT_STOP|S_BREAKER_STOPS|S_SFP_STOP|S_RANGE_DEVIATION|S_STB_FORMATION',
              'source_stop / build_case SFP extreme','source defining zone / explicit raid impulse / completed pattern','WAIT_UNRESOLVED_STOP_GEOMETRY')
    for name in ('id','low','high'):
        field('source_defining_zone.'+name,ALL.replace('SFP|',''),C,'S_POI','source_stop / build_case','selected whole source zone','WAIT_UNRESOLVED_STOP_GEOMETRY')
    for name in ('open','high','low','close','tf','completed_at','known_at','evidence'):
        field('sfp.raid.'+name,'SFP',A,'S_SFP_FORMATION','Bar.observed','completed native pattern candle','WAIT_UNRESOLVED_SOURCE_GEOMETRY')
    field('sfp.old_level.price','SFP',C,'S_SFP_FORMATION|S_POOL_SCOPE','GeometryIndex + externality annotation','known strict swing / selected source range boundary','WAIT_UNRESOLVED_SOURCE_GEOMETRY',
          'Strict swing price objective; external/protected role is qualitative')
    for name in ('open','known_at','evidence','actual_open_time'):
        field('sfp.next_open.'+name,'SFP',A,'S_SFP_FORMATION','GeometryIndex.next_open','next completed archived native candle OPEN only','WAIT_UNRESOLVED_SOURCE_GEOMETRY',
              notes='Conservative availability at next native CLOSE, not fictitious +1 second; no next H/L/C supplied to predicate')
    for name in ('open','high','low','close','tf','completed_at','known_at','evidence'):
        field('atr_bars[0..14].'+name,'SFP',A,'S_SFP_STOP','GeometryIndex.atr_bars / frozen atr14','15 contiguous native bars through pattern CLOSE','WAIT_UNRESOLVED_STOP_GEOMETRY',notes='Estimator is N11_ATR_SMA14 technical normalization, not source estimator')
    field('reaction','SFP|OB_CONSERVATIVE',Q,'S_OB_CONS_TRIGGER|S_SFP_REFINE','audited annotation + typed selection','pre-existing source POI reaction','WAIT_CAUSAL_REACTION_BOS')
    field('bos','SFP|OB_CONSERVATIVE',C,'S_BOS','structure_break','explicit protected endpoint + completed M15 close','WAIT_CAUSAL_REACTION_BOS','Protected endpoint cannot be chosen from every minor swing')
    field('bos.tf','SFP|OB_CONSERVATIVE',C,'S_OB_CONS_TF','source_entry_poi','frozen M15 refinement','WAIT_NO_AVAILABLE_LOWER_TF')
    for name in ('id','low','high','unique','source_exit_poi'):
        field('range_exit.'+name,'RANGE_CONSERVATIVE|RANGE_RETURN_CHOCH',C,'S_RANGE_EXIT|S_RANGE_FORMATION',
              'explicit selected range + target_plan','source endpoints + optional explicit nearer opposing POI','WAIT_UNRESOLVED_CONTEXTUAL_FTA')
    for name in ('id','tf','low','high','contextual','opposing','source_validated','source_type','consumed'):
        field('contextual_pois[].'+name,ALL,C if name not in ('contextual','source_validated') else Q,'S_FTA|S_POI',
              'contextual_fta','all source-validated known M15/H1/H4/D1 POIs','WAIT_UNRESOLVED_CONTEXTUAL_FTA','Contextual relationship requires annotation; consumed state explicit')
    field('contextual_poi_inventory.complete_for_known_prefix',ALL,Q,'S_FTA','explicit inventory completeness attestation','entire known prefix + rejected/unresolved candidate census','WAIT_UNRESOLVED_CONTEXTUAL_FTA','Empty inventory does not prove completeness')
    field('liquidity_inventory.complete_for_known_prefix',ALL,Q,'S_POOL_SCOPE|S_LIQUIDITY_CONTEXT','explicit inventory completeness attestation','all contextual pools at known prefix','WAIT_UNRESOLVED_LIQUIDITY_CONTEXT')
    for name in ('id','tf','price','scope','role','entry_relation','structure_relation','setup_direction','source_rule_ids','source_validated','sweep'):
        field('liquidity[].'+name,ALL,Q if name in ('scope','role','structure_relation','source_validated') else C,
            'S_POOL_SCOPE|S_ADVERSE_BLOCK|S_ADVERSE_WAIT','GeometryIndex / pool_scope / liquidity_role','exact pools/sweeps + selected endpoints + contextual annotation','WAIT_UNRESOLVED_LIQUIDITY_CONTEXT','UNKNOWN never becomes NEUTRAL')
    field('post_sweep_revalidation.value',ALL,Q,'S_ADVERSE_WAIT','complete source revalidation attestation','all updated source components after causal sweep','WAIT_POST_SWEEP_REVALIDATION')
    for name in ('context','formation','confirmation','poi'):
        field('identity_evidence.'+name+'.id',ALL,C,'S_POI|S_STRUCTURE','identity_records / object_record','immutable source objects','WAIT_UNRESOLVED_SETUP_IDENTITY',notes='N11_IDENTITY; branch absent from physical hash')
    field('idea_poi_id',ALL,C,'S_POI','identity_records','original physical POI not refinement','WAIT_UNRESOLVED_SETUP_IDENTITY')
    field('zone_first_test.value',ALL,C,'S_OB_FIRST_TEST','ConsumedRegistry.test + exact eligible-test evidence','causal chronological eligible test','WAIT_FIRST_TEST_ONLY','Unordered same-bar touch/formation ambiguity UNKNOWN')
    # Common record leaf fields explicitly apply to EVERY record path above.
    paths=['instrument_metadata','entry_poi','stop_anchor','source_defining_zone','sfp.old_level','reaction','bos',
           'range_exit','range_exit.source_exit_poi','contextual_pois[]','contextual_poi_inventory','liquidity[]',
           'liquidity[].sweep','liquidity_inventory','post_sweep_revalidation','zone_first_test']
    paths += ['identity_evidence.'+n for n in ('context','formation','confirmation','poi')]
    paths += ['facts.'+p for p in sorted({n['predicate'] for n in tree['source_nodes']}|{'ltf_bos_source_entry','breaker_confirmation','range_reclaim_retest'}) if not p.startswith('sfp_') and p!='conservative_tf']
    for path in paths:
        for leaf in ('known_at','completed_at','evidence','source_validated','dependencies[]'):
            field(path+'.'+leaf,ALL,Q if leaf=='source_validated' else C,'',
                  'attest_existing_object / annotation_fact' if leaf=='source_validated' else 'typed producer envelope / frozen available validation',
                  'explicit source-validated object + cited causal dependency chain','WAIT_UNRESOLVED_SOURCE_GEOMETRY',
                  notes='Envelope leaves; dependencies optional when none exist. source_validated is required only where frozen consumer checks it (metadata/identity/inventory validation uses its own contract). C is automatic only GIVEN exact explicit source-selected inputs, not automatic endpoint/qualitative selection.')
    for name in ('used_zones','used_setups','used_formations','complete_same_event_batch','physical_idea_id','setup_id'):
        field('selector_state.'+name,ALL,C,'','frozen select_ideas / ConsumedRegistry / identity_records','explicit same-event validated plans and chronological source-use events','WAIT_FIRST_TEST_ONLY',notes='N11_BATCH/N11_IDENTITY/U6, not SOURCE_RULE')
    field('ordered_intrabar_quotes',ALL,E,'','no producer from these OHLC archives','would require public historical ordered quotes','WAIT_INTRABAR_UNKNOWN',notes='Execution-only field, outside this evidence-only run; no synthesized fill path')
    write_csv(D/'EVIDENCE_CAPABILITY_MATRIX.csv',rows,list(rows[0]))
    official=D/'provenance/bybit_official_instrument.mdx'
    save(D/'HISTORICAL_INSTRUMENT_METADATA_v1.json',{'version':'1','scope':[START,END+1],'intervals':'[effective_from,effective_to)',
        'verdict':'UNKNOWN_ALL_REQUESTED_PERIODS','records':[
            {'symbol':s,'effective_from':START,'effective_to':END+1,'values':None,
             'verification_status':'UNKNOWN','provenance':{'repository_search':'No historical effective-dated instrument snapshot found',
                 'archive_search':'Immutable project copies/client/models and synthetic fixtures do not prove filters',
                 'authoritative_attempt':'GET https://api.bybit.com/v5/market/instruments-info?category=linear&symbol=BTCUSDT',
                 'attempt_result':'CONNECT tunnel 403; exit 56; no API response received',
                 'official_document':str(official.relative_to(ROOT)),'source_sha256':checksum(official),
                 'official_document_commit':'59e3d457dea6b419a14987c19a3aabf4ffb38238','fetched_date_UTC':'2026-10-11',
                 'known_semantics':'Fetch date is not historical effective/known time',
                 'rejected_as_period_proof':'Current docs response example lacks applicable effective interval; launchTime is not filter effective_from',
                 'effective_period_proof':False,'historical_known_at':None,'authoritative':True}}
            for s in ('BTCUSDT','ETHUSDT')],
        'not_inferred_from':['today filters','OHLC decimal digits','GCD of candle prices','synthetic tick .1','launch timestamp'],
        'next_required_evidence':'Dated authoritative snapshots + change log/unchanged-period proof covering each admitted interval; public access alone is insufficient',
        'trade_entry_allowed':False})
    save(D/'ANNOTATION_SCHEMA_v1.json',{'version':'1','concepts':QUALITATIVE,'states':['PASS','FAIL','UNKNOWN'],
        'required':['concept','state','object_ids','source_rule_ids','decision_at','known_at','completed_at','allowed_window','annotator_id','rationale','provenance'],
        'provenance_required':['blinded_pack_sha256'],'disagreement':'UNKNOWN, no majority-vote machine truth',
        'qualitative_state_is_not_geometry_validation':'PASS does not manufacture an entry POI, protected endpoint, source OB or complete inventory',
        'validator':'scripts/original_v1_1_evidence_adapter_v2.py:validate_annotation','trade_entry_allowed':False})
    text('EVIDENCE_ADAPTER_V2_SPEC.md', '''# SOURCE_FAITHFUL_HISTORICAL_EVIDENCE_ADAPTER_v2

Evidence-only addition to a49c40e. Frozen strategy 43e9d7a, U1–U6, N11, baseline C and Source Fidelity Audit are immutable. BACKTEST/SHADOW only; trade_entry_allowed=false. No accounting, order lifecycle, fills, profitability, parameter search or production integration.

The first 176365 RAW → zero complete/ALLOW/FILLED/CLOSED result demonstrates an absent evidence layer, not absence of edge. Old instrument_metadata=None/facts={} are replaced with real causal primitives and typed annotation interfaces; this does not invent historical annotations.

RAW cohort is regenerated byte-equivalently from the frozen broad prefilter. It is not an exhaustive universe of discretionary source setups. Necessary geometric PASS is NOT SOURCE PASS. SFP follow-up checks next OPEN at the next native completion, the earliest conservative observation supplied by this OHLC archive. formation_at stays original; decision_at is explicit and later. No future H/L/C enters its OPEN predicate. Other raw proposals retain their original CLOSE checkpoint. Unfinished reaction/BOS/POI chains wait; they are never retrospectively labelled ready. Annotation can supply a later explicit causal decision checkpoint in a separately versioned evidence submission, never silently rewrite this run.

The categories form an exclusive partition: proven OBJECTIVE_FAIL; otherwise missing primitive/TF coverage UNKNOWN; otherwise QUALITATIVE_REQUIRED; EVIDENCE_COMPLETE only when frozen evaluate returns SOURCE_ALLOW_PLAN_ONLY. Parallel metadata/context/entry/inventory gaps are reported for all rows. Geometry PASS counts only observed necessary components, can overlap UNKNOWN or annotation workload, and does not constitute a stage admitting trades. Missing SOURCE-valid prior OB is UNKNOWN, never a Breaker label.

All historical qualitative catalogs are empty. Structural swings and FVG are exact SOURCE components. Candidate OB/STB/SFP/range records remain source_validated=false for the full setup. Protected structural endpoints, meaningful/adverse scope, aggressive/whole impulse, smooth approach, flow, clear range and contextual relations require cited blinded annotation. No amount of geometric price data substitutes that decision. All four TFs are available context, no universal owner/ladder gate.

Historical metadata is an independent effective-date gate. UNKNOWN intervals are preserved, no current docs sample is backdated. Metadata retrieval failure is external, not strategy rejection. Read HISTORICAL_INSTRUMENT_METADATA_v1.json.

The pack contains the exact qualitative cohort plus known-prefix view references. Each candidate's effective cutoff is enforced by the materializer; shared archives contain full data but must never be opened directly by annotators. Use only materialized candidate views. 100 per batch is an operational transport size, not a strategy parameter. Annotation submission is validated against source citations, IDs, timestamps and outcome denylist. Disagreement/absence → UNKNOWN.

No diagnostic engine comparison occurs before this freeze. Old880 uses outcome-free roster and identity/time/direction/TF projection; old machine geometry and trading outcomes are discarded. An exact RAW event match is a hypothesis, not admission evidence.

Run and reproducibility commands are in REPRODUCIBILITY.md. Immutable namespace is sealed by freeze_manifest.json after QA; --resume-existing checks hashes without financial computations. Stop after PRE_FINANCIAL_EVIDENCE_FREEZE.
''')
    text('OBJECTIVE_SOURCE_DETECTORS.md', '''# Deterministic components and conditional geometry

Implementation: scripts/original_v1_1_objective_geometry_v2.py. Decimal prices; completed contiguous native bars only. Strict three-bar swing is known at right-neighbour CLOSE (S_SWING, SW5 p2). Pair HH/HL/LH/LL is arithmetic relative to prior same-side confirmed swing; protected/key status remains UNKNOWN. A sequence of four explicitly protected, alternating source endpoints can identify HH/HL or LH/LL (S_STRUCTURE, SW5 p2–3). No arbitrary alternation repair or most recent owner selection.

structure_break consumes explicit protected structural endpoints: completed body CLOSE beyond protected HL/LH yields BOS (S_BOS, SW5 p4–5). CONF separately requires a source-selected new-structure key extreme, not every price breakout (S_CONF, SW5 p6–7). Raw last-swing body-cross alone is not SOURCE BOS/CONF. Missing protected selection is UNKNOWN.

Each strict swing supplies a pool candidate (S_POOL_SCOPE, DOC14 P169–198); chronological sweep is strict low<level/high>level after pool became known. Equal touch is not raid. Meaningful/adverse is never set by geometric existence. Internal/external is conditional on explicitly selected source range/impulse boundaries and native TF. Previous UTC DAY/WEEK/MONTH levels use full completed calendar periods only (S_PREVIOUS_LEVELS, SW12 p9–10); partial periods are omitted.

SFP has known old strict-swing price, raid and reclaim completed CLOSE; external structural/range role still needs source selection (S_SFP_FORMATION, DOC16 P68–83/DOC19 P157–162). The next OPEN record contains open/known_at/evidence and actual_open_time, never future H/L/C/completed_at. Pattern native TF preserved. ATR uses fifteen contiguous native bars ending at pattern CLOSE and exactly fourteen TRs, frozen N11_ATR_SMA14; no later candle changes ATR. Source stop at SFP extreme is deterministic, admission is not.

OB candidate requires known pool raid by opposite source candle followed by full native range engulf and directional body. Whole wick source zone (S_OB_ZONE, SW9 p2–3) is retained. Aggressive impulse/BOS/HTF contextual containment/trend/first eligible reaction are not inferred from this necessary prefilter (S_OB_FORMATION/S_OB_APPROACH/S_OB_CONS_TRIGGER). They are exact conditional geometry plus annotation. Provisional OB is never a SOURCE-valid Breaker parent.

breaker_geometry requires a previously SOURCE-valid OB, later body break, source-confirmed new structure and whole-impulse annotation. Whole-impulse low/high must be an explicit selected source interval, never the current candle masquerading as the entire impulse. Unvalidated parent/chopping ambiguity → UNKNOWN (S_BREAKER_FORMATION, SW9 p7–8). New high/low and related structure must be cited; stop uses full selected raid/impulse extreme, body zone is distinct.

FVG is exact first/third wick gap of three completed native bars (S_FVG, DOC16 P51–60), midpoint=(low+high)/2; equal edges create no gap. Gap geometry alone is not contextual FTA or entry. OTE 0.705–0.79 and P/D 0.5 are computed only on explicitly SOURCE-valid selected origin/endpoint pairs (S_OTE/S_PD); no universal OTE gate. Range selection is separate from merely two swings. range_deviation_geometry and range_retest_geometry emit exact chronological components only on an explicitly validated range, with strict boundary raid/reclaim and later known return/retest; these do not decide range clarity or invent a return-zone CHOCH. Raw bracket deviation/reclaim is a component hypothesis, not clarity, reaction at midpoint, external POI or return/retest confirmation (S_RANGE_FORMATION/CONSERVATIVE).

STB/BTS candidates retain raid/manipulation/full absorption. source-confirmed trend, flow, BOS OR CONF and selected P/D range are required before promotion (SW22 p2–4). No invented AND of BOS and CONF. refined_poi_geometry creates a new validated M15 refinement only after source BOS, preserving its original physical parent. source_entry_poi preserves distinct active branch contracts: SFP/OB reaction→M15 BOS→new causal POI; Breaker confirmed broken-OB POI; STB confirmed manipulation POI at midpoint; Range source-confirmed reclaim/return/retest POI. Ambiguous objects/anchors wait, never rank by outcomes.

ConsumedRegistry records first explicitly eligible chronologically ordered source test. Ambiguous unordered OHLC touch stays UNKNOWN. Repeated use of identical POI is consumed; fresh formation+confirmation+POI gives new immutable identity. No cooldown/retry count. contextual_fta scans validated known objects across all four TFs, explicit contextual/opposing/consumed fields, completeness attestation mandatory; frozen target_plan selects nearest favorable opposing known contextual POI. No future POI, no automatic complete empty inventory.
''')
    text('CANONICAL_ID_CONTRACT.md', '''# Canonical causal object identity

object_record hashes JSON [EVIDENCE_OBJECT_v2, kind, symbol, native_tf, known_at, immutable_payload] with sorted keys and compact separators. Values are decimal strings and exact native times. No branch, status, annotation verdict or future suffix is included. swing/structure/impulse/liquidity_pool/POI/OB/breaker/SFP/STB/range/FVG/formation/confirmation/refined_POI/contextual_origin share this constructor. Kind denotes physical source object type, not an entry branch. Branch confluence references the same original physical POI; refinement retains parent_poi_id. Promotion is an evidence attestation referencing an existing ID, never relabels the object or recalculates its identity.

Frozen N11_IDENTITY hashes [symbol, context.id, original_POI.id] for physical_idea_id and zone_id. setup_id hashes [physical_idea_id, direction, formation.id, confirmation.id]. Formation/confirmation IDs refer to immutable physical events shared across source-permitted branches, not branch-prefixed serials. Original contextual origin selection can be qualitative; unknown original context does not get a fabricated physical ID.

Known object bytes/IDs survive prefix replay and arbitrary future candle mutation. Appending confirmation/sweep/consumed annotations adds event records; it cannot edit the founding object. New entry/refined POI links original parent. Re-entry requires fresh source formation+confirmation+POI; changing a branch label cannot reset consumption. All same-event complete cases must pass frozen select_ideas before any lifecycle activation; this stage does not activate positions.
''')
    registry=json.loads((S/'original_strategy_rule_registry_v1_1.json').read_text())['rules']
    cite={r['rule_id']:[{'source_id':c['source_id'],'location':c['page_or_paragraph'],'source_sha256':c['source_sha256']} for c in r.get('page_diagram',[])] for r in registry if r['category']=='SOURCE_RULE'}
    save(D/'SOURCE_CITATION_INDEX.json',cite)
    sections=['# Qualitative evidence annotation protocol v1','',
        'Use materialized blinded views only. Annotator sees the entire available completed prefix across D1/H4/H1/M15 plus immutable structural/POI/liquidity objects. Allowed window [available warmup start, decision_at]. No unseen future bar, outcome, prior admission, machine owner, significance/tolerance label, monetary metric or baseline prediction. No numeric thresholds are introduced.',
        'Every record: concept, PASS/FAIL/UNKNOWN, object_ids, applicable source_rule_ids, exact citations from SOURCE_CITATION_INDEX.json, decision_at, completed_at<=known_at<=decision_at, allowed_window, annotator_id, rationale, provenance.blinded_pack_sha256. Historical availability time denotes information content, not modern annotation wall-clock; record annotation wall-clock separately in provenance. Any selected structural object must already be known; source selection is an explicit attestation, never an automatic detector label. allowed_window ends no later than known_at; an annotator viewing candles through decision_at cannot backdate evidence to the object birth. SOURCE availability=max founding geometry time and annotation/dependency known times. attest_existing_object preserves founding payload and ID while adding a separate source_attestation record; downstream producers enforce its effective knowledge time.',
        'PASS means the cited source relationship is explicitly established on this known prefix; FAIL requires a visible contradictory required SOURCE condition, never missing context. UNKNOWN covers insufficiency, multiple source-permitted selections, unclear qualitative meaning, or annotator disagreement. Each concept uses source wording without hidden percentage/ATR/time cutoffs. Independent annotations with any different state collapse to UNKNOWN; no voting, outcome tie-break or post-hoc selection. Source geometry and entry/stop selection are separate typed contracts; qualitative PASS alone cannot manufacture them.',
        'For adverse role: exact pool ID/native TF, entry relation, setup direction, structure/flow relation, source rule, evidence/known_at mandatory. ADVERSE→WAIT_SWEEP. Sweep then requires full fresh source revalidation, never automatic entry. UNKNOWN never implies no adverse liquidity.']
    definitions={
        'meaningful_liquidity':'pool belongs to source-described structural/substructural liquidity context, not merely any numerical level',
        'adverse_liquidity':'pool is against this source setup in its structure/order-flow context',
        'smooth_approach':'visible smooth structural approach to the HTF OB, preserving source qualitative wording',
        'whole_impulse':'the SOURCE-valid OB is broken in one whole impulse without chopping; full interval endpoints identified',
        'clear_range':'identified impulse/correction boundaries, midpoint reaction and unambiguous source range',
        'reasonable_tilt':'source EQH left higher/right lower or EQL left lower/right higher, within cited substructure; source reasonable scope',
        'protected_endpoints':'explicit key protected structural points belonging to the chosen source structure, not all minor strict swings',
        'contextual_poi_relation':'source-valid POI is relevant/opposing in this setup context on its native TF',
        'branch_confirmation':'the exact selected branch source confirmation and causal sequence is established',
        'source_stop_anchor':'one exact source defining extreme identified before entry, with no competing source anchor',
        'inventory_completeness':'all known contextual source POIs/pools addressed, including unknown candidates; no unreviewed candidate omitted',
        'zone_first_test':'first eligible source test of this original POI established chronologically; unordered ambiguous touch stays unknown',
    }
    for concept,rules in QUALITATIVE.items():
        location='; '.join(r+': '+', '.join(c['source_id']+' '+c['location'] for c in cite[r]) for r in rules)
        definition=definitions.get(concept,'the required '+concept.replace('_',' ')+' relationship is established according to the exact citations below and active branch contract')
        sections += ['', '## '+concept, '', 'View: cited source objects, their origin/dependencies and completed relevant four-TF prefix.',
            'Citations: '+location+'.', 'PASS: '+definition+'.',
            'FAIL: visible evidence contradicts that required source relationship; record exact contradictory objects and source condition.',
            'UNKNOWN: relationship cannot be uniquely established, source wording remains qualitative, or required object/context is missing.',
            'Window/time/provenance/disagreement: common protocol above; never future bars or outcomes. No automatic numerical substitute.']
    text('QUALITATIVE_EVIDENCE_ANNOTATION_PROTOCOL_v1.md','\n'.join(sections))
    text('REPRODUCIBILITY.md', '''# Reproducibility and STOP boundary

Use /workspace/crypto-bot-venv/bin/python from repository root. Initial objective-only run: python scripts/run_original_v1_1_evidence_adapter_v2.py. Existing outputs are never overwritten. Fresh deterministic replay: python scripts/run_original_v1_1_evidence_adapter_v2.py --replay-output /tmp/evidence_v2_replay. Verify all output hashes against delivery. Frozen verification: python scripts/run_original_v1_1_evidence_adapter_v2.py --resume-existing. This verifies adapter/parent/dataset hashes; it never calls accounting or reruns financial metrics.

Blinded batch: python scripts/materialize_original_v1_1_annotation_pack.py --batch 1 --output /tmp/blinded_batch_1 (new directory only). Complete warmup prefix may be large; the index is compact and portable, materialization is intentionally lazy. Annotators receive only materialized views, never the shared full-history archives. 100 candidate references per chronological batch. For one lazy view use --candidate-id <id> --output /tmp/single_blinded_candidate; complete materialization of 100 entire prefixes can be large, so prefer one-at-a-time review. No historical annotation exists in this freeze; tooling is ready for PASS/FAIL/UNKNOWN submissions with explicit provenance.

Seal after completed replay and all QA: python scripts/seal_original_v1_1_evidence_adapter_v2.py --validate /tmp/evidence_v2_final_replay; python scripts/seal_original_v1_1_evidence_adapter_v2.py --seal. Reviewable reports/provenance and QA outputs must already be present. On a fresh checkout, inherited original CSV bytes can be verified directly from their lossless .csv.gz archives without materialization or financial parsing.\n\nQA: python -m unittest discover -s tests -v; python -m compileall -q src scripts tests; mypy src; ruff check the six new scripts and new tests. verify_original_strategy_spec_v1_1.py --resume-existing and verify_original_strategy_spec_v1.py --resume-existing are frozen hash/causality checks, not financial history runs. All first-result files are checked by SHA256 only, monetary contents are not imported.

Sealed artifact paths and hashes are in freeze_manifest.json; manifest excludes itself to avoid circular hash. Source request, official metadata schema response example, code, tests, full objective trace/cohort, compressed blinded pack and QA outputs are retained. Commit message PRE_FINANCIAL_EVIDENCE_FREEZE on medium-term-source-research; no force push, no main merge. Stop here. Another financial run requires a separate explicit user instruction.
''')


if __name__=='__main__':
    build()
