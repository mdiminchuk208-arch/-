# Next Task — MACHINE_STRATEGY_v3 Pre-Outcome Design Freeze

The failure audit is frozen and the v3 design gate is open. Do NOT run a new financial backtest yet.

## Objective
Design a new deterministic `MACHINE_STRATEGY_v3` architecture that addresses the failure mechanisms identified by the frozen audit without mining historical P&L, selecting profitable subgroups, or simply adding another outcome-fitted filter to v2.x.

This task is DESIGN + SPECIFICATION + NON-FINANCIAL QA only. The full v3 financial result must remain unknown until the specification and implementation are frozen.

## Mandatory evidence basis
Use only the frozen audit and pre-outcome/source/market-structure evidence. Treat the following as diagnostic constraints, not directly selectable rules:
- v2 SHORT has negative gross before costs across all years and both symbols; do not simply disable SHORT.
- aggregate gross edge is erased by modeled costs.
- nearest structural FTA frequently lies inside 1 planned R.
- tiny structural stop denominators can create unstable R and huge cost/R ratios.
- no LONG/SHORT sign/accounting bug was found.
- intrabar timing, historical tick epochs, actual spread/funding, portfolio/margin behavior and untouched OOS remain unresolved.

## Required multi-agent workflow
Actually launch and use the configured roles where possible:
1. `strategy_explorer`: map frozen audit findings to causal design requirements. No rule proposal based only on P&L ranking.
2. `execution_auditor`: define executable price/risk/cost invariants and symmetry requirements for LONG/SHORT.
3. `strategy_designer`: propose the v3 architecture and deterministic rules.
4. `backtest_reviewer`: independently challenge leakage, post-hoc selection, hidden tuning, non-causal fields, asymmetry and unverifiable execution assumptions before freeze.

Record each role's conclusions under the v3 design namespace.

## v3 architecture questions that must be resolved before freeze

### A. Direction and market-state architecture
Create a causal, deterministic market-state/context model that is applied symmetrically to LONG and SHORT.
- It may use only information known at decision time.
- It must not be `LONG allowed / SHORT disabled` because v2 historical P&L said so.
- If directional admission differs, it must arise from the same mirrored market-state logic.
- Define trend/range/transition/uncertain handling explicitly enough for deterministic implementation.
- Preserve M15/H1/H4/D1 as the executable timeframe universe unless a new timeframe is justified independently of outcome data.

### B. Structural risk normalization
Redesign stop/risk handling so valid structure cannot produce economically meaningless or numerically unstable denominators.
- Preserve structural invalidation semantics.
- Add any minimum executable risk/tick/volatility/cost floor only if it is derived from causal market/execution mechanics, not optimized from historical winners/losses.
- Define units, rounding, epsilon, ATR/volatility calculation, timestamp availability and LONG/SHORT mirroring.
- Cases that cannot be represented honestly with available historical execution metadata must WAIT/REJECT explicitly; do not fabricate precision.

### C. Entry/target/FTA economics
Redesign the relationship between entry, structural stop, nearest opposing liquidity/FTA and modeled transaction cost.
- Do not move a target farther merely to manufacture R:R.
- If the nearest causally valid target cannot support an economically executable trade after declared costs, define a deterministic pre-entry WAIT/REJECT condition based on the architecture.
- Any threshold or safety margin must have an explicit ex-ante rationale and must NOT be chosen by scanning historical PF/WR/Net R.
- Define target priority and what happens when multiple FTAs/POIs exist.

### D. Setup-family architecture
Review SFP, OB, Breaker, STB and Range as machine setup families.
- Do not retain or remove a family because its historical subgroup P&L was good/bad.
- Keep a family only if its signal, confirmation, entry, invalidation and target semantics can be made causal, deterministic and economically coherent.
- Branch-specific mechanics are allowed when structurally justified, but must be specified before results.

### E. Execution and intrabar ambiguity
Define exact rules for:
- limit/market entry representation;
- unfilled and gap-invalidated setups;
- same-bar entry/stop/target ambiguity;
- `WAIT_INTRABAR_ORDER` or conservative alternative;
- tick/price rounding when historical tick proof is unavailable;
- fees, slippage and funding treatment;
- one physical idea / duplicate prevention;
- first-test/re-entry semantics.

Never convert unknown OHLC intrabar order into invented elapsed-time precision.

### F. Portfolio-independent base
Keep v3 base-strategy evaluation independent of project-level sizing overlays.
Do NOT yet apply:
- 2–5% score sizing;
- max open risk 6%;
- leverage policy;
- correlation portfolio rules;
- exchange fallback logic.
These remain later overlays after a base strategy qualifies.

## Data-exposure / validation protocol
Before freeze, create a machine-readable dataset exposure inventory covering every period/symbol/timeframe previously used for:
- source research;
- v2/v2.1/v2.2 development;
- old 2026 fitted development work;
- any audit diagnostics.

Then preregister:
1. development dataset(s), already contaminated and usable only for design diagnostics;
2. robustness partitions;
3. a genuinely untouched chronological OOS/forward dataset, if one exists;
4. objective STOP if no pristine OOS can be established.

Do not label reused 2026 data OOS merely because v3 has not yet been run on it.

## Freeze requirements
Create an immutable namespace such as:
`docs/machine_strategy_v3_design/`

Required artifacts:
- `MACHINE_STRATEGY_V3_SPEC.md`
- `MACHINE_STRATEGY_V3_SPEC.json`
- `CAUSAL_HYPOTHESES.md`
- `RULE_PROVENANCE.json`
- `DIRECTION_AND_REGIME_SPEC.json`
- `RISK_NORMALIZATION_SPEC.json`
- `ENTRY_TARGET_EXECUTION_SPEC.json`
- `SETUP_FAMILY_SPEC.json`
- `DATA_EXPOSURE_INVENTORY.json`
- `VALIDATION_PROTOCOL.md`
- `INDEPENDENT_REVIEW.md`
- `QA_REPORT.md`
- `freeze_manifest.json`

Every machine rule must be tagged with provenance such as:
- `SOURCE_DERIVED`
- `MACHINE_RULE_PRE_OUTCOME`
- `EXECUTION_SAFETY_RULE`
- `UNRESOLVED_WAIT_RULE`

No rule may be tagged or justified as `historically profitable subgroup`.

## Non-financial implementation QA
Implementation may be created in this task only if needed to prove determinism and causal executability, but DO NOT produce aggregate financial outcome metrics.

Required checks before freeze:
- deterministic replay;
- prefix/future mutation / no-lookahead;
- LONG/SHORT reflection/symmetry tests where mathematically applicable;
- timestamp known-at validation;
- unit/rounding/cost identity tests;
- intrabar ambiguity tests;
- frozen namespace invariance;
- no reads from outcome/P&L columns inside admission logic;
- static/lint/type/compile tests.

If a test would reveal the aggregate v3 P&L, do not run it until after the pre-outcome freeze commit.

## Decision gate
At the end of this task, freeze and publish the exact v3 design and implementation state.
Update `agent_control/STATUS.md` and `CURRENT_STATE.md` with:
- v3 design freeze commit SHA;
- spec/manifest hashes;
- actual agents used;
- unresolved execution/data risks;
- exact untouched-OOS plan;
- whether the system is ready for the first v3 financial backtest.

Do NOT run that financial backtest in this task.
Do NOT enable PAPER or LIVE.
`trade_entry_allowed=false` remains invariant.
