# Qualitative evidence annotation protocol v1

Use materialized blinded views only. Annotator sees the entire available completed prefix across D1/H4/H1/M15 plus immutable structural/POI/liquidity objects. Allowed window [available warmup start, decision_at]. No unseen future bar, outcome, prior admission, machine owner, significance/tolerance label, monetary metric or baseline prediction. No numeric thresholds are introduced.
Every record: concept, PASS/FAIL/UNKNOWN, object_ids, applicable source_rule_ids, exact citations from SOURCE_CITATION_INDEX.json, decision_at, completed_at<=known_at<=decision_at, allowed_window, annotator_id, rationale, provenance.blinded_pack_sha256. Historical availability time denotes information content, not modern annotation wall-clock; record annotation wall-clock separately in provenance. Any selected structural object must already be known; source selection is an explicit attestation, never an automatic detector label. allowed_window ends no later than known_at; an annotator viewing candles through decision_at cannot backdate evidence to the object birth. SOURCE availability=max founding geometry time and annotation/dependency known times. attest_existing_object preserves founding payload and ID while adding a separate source_attestation record; downstream producers enforce its effective knowledge time.
PASS means the cited source relationship is explicitly established on this known prefix; FAIL requires a visible contradictory required SOURCE condition, never missing context. UNKNOWN covers insufficiency, multiple source-permitted selections, unclear qualitative meaning, or annotator disagreement. Each concept uses source wording without hidden percentage/ATR/time cutoffs. Independent annotations with any different state collapse to UNKNOWN; no voting, outcome tie-break or post-hoc selection. Source geometry and entry/stop selection are separate typed contracts; qualitative PASS alone cannot manufacture them.
For adverse role: exact pool ID/native TF, entry relation, setup direction, structure/flow relation, source rule, evidence/known_at mandatory. ADVERSE→WAIT_SWEEP. Sweep then requires full fresh source revalidation, never automatic entry. UNKNOWN never implies no adverse liquidity.

## market_context

View: cited source objects, their origin/dependencies and completed relevant four-TF prefix.
Citations: S_STRUCTURE: SW5 p2–3, 19 word/document.xml:P0053–P0073.
PASS: the required market context relationship is established according to the exact citations below and active branch contract.
FAIL: visible evidence contradicts that required source relationship; record exact contradictory objects and source condition.
UNKNOWN: relationship cannot be uniquely established, source wording remains qualitative, or required object/context is missing.
Window/time/provenance/disagreement: common protocol above; never future bars or outcomes. No automatic numerical substitute.

## liquidity_context

View: cited source objects, their origin/dependencies and completed relevant four-TF prefix.
Citations: S_LIQUIDITY_CONTEXT: 14 word/document.xml:P0113–P0120, 19 word/document.xml:P0117–P0121.
PASS: the required liquidity context relationship is established according to the exact citations below and active branch contract.
FAIL: visible evidence contradicts that required source relationship; record exact contradictory objects and source condition.
UNKNOWN: relationship cannot be uniquely established, source wording remains qualitative, or required object/context is missing.
Window/time/provenance/disagreement: common protocol above; never future bars or outcomes. No automatic numerical substitute.

## ob_formation

View: cited source objects, their origin/dependencies and completed relevant four-TF prefix.
Citations: S_OB_FORMATION: SW9 p2–2.
PASS: the required ob formation relationship is established according to the exact citations below and active branch contract.
FAIL: visible evidence contradicts that required source relationship; record exact contradictory objects and source condition.
UNKNOWN: relationship cannot be uniquely established, source wording remains qualitative, or required object/context is missing.
Window/time/provenance/disagreement: common protocol above; never future bars or outcomes. No automatic numerical substitute.

## higher_poi

View: cited source objects, their origin/dependencies and completed relevant four-TF prefix.
Citations: S_OB_FORMATION: SW9 p2–2.
PASS: the required higher poi relationship is established according to the exact citations below and active branch contract.
FAIL: visible evidence contradicts that required source relationship; record exact contradictory objects and source condition.
UNKNOWN: relationship cannot be uniquely established, source wording remains qualitative, or required object/context is missing.
Window/time/provenance/disagreement: common protocol above; never future bars or outcomes. No automatic numerical substitute.

