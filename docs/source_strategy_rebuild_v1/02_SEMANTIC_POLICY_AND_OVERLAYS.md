# Source Strategy Rebuild v1 — semantic policy and overlays

## Rule classes

Every executable rule must carry exactly one class:

1. `SOURCE_RULE` — directly supported by the frozen user-supplied source corpus.
2. `USER_RESOLUTION_PRE_BACKTEST` — an explicit user choice made before outcomes to select among source-permitted variants or resolve an ambiguity (U1–U6).
3. `TECHNICAL_NORMALIZATION` — a deterministic machine definition needed to make an underspecified source/user rule computable (including N11 conventions where still applicable).
4. `PROJECT_OVERLAY` — bot/exchange/risk/qualification/frequency/safety policy that is not part of the source strategy.

A user resolution, normalization or project overlay must never be presented as if the source itself specified it.

## Source corpus policy

Use the complete frozen source registry/citations in `docs/original_strategy_spec_v1_1/` plus the underlying user-supplied materials, including Methodichka and the cited SW/Smart Money documents. Do not reduce the strategy to Methodichka alone when another frozen source rule has provenance in the registry.

## Unknown semantics policy

If a source concept exists but its exact numeric meaning is missing, the engine must not silently convert it to a hard rejection.

During source-fidelity/detector stages:
- preserve the formation/candidate;
- attach `UNKNOWN_<CONCEPT>` or the existing source-evidence WAIT category;
- record the exact missing semantic/evidence;
- do not delete the opportunity from coverage telemetry;
- do not create P&L from that unresolved candidate.

Only after the normalization/evidence contract is separately frozen may that concept become deterministic PASS/FAIL in the executable detector.

`UNKNOWN`, `QUALITATIVE_REQUIRED`, `OBJECTIVE_FAIL`, and `EVIDENCE_COMPLETE` are distinct. Never convert UNKNOWN into FAIL.

## Rule-following code, not discretionary chart judgment

The target implementation is rule-following causal code. Images/diagrams in the source are evidence for understanding rules, not a production requirement to ask a vision model to guess trades.

Where a frozen SOURCE_RULE is objectively expressible from OHLC/metadata, implement it directly. Where the source remains genuinely qualitative, preserve explicit evidence requirements/UNKNOWN rather than inventing a classifier or hidden threshold.

## Timeframe policy

Source truth is fractal: structure works across timeframes and SFP is source-valid across timeframes.

Preserve user resolution U4:
- scan M15/H1/H4/D1;
- D1 global context;
- H4 local/higher context;
- H1 primary medium-term analysis;
- M15 refinement/confirmation and supported setups;
- no mandatory universal all-TF alignment;
- no M1/M5 in the currently frozen executable profile.

This must **not** become an H1/H4-only setup detector. M15 source formations remain visible. A M15 branch that requires a strictly lower refinement TF may WAIT for unavailable lower-TF refinement, but that is coverage/evidence state, not proof that the source formation never existed.

## Preserve U1–U6

The rebuild must import the exact pre-outcome user resolutions from `ORIGINAL_STRATEGY_SPEC_v1_1.md` rather than silently replacing them:
- U1 `FULL_CONTEXTUAL_FTA_EXIT` (Range 80/20 same-zone variant as frozen);
- U2 fixed initial protective stops by family;
- U3 entry-branch choices for OB/SFP/Range/STB/Breaker;
- U4 timeframe roles above;
- U5 adverse liquidity WAIT/revalidation policy;
- U6 FIRST_TEST_ONLY re-entry identity.

These remain user resolutions, not source rules.

## Preserve N11 provenance

N11_ENTRY/TARGET/STOP_TICK/ATR_SMA14/BODY_TF/IDENTITY/BATCH/EVIDENCE/EVENTS/SOURCE_SCOPE are explicit machine conventions. Reuse them only with their original provenance labels and only when they do not create source-fidelity starvation. Stage 2 must test their coverage impact before money is evaluated.

## User frequency requirement — PROJECT_OVERLAY

The user requires a practical strategy with frequent opportunities and set a sanity expectation of roughly at least one actionable setup opportunity per day per coin.

Before any P&L, run an outcome-blind coverage gate reporting:
- raw source formations per coin/year/TF/family;
- evidence-complete/source-decision-ready setups;
- actionable setup plans after U1–U6/N11 semantics;
- every drop/WAIT reason and count.

Project sanity target: `>=365 actionable setup opportunities / coin-year` across the active timeframe universe.

This is not a source claim and never authorizes fake trades. If the detector remains at tens of opportunities per year, result is `SOURCE_FIDELITY_STOP` and the source/evidence implementation must be repaired before profitability testing.

## Project overlays after source decision

Only after a source/user-resolved setup exists may project overlays apply:
- OKX execution compatibility model;
- fee/slippage/funding assumptions;
- anti-scalp/cost viability where retained by project policy;
- account/risk/portfolio limits;
- financial qualification target WR >=70% and robustness thresholds;
- PAPER/LIVE safety gates.

A PROJECT_OVERLAY must not decide whether a historical SOURCE formation exists.

## Prohibited shortcuts

- no outcome-derived tuning before source detector freeze;
- no family/direction deletion based on old financial results;
- no arbitrary cooldown/expiry copied from old engines;
- no hidden thresholds for qualitative source words;
- no financial test until source-fidelity/coverage and execution-plan semantics pass.
