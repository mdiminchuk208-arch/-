# v4.1 one-shot development financial report

Runner: `MACHINE_STRATEGY_V4_1_DEVELOPMENT_FINANCIAL_STOP`; independent auditor: `MACHINE_STRATEGY_V4_1_DEVELOPMENT_FINANCIAL_STOP`. Final gate acceptance requires the separate serial reviews and result freeze.

First outcome commit: `e7692453c9f11fd9124dbac50596fdbbe1874b70`. External checkpoint SHA256: `7dfaa6fb20c07febdbdb4a98278ce6c92ea4d1a026499656b3c9c5ed0280d6f8`.

Exposed OKX development history [2024-10-13, 2026-10-13), BTC/ETH USDT swaps, both directions and all five preregistered families. This is not pristine OOS. All nine frozen modeled compatibility scenarios retained.

Candidates: 54; case statuses: `{"ALL_SCENARIOS_NO_FILL": 46, "CLOSED": 7, "COMPATIBILITY_DISAGREEMENT": 1}`; all scenario records: 486.

Cases with any/all-nine fill evidence: 8 / 8. Scenario terminal statuses: `{"CLOSED": 63, "UNFILLED_EXPIRED": 18, "UNFILLED_RETIRED": 396, "WAIT_INTRABAR_ORDER": 9}`.

Only all-nine CLOSED cases enter qualification statistics. Incompatible cases retain all state-level diagnostic values in the immutable raw files and ALL_SCENARIO_STATES.csv; their values never enter the qualified population.

| Metric | Base | Doubled fee/slippage |
|---|---:|---:|
| CLOSED | 7 | 7 |
| WIN | 2 | 2 |
| LOSS | 5 | 5 |
| win_rate | 0.285714 | 0.285714 |
| profit_factor_R | 0.462899 | 0.301548 |
| expectancy_R | -0.347599 | -0.574634 |
| net_R | -2.433195 | -4.022435 |
| gross_R | -0.850574 | -0.850574 |
| net_cash | -613.690876 | -1095.340404 |
| max_drawdown_R | 3.772211 | 5.047838 |
| max_consecutive_net_losses | 3 | 3 |
| wilson_95pct_lower | 0.082219 | 0.082219 |
| gross_cash | -132.710000 | -132.710000 |
| fees_cash | 361.237146 | 722.474292 |
| slippage_cash | 120.412382 | 240.824764 |
| funding_cash | 0.668652 | 0.668652 |
| net_cash | -613.690876 | -1095.340404 |
| fees_R | 1.191930 | 2.383860 |
| slippage_R | 0.397310 | 0.794620 |
| funding_R | 0.006619 | 0.006619 |

Cash is modeled USDT using retained scenario quantities. R uses each case's immutable reference P01_Q001 U. No common account equity or portfolio-return claim is made. Fees/slippage are fixed modeled per-leg assumptions; funding uses sealed actual signed rates and the conservative coherent timing witness with settlement-close proxy. Doubled costs reuse the exact same event paths.

## Preregistered checks

| Check | Runner | Auditor |
|---|---|---|
| closed_trades_min | False | False |
| coin_concentration | False | False |
| coin_direction_closed_min | False | False |
| coin_direction_net_positive | False | False |
| compatibility_agreement | False | False |
| doubled_net_positive | False | False |
| doubled_profit_factor_min | False | False |
| expectancy_positive | False | False |
| filled_unknown_exit | False | False |
| max_drawdown | True | True |
| max_loss_streak | True | True |
| net_R_positive | False | False |
| net_cash_positive | False | False |
| profit_factor_min | False | False |
| quarter_concentration | False | False |
| wilson | False | False |
| win_rate_min | False | False |

## coin_direction

| Group | CLOSED | WIN | LOSS | WR | PF R | Expectancy R | Net R | Net cash |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BTC-USDT-SWAP:SHORT | 3 | 1 | 2 | 0.333333 | 0.669432 | -0.220403 | -0.661210 | -596.024699 |
| ETH-USDT-SWAP:LONG | 1 | 1 | 0 | 1.000000 | Infinity | 0.758026 | 0.758026 | 37.438185 |
| ETH-USDT-SWAP:SHORT | 3 | 0 | 3 | 0.000000 | 0.000000 | -0.843337 | -2.530010 | -55.104361 |

## direction

| Group | CLOSED | WIN | LOSS | WR | PF R | Expectancy R | Net R | Net cash |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| LONG | 1 | 1 | 0 | 1.000000 | Infinity | 0.758026 | 0.758026 | 37.438185 |
| SHORT | 6 | 1 | 5 | 0.166667 | 0.295573 | -0.531870 | -3.191220 | -651.129061 |

## family