## trend_aligned

View: cited source objects, their origin/dependencies and completed relevant four-TF prefix.
Citations: S_OB_TREND: SW9 p3–3, SW9 p16–16; S_STB_FORMATION: SW22 p2–3.
PASS: the required trend aligned relationship is established according to the exact citations below and active branch contract.
FAIL: visible evidence contradicts that required source relationship; record exact contradictory objects and source condition.
UNKNOWN: relationship cannot be uniquely established, source wording remains qualitative, or required object/context is missing.
Window/time/provenance/disagreement: common protocol above; never future bars or outcomes. No automatic numerical substitute.

## smooth_approach

View: cited source objects, their origin/dependencies and completed relevant four-TF prefix.
Citations: S_OB_APPROACH: SW9 p4–4.
PASS: visible smooth structural approach to the HTF OB, preserving source qualitative wording.
FAIL: visible evidence contradicts that required source relationship; record exact contradictory objects and source condition.
UNKNOWN: relationship cannot be uniquely established, source wording remains qualitative, or required object/context is missing.
Window/time/provenance/disagreement: common protocol above; never future bars or outcomes. No automatic numerical substitute.

## reaction_bos_new_poi

View: cited source objects, their origin/dependencies and completed relevant four-TF prefix.
Citations: S_OB_CONS_TRIGGER: SW9 p4–6.
PASS: the required reaction bos new poi relationship is established according to the exact citations below and active branch contract.
FAIL: visible evidence contradicts that required source relationship; record exact contradictory objects and source condition.
UNKNOWN: relationship cannot be uniquely established, source wording remains qualitative, or required object/context is missing.
Window/time/provenance/disagreement: common protocol above; never future bars or outcomes. No automatic numerical substitute.

## breaker_formation

View: cited source objects, their origin/dependencies and completed relevant four-TF prefix.
Citations: S_BREAKER_FORMATION: SW9 p7–8.
PASS: the required breaker formation relationship is established according to the exact citations below and active branch contract.
FAIL: visible evidence contradicts that required source relationship; record exact contradictory objects and source condition.
UNKNOWN: relationship cannot be uniquely established, source wording remains qualitative, or required object/context is missing.
Window/time/provenance/disagreement: common protocol above; never future bars or outcomes. No automatic numerical substitute.

## flow_context

View: cited source objects, their origin/dependencies and completed relevant four-TF prefix.
Citations: S_FLOW: SW22 p5–6.
PASS: the required flow context relationship is established according to the exact citations below and active branch contract.
FAIL: visible evidence contradicts that required source relationship; record exact contradictory objects and source condition.
UNKNOWN: relationship cannot be uniquely established, source wording remains qualitative, or required object/context is missing.
Window/time/provenance/disagreement: common protocol above; never future bars or outcomes. No automatic numerical substitute.

## poi_reaction

View: cited source objects, their origin/dependencies and completed relevant four-TF prefix.
Citations: S_POI: SW9 p10–11.
PASS: the required poi reaction relationship is established according to the exact citations below and active branch contract.
FAIL: visible evidence contradicts that required source relationship; record exact contradictory objects and source condition.
UNKNOWN: relationship cannot be uniquely established, source wording remains qualitative, or required object/context is missing.
Window/time/provenance/disagreement: common protocol above; never future bars or outcomes. No automatic numerical substitute.

## stb_raid_absorption_structure

View: cited source objects, their origin/dependencies and completed relevant four-TF prefix.
Citations: S_STB_FORMATION: SW22 p2–3.
PASS: the required stb raid absorption structure relationship is established according to the exact citations below and active branch contract.
FAIL: visible evidence contradicts that required source relationship; record exact contradictory objects and source condition.
UNKNOWN: relationship cannot be uniquely established, source wording remains qualitative, or required object/context is missing.
Window/time/provenance/disagreement: common protocol above; never future bars or outcomes. No automatic numerical substitute.

## pd_context

