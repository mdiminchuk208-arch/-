# Independent backtest reviewer

Actual agent: `/root/backtest_reviewer`; cloud collaboration, `gpt-6-sol`, high reasoning. Applied `.codex/agents/backtest-reviewer.toml`. Reviewed frozen inputs, new pure diagnostic code/tests and generated audit outputs without editing or rerunning historical execution.

## Independent checks

- Recomputed all 498 reported direction/year/month/symbol/branch/TF/context/status and exit groups directly from frozen executions: zero count, gross, fee, slippage or net mismatches.
- Independently reclassified all 761 base cases with the already-frozen v2.1/v2.2 rule formulas: included/excluded counts 373+388 and 238+523, with zero overlap or partition mismatches. The nearest v2.2 ratio to its frozen 1R boundary is approximately 5.7e-6 away; float boundary noise does not explain that cohort.
- Confirmed 6/4/4 same-bar timing findings and 5/2/1 unresolved cases, all LONG. Independently checked all saved execution chronology: no fill before decision, observation before fill, consumption before observation, exit before fill or exit knowledge before exit.
- Verified 14 frozen machine namespaces, predecessor invariance, pre-outcome/result commit ancestry and unchanged nested outcomes. v2.1/v2.2 have 83/39 CLOSED and reuse earlier cases; they are dependent development evidence.
- Reviewed full QA logs initially showing 957 tests, Ruff and mypy PASS. Additional guard tests and final QA are recorded in `QA_REPORT.md`; the final review receipt covers the final code and output hashes.

## Findings requiring closure before seal

The first review returned a conditional PASS with these corrections: actually retain independent review files before claiming them; verify `ALL_TRADES` as the filled partition as well as `CLOSED_TRADES`; label the same-input prefix computation as local projection determinism; broaden the outcome denylist to execution reason/timing/cost fields; check impulse end timestamp and saved execution chronology explicitly.

Parent implemented these changes without changing any frozen strategy, cohort, threshold or historical outcome. Final reviewer approval and code/generated-file hashes are required by the new seal guard and retained in `FINAL_REVIEW.json`. This document alone does not claim final approval.

## Anti-overfit and interpretation

v2.2 total net changes sign when its worst SHORT is omitted diagnostically; its LONG net changes sign when its top two gains are omitted. Neither omission is a strategy proposal. Causal signal-versus-fill/exit attribution, historical exchange realism, funding and untouched OOS/forward performance remain unresolved. Calendar/context slices are overlapping observations, not independent proof of production advantage.

Conclusion: a separate pre-outcome v3 design may be investigated only after this audit freezes. No production candidate, direction removal, fitted filter, parameter search, new financial run or trading activation is justified by the current audit. `trade_entry_allowed=false`.
