"""Freeze machine selectors before any historical financial outcome is calculated."""

from __future__ import annotations

import argparse
from pathlib import Path

from machine_strategy_research_io import (
    original_invariance,
    qa_stage,
    read,
    seal_machine,
    verify_machine,
)
from machine_strategy_v2_core import PARAMETERS, PRIORITY
from original_v1_1_financial_data import ROOT, save, write_csv

DEST = ROOT / "docs/machine_strategy_v2_design"
CODE = [
    "scripts/machine_strategy_v2_core.py",
    "scripts/machine_strategy_research_io.py",
    "scripts/build_machine_strategy_v2_design.py",
    "tests/test_machine_strategy_v2_core.py",
]
CITATIONS = ROOT / "docs/original_v1_1_blinded_annotation_v1/SOURCE_CITATIONS.json"
RULES = [
    (
        "M2_TF",
        "S_FRACTAL",
        "D1 global; H4 local; H1 primary completed decision; M15 refinement. H1/H4 formation branches only. D1/M15 do not independently create entry ideas. No universal TF alignment.",
    ),
    (
        "M2_SWING",
        "S_SWING",
        "Reuse strict three-bar raw swings. Center extreme strictly exceeds both neighbors; known_at is right-bar CLOSE. Equal extremes are not swings.",
    ),
    (
        "M2_BOS",
        "S_BOS",
        "On completed bar, CLOSE crosses latest already-known HIGH for LONG or LOW for SHORT; prior CLOSE is not beyond that same level. Both break reference and latest opposing origin swing are known by bar OPEN. Latest completed break replaces provisional pending break; stable canonical ID tie-break.",
    ),
    (
        "M2_CONF",
        "S_CONF",
        "First later confirmed strict HIGH (LONG)/LOW (SHORT), center at or after BOS bar and beyond broken reference, confirms the pending machine leg. Endpoint and protected origin commit atomically at right-bar CLOSE. A body loss of origin cancels pending; a body loss of protected price invalidates active context.",
    ),
    (
        "M2_CONTEXT",
        "S_STRUCTURE",
        "Current direction/structural leg/origin/protected endpoint use latest confirmed machine BOS+CONF. Origin is latest opposing swing known at BOS OPEN, not a discretionarily annotated Original protected endpoint. D1 and H4 need confirmed context. Missing observed context produces WAIT_NO_CONFIRMED_CONTEXT, not an undefined selector.",
    ),
    (
        "M2_IMPULSE",
        "S_OTE",
        "Selected impulse is the origin and confirming endpoint of current confirmed BOS. It freezes start/end swing IDs, BOS ID, direction, known_at and canonical ID; latest confirmed leg is deterministic context tie-break.",
    ),
    (
        "M2_PD_OTE",
        "S_PD",
        "Dealing low/high=min/max selected endpoints; EQ=0.5, OTE retracements=0.705–0.79 from endpoint toward origin. PD/OTE are recorded causal context; no universal Fib admission gate.",
    ),
    (
        "M2_HTF",
        "S_FLOW",
        "Trade direction must match H1. H4-aligned trend accepted regardless of D1 direction. Counter-H4 ideas require original formation bar intersection with a same-direction unconsumed contextual H4/D1 POI. D1 direction is context information, not universal alignment.",
    ),
    (
        "M2_LIQ_SCOPE",
        "S_POOL_SCOPE",
        "Only already-known unswept strict-swing pools on H1/H4/D1. Structural flag=protected/end swing identity. Internal strictly between selected impulse low/high; all remaining pools external.",
    ),
    (
        "M2_LIQ_ROLES",
        "S_LIQUIDITY_CONTEXT",
        "Ahead-of-entry pool with profit-side HIGH/LONG or LOW/SHORT is TARGET_FUEL. Opposite-side behind-entry pool beyond proposed stop and internal to impulse is ADVERSE; remaining pools NEUTRAL. Reject stop placed before internal adverse pool. No standalone liquidity entry.",
    ),
    (
        "M2_FVG",
        "S_FVG",
        "Strict three-candle gap retained unchanged. Contextual machine POI is born with a same-direction pending/current BOS origin; that origin must causally CONF before selection. POI carries raw source geometry reference but machine contextual validity is not SOURCE_RULE.",
    ),
    (
        "M2_OB",
        "S_OB_FORMATION",
        "Reuse raw raid plus opposing candle and full-range engulf geometry from immutable GeometryIndex, not arbitrary last opposing candle. Original OB reaction after birth must precede M15 BOS+CONF. Select new M15 OB or FVG with that BOS origin, born no earlier than BOS, wholly within original full OB interval.",
    ),
    (
        "M2_SFP",
        "S_SFP_FORMATION",
        "Completed wick raid/reclaim of latest already-known strict swing. H1/H4 only for this machine profile. Next native OPEN must stay reclaimed; conservative OHLC availability exposes it at that native bar CLOSE. Then M15 BOS+CONF and new POI wholly inside completed pattern interval. No next-close substitution for OPEN.",
    ),
    (
        "M2_STB",
        "S_STB_FORMATION",
        "Reuse raid-engulf raw STB/BTS geometry; require causal H1 context direction and subsequent M15 BOS+CONF. Entry midpoint of original manipulation candle body. It remains a distinct STB branch; conflicting raw OB sibling is suppressed by fixed priority.",
    ),
    (
        "M2_BREAKER",
        "S_BREAKER_FORMATION",
        "Existing raw OB with machine contextual-at-birth relationship, already known at bar OPEN; opposite body-close break of full OB extreme creates unique breaker formation. Stop anchor covers entire known parent-OB-birth-to-break interval. Opposite subsequent M15 BOS+CONF and body-zone retest limit entry. Parent relationship is MACHINE validation, not retroactive SOURCE validation.",
    ),
    (
        "M2_RANGE",
        "S_RANGE_FORMATION",
        "After selected impulse CONF, latest later interior opposing correction swing defines correction-to-impulse-end range. Require completed EQ contact and close inside range. First strict wick deviation and inside CLOSE per range/direction creates formation. Subsequent boundary contact and inside CLOSE is retest; then M15 BOS+CONF. Replacement correction swing creates a new range identity.",
    ),
    (
        "M2_SMOOTH",
        "S_OB_APPROACH",
        "Operational smooth/whole approach means no opposite M15 BOS from reaction/break through selected refinement CONF. No new arbitrary percentage, slope score or future effectiveness test.",
    ),
    (
        "M2_POI_PRIORITY",
        "S_POI",
        "For SFP/OB choose M15 OB before FVG, latest born_at then canonical ID, within original interval and with exact confirming BOS origin. Other branches use original body/deviation zone. All ties use causal content only.",
    ),
    (
        "M2_FIRST_TEST",
        "S_OB_FIRST_TEST",
        "Native contextual raw POI eligible when its origin BOS is confirmed by bar OPEN and active native context has same direction. First later OHLC contact consumes it at completed-bar time, irrespective of whether trade is emitted. Repeated consumed POI forbidden. Synthetic breaker/range entry POI first becomes eligible after branch prerequisites; first future order contact recorded in execution. One order per entry POI; order reservation is distinct from consumption.",
    ),
    (
        "M2_IDENTITIES",
        "S_OB_FIRST_TEST",
        "Physical event normalization=(symbol, formation CLOSE, direction), independent of branch and TF. Setup=(physical, formation ID, refinement CONF, entry POI). This is explicit machine equivalence, not proof of Original source identity. New structure/formation gets new IDs; replay of same POI/event is idempotent.",
    ),
    (
        "M2_BRANCH_PRIORITY",
        "S_POI",
        "Sibling priority BREAKER > STB > SFP > OB > RANGE; within branch H4 before H1, then setup ID. Emit once per normalized physical event and once per entry POI; keep chosen branch and rejected siblings. Not chosen by branch performance.",
    ),
    (
        "M2_ENTRY",
        "S_OB_ZONE",
        "Separate source geometry from theoretical executable entry. SFP/OB/Breaker proximal edge (high LONG, low SHORT), STB body midpoint, Range reclaimed boundary. No exchange tick rounding asserted.",
    ),
    (
        "M2_STOP",
        "S_SL_OFF_POOL",
        "Fixed initial stop; no BE. SFP completed pattern extreme plus outward ATR SMA14 of exactly 14 TRs including pattern and preceding close. Other anchors OB source full extreme, STB manipulation extreme, Breaker entire parent-to-break extreme, Range deviation extreme; explicit relative epsilon 1e-8 beyond anchor in theoretical mode. Epsilon is not a historical tick.",
    ),
    (
        "M2_FTA",
        "S_FTA",
        "Complete causal H1/H4/D1 inventory of unconsumed opposite contextual OB/STB/FVG and unswept profit-side strict swing liquidity. Price-nearest forward proximal zone edge/pool wins, canonical ID resolves ties. Entry inside opposing zone rejected. Accepting strict-swing liquidity as machine FTA is an explicit extension. No future zone success information.",
    ),
    (
        "M2_RANGE_EXIT",
        "S_RANGE_CONSERVATIVE",
        "Range far boundary moved inward by explicit theoretical epsilon and nearer contextual FTA cap. Frozen 80/20 same-zone no-remainder model means coincident target price; aggregate full exit equivalent to two proportional legs. No fixed percent TP.",
    ),
    (
        "M2_EXPIRY",
        "S_POI",
        "Pending formation expires after 16 H1 cycles independent of outcome. Order lives next one H1 cycle/four M15 bars. No elapsed future holding-time filter. No re-entry of emitted physical event or entry POI.",
    ),
    (
        "M2_INTRABAR",
        "S_SL_OFF_POOL",
        "Execution finest supported TF=M15. Known OPEN gap first; otherwise no invented TP-first/SL-first. Filled-bar ambiguous target-before-limit order or simultaneous SL/FTA means WAIT_INTRABAR_ORDER. A wick limit with stop-only crossing is ordered under explicitly continuous intra-bar path; no arbitrary outcome ordering.",
    ),
    (
        "M2_SOURCE_BOUNDARY",
        "S_STRUCTURE",
        "All contextual/selector rules above are MACHINE_RULE_PRE_BACKTEST. Retain raw SOURCE geometry references and primary citations; source_validated=false for machine cases. Original v1/v1.1 and all prior freezes untouched.",
    ),
]
RULES.append(
    (
        "M2_SFP_BODY_EXIT",
        "S_SFP_BODY_EXIT",
        "After fill, SFP body loss of completed pattern extreme exits only at completed native setup-TF CLOSE. M15 wick chronology is processed before native CLOSE; fixed initial SL remains unchanged and no BE is applied.",
    )
)
POLICY = {
    "classification": "MACHINE_RULE_PRE_BACKTEST",
    "minimum_closed": 200,
    "net_PF_strictly_above": 1,
    "net_expectancy_strictly_above": 0,
    "maximum_closed_return_drawdown_R": 20,
    "minimum_positive_calendar_years": 2,
    "maximum_single_group_net_positive_profit_share": "0.80",
    "maximum_intrabar_unresolved_fraction": "0.20",
    "required_execution_realism": "VERIFIED_PRICE_METADATA_AND_COST_FUNDING_SUPPORT_FOR_PRODUCTION",
    "role": "Pre-outcome research acceptance gates, not SOURCE rules. Closed independent-case cumulative-R drawdown is diagnostic, not live portfolio drawdown.",
    "improvement_limit": 2,
    "improvement_method": "After frozen robustness only: one logical causal hypothesis per new version, no parameter search; previous versions immutable. Same dataset retests are development diagnostics, not independent validation.",
    "paper_minimum_closed": 200,
    "paper_minimum_calendar_days": 30,
    "trade_entry_allowed": False,
}
DOCS = {
    "MACHINE_STRATEGY_V2_SPEC.md": """# Machine Strategy v2\n\nOriginal v1/v1.1 remains the immutable source reference. This is a deterministic machine interpretation, not exact Original. All selectors not uniquely dictated by source are MACHINE_RULE_PRE_BACKTEST. Do not promote them to SOURCE_RULE.\n\nPreserve SFP, OB, Breaker, STB/BTS, Range, FVG/IMB, liquidity, BOS, CONF, OTE/PD, FTA, FIRST_TEST_ONLY, fixed stop and M15/H1/H4/D1. Formation TFs are H1/H4; H1 decision and M15 refinement apply consistently. Missing observations cause defined WAIT/reject outcomes rather than discretion. Every critical selector has a total rule, deterministic tie-break and causal known_at.\n\nThe rule registry is normative together with frozen executable core; specialized documents identify the exact rule IDs. SOURCE_CITATIONS.json preserves primary file/page/hash/literal passages. No historical results, labels, fitted winners, future candles or profitability subgroups are design inputs. Design QA uses synthetic prefixes only.\n\nHistorical price/quantity verification is separate. Theoretical unrounded execution, relative stop/boundary epsilon and modeled costs require explicit Stage 2 registration. No historical exchange-realistic execution assertion. No automatic production or real orders; trade_entry_allowed=false.\n""",
    "MACHINE_DECISION_TREE.md": """# Machine decision tree\n\nCompleted H1 cutoff -> advance only completed D1/H4/H1/M15 prefixes -> known swings -> body BOS -> confirming new endpoint -> selected impulse/protected origin -> known H1/H4/D1 context -> raw H1/H4 branch formation -> required next OPEN/reaction/retest -> M15 BOS+CONF -> origin-bound new POI or original branch entry POI -> unconsumed first-eligible state -> unique fixed stop -> complete causal liquidity/FTA inventory -> valid forward target -> deterministic physical/branch/POI dedup -> ALLOWED_MACHINE_SETUP -> next-cycle theoretical order.\n\nAbsent context/confirmation/POI/FTA = named WAIT until fixed expiry; invalid geometry/adverse liquidity/consumed or duplicate = reject. No source discretionary UNKNOWN is silently converted to source PASS. No order for M15/D1 standalone setup. Stage 1 Gate passes only if all machine definitions are complete; observational WAIT does not mean an undefined definition.\n""",
    "MACHINE_CONTEXT_MODEL.md": "# Context model\n\nNormative rules M2_SWING, M2_BOS, M2_CONF, M2_CONTEXT, M2_IMPULSE, M2_PD_OTE and M2_HTF. A BOS here is a machine break of the latest known reference, not a claim that arbitrary raw reference is Original protected structure. The origin becomes protected only after causal endpoint CONF. Endpoint updates occur on confirmation; body invalidation retires context. Latest confirmed BOS selects a single impulse; stable IDs resolve equal-time ambiguity.\n",
    "MACHINE_LIQUIDITY_MODEL.md": "# Liquidity model\n\nM2_LIQ_SCOPE, M2_LIQ_ROLES and M2_FTA assign every known unswept pool a structural flag, INTERNAL/EXTERNAL scope and TARGET_FUEL/ADVERSE/NEUTRAL role relative to actual pre-entry entry/stop geometry. Missing structural context waits. Inventory is complete for known H1/H4/D1 prefixes. Liquidity alone cannot trigger a branch.\n",
    "MACHINE_POI_SELECTION.md": "# POI and first-test selection\n\nM2_FVG, M2_POI_PRIORITY, M2_FIRST_TEST and M2_IDENTITIES. Native contextual-at-birth POI requires a causal origin BOS and confirmation before selection. Strict gap geometry remains raw SOURCE geometry; contextual attribution is machine policy. One eligible native contact consumes a POI. Reservation of a emitted order does not assert consumption; no second order is emitted for that POI. All three concepts born_at, first_eligible_touch/consumed_at, and setup identity are separate.\n",
    "MACHINE_BRANCH_RULES.md": "# Branch contracts\n\nSFP: completed H1/H4 raid/reclaim -> native next OPEN reclaimed -> M15 BOS/CONF -> new origin-bound M15 OB/FVG -> fixed pattern ATR stop -> nearest causal FTA.\n\nOB: raw source raid/engulf geometry -> later reaction -> M15 BOS/CONF -> new origin-bound POI -> source extreme stop -> FTA.\n\nBreaker: machine-contextual parent OB -> opposite body break -> M15 BOS/CONF without opposite BOS -> body-zone retest limit -> whole parent-to-break extreme stop -> FTA.\n\nSTB/BTS: raw manipulation/engulf -> H1 context and M15 BOS/CONF -> manipulation body midpoint -> manipulation extreme stop -> FTA.\n\nRange: confirmed impulse plus interior correction -> EQ reaction -> first deviation/reclaim -> later boundary retest -> M15 BOS/CONF -> boundary limit -> deviation stop -> nearest FTA/far-boundary cap, coincident 80/20 exit.\n\nM2_BRANCH_PRIORITY selects a single machine physical event sibling; rejected siblings retained. Definitions and citations are in registry M2_OB/M2_SFP/M2_STB/M2_BREAKER/M2_RANGE/M2_SMOOTH.\n",
    "MACHINE_ENTRY_STOP_TARGET.md": "# Entry / stop / target\n\nNormative M2_ENTRY, M2_STOP, M2_FTA and M2_RANGE_EXIT. Source/raw defining geometry, unrounded theoretical price and verified exchange executable price are separate fields. Historical tick proof is absent; no exchange price is invented. Fixed initial stop never moves to BE. Nearest causal contextual FTA defines full non-Range exit; Range 80/20 same-zone aggregate exit remains structural. No fixed percentage targets or future holding-time filters.\n",
    "MACHINE_INTRABAR_POLICY.md": "# Intrabar order\n\nM2_INTRABAR/M2_EXPIRY are frozen before financial calculation. Orders become available strictly after H1 decision close; M15 is finest evidence. OPEN gap events precede later bar extrema. A single SL/FTA hit in a previously filled bar is resolved. Both in one M15 bar remain WAIT_INTRABAR_ORDER. For a wick-touch limit, a target hit without ordered evidence might precede fill and remains WAIT; a stop-only crossing after traversing limit is ordered under an explicitly continuous within-bar path. No arbitrary TP-first/SL-first. Precise fill/exit timestamps are observation times or bounds, not invented intrabar instants.\n",
}
FILES = list(DOCS) + [
    "MACHINE_RULE_REGISTRY.csv",
    "SOURCE_CITATIONS.json",
    "GATE_1.json",
    "READINESS_POLICY.json",
    "STAGE_0_PRESERVATION.json",
]


