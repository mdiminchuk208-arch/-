# Next task — independent review/freeze of v4.1 failure audit with source-fidelity check

State: `MACHINE_STRATEGY_V4_1_FAILURE_AUDIT_REVIEW_PENDING`.

The financial gate is frozen STOP and closed. Do not run/recover/finalize/replay historical financial execution or modify `docs/machine_strategy_v4_1_development_financial_v1/`.

Authored audit namespace: `docs/machine_strategy_v4_1_failure_audit_v1/`.
Work order: `agent_control/V4_1_FAILURE_AUDIT_REVIEW_WORK_ORDER.md`.
New mandatory evidence: `docs/machine_strategy_v4_1_failure_audit_v1/SOURCE_FIDELITY_FINDING.md`.

Review with zero historical financial engine calls:
1. Independently verify the frozen v4.1 funnel: 54 candidates /486 states /46 no-fill /8 filled /7 CLOSED /1 all-nine filled unresolved.
2. Verify that 396 `UNFILLED_RETIRED` +18 `UNFILLED_EXPIRED` correspond to44 all-nine retired +2 all-nine expired candidates, given zero mixed terminal-status cases.
3. Review causal language around entry reachability, lifecycle retirement, family composition, directional evidence and planned payoff versus realized gross edge.
4. **Mandatory source-fidelity review:** compare v4/v4.1 candidate-generation/admission semantics against the supplied methodology and prior source-evidence plan. Explicitly assess whether H1-only proposal timing and deterministic WAIT/REJECT gates over-constrained visual/contextual source concepts and caused candidate starvation. The source evidence includes `Методичка.docx` and the prior plan recording 176,365 raw geometric proposals plus the instruction not to turn qualitative concepts into hidden numeric thresholds.
5. Confirm that the methodology describes market structure and SFP across timeframes and visual/contextual OB, Breaker, liquidity and Range geometry; do not interpret 54 candidates/two years as natural strategy frequency unless independently supported.
6. Verify cost/funding conclusion: gross CLOSED aggregate is already negative before modeled costs; fees/slippage amplify rather than create the negative sign.
7. Preserve anti-overfit boundaries: no SHORT ban, H4/SFP/LONG selection, family deletion, cost rescue, RR tuning or hypothetical unresolved exit.
8. If source-fidelity mismatch is accepted, the future design gate must start from a source-faithful continuous candidate/visual-annotation layer and must pass an **opportunity-coverage gate before P&L**. Do not force trades merely to hit a count; report candidate frequency and rejection funnel first.
9. Produce independent review receipts, QA/source-causality/source-fidelity consistency evidence and exact `FAILURE_AUDIT_FREEZE_MANIFEST.json`.
10. Final independent reviewer issues exactly `MACHINE_STRATEGY_V4_1_FAILURE_AUDIT_PASS` or `MACHINE_STRATEGY_V4_1_FAILURE_AUDIT_STOP`.

Only audit PASS may open a separately named pre-outcome strategy design gate. No v4.2 implementation or historical financial test is authorized yet.

Safety: `trade_entry_allowed=false`; production NONE; no PAPER/LIVE/private exchange API/orders/platform.
