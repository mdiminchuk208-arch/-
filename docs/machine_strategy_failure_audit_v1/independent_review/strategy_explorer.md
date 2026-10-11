# Independent strategy explorer

Actual agent: `/root/strategy_explorer`; cloud collaboration, `gpt-6-sol`, high reasoning. Applied the repository role instructions from `.codex/agents/strategy-explorer.toml`. Read-only analysis of frozen artifacts; no strategy rule, new cohort, financial execution, or exchange call.

## Findings

- v2 SHORT is negative before modeled costs across every covered year and both symbols. The canonical Decimal audit totals are gross -22.717114R and net -75.062863R for 105 CLOSED. LONG has gross +73.709148R and net +27.073083R for 118 CLOSED. Rounded preliminary agent sums were superseded by the independently verified canonical artifact calculations.
- Losses concentrate in 2024 and RANGE, but extend beyond them. SHORT RANGE has 20 CLOSED, approximately -16.804 gross / -52.021 net R; non-RANGE SHORT has 85 CLOSED and approximately -23.042 net R. ETH SHORT RANGE contributes approximately -39.11 net R across 12 cases; 2024 SHORT approximately -49.31 net R across 45 cases. These classifications overlap and do not establish independent causal replication.
- Execution selects a different geometry distribution from the full candidate population. v2 SHORT has 347 cases: 105 CLOSED, 109 unfilled/expired and 133 gap-invalidated. LONG has 414: 118 CLOSED, 144 unfilled/expired, 147 gap-invalidated and five unresolved. Median planned target/stop is 0.481206R for CLOSED SHORT, versus approximately 2.119R for unfilled SHORT. CLOSED LONG median is 0.496659R. No outcome is assigned to an unfilled order.
- Target/stop geometry and exit mix matter: 89/118 LONG and 78/105 SHORT CLOSED plans have a nearest FTA below 1R. Fixed-stop and FTA frequencies differ by direction. Strong LONG aggregate gross also depends on a few extreme winners; deleting the best three diagnostically would exceed the observed net gain. These leave-out calculations are influence checks, never proposed exclusions.
- v2.1 and v2.2 are nested descendants of v2 with unchanged shared outcomes, not independent experiments or evidence that their thresholds are optimal.

## Evidence and limits

Inputs: frozen `docs/machine_strategy_v2_result/{ALL_CASE_EXECUTIONS,CLOSED_TRADES}.jsonl.gz`, v2 pre-outcome cases, and equivalent v2.1/v2.2 namespaces. Canonical corroboration: `LONG_SHORT_ASYMMETRY.json`, `EXIT_REASON_BREAKDOWN.json`, `EXTREME_R_AUDIT.json`, and `CASE_DIAGNOSTICS.csv` in this audit namespace.

Calendar, symbol, branch, TF, frozen context/PD/OTE and exit classifications cross-classify the same cases. Realized gross jointly reflects signal selection, fill selection, exits and the market path; causal attribution to market structure alone is not identifiable from these saved results. D1 context IDs are not a frozen direction/alignment or market-regime label. No independent OOS conclusion or LONG-only production recommendation follows.

Conclusion: the failure mechanisms justify a separate causal pre-outcome design investigation after this audit is frozen. Keep both directions and all frozen evidence; no threshold or subgroup is selected here. `trade_entry_allowed=false`.