View: cited source objects, their origin/dependencies and completed relevant four-TF prefix.
Citations: S_PD: SW22 p4–4, 19 word/document.xml:P0140–P0155.
PASS: the required pd context relationship is established according to the exact citations below and active branch contract.
FAIL: visible evidence contradicts that required source relationship; record exact contradictory objects and source condition.
UNKNOWN: relationship cannot be uniquely established, source wording remains qualitative, or required object/context is missing.
Window/time/provenance/disagreement: common protocol above; never future bars or outcomes. No automatic numerical substitute.

## clear_range

View: cited source objects, their origin/dependencies and completed relevant four-TF prefix.
Citations: S_RANGE_FORMATION: 06 word/document.xml:P0037–P0072, 19 word/document.xml:P0122–P0128.
PASS: identified impulse/correction boundaries, midpoint reaction and unambiguous source range.
FAIL: visible evidence contradicts that required source relationship; record exact contradictory objects and source condition.
UNKNOWN: relationship cannot be uniquely established, source wording remains qualitative, or required object/context is missing.
Window/time/provenance/disagreement: common protocol above; never future bars or outcomes. No automatic numerical substitute.

## range_deviation

View: cited source objects, their origin/dependencies and completed relevant four-TF prefix.
Citations: S_RANGE_DEVIATION: 06 word/document.xml:P0074–P0094, 19 word/document.xml:P0125–P0130.
PASS: the required range deviation relationship is established according to the exact citations below and active branch contract.
FAIL: visible evidence contradicts that required source relationship; record exact contradictory objects and source condition.
UNKNOWN: relationship cannot be uniquely established, source wording remains qualitative, or required object/context is missing.
Window/time/provenance/disagreement: common protocol above; never future bars or outcomes. No automatic numerical substitute.

## outside_poi

View: cited source objects, their origin/dependencies and completed relevant four-TF prefix.
Citations: S_RANGE_AGGRESSIVE: 06 word/document.xml:P0111–P0118.
PASS: the required outside poi relationship is established according to the exact citations below and active branch contract.
FAIL: visible evidence contradicts that required source relationship; record exact contradictory objects and source condition.
UNKNOWN: relationship cannot be uniquely established, source wording remains qualitative, or required object/context is missing.
Window/time/provenance/disagreement: common protocol above; never future bars or outcomes. No automatic numerical substitute.

## range_reclaim_retest

View: cited source objects, their origin/dependencies and completed relevant four-TF prefix.
Citations: S_RANGE_CONSERVATIVE: 06 word/document.xml:P0124–P0129, 19 word/document.xml:P0129–P0130.
PASS: the required range reclaim retest relationship is established according to the exact citations below and active branch contract.
FAIL: visible evidence contradicts that required source relationship; record exact contradictory objects and source condition.
UNKNOWN: relationship cannot be uniquely established, source wording remains qualitative, or required object/context is missing.
Window/time/provenance/disagreement: common protocol above; never future bars or outcomes. No automatic numerical substitute.

## return_choch_zone

View: cited source objects, their origin/dependencies and completed relevant four-TF prefix.
Citations: S_RANGE_CONSERVATIVE: 06 word/document.xml:P0124–P0129, 19 word/document.xml:P0129–P0130.
PASS: the required return choch zone relationship is established according to the exact citations below and active branch contract.
FAIL: visible evidence contradicts that required source relationship; record exact contradictory objects and source condition.
UNKNOWN: relationship cannot be uniquely established, source wording remains qualitative, or required object/context is missing.
Window/time/provenance/disagreement: common protocol above; never future bars or outcomes. No automatic numerical substitute.

## ltf_bos_source_entry

View: cited source objects, their origin/dependencies and completed relevant four-TF prefix.
Citations: S_SFP_REFINE: 16 word/document.xml:P0084–P0087.
PASS: the required ltf bos source entry relationship is established according to the exact citations below and active branch contract.
FAIL: visible evidence contradicts that required source relationship; record exact contradictory objects and source condition.
UNKNOWN: relationship cannot be uniquely established, source wording remains qualitative, or required object/context is missing.
Window/time/provenance/disagreement: common protocol above; never future bars or outcomes. No automatic numerical substitute.

## breaker_confirmation

