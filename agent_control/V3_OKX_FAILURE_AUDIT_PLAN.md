# MACHINE_STRATEGY_v3 OKX — Causal Failure Audit Plan

Purpose: convert the first frozen negative OKX result into a causal, pre-redesign diagnosis. This is not an optimization pass and must not generate a second v3 financial run.

## Frozen result to explain
- 99 unique reference candidates across BTC-USDT-SWAP and ETH-USDT-SWAP.
- 20 all-nine-scenario CLOSED, 70 all-scenario NO_FILL, 9 eligibility disagreements.
- Known CLOSED base: WR 50%, PF_R 0.278459, expectancy -0.309356R, net -6.187114R.
- Doubled costs: WR 45%, PF_R 0.162663, net -9.243979R.
- Gross edge is already negative before costs.
- CLOSED>=200 is impossible for this fixed catalog even under the optimistic 99/99 bound.

## Priority 1 — admission scarcity
Use existing raw formation/funnel logs only. Separate repeated retry counters from unique opportunity origins.

For BTC and ETH trace the path:
RAW family -> pending formation -> context/direction gate -> refinement/BOS -> origin-bound POI -> structural-approach filter -> reservation -> candidate.

Quantify unique-origin attrition at each gate, especially:
- WAIT_ORIGIN_BOUND_REFINEMENT_POI (~16k per product retry events);
- WAIT_REFINEMENT_BOS_CONF (~14k per product retry events);
- REJECT_NON_SMOOTH_STRUCTURAL_APPROACH (~5.2k per product retry events);
- WAIT_H1_M15_DIRECTION (~1.7k per product retry events);
- WAIT_NO_CONFIRMED_STATE (~1k per product retry events).

Do not interpret retry counts as unique signals. Produce unique-origin / unique-physical-setup counts and transition rates.

Questions to answer causally:
1. Are multiple filters duplicating the same concept and collapsing the sample?
2. Is refinement/BOS confirmation arriving too late relative to the actual move?
3. Does origin-bound POI logic create structurally unreachable entries?
4. Does the non-smooth-approach filter reject most otherwise valid contexts?
5. Are reservations/sibling rules materially suppressing independent candidates, or are they a minor effect?

## Priority 2 — no-fill mechanics
There are 70 all-scenario no-fill cases. For every case classify the exact mechanical reason using already frozen candidate geometry and future price path, without changing any rule:
- price never retraced to entry;
- entry became stale after move;
- stop/target geometry displaced entry too far;
- reservation/expiry window too short;
- quantization family materially changed eligibility;
- conflict/sibling handling prevented otherwise reachable fill.

Report distributions by family, direction, coin, TF/context, entry-distance-to-market, ATR-normalized entry distance, time-to-expiry and maximum favorable/adverse excursion before expiry.

## Priority 3 — negative gross edge on CLOSED cases
For all 20 all-scenario CLOSED cases and diagnostic disagreement closures:
- decompose gross_R, cost_R, funding_R, net_R;
- compare entry quality, stop distance, nearest FTA, target geometry, realized MFE/MAE, holding time and exit mechanism;
- identify whether losses come primarily from bad directional selection, late entry, too-tight stop, too-near target, regime mismatch, or structural invalidation after entry;
- preserve LONG/SHORT symmetry and do not select a direction based on this sample.

Do not treat tiny H4/BREAKER or cash-only positive slices as production rules.

## Priority 4 — nine eligibility disagreements
For each disagreement produce an exact scenario table:
- reference candidate geometry;
- all nine price-grid x lot/min scenarios;
- eligibility/fill/closure state;
- economic rejection reason;
- whether the disagreement is caused by price grid, lot/minimum, risk denominator, nearest FTA or order construction.

Determine whether disagreement indicates a compatibility-model artifact or a genuine strategy fragility. Do not impute winners/losses for unresolved cases.

## Priority 5 — causal redesign hypotheses
After the audit, output a ranked set of hypotheses for a new version. Each hypothesis must:
- point to a frozen failure mechanism;
- specify which rule family would change;
- state the expected causal effect (more valid candidates, better entry quality, improved payoff, reduced no-fill, etc.);
- identify the main overfit risk;
- define what must be preregistered before the new version sees financial outcomes.

Do NOT choose numeric thresholds from the failed P&L. Prefer structural changes with interpretable causality over parameter sweeps.

Potential hypothesis classes to evaluate, not automatically adopt:
- simplify duplicated confirmation/refinement gates;
- allow earlier causal confirmation where current BOS/refinement is systematically late;
- redesign origin-bound POI reachability while preserving no-lookahead;
- replace binary non-smooth-approach rejection with a preregistered structural quality model only if failure evidence supports it;
- revise entry geometry/expiry mechanics to reduce systematic no-fill without chasing price;
- revise stop/FTA construction if gross losses are driven by asymmetric payoff geometry;
- add regime-conditioned admission only if the failure audit shows a causal market-regime split with adequate independent support.

## Required outputs
Create immutable namespace `docs/machine_strategy_v3_okx_failure_audit_v1/` with at least:
- FAILURE_AUDIT_REPORT.md
- ADMISSION_FUNNEL_CAUSAL.json
- NO_FILL_DIAGNOSTICS.json
- CLOSED_EDGE_DECOMPOSITION.json
- ELIGIBILITY_DISAGREEMENTS.json
- REDESIGN_HYPOTHESES.json
- QA_REPORT.md
- INDEPENDENT_REVIEW.md
- freeze_manifest.json

## Workflow
Serial-first.
1. strategy_explorer: read-only causal formation/funnel analysis.
2. execution_auditor: no-fill and disagreement mechanics.
3. backtest_reviewer or statistics_robustness_analyst: closed-case decomposition and dependence caveats.
4. final_independent_reviewer: freeze diagnosis.
Root is the only writer.

After the diagnosis freeze, if the evidence supports actionable causal changes, automatically open a separately named new strategy-design version (v3.1 or v4) before any new financial evaluation. Do not ask the user for routine approval.

No new v3 financial run. No OOS/PAPER/LIVE/private API/orders/platform work. `trade_entry_allowed=false`.
