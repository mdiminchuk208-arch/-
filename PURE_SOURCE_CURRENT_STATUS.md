# PURE SOURCE — authoritative current status

**Status date:** 2026-10-17  
**Current rebuild stage:** Stage 20 — Causal Claim Binding
**Base:** Stage 19 merge `3a4cf35d400efc352432a8cdc64d473fa50b4116`

> This file is the current continuation entrypoint for PURE SOURCE strategy work.
> Historical `README.md`, `CONTINUATION_STATUS.md`, old Bybit replays, source-permitted physical cases and earlier PnL reports remain preserved evidence, but they are **not SOURCE truth** and must not be used to resolve current SOURCE ambiguity.

## Current verdict

The PURE SOURCE baseline is **`NOT_IDENTIFIABLE`** as one unique executable financial strategy.

This remains intentionally fail-closed:

- `trade_entry_allowed=false`;
- no financial PURE SOURCE backtest is authorized yet;
- no PAPER/LIVE/private exchange API/orders;
- no PROJECT overlays in SOURCE baseline;
- historical PnL must not choose among SOURCE-permitted alternatives;
- qualitative SOURCE terms must not be replaced by optimized numeric proxies.

Stage 15 established deterministic diagnostic replay. Stage 16 froze the identifiability frontier and priority-1 Methodichka evidence. Stage 17 created stable, non-ranked identities for finite SOURCE alternatives. Stage 18 now defines an auditable causal contract for genuinely qualitative SOURCE facts.

## Hard semantic boundaries

`OBJECT VALIDITY != TRADE ELIGIBILITY` remains a hard invariant.

Stage 17 added:

`EXACT SOURCE ALTERNATIVE != TRADE ELIGIBILITY`.

Stage 18 adds:

`QUALITATIVE PASS/FAIL != UNTRACEABLE OPINION`.

A qualitative PASS or FAIL must have a frozen semantic ID, observed closed-data window, `known_at`, subject IDs, source references, annotation method, provenance reference, rationale code and canonical evidence ID. UNKNOWN deliberately has no provenance/evidence ID and cannot masquerade as confirmed evidence.

## Source details confirmed from the priority-1 Methodichka

The extracted `19.clean.txt` is tied by the frozen archive manifest to `Криптология/Методичка.docx`, so it outranks SW modules when reconstructing the rules.

It confirms:

- OB: last candle before imbalance; movement updates structure; OB sweeps a low/high or wick; body should be large and wicks small. The exact numeric meaning of “large/small” is not supplied.
- Breaker: impulsively pierced OB that swept a high/low, is pierced by imbalance and is followed by CHOCH.
- Range: no structure inside; first high after the impulse and first low define it; reaction from 0.5 validates it; setup follows deviation, return, zone test and CHOCH.
- OTE: source levels include 0.5 / 0.62 / 0.705 / 0.79; OTE is explicitly 0.705–0.79. Correct impulse-anchor selection remains a provenance problem.
- SFP: original pattern is three candles, may have a fourth confirmation candle, applies on all timeframes and requires liquidity context to be swept.

These findings narrow the frontier but do **not** yet make one unique executable financial baseline.

## Stage 17 branch registry

Finite explicit alternatives are represented separately without precedence:

- `OB_DIRECT_ENTRY`;
- `OB_EXECUTION_PATH`;
- `OB_STOP_ANCHOR`;
- `BREAKER_STOP_ANCHOR`;
- `STB_BTS_ENTRY`;
- `FTA_FIXATION`;
- `SFP_ATR_PERIOD`.

Exact branches such as STB/BTS midpoint 0.5, full FTA fixation or ATR 14 remain conditional on valid causal parent evidence and are not defaults.

Files:

- `config/pure_source_branch_registry_v2.json`
- `src/crypto_bot/strategy/pure_source_branch_registry_v2.py`
- `docs/PURE_SOURCE_ENGINE_STAGE17_BRANCH_REGISTRY.md`

## Stage 18 qualitative provenance

A frozen semantic catalog now covers qualitative claims used or required around:

- OB aggressive impulse;
- OB large body / small wicks;
- Breaker fast/whole impulse;
- Breaker continuous movement without OB trading;
- source-qualified impulse segmentation for Range/OTE;
- Range strong impulse, midpoint reaction and absence of internal structure;
- STB/BTS full manipulation engulf;
- Demand/Supply last-movement segmentation;
- EQH/EQL substructure and reasonable tilt;
- SFP liquidity context.

A `SourceQualitativeClaim` is causal only when `known_at >= observation_end_at`. PASS/FAIL requires auditable provenance. UNKNOWN cannot carry a fake evidence ID.

Stage 18 allows only explicit annotation transports:

- `HUMAN_SOURCE_ANNOTATION`;
- `CURATED_SOURCE_DATASET_ANNOTATION`.

It explicitly forbids automatic numeric proxy inference and rejects ranking/proxy/outcome metadata such as score, confidence, probability, preferred, WR, PF, expectancy and PnL.

Stage 18 also preserves scope: object-formation evidence cannot silently be relabelled as trade context or vice versa. In particular, SFP liquidity context is typed as `TRADE_CONTEXT` rather than structural SFP formation.