| Group | CLOSED | WIN | LOSS | WR | PF R | Expectancy R | Net R | Net cash |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BREAKER | 1 | 0 | 1 | 0.000000 | 0.000000 | -0.999946 | -0.999946 | -799.459771 |
| RANGE | 1 | 0 | 1 | 0.000000 | 0.000000 | -0.993845 | -0.993845 | -21.702769 |
| SFP | 2 | 1 | 1 | 0.500000 | 1.416017 | 0.111352 | 0.222703 | 16.108593 |
| STB | 3 | 1 | 2 | 0.333333 | 0.669132 | -0.220703 | -0.662108 | 191.363072 |

## product

| Group | CLOSED | WIN | LOSS | WR | PF R | Expectancy R | Net R | Net cash |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BTC-USDT-SWAP | 3 | 1 | 2 | 0.333333 | 0.669432 | -0.220403 | -0.661210 | -596.024699 |
| ETH-USDT-SWAP | 4 | 1 | 3 | 0.250000 | 0.299614 | -0.442996 | -1.771984 | -17.666176 |

## setup_tf

| Group | CLOSED | WIN | LOSS | WR | PF R | Expectancy R | Net R | Net cash |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 240 | 1 | 1 | 0 | 1.000000 | Infinity | 1.339016 | 1.339016 | 565.348672 |
| 60 | 6 | 1 | 5 | 0.166667 | 0.167326 | -0.628702 | -3.772211 | -1179.039548 |

## Concentration and uncertainty

```json
{
  "calendar_quarters_R": {
    "2025-Q2": "-1.0002810299892828295983172693702297038748751008535042184348155251490885098534067",
    "2025-Q4": "-0.99994578038158630325295040749809706808899007173355371020941106521260354806370237",
    "2026-Q1": "-0.23581912720708811977011410921419774478601191112652868962469578653743997314020955",
    "2026-Q2": "-1.0008429896884652348001530779072366453122543905436587078977720797305085993570463",
    "2026-Q3": "0.80369405798782199828254137084985539170490425957717026115404241058580010824141799"
  },
  "coins_R": {
    "BTC-USDT-SWAP": "-0.6612104415293641369714734730476482842508702386685650542601968831947319209318719",
    "ETH-USDT-SWAP": "-1.771984427749236352167520020092257486106356976011510010752455162849108601241075"
  },
  "largest_calendar_quarter_profit_share": "1",
  "largest_coin_profit_share": null
}
```

Compatibility disagreements: 1. Frozen conservative unknown counter: 9; actual filled-with-unknown states from stored fill evidence: 9.

Runner/auditor frozen field filled_unknown_exit_states conservatively includes all four unknown statuses even without fill evidence; unchanged

Intervals from observer; never a pre-entry filter. Lower/upper bin inventories bound duration uncertainty; no exact fill/exit time asserted.

Holding lower bins: `{"1h-4h": 2, "4h-1d": 3, "<1h": 2}`; upper bins: `{"1h-4h": 3, "4h-1d": 3, "<1h": 1}`.

## All cases

ALL_CASES.csv lists every candidate chronologically; ALL_SCENARIO_STATES.csv lists every one of its nine states, including all rejects, unfilled and unknown states. Raw catalog/case JSONL preserves complete geometry, context, lifecycle and funding witness. No direction, family, interval or grid has been removed based on outcomes.

## Limits

- historical tick/lot epochs unverified; nine synthetic compatibility grids are modeled stress
- historical ordinary account-applicable OKX fee is unverified; frozen model costs used
- mark/queue/fill reality and API publication delay are unverified
- development history is exposed and is not pristine OOS

No parameter search, financial replay, new robustness experiment or OOS evaluation was performed by this renderer. PAPER/LIVE/private API/orders remain prohibited; trade_entry_allowed=false; production candidate NONE.

## Execution classification detail

54 candidates produced8 cases with fill evidence in all nine scenarios:7 all-nine CLOSED and1 filled unresolved case. All nine states of that unresolved ETH LONG RANGE H1 case are WAIT_INTRABAR_ORDER. The frozen coarse case label records COMPATIBILITY_DISAGREEMENT=1; there are0 mixed terminal-status cases across grids. Preserve its recorded checks and all unknown states; do not interpret the coarse counter as proof of differing grid terminal statuses or impute an exit. Detailed case ID and every scenario state are in CACHED_EXECUTION_CLASSIFICATION_NOTES.json.

All five families remain enabled in the frozen specification. OB emitted0 candidates and0 CLOSED in this fixed window; BTC LONG emitted9 candidates and0 CLOSED. Missing positive/cohort evidence is not an excluded losing subgroup. The candidate-cohort inventory in the classification notes includes every emitted case. No financial result or strategy rule was changed by this clarification.