View: cited source objects, their origin/dependencies and completed relevant four-TF prefix.
Citations: S_BREAKER_FORMATION: SW9 p7–8.
PASS: the required breaker confirmation relationship is established according to the exact citations below and active branch contract.
FAIL: visible evidence contradicts that required source relationship; record exact contradictory objects and source condition.
UNKNOWN: relationship cannot be uniquely established, source wording remains qualitative, or required object/context is missing.
Window/time/provenance/disagreement: common protocol above; never future bars or outcomes. No automatic numerical substitute.

## sl_off_liquidity

View: cited source objects, their origin/dependencies and completed relevant four-TF prefix.
Citations: S_SL_OFF_POOL: SW11 p8–8.
PASS: the required sl off liquidity relationship is established according to the exact citations below and active branch contract.
FAIL: visible evidence contradicts that required source relationship; record exact contradictory objects and source condition.
UNKNOWN: relationship cannot be uniquely established, source wording remains qualitative, or required object/context is missing.
Window/time/provenance/disagreement: common protocol above; never future bars or outcomes. No automatic numerical substitute.

## meaningful_liquidity

View: cited source objects, their origin/dependencies and completed relevant four-TF prefix.
Citations: S_LIQUIDITY_CONTEXT: 14 word/document.xml:P0113–P0120, 19 word/document.xml:P0117–P0121.
PASS: pool belongs to source-described structural/substructural liquidity context, not merely any numerical level.
FAIL: visible evidence contradicts that required source relationship; record exact contradictory objects and source condition.
UNKNOWN: relationship cannot be uniquely established, source wording remains qualitative, or required object/context is missing.
Window/time/provenance/disagreement: common protocol above; never future bars or outcomes. No automatic numerical substitute.

## adverse_liquidity

View: cited source objects, their origin/dependencies and completed relevant four-TF prefix.
Citations: S_ADVERSE_BLOCK: 03 word/document.xml:P0061–P0066; S_ADVERSE_WAIT: 14 word/document.xml:P0155–P0159.
PASS: pool is against this source setup in its structure/order-flow context.
FAIL: visible evidence contradicts that required source relationship; record exact contradictory objects and source condition.
UNKNOWN: relationship cannot be uniquely established, source wording remains qualitative, or required object/context is missing.
Window/time/provenance/disagreement: common protocol above; never future bars or outcomes. No automatic numerical substitute.

## whole_impulse

View: cited source objects, their origin/dependencies and completed relevant four-TF prefix.
Citations: S_BREAKER_FORMATION: SW9 p7–8.
PASS: the SOURCE-valid OB is broken in one whole impulse without chopping; full interval endpoints identified.
FAIL: visible evidence contradicts that required source relationship; record exact contradictory objects and source condition.
UNKNOWN: relationship cannot be uniquely established, source wording remains qualitative, or required object/context is missing.
Window/time/provenance/disagreement: common protocol above; never future bars or outcomes. No automatic numerical substitute.

## reasonable_tilt

View: cited source objects, their origin/dependencies and completed relevant four-TF prefix.
Citations: S_EQ_STRUCTURE: 14 word/document.xml:P0122–P0159.
PASS: source EQH left higher/right lower or EQL left lower/right higher, within cited substructure; source reasonable scope.
FAIL: visible evidence contradicts that required source relationship; record exact contradictory objects and source condition.
UNKNOWN: relationship cannot be uniquely established, source wording remains qualitative, or required object/context is missing.
Window/time/provenance/disagreement: common protocol above; never future bars or outcomes. No automatic numerical substitute.

## protected_endpoints

View: cited source objects, their origin/dependencies and completed relevant four-TF prefix.
Citations: S_STRUCTURE: SW5 p2–3, 19 word/document.xml:P0053–P0073; S_BOS: SW5 p4–5, 19 word/document.xml:P0088–P0100.
PASS: explicit key protected structural points belonging to the chosen source structure, not all minor strict swings.
FAIL: visible evidence contradicts that required source relationship; record exact contradictory objects and source condition.
UNKNOWN: relationship cannot be uniquely established, source wording remains qualitative, or required object/context is missing.
Window/time/provenance/disagreement: common protocol above; never future bars or outcomes. No automatic numerical substitute.

## contextual_poi_relation

