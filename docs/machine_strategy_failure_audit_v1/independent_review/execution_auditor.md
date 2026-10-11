# Independent execution auditor

Actual agent: `/root/execution_auditor`; cloud collaboration, `gpt-6-sol`, high reasoning. Applied `.codex/agents/execution-auditor.toml`. Read-only inspection of frozen planning, execution and accounting, without private API access or historical financial rerun.

## Findings

- All 345 CLOSED version records match signed gross, actual fill-to-stop risk, 6 bp fees per entry/exit leg, 2 bp slippage per leg and net ex funding. No direction sign or saved cost identity defect was found. Funding remains unavailable and null, not asserted zero. Frozen planning/execution direction predicates show no obvious LONG/SHORT sign defect; bounded checks do not prove all exchange paths.
- A timing evidence defect affects wick-fill followed by same-bar stop: `fill_at=exit_at=bar.end`, with point `exit_time_bounds`, despite OHLC supporting only an intrabar interval. Counts are six v2 cases (five SHORT, one LONG), four v2.1, and four v2.2; descendants repeat inherited cases. This does not change the saved P&L identity. Recorded zero holding time is an observation convention, not exact elapsed time. The frozen implementation is preserved.
- All unresolved intrabar cases are LONG: 5/2/1. Resolved-only directional results therefore retain asymmetric censoring. Their unknown P&L must not be replaced with zero or inferred retrospectively.
- SHORT case `ede81fd2453984e72a532c1e1b4f0a3385d426073829b6d222ecbe518e16a5d3` has entry/fill 3121.5, stop 3121.8300312183 and initial price risk 0.3300312183, about 1.057 bp. Gross is -1R; fees 11.3504353861635R, slippage 3.7834784620545R, net -16.1339138482180R. The relative epsilon contributes only 0.0000312183; the narrow entry-anchor gap produces the denominator. This one inherited case contributes approximately 62.9% of v2.2 SHORT costs and 50.4% of its net loss.
- Tight denominators occur in LONG too. LONG winner `fbca59e5e39cb013027a2dcc30668bfbaab6891bbaa20ecd36b351fa12b346ae` has about 1.626 bp risk, gross +33.361584R, costs 9.869720R and net +23.491864R. LONG loser `82947a4dc7f77cf501abd1697bef3fa2845efc1edb8875e04995e9cbda4424a7` has about 1.692 bp risk and approximately -10.458R net. Notional/risk is a mathematical normalization ratio, not verified account leverage or an executable portfolio result.

## Transformation contract used by parent QA

For a positive affine reflection `p -> C-p`, swap LONG/SHORT and reflect OHLC as open'=C-open, high'=C-low, low'=C-high, close'=C-close. Compare event order, signed gross and transformation-aware prices. Price-proportional cost totals need not match under reflection; their exact transformed formula must match instead. Relative epsilon is likewise not invariant under reflection. Positive price scaling above the epsilon floor preserves normalized gross, costs and net.

Parent retained synthetic coverage for 13 execution scenarios and five planning branches in `tests/test_machine_strategy_failure_symmetry.py`. These tests use artificial bars, not a new historical run. Static evidence: `scripts/machine_strategy_v2_core.py`, `scripts/machine_strategy_v2_execution.py`; saved case IDs and prices are in `EXTREME_R_AUDIT.json`.

Unresolved realism: historical tick epochs/rounding, bid-ask spread, funding, shared margin and account sizing. Do not attribute all directional differences to market structure or claim exchange-equivalent execution. `trade_entry_allowed=false`.
