# First frozen OKX development validation

Decision: **MACHINE_STRATEGY_V3_QUALIFICATION_STOP**. Compatibility implementation READY remains frozen at `e57b15091bda7e994133e586d7ab851d32011c5d`; it makes no financial qualification claim.

The full frozen history contains 210,240 native M15 bars and 4,380 signed funding settlements. All 99 selected candidates are retained: BTC 50, ETH 49. Twenty are CLOSED under all nine scenarios, 70 have no fill, and nine have eligibility disagreement. Twenty-one have a fill under at least one scenario. There are no filled-unknown exits; the nine retained eligibility disagreements independently force STOP. Even all 99 candidates closing would not reach the preregistered minimum of 200.

The following metrics describe only the known all-nine-CLOSED subset. They are not the full unresolved catalog's WR/PF or a portfolio return.

| Metric | Base modeled costs | Doubled fees/slippage |
|---|---:|---:|
| CLOSED | 20 | 20 |
| WIN / LOSS | 10 / 10 | 9 / 11 |
| WR | 50% | 45% |
| PF, fixed R ledger | 0.278459 | 0.162663 |
| PF, USDT cash | 0.371523 | 0.208388 |
| Expectancy / Avg R | -0.309356 | -0.462199 |
| Net R | -6.187114 | -9.243979 |
| Gross USDT | -1632.621000 | -1628.823000 |
| Fees USDT | 1330.770609 | 2665.692539 |
| Slippage USDT | 443.590203 | 888.564180 |
| Signed funding USDT | -13.515747 | -13.538767 |
| Net USDT | -3420.497559 | -5196.618486 |
| Case-ledger DD R | 6.187114 | 9.243979 |
| Max net loss streak | 4 | 4 |

Base gross edge is already negative before costs. Fees and slippage worsen it. All four coin/direction groups have negative net R and only 4–8 CLOSED cases each; ETH SHORT cash is positive but R is negative, so it fails the frozen two-unit check. The Wilson lower bound is 0.2993, and positive-quarter share is 0.7979 versus the limit 0.50. Passing DD/streak cannot rescue sample/edge/slice failures. One case selects a different worst scenario in the doubled column; its aggregate gross/funding changes are expected under the frozen per-column rule.

Full exact values are in FINANCIAL_RESULT.json; all cases are in ALL_CASES.csv and per-scenario JSONL, qualifying CLOSED cases in CLOSED_CASES.csv, disagreements in UNRESOLVED_CASES.json, and reference counters in FUNNEL.json. WAIT/rejection counters may include repeated retries, not unique opportunities. Holding-time interval distributions are in both result columns. No duration-based retrospective removal occurred.

Execution grids are finite synthetic assumptions, fees are modeled 6bp + 2bp per leg, and funding uses the declared M15 settlement-close proxy. Neither exact historical venue filters, actual account fees/marks, liquidity/latency nor portfolio capital are proved. This is development data; no OOS/PAPER/LIVE or production candidate exists. `trade_entry_allowed=false`.

Large original audit JSON files remain in the workspace. Their exact bytes are published as gzip in `packed/`, with raw/compressed hashes in CATALOG_AUDIT_STORAGE.json. On a fresh checkout run `python scripts/pack_okx_v3_catalog_audits_v1.py --restore` before externally pinned checkpoint/READY verification. Fresh restore and idempotence were verified without modifying original workspace artifacts.
