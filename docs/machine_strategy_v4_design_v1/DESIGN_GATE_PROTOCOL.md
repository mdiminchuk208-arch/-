# MACHINE_STRATEGY_v4 — Design Gate Protocol

State: DESIGN_GATE_OPEN. This opens a new design task; no v4 specification, implementation or financial qualification is complete.

## Entry evidence

The v3 causal failure audit was independently reviewed, frozen and published in commit `54419daa29e7e68d6f692daee9cf2132203393ef`, manifest `9b0353dbfeabfa2768f4a1f62af820c128f98c48faad09544acee4c0547867a3`. Its six hypotheses are conditional research inputs, not adopted rules. v3 remains QUALIFICATION_STOP. All Original/v2/v3 rules, data, outcomes and frozen artifacts remain immutable.

Read `DESIGN_INPUTS.json`, the pinned failure report, provenance, evidence gaps and hypotheses. No v3 rerun is needed. The exposed OKX warmup/development history remains development data for v4; it is not pristine OOS merely because the strategy is renamed. Future untreated validation must be separately registered.

## Design scope

Produce one deterministic, causally justified v4 design before any v4 financial result is generated or viewed. Do not compare alternative entries, stops, exits or thresholds by historical P&L. Do not optimize WR/PF or select tiny favorable direction/coin/branch/time slices. No automatic deletion of SHORT or adverse cases.

Every proposed change must link to a frozen failure mechanism, its uncertainty, exact source citation if applicable, SOURCE_RULE/PROJECT_POLICY/TECHNICAL_NORMALIZATION classification, the causal rationale and the explicit decision-time fields. Source-permitted alternatives and material ambiguities remain visible; a machine choice is separately labeled policy, never promoted to SOURCE_RULE. Any source reconstruction additions belong in the new namespace, not the frozen source audit.

H00 is an observer-only prerequisite: define unique origin/physical IDs, gate exposures, first passes, repeated waits, terminal dispositions and causal snapshots. Historical aggregate retry counters cannot recover missing per-origin transitions. No replay of frozen v3 to fill those gaps.

Evaluate H01 approach semantics, H02 completed-mark/FTA lifecycle, H03 resting-entry validity/lifetime, H04 structural-versus-executable-zone contract and H05 structural payoff/anti-scalp feasibility. Each must be adopted, deferred or rejected on an explicit causal basis, never an outcome ranking. The audit does not establish that extending expiry, moving entry/FTA, weakening approach vetoes or applying an economic cutoff produces positive edge. No numeric cutoff has been selected by this opening.

Pre-entry anti-scalp decisions use valid setup/context, structural targets and full round-trip fee/slippage estimates only; LTF cannot originate the medium-term idea. Preserve structure/liquidity/FTA targets, no fixed percentage TP replacements, no realized holding-time filter. Never move to a farther FTA merely to pass economics. Stop/target/BE/exit choices require explicit source or policy provenance and no performance-based choice among source-permitted alternatives.

## Required design artifacts

- MACHINE_STRATEGY_v4_SPEC.md and deterministic decision-tree JSON/Markdown;
- rule/source/policy/technical registries, conflict/ambiguity registry and versioned v3-to-v4 change log;
- setup/context/refinement/entry/stop/target/exit/re-entry contracts, LONG/SHORT mirrors and event-time invariants;
- observer telemetry schema including gate-level denominators and known_at timestamps;
- explicit executable-zone, grid/lot, no-fill, cancellation, funding, fixed-risk-denominator and OHLC-ambiguity contracts;
- preregistration: one design, inherited qualification thresholds, outcome isolation, data exposure, separate future untouched validation plan and STOP gates;
- synthetic design-consistency, source-provenance, causality and symmetry checks, plus independent reviews;
- DESIGN_FREEZE_MANIFEST.json with all design/code/source inputs and reviewed artifacts externally pinned before implementation readiness.

This gate does not implement the historical adapter or run the strategy. After a complete reviewed design freeze, open a separately named implementation-readiness gate. Only its complete reviewed implementation freeze can establish eligibility for a separate one-shot financial validation gate. No financial run is authorized by this protocol.

## Qualification and safety

Carry forward all frozen qualification requirements unchanged: WR >=70%, CLOSED >=200, base PF >=1.20, net expectancy/net P&L >0, doubled-cost PF >=1.00 and net P&L >0, drawdown <=20R, loss streak <=10, each coin+direction >=30 CLOSED and net positive, Wilson 95% lower bound >=0.60, largest quarter/coin profit shares <=0.50/0.80, zero filled unknown exits and no critical causality/integrity failures. Reference the pinned compatibility policy for exact denominator/adverse-scenario semantics. The observed v3 WR 50% is not a replacement qualification threshold.

No OOS execution, PAPER, LIVE, private exchange API, orders, credentials or platform work. `trade_entry_allowed=false`. Hooks remain inactive. Synthetic tick grids/current metadata/cost and mark proxies are explicit assumptions, not verified historical exchange epochs.

## Workflow and STOP

Use ECC runtime and project roles serially: strategy_designer for the one design after this published audit; execution_auditor for executable contracts and symmetry; backtest_reviewer for causality/source consistency/anti-overfit; final_independent_reviewer for design freeze. Root is sole writer; at most one specialist plus root. Add a narrow source specialist only for a concrete evidence gap.

PASS requires deterministic complete contracts, traceable provenance, successful synthetic QA, independent acceptance and an externally pinned design manifest. If a material ambiguity cannot be made into a transparent causal policy without a source contradiction, record NOT_IDENTIFIABLE/STOP with exact evidence and the smallest external blocker. Do not silently invent source authority or ask for routine parameter approval.