def build(output):
    if (output / "GATE_1.json").exists():
        raise ValueError("Existing stage preserved")
    parents = original_invariance()
    output.mkdir(parents=True, exist_ok=True)
    source = read(CITATIONS)
    registry = []
    for rule, citation, definition in RULES:
        if citation not in source:
            raise ValueError("Missing primary source reference: " + citation)
        registry.append(
            {
                "rule_id": rule,
                "classification": "MACHINE_RULE_PRE_BACKTEST",
                "source_reference_id": citation,
                "source_citation_locator": "SOURCE_CITATIONS.json#" + citation,
                "definition": definition,
                "promoted_to_SOURCE_RULE": False,
                "outcome_input_used": False,
            }
        )
    write_csv(output / "MACHINE_RULE_REGISTRY.csv", registry, list(registry[0]))
    for name, body in DOCS.items():
        (output / name).write_text(body)
    (output / "SOURCE_CITATIONS.json").write_bytes(CITATIONS.read_bytes())
    save(output / "READINESS_POLICY.json", POLICY)
    save(
        output / "GATE_1.json",
        {
            "status": "PASS_DETERMINISTIC_DEFINITIONS",
            "critical_definition_UNKNOWN": 0,
            "required_observations_may_WAIT": True,
            "historical_cohort_built": False,
            "financial_outcomes_viewed": False,
            "parameters": PARAMETERS,
            "branch_priority": PRIORITY,
            "machine_rule_count": len(RULES),
            "trade_entry_allowed": False,
        },
    )
    save(
        output / "STAGE_0_PRESERVATION.json",
        {
            "current_parent_commit": "6918d82b94db52f96bc542533235fbe98be6092c",
            "original_invariance": parents,
            "main_modified": False,
            "Original_source_reference_preserved": True,
            "concepts": [
                "SFP",
                "OB",
                "Breaker",
                "STB/BTS",
                "Range",
                "FVG/IMB",
                "liquidity",
                "BOS",
                "CONF",
                "OTE",
                "PD",
                "FTA",
                "FIRST_TEST_ONLY",
                "fixed initial stop",
                "M15/H1/H4/D1",
            ],
            "new_machine_selectors_classified": True,
            "trade_entry_allowed": False,
        },
    )
    print("MACHINE_DESIGN_COMPLETE", len(RULES), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    g = parser.add_mutually_exclusive_group()
    g.add_argument("--replay-output", type=Path)
    g.add_argument("--validate-replay", type=Path)
    g.add_argument("--seal", action="store_true")
    g.add_argument("--resume-existing", action="store_true")
    a = parser.parse_args()
    if a.resume_existing:
        verify_machine(DEST)
        original_invariance()
        print("VERIFIED_RESUME MACHINE_v2_DESIGN")
    elif a.validate_replay:
        qa = qa_stage(DEST, CODE, a.validate_replay, FILES)
        (DEST / "QA_REPORT.md").write_text(
            f"# Design QA\n\nPASS: {qa['tests']} inherited/new tests and {len(FILES)} deterministic design files. Synthetic strict swing/BOS/CONF, prefix identity/future mutation, all five branch positive contracts, consumed POI, context WAIT, FTA/no future citation, TF disagreement and LIVE rejection verified. Primary source citation IDs exist; no machine selector is SOURCE. Original/current predecessor hashes unchanged. Full configured lint for new files; inherited src fatal error lint, compile and mypy pass. No historical cohort or financial run. trade_entry_allowed=false.\n"
        )
    elif a.seal:
        seal_machine(
            DEST,
            CODE,
            stage="DESIGN",
            version="v2",
            parents={
                str((ROOT / p / "freeze_manifest.json").relative_to(ROOT)): sha
                for p, sha in __import__("machine_strategy_research_io").PARENTS.items()
            },
            status="PASS_DETERMINISTIC_DEFINITIONS",
        )
    else:
        build(a.replay_output or DEST)


if __name__ == "__main__":
    main()