Files:

- `config/pure_source_qualitative_semantics_v2.json`
- `src/crypto_bot/strategy/source_qualitative_provenance_v2.py`
- `tests/test_source_qualitative_provenance_v2.py`
- `docs/PURE_SOURCE_ENGINE_STAGE18_QUALITATIVE_PROVENANCE.md`

## Current blocking frontier

### 1. Qualitative consumers are not yet fully migrated

Existing OB/Breaker, Range/STB, Demand/Supply and liquidity modules already use a lightweight legacy `QualitativeEvidence` shape. Stage 18 defines the stronger authoritative claim contract but does **not** silently change all consumers in the same step.

Next migration must make those consumers accept audited Stage 18 claims (or remain UNKNOWN) while preserving all existing SOURCE definitions and causality tests.

### 2. Exact geometry / lifecycle remains unspecified in places

Still unresolved where SOURCE does not supply an exact coordinate/lifecycle, including:

- exact quote inside OB/new POI variants;
- exact beyond-anchor stop buffer;
- some protective-stop geometry;
- partial FTA fraction and remainder lifecycle;
- some re-entry identity/eligibility details.

Stage 17 preserves these as properties of specific alternatives rather than choosing a winner.

### 3. Context selection remains unresolved

Where several source-valid timeframes, liquidity pools or identities coexist, no PROJECT ranking/filter may choose among them. Meaningful/adverse liquidity selection and exact re-entry identity remain separate source-provenance problems where not explicitly defined.

## Source authority

Use this order only:

1. Методичка
2. SW5
3. SW9
4. SW11
5. SW12
6. SW22
7. other confirmed ORIGINAL SOURCE materials
8. SOURCE Rule Registry

Repository code is infrastructure / historical evidence, not SOURCE truth.

The verified source set remains frozen under `docs/source_freeze_v1/`, `data/source_materials/primary_pdf_2026_10_09/` and `data/source_materials/cryptology_2026_10_09/`.

## Next permitted work

Migrate qualitative consumers incrementally onto Stage 18 claims. The first safe target is OB/Breaker because its current legacy qualitative requirements already map cleanly to Stage 18 semantics. Each migration must:

- preserve current SOURCE formation rules;
- preserve closed-candle timing;
- reject future-known annotations;
- retain full claim provenance;
- remain `trade_entry_allowed=false`;
- not add PROJECT policy or numeric thresholds.

A financial PURE SOURCE backtest remains blocked until required object provenance, execution geometry and exit lifecycle are sufficiently identified.

Machine-readable frontier: `config/pure_source_identifiability_frontier_v2.json`.
Stage 16: `docs/PURE_SOURCE_ENGINE_STAGE16_IDENTIFIABILITY_FRONTIER.md`.
Stage 17: `docs/PURE_SOURCE_ENGINE_STAGE17_BRANCH_REGISTRY.md`.
Stage 18: `docs/PURE_SOURCE_ENGINE_STAGE18_QUALITATIVE_PROVENANCE.md`.

## Stage19 source reconstruction checkpoint

Base: Stage18 merge `61d6693a993eb28b4d40b58baa4073566cae01b4` (PR21). Full priority1Methodichka coverage now records47rule/concept records,171text paragraphs and31distinct figures/41references. Primary/secondary comparison and source conflict registry retain exact citations and priority. See `docs/PURE_SOURCE_ENGINE_STAGE19_RULE_LEDGER.md` and `docs/pure_source_stage19_ledger_v1/`.

The illustrated Range path is clarified as return/CHOCH before pre-break-OB retest, with opposite-boundary target; it remains one scenario. Conditional LONG OTE level orientation is visually known, while anchors and unshown SHORT remain unresolved. SFP body engulf is illustrated, not universally imposed. No runtime SOURCE rule or market object behavior changes in this stage.

Next safe work: actual closed-parent/window binding and first-ingestion timing for Stage18annotation claims, then incremental qualified consumers. Missing evidence stays UNKNOWN. Allfinancial/PAPER/LIVE/privateAPI permissions and trade_entry_allowed remain false; NOT_IDENTIFIABLE remains the verdict.

## Stage20 causal claim binding checkpoint

`SourceClaimJournal` now binds Stage18 annotations to real closed candle windows, actual causal parents, content-hashed witness bytes and first accepted caller replay time. Missing/conflicting evidence remains UNKNOWN. Append-only closed data, parent identity/lifecycle, exact newly_closed and monotonic clocks prevent accepted history from being rewritten in a journal.

This is infrastructure, not a claim of historical annotation truth/authorship/blindness or authenticated arrival. Full typed claim/scope/window/provenance must survive consumer integration; the legacy projection alone is insufficient. Production consumers remain unchanged. See `docs/PURE_SOURCE_ENGINE_STAGE20_CAUSAL_CLAIM_BINDING.md`.

Next safe work: typed, provenance-retaining consumer adapters, separately audited against priority1 definitions; do not promote stricter legacy intersections to universal SOURCE rules. Market annotation content and unresolved execution geometry remain SOURCE blockers. NOT_IDENTIFIABLE and all financial/trading permissions false.
