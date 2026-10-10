# QA — executable profile v1 / spec v1.1

Final validation is in `data/reports/original_strategy_spec_v1_1_2026_10_11/qa`.

| Check | Result |
| --- | --- |
| All previous tests + new profile tests | 661 PASS = 611 previous + 50 new |
| Focused source profile tests | 50 PASS |
| Synthetic LONG/SHORT source-plan contracts | 12 PASS across 6 active branches |
| SOURCE_RULE unchanged | 53 exact inherited records; literal citations verified against frozen v1 |
| User resolution separation | 6 USER_RESOLUTION_PRE_BACKTEST records |
| New technical conventions | 10 TECHNICAL_NORMALIZATION_PRE_BACKTEST records |
| Source tree consistency | 37 source predicates; no PROJECT_POLICY/U/N injected |
| Causality | completed bars, known_at, dependency availability and OPEN ordering PASS |
| Prefix/future mutation, deterministic replay, BACKTEST/SHADOW parity | PASS |
| No future duration/P&L inputs | recursive rejection PASS |
| Physical identity, first test, conflicting branches | PASS; no duplicate lifecycle admission |
| Fixed SL, source FTA, Range same-zone remainder, SFP manual close | PASS |
| Builder repeatability | SHA256-identical 35 generated documents |
| Ruff + compile | PASS on 3 new scripts and new test |
| mypy production | PASS, 53 source files |
| Frozen v1/archive audit/baseline | PASS: 55 frozen v1 artifacts; 17,851 archived Git blobs include 17,728 baseline blobs |

`EXECUTABLE_PROFILE_IDENTIFIABLE=TRUE` describes the causal-evidence contract.
`EXACT_ORIGINAL_IDENTIFIABLE=FALSE`; automatic qualitative OHLC detector is not
identified. Evidence gaps are listed in REMAINING_EVIDENCE_REQUIREMENTS.md and
produce WAIT. All ALLOW plans retain `trade_entry_allowed=false`.

The existing regression suite flushes two diagnostic stdout lines after its
unittest OK summary. The verifier matches the actual summary and requires exit0;
it does not assume OK is the final byte of the log.

The exact uploaded request is preserved with original CRLF bytes. A separate
staged whitespace receipt records any findings for that input; new code and
generated documents use LF. No archived formatting is changed.

No profitability backtest, parameter search, financial comparison, production
integration or LIVE/private API operation was performed. Production canonical
40/30/30 and cost-adjusted BE are byte-identical to the archived baseline.