View: cited source objects, their origin/dependencies and completed relevant four-TF prefix.
Citations: S_POI: SW9 p10–11; S_FTA: SW9 p11–13, SW9 p16–16.
PASS: source-valid POI is relevant/opposing in this setup context on its native TF.
FAIL: visible evidence contradicts that required source relationship; record exact contradictory objects and source condition.
UNKNOWN: relationship cannot be uniquely established, source wording remains qualitative, or required object/context is missing.
Window/time/provenance/disagreement: common protocol above; never future bars or outcomes. No automatic numerical substitute.

## selected_impulse

View: cited source objects, their origin/dependencies and completed relevant four-TF prefix.
Citations: S_OTE: 19 word/document.xml:P0138–P0156; S_PD: SW22 p4–4, 19 word/document.xml:P0140–P0155.
PASS: the required selected impulse relationship is established according to the exact citations below and active branch contract.
FAIL: visible evidence contradicts that required source relationship; record exact contradictory objects and source condition.
UNKNOWN: relationship cannot be uniquely established, source wording remains qualitative, or required object/context is missing.
Window/time/provenance/disagreement: common protocol above; never future bars or outcomes. No automatic numerical substitute.

## selected_range

View: cited source objects, their origin/dependencies and completed relevant four-TF prefix.
Citations: S_RANGE_FORMATION: 06 word/document.xml:P0037–P0072, 19 word/document.xml:P0122–P0128; S_PD: SW22 p4–4, 19 word/document.xml:P0140–P0155.
PASS: the required selected range relationship is established according to the exact citations below and active branch contract.
FAIL: visible evidence contradicts that required source relationship; record exact contradictory objects and source condition.
UNKNOWN: relationship cannot be uniquely established, source wording remains qualitative, or required object/context is missing.
Window/time/provenance/disagreement: common protocol above; never future bars or outcomes. No automatic numerical substitute.

## zone_first_test

View: cited source objects, their origin/dependencies and completed relevant four-TF prefix.
Citations: S_OB_FIRST_TEST: SW9 p3–3.
PASS: first eligible source test of this original POI established chronologically; unordered ambiguous touch stays unknown.
FAIL: visible evidence contradicts that required source relationship; record exact contradictory objects and source condition.
UNKNOWN: relationship cannot be uniquely established, source wording remains qualitative, or required object/context is missing.
Window/time/provenance/disagreement: common protocol above; never future bars or outcomes. No automatic numerical substitute.

## inventory_completeness

View: cited source objects, their origin/dependencies and completed relevant four-TF prefix.
Citations: S_FTA: SW9 p11–13, SW9 p16–16; S_POOL_SCOPE: 14 word/document.xml:P0169–P0198.
PASS: all known contextual source POIs/pools addressed, including unknown candidates; no unreviewed candidate omitted.
FAIL: visible evidence contradicts that required source relationship; record exact contradictory objects and source condition.
UNKNOWN: relationship cannot be uniquely established, source wording remains qualitative, or required object/context is missing.
Window/time/provenance/disagreement: common protocol above; never future bars or outcomes. No automatic numerical substitute.

## source_stop_anchor

View: cited source objects, their origin/dependencies and completed relevant four-TF prefix.
Citations: S_PLAN: SW11 p2–4.
PASS: one exact source defining extreme identified before entry, with no competing source anchor.
FAIL: visible evidence contradicts that required source relationship; record exact contradictory objects and source condition.
UNKNOWN: relationship cannot be uniquely established, source wording remains qualitative, or required object/context is missing.
Window/time/provenance/disagreement: common protocol above; never future bars or outcomes. No automatic numerical substitute.

## branch_confirmation

View: cited source objects, their origin/dependencies and completed relevant four-TF prefix.
Citations: S_BOS: SW5 p4–5, 19 word/document.xml:P0088–P0100; S_CONF: SW5 p6–7.
PASS: the exact selected branch source confirmation and causal sequence is established.
FAIL: visible evidence contradicts that required source relationship; record exact contradictory objects and source condition.
UNKNOWN: relationship cannot be uniquely established, source wording remains qualitative, or required object/context is missing.
Window/time/provenance/disagreement: common protocol above; never future bars or outcomes. No automatic numerical substitute.
