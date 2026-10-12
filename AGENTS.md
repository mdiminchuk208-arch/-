# Crypto Bot Autonomous Agent Rules

## Mission
Build the strongest statistically validated machine-trading strategy possible from the existing Crypto Bot research while preserving every frozen historical result. The goal is not to manufacture a profitable backtest; the goal is to discover and validate a positive edge that survives realistic costs, robustness checks, and independent validation.

## Frozen baseline
Start from frozen workflow commit `ba65e91c2b1675f48e80ac785bb3adf89d17bb0b`.
Never rewrite or delete frozen Original, v2, v2.1, v2.2, evidence, metadata, robustness, or comparative artifacts.

Known development verdicts:
- v2: FAIL
- v2.1: FAIL
- v2.2: FAIL
- current production candidate: NONE
- paper/live: OFF

## Required workflow
1. Read `agent_control/OBJECTIVE.md`, `CURRENT_STATE.md`, and `NEXT_TASK.md` before work.
2. Perform failure audit before proposing a new strategy version.
3. Separate diagnosis from design.
4. Any new strategy version must be fully specified and frozen before viewing its financial result.
5. Run deterministic QA, no-lookahead, prefix/future-mutation checks, and reproducibility checks before accepting a result.
6. Do not select a production candidate without robustness plus independent OOS/forward validation.
7. Paper trading requires separate qualification and does not inherit historical CLOSED counts.
8. Real trading remains disabled until explicit user authorization.

## Multi-agent operating model
The configured project team contains specialized roles. Do not launch every role mechanically. For each gate, select the smallest competent team, usually 4-8 specialists plus independent review.

Core strategy roles:
- `strategy_explorer`
- `strategy_designer`
- `execution_auditor`
- `backtest_reviewer`

Specialist roles:
- `market_regime_researcher`
- `historical_data_engineer`
- `tick_metadata_researcher`
- `market_microstructure_auditor`
- `backtest_engineer`
- `cost_funding_auditor`
- `statistics_robustness_analyst`
- `oos_forward_validator`
- `no_lookahead_auditor`
- `overfit_red_team`
- `final_independent_reviewer`

Dispatch rules:
- Use research/audit roles as read-only independent evidence gatherers whenever possible.
- Only one scoped writer/executor may modify implementation/data-adapter code at a time. Do not run `historical_data_engineer` and `backtest_engineer` as concurrent writers on overlapping files.
- Critical gates require at least one independent reviewer that did not author the implementation under review.
- Financial-result gates require both `statistics_robustness_analyst` and `overfit_red_team`, plus an independent final review before any qualification claim.
- OOS/forward gates require `oos_forward_validator` and `no_lookahead_auditor`.
- Historical execution-readiness work should involve `historical_data_engineer`, `tick_metadata_researcher`, `market_microstructure_auditor`, and `execution_auditor` as relevant.
- Record which agents actually ran, what each reviewed, and any disagreements in the gate artifacts or `STATUS.md`.
- Agent count is not evidence quality. Prefer independent, non-overlapping checks over duplicate opinions.

## Anti-overfit rules
Never optimize by repeatedly sweeping thresholds against the same historical sample until PF/WR looks good.
Never delete losing years, directions, branches, symbols, or setup families merely because they hurt historical P&L.
Never reuse future/OOS outcomes to redefine a pre-entry rule.
Never call a post-hoc profitable subgroup the production strategy without a new pre-outcome specification and independent validation.

Retrospective diagnostics are allowed only to identify plausible failure mechanisms. A new rule must have a market-structure/economic rationale and must be preregistered in a new version before its test result is inspected.

## Current research priority
Follow `agent_control/NEXT_TASK.md` as the authoritative current gate. The frozen v2 diagnostics and v3 design remain evidence, not permission to tune against historical P&L. Preserve symmetric LONG/SHORT reasoning unless a future pre-outcome causal specification states otherwise.

## Safety
- `trade_entry_allowed=false`
- no real orders
- no withdrawal permissions
- no private exchange secrets in repository
- no production API key changes
- no hidden assumptions presented as verified execution

## Git discipline
Work only on `machine-v3-research` unless explicitly instructed otherwise.
Do not modify `main` or frozen historical branches.
Commit coherent milestones with descriptive messages.
After each milestone update `agent_control/CURRENT_STATE.md` and `agent_control/STATUS.md`.
