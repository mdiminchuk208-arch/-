# Corrected Bybit source trade-case validation

Primary: **0 unique FILLED + CLOSED trade cases**. Full strict replay: 0 CLOSED, 0 FILLED, 0 OPEN, 0 PENDING censored. **MAX CLOSED = 0 under the registered corrected machine policy**; target50 was not reached.

**BACKTEST/SHADOW only; trade_entry_allowed=false; LIVE/private API/orders prohibited.**

The five newly uploaded files are Windows shortcuts, byte-identical to the old archive links, not PDF contents. Eight available DOCX originals and their diagrams were read previously; available Range, D/S, Smart Money Trader2 and Liquidity texts were checked for this correction. Missing SW5/9/11/12/22 contents cannot be newly read or promoted from SECONDARY_SOURCE to SOURCE_RULE. This result validates a declared machine interpretation of available originals and explicit user requirements, not the complete discretionary methodology. [Attachment receipt](data/source_materials/correction_2026_10_09/attachment_receipt.json).

Pre-outcome registration: `363fa01`; corrected implementation/tests and deterministic choices: `2b09acb`, both published before any corrected outcomes. Final NEW-POI proof guard/parallel runner commit `742fda0` also precedes outcomes; the interrupted no-outcome pass and exact code snapshot are retained under `data/reports/source_cases_bybit_2026_10_09_pre_qa`. [Correction protocol](SOURCE_CORRECTION_PROTOCOL.md) and [source registry](SOURCE_RECONSTRUCTION_2026_10_09.md) distinguish evidence and interpretations. No outcome-based threshold, symbol, period, entry, stop or exit selection occurred. Frozen studies were not rerun.

## Corrected behavior and sample semantics

STRICT_CONSERVATIVE mappings:15/5,60/5,60/15,240/5,240/15. 240/60 belongs only to ANY_TF research. Each unique physical opportunity is deduplicated before outcomes; first available READY wins, deterministic ties prefer higherHTF/lowerLTF/fixed symbol priority. Alias/mapping duplicates do not manufacture sample size. Each retained READY receives an independent case with reference1170USDT and planned risk23.4USDT(2%), including base entry/SL friction. It is independent of other symbols, account occupancy, compounding and3x portfolio budget. Case PnLs are descriptive sums of independent exposures, never shared-capital NAV or portfolio drawdown.

Primary consists of first50 CLOSED cases by actual filled entry interval start, with READY/tie order. OPEN cases are excluded from CLOSED metrics and explicitly right-censored, not forced closed. All later cases/closures remain in the full artifacts. This complete40-series dataset (993575 candles,10symbols, native5/15/60/240m) was checked against saved SHA/count/identity/order/alignment/OHLC requirements. All January–September2026 history is already-inspected DEVELOPMENT, never OOS.

Range now requires a fresh causal external typed POI actually interacted with on deviation, a separate native close accepting inside the Range, and a later boundary retest. SFP alone cannot create RANGE_POI. D/S is a separate last opposite move detector, permits multiple candles and no FVG, requires forming-move old liquidity raid/full absorption/structure/freshness/P-D. Failed OB no longer becomes D/S. Order Flow stores HH/HL or LL/LH sequence, reclaimed structural liquidity/key test, subsequent body break, separate CONF and fresh global HTF destination. Global destination test, including smaller native candle observation, invalidates it; trend alone cannot authorize READY.

Local quote/SL choices were fixed by type: OB proximal boundary/full wick extreme; Breaker proximal boundary/conservative breaking-sweep extreme; STB/BTS midpoint/full manipulation wick; D/S midpoint/full last move wick; FVG midpoint/reaction raid within an independently proven context. All entries require reaction raid→body BOS→new structure→distinct CONF→fresh local POI. Liquidity role evidence spans the whole active structural leg and adverse equal pools, including pools beyond SL. Cause/destination/against/unrelated roles are recorded.

Non-Range full FTA is a declared interpretation; Range80% inside opposite boundary plus optional20% to a pre-entry external FTA, otherwise remainder inside. Original technical SL throughout, no automatic BE. This additive policy does not change frozen canonical40/30/30 or cost-adjusted BE afterTP1. Fee.06% and slippage.02% per side are project assumptions. Funding/spread/ticks are unavailable. Stop-first OHLC ambiguity, entry-bar favorable target CLOSE proof and adverse gap fills remain conservative. Intrabar fill times are5m intervals known at close. MAE shown is a post-entry-bar OHLC upper bound; entry-bar extrema may precede unknown fill and are excluded. Entry-bar closures therefore have N/A true MAE.

## OLD7 / flawed fc61f3513 / corrected cases

OLD7 spans six independent mapping accounts; fc61f35 used one sequential account with flawed source rules. Neither is a matched causal performance comparison. The previous13-trade report remains [verbatim](data/reports/source_bybit_fc61f35_intermediate/report.md), with its original artifacts.

| Metric | OLD7 descriptive | fc61f35 intermediate13 | Corrected primary cases |
|---|---:|---:|---:|
| CLOSED | 7 | 13 | 0 |
| Wins | 2 | 2 | 0 |
| Losses | 5 | 11 | 0 |
| WinRate | 0.285714 | 0.153846 | N/A |
| ProfitFactor | 0.179384 | 0.140376 | N/A |
| Expectancy | -13.742184 | -15.416649 | N/A |
| AvgR | -0.585909 | -0.712264 | N/A |
| MedianR | -1.000000 | -1.000000 | N/A |
| NetPnL | -96.195286 | -200.416434 | 0 |
| Fees | 17.744520 | 39.332695 | 0 |
| Slippage | 5.914837 | 13.110893 | 0 |
| MaxDrawdown | N/A | 237.295751 | N/A |

N/A case drawdown reflects independent cases, not absent losses. Portfolio NAV drawdown appears separately.

When CLOSED=0, zero net PnL reflects no trades; WR/PF/expectancy/R are undefined and cannot be compared as an improvement over either old sample.

### OLD7 preserved research ledger

| Symbol | Direction | Mapping | Entry interval | Exit | NetPnL | R |
|---|---|---|---|---|---:|---:|
| BNBUSDT | LONG | 240/5 | 2026-03-31T09:55:00+00:00 | 2026-04-02T03:05:00+00:00 | -23.400000 | -1.000000 |
| BTCUSDT | SHORT | 240/60 | 2026-04-29T09:00:00+00:00 | 2026-05-01T13:00:00+00:00 | 11.165866 | 0.477174 |
| AVAXUSDT | LONG | 60/15 | 2026-05-12T14:15:00+00:00 | 2026-05-12T14:45:00+00:00 | -23.400000 | -1.000000 |
| BNBUSDT | LONG | 240/15 | 2026-09-10T12:30:00+00:00 | 2026-09-10T13:00:00+00:00 | -23.400000 | -1.000000 |
| XRPUSDT | SHORT | 15/5 | 2026-09-19T05:25:00+00:00 | 2026-09-21T01:25:00+00:00 | 9.862166 | 0.421460 |
| XRPUSDT | SHORT | 60/5 | 2026-09-19T05:25:00+00:00 | 2026-09-21T08:40:00+00:00 | -23.400000 | -1.000000 |
| AVAXUSDT | SHORT | 240/60 | 2026-09-20T11:00:00+00:00 | 2026-09-20T15:00:00+00:00 | -23.623317 | -1.000000 |

## Re-audit of all13 intermediate closures

| Symbol | Direction | Mapping | Old HTF/local POI | Old result/PnL | Classification | Reasons at old cutoff |
|---|---|---|---|---|---|---|
| ETHUSDT | SHORT | 60/15 | BTS/BTS | LOSS -23.400000 | FALSE_POSITIVE_IMPLEMENTATION | NO_CAUSALLY_ACTIVE_GLOBAL_ORDER_FLOW_AT_OLD_READY; OLD_UNIVERSAL_ENTRY_DIFFERS_FROM_REGISTERED_POI_POLICY |
| LINKUSDT | SHORT | 60/5 | RANGE_POI/ORDER_BLOCK | LOSS -22.932000 | FALSE_POSITIVE_IMPLEMENTATION | RANGE_WITHOUT_REQUIRED_CAUSAL_EXTERNAL_POI; NO_CAUSALLY_ACTIVE_GLOBAL_ORDER_FLOW_AT_OLD_READY |
| DOGEUSDT | LONG | 15/5 | STB/STB | LOSS -22.473360 | FALSE_POSITIVE_IMPLEMENTATION | NO_CAUSALLY_ACTIVE_GLOBAL_ORDER_FLOW_AT_OLD_READY; OLD_UNIVERSAL_ENTRY_DIFFERS_FROM_REGISTERED_POI_POLICY |
| BTCUSDT | LONG | 15/5 | RANGE_POI/STB | LOSS -22.023893 | FALSE_POSITIVE_IMPLEMENTATION | RANGE_WITHOUT_REQUIRED_CAUSAL_EXTERNAL_POI; NO_CAUSALLY_ACTIVE_GLOBAL_ORDER_FLOW_AT_OLD_READY; OLD_UNIVERSAL_ENTRY_DIFFERS_FROM_REGISTERED_POI_POLICY |
| DOGEUSDT | LONG | 240/15 | STB/FVG | LOSS -21.583415 | FALSE_POSITIVE_IMPLEMENTATION | NO_CAUSALLY_ACTIVE_GLOBAL_ORDER_FLOW_AT_OLD_READY; OLD_UNIVERSAL_ENTRY_DIFFERS_FROM_REGISTERED_POI_POLICY |
| XRPUSDT | SHORT | 240/15 | SUPPLY/FVG | LOSS -21.151747 | FALSE_POSITIVE_IMPLEMENTATION | NO_CAUSALLY_ACTIVE_GLOBAL_ORDER_FLOW_AT_OLD_READY; OLD_UNIVERSAL_ENTRY_DIFFERS_FROM_REGISTERED_POI_POLICY; OLD_DS_WAS_FVG_DEPENDENT_FAILED_OB_FALLBACK |
| DOGEUSDT | LONG | 240/60 | RANGE_POI/STB | LOSS -20.728712 | FALSE_POSITIVE_IMPLEMENTATION | 240_60_OUTSIDE_STRICT_CONSERVATIVE_SCOPE; RANGE_WITHOUT_REQUIRED_CAUSAL_EXTERNAL_POI; NO_CAUSALLY_ACTIVE_GLOBAL_ORDER_FLOW_AT_OLD_READY; OLD_UNIVERSAL_ENTRY_DIFFERS_FROM_REGISTERED_POI_POLICY |
| LTCUSDT | LONG | 60/15 | RANGE_POI/DEMAND | LOSS -20.314137 | FALSE_POSITIVE_IMPLEMENTATION | RANGE_WITHOUT_REQUIRED_CAUSAL_EXTERNAL_POI; NO_CAUSALLY_ACTIVE_GLOBAL_ORDER_FLOW_AT_OLD_READY; OLD_UNIVERSAL_ENTRY_DIFFERS_FROM_REGISTERED_POI_POLICY |
| LINKUSDT | LONG | 240/15 | RANGE_POI/FVG | LOSS -19.907855 | FALSE_POSITIVE_IMPLEMENTATION | RANGE_WITHOUT_REQUIRED_CAUSAL_EXTERNAL_POI; NO_CAUSALLY_ACTIVE_GLOBAL_ORDER_FLOW_AT_OLD_READY; OLD_UNIVERSAL_ENTRY_DIFFERS_FROM_REGISTERED_POI_POLICY |
| LINKUSDT | SHORT | 240/15 | SUPPLY/BTS | LOSS -19.509698 | FALSE_POSITIVE_IMPLEMENTATION | NO_CAUSALLY_ACTIVE_GLOBAL_ORDER_FLOW_AT_OLD_READY; OLD_UNIVERSAL_ENTRY_DIFFERS_FROM_REGISTERED_POI_POLICY; OLD_DS_WAS_FVG_DEPENDENT_FAILED_OB_FALLBACK |
| LINKUSDT | SHORT | 240/15 | SUPPLY/BTS | LOSS -19.119504 | FALSE_POSITIVE_IMPLEMENTATION | NO_CAUSALLY_ACTIVE_GLOBAL_ORDER_FLOW_AT_OLD_READY; OLD_UNIVERSAL_ENTRY_DIFFERS_FROM_REGISTERED_POI_POLICY; OLD_DS_WAS_FVG_DEPENDENT_FAILED_OB_FALLBACK |
| XRPUSDT | LONG | 240/5 | STB/FVG | WIN 3.722067 | FALSE_POSITIVE_IMPLEMENTATION | NO_CAUSALLY_ACTIVE_GLOBAL_ORDER_FLOW_AT_OLD_READY; OLD_UNIVERSAL_ENTRY_DIFFERS_FROM_REGISTERED_POI_POLICY |
| XRPUSDT | LONG | 15/5 | DEMAND/FVG | WIN 29.005818 | FALSE_POSITIVE_IMPLEMENTATION | NO_CAUSALLY_ACTIVE_GLOBAL_ORDER_FLOW_AT_OLD_READY; OLD_UNIVERSAL_ENTRY_DIFFERS_FROM_REGISTERED_POI_POLICY; OLD_DS_WAS_FVG_DEPENDENT_FAILED_OB_FALLBACK |

Audit counts: `{'FALSE_POSITIVE_IMPLEMENTATION': 13}`. Exact old entries remaining eligible under corrected machine policy: 0. This does not declare the discretionary opportunities unprofitable or impossible; it tests the old executable entry/stop/scope/evidence contract. Every per-symbol intermediate_audit.json retains complete old ledger rows and independent current-prefix snapshots at old READY and entry start. Missing originals remain uncertain.

### Five former RANGE losses: causal external POI

| Signal | Mapping | External POI existed and interacted before old deviation? | Verdict |
|---|---|---|---|
| 9c181eee25ee9e39d8b5a523 | 60/5 | NO causal qualifying external POI | FALSE_POSITIVE_IMPLEMENTATION |
| ca98f11190187b5877332b3a | 15/5 | NO causal qualifying external POI | FALSE_POSITIVE_IMPLEMENTATION |
| 25faa78ab0a2eea4d4c48c20 | 240/60 | NO causal qualifying external POI | FALSE_POSITIVE_IMPLEMENTATION |
| d5cd448d6c02f037d76c9d35 | 60/15 | NO causal qualifying external POI | FALSE_POSITIVE_IMPLEMENTATION |
| b58c6bbb565b806e85fa6798 | 240/15 | NO causal qualifying external POI | FALSE_POSITIVE_IMPLEMENTATION |

These are failures of the declared executable contract. Alternative source-allowed entry/SL choices differing from the new fixed choices are not by themselves evidence that the discretionary trade was invalid. Unmodelled qualitative POIs and missing original chapters prevent a literal source verdict. The external POI audit uses reconstructed qualified typed OB/Breaker/D-S/STB-BTS zones; standalone FVG is not admitted as external Range permission in this conservative interpretation.


## Primary case ledger

| # | Symbol | L/S | Mapping | Setup | HTF/local POI | READY | Fill interval start | Entry | SL | Targets | Exit | Result | NetPnL | R | Fees | Slippage | Post-entry-bar MAE R bound |
|---:|---|---|---|---|---|---|---|---:|---:|---|---|---|---:|---:|---:|---:|---:|

No source case actually filled; no50 outcomes or execution-based performance estimate exists.

### Every READY order: independent real-bar no-fill evidence

| Symbol | Mapping | Setup | READY | Limit | SL | Targets | Cancel known at | Reason | Prior5m bars | Raw limit touched while active? |
|---|---|---|---|---:|---:|---|---|---|---:|---|
| DOGEUSDT | 15/5 | HTF_POI_LTF_RAID_BOS_CONF | 2026-08-17T16:15:00+00:00 | 0.070085 | 0.070050 | [0.0706] | 2026-08-17T16:45:00+00:00 | CANCEL_CONFIRMED_LTF_STRUCTURE_BROKEN | 6 | NO |
| BTCUSDT | 60/5 | RANGE_DEVIATION | 2026-09-06T23:00:00+00:00 | 79672.900000 | 79604.600000 | [80188.09999999999, 80787.0] | 2026-09-06T23:10:00+00:00 | CANCEL_OPEN_OUTSIDE_SL_FTA | 2 | NO |
| BTCUSDT | 15/5 | HTF_POI_LTF_RAID_BOS_CONF | 2026-09-14T13:50:00+00:00 | 77524.750000 | 77429.500000 | [78542.2] | 2026-09-14T14:20:00+00:00 | CANCEL_FLOW_DESTINATION_TESTED | 6 | NO |

All actual5m OHLC bars while each limit existed are retained in [pending_order_audit.json](data/reports/source_case_qa_2026_10_09/pending_order_audit.json). None touched its entry quote before cancellation; account occupancy/budget did not reject any case. This proves the observed maximum under the fixed model and coverage, not an exhaustive discretionary maximum.


## Primary breakdown (including zero groups)

### direction

| Group | CLOSED | Wins | Losses | WR | PF | Expectancy | AvgR | MedianR | NetPnL |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| LONG | 0 | 0 | 0 | N/A | N/A | N/A | N/A | N/A | 0 |
| SHORT | 0 | 0 | 0 | N/A | N/A | N/A | N/A | N/A | 0 |

### local_poi_type

| Group | CLOSED | Wins | Losses | WR | PF | Expectancy | AvgR | MedianR | NetPnL |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ORDER_BLOCK | 0 | 0 | 0 | N/A | N/A | N/A | N/A | N/A | 0 |
| BREAKER | 0 | 0 | 0 | N/A | N/A | N/A | N/A | N/A | 0 |
| DEMAND | 0 | 0 | 0 | N/A | N/A | N/A | N/A | N/A | 0 |
| SUPPLY | 0 | 0 | 0 | N/A | N/A | N/A | N/A | N/A | 0 |
| STB | 0 | 0 | 0 | N/A | N/A | N/A | N/A | N/A | 0 |
| BTS | 0 | 0 | 0 | N/A | N/A | N/A | N/A | N/A | 0 |
| FVG | 0 | 0 | 0 | N/A | N/A | N/A | N/A | N/A | 0 |
| RANGE_POI | 0 | 0 | 0 | N/A | N/A | N/A | N/A | N/A | 0 |

### mapping

| Group | CLOSED | Wins | Losses | WR | PF | Expectancy | AvgR | MedianR | NetPnL |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 15/5 | 0 | 0 | 0 | N/A | N/A | N/A | N/A | N/A | 0 |
| 60/5 | 0 | 0 | 0 | N/A | N/A | N/A | N/A | N/A | 0 |
| 60/15 | 0 | 0 | 0 | N/A | N/A | N/A | N/A | N/A | 0 |
| 240/5 | 0 | 0 | 0 | N/A | N/A | N/A | N/A | N/A | 0 |
| 240/15 | 0 | 0 | 0 | N/A | N/A | N/A | N/A | N/A | 0 |

### poi_type

| Group | CLOSED | Wins | Losses | WR | PF | Expectancy | AvgR | MedianR | NetPnL |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ORDER_BLOCK | 0 | 0 | 0 | N/A | N/A | N/A | N/A | N/A | 0 |
| BREAKER | 0 | 0 | 0 | N/A | N/A | N/A | N/A | N/A | 0 |
| DEMAND | 0 | 0 | 0 | N/A | N/A | N/A | N/A | N/A | 0 |
| SUPPLY | 0 | 0 | 0 | N/A | N/A | N/A | N/A | N/A | 0 |
| STB | 0 | 0 | 0 | N/A | N/A | N/A | N/A | N/A | 0 |
| BTS | 0 | 0 | 0 | N/A | N/A | N/A | N/A | N/A | 0 |
| FVG | 0 | 0 | 0 | N/A | N/A | N/A | N/A | N/A | 0 |
| RANGE_POI | 0 | 0 | 0 | N/A | N/A | N/A | N/A | N/A | 0 |

### setup_type

| Group | CLOSED | Wins | Losses | WR | PF | Expectancy | AvgR | MedianR | NetPnL |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| HTF_POI_LTF_RAID_BOS_CONF | 0 | 0 | 0 | N/A | N/A | N/A | N/A | N/A | 0 |
| RANGE_DEVIATION | 0 | 0 | 0 | N/A | N/A | N/A | N/A | N/A | 0 |

### symbol

| Group | CLOSED | Wins | Losses | WR | PF | Expectancy | AvgR | MedianR | NetPnL |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BTCUSDT | 0 | 0 | 0 | N/A | N/A | N/A | N/A | N/A | 0 |
| ETHUSDT | 0 | 0 | 0 | N/A | N/A | N/A | N/A | N/A | 0 |
| SOLUSDT | 0 | 0 | 0 | N/A | N/A | N/A | N/A | N/A | 0 |
| XRPUSDT | 0 | 0 | 0 | N/A | N/A | N/A | N/A | N/A | 0 |
| BNBUSDT | 0 | 0 | 0 | N/A | N/A | N/A | N/A | N/A | 0 |
| DOGEUSDT | 0 | 0 | 0 | N/A | N/A | N/A | N/A | N/A | 0 |
| ADAUSDT | 0 | 0 | 0 | N/A | N/A | N/A | N/A | N/A | 0 |
| LINKUSDT | 0 | 0 | 0 | N/A | N/A | N/A | N/A | N/A | 0 |
| AVAXUSDT | 0 | 0 | 0 | N/A | N/A | N/A | N/A | N/A | 0 |
| LTCUSDT | 0 | 0 | 0 | N/A | N/A | N/A | N/A | N/A | 0 |

## Complete-case funnel and censoring

Strict mapped setup stages (ANY_TF excluded):

```json
{
  "setups": 26795,
  "qualified_structure": 6285,
  "liquidity_passed": 85,
  "poi_passed": 85,
  "READY": 3,
  "order_flow_passed": 5,
  "pd_passed": 3
}
```

```json
{
  "CLOSED": 0,
  "FILLED": 0,
  "OPEN_CENSORED": 0,
  "PENDING_CENSORED": 0,
  "READY": 3,
  "admission_decisions": {
    "CANCEL_CONFIRMED_LTF_STRUCTURE_BROKEN": 1,
    "CANCEL_FLOW_DESTINATION_TESTED": 1,
    "CANCEL_OPEN_OUTSIDE_SL_FTA": 1,
    "VIRTUAL_LIMIT_PENDING": 3
  },
  "cohort": "BYBIT_2026_ALREADY_INSPECTED_DEVELOPMENT",
  "duplicates": 0,
  "max_post_entry_bar_MAE_R": null,
  "primary_selection": "FIRST_50_FILLED_CLOSED_BY_ENTRY_CHRONOLOGY",
  "scope": "strict",
  "shared_capital": false,
  "source_certification": "DECLARED_MACHINE_POLICY_MISSING_ORIGINAL_ADVANCED_PRO_PDFS",
  "status": "COMPLETE_FULL_NATIVE_DATASET",
  "trade_entry_allowed": false,
  "unique_opportunities": 3,
  "validation_mode": "SOURCE_TRADE_CASE_VALIDATION"
}
```

Full strict CLOSED metrics, beyond the primary first50:

```json
{
  "AvgHoldingSeconds": null,
  "AvgLoss": null,
  "AvgR": null,
  "AvgWin": null,
  "BE": 0,
  "CLOSED": 0,
  "Expectancy": null,
  "Fees": 0,
  "GrossAfterSlippageBeforeFees": 0,
  "GrossPnL": 0,
  "Losses": 0,
  "MaxDrawdown": null,
  "MaxDrawdownFraction": null,
  "MaxLosingStreak": 0,
  "MaxWinningStreak": 0,
  "MedianR": null,
  "NetPnL": 0,
  "PayoffRatio": null,
  "ProfitFactor": null,
  "Slippage": 0,
  "WinRate": null,
  "Wins": 0
}
```

## Separate PORTFOLIO_SIMULATION

Same deduplicated strict signals, one pending/open account, current-equity2% risk and3x virtual notional cap. This is a capital/occupancy experiment, excluded from primary strategy-quality cases. Its raw detector funnel covers all6 detection mappings, including ANY_TF; entries/CLOSED/censoring and portfolio PnL/NAV use strict signals only. The strict setup-stage funnel above separates that scope.

```json
{
  "funnel": {
    "CLOSED": 0,
    "READY": 3,
    "entries": 0,
    "liquidity_passed": 85,
    "open_censored": 0,
    "order_flow_passed": 5,
    "pd_passed": 3,
    "pending_censored": 0,
    "poi_passed": 85,
    "qualified_structure": 6497,
    "setups": 27798,
    "source_contexts": 67568
  },
  "primary": {
    "AvgHoldingSeconds": null,
    "AvgLoss": null,
    "AvgR": null,
    "AvgWin": null,
    "BE": 0,
    "CLOSED": 0,
    "Expectancy": null,
    "Fees": 0,
    "GrossAfterSlippageBeforeFees": 0,
    "GrossPnL": 0,
    "Losses": 0,
    "MaxDrawdown": 0.0,
    "MaxDrawdownFraction": 0.0,
    "MaxLosingStreak": 0,
    "MaxWinningStreak": 0,
    "MedianR": null,
    "NetPnL": 0,
    "PayoffRatio": null,
    "ProfitFactor": null,
    "Slippage": 0,
    "WinRate": null,
    "Wins": 0
  },
  "admission_decisions": {
    "CANCEL_CONFIRMED_LTF_STRUCTURE_BROKEN": 1,
    "CANCEL_FLOW_DESTINATION_TESTED": 1,
    "CANCEL_OPEN_OUTSIDE_SL_FTA": 1,
    "VIRTUAL_LIMIT_PENDING": 3
  },
  "final_cash": 1170.0,
  "final_equity": 1170.0
}
```

## Separate ANY_TF 240/60 research

Excluded from the strict primary sample and portfolio. Independent development cases only.

```json
{
  "READY": 0,
  "unique_opportunities": 0,
  "FILLED": 0,
  "CLOSED": 0,
  "OPEN_CENSORED": 0,
  "all_closed": {
    "AvgHoldingSeconds": null,
    "AvgLoss": null,
    "AvgR": null,
    "AvgWin": null,
    "BE": 0,
    "CLOSED": 0,
    "Expectancy": null,
    "Fees": 0,
    "GrossAfterSlippageBeforeFees": 0,
    "GrossPnL": 0,
    "Losses": 0,
    "MaxDrawdown": null,
    "MaxDrawdownFraction": null,
    "MaxLosingStreak": 0,
    "MaxWinningStreak": 0,
    "MedianR": null,
    "NetPnL": 0,
    "PayoffRatio": null,
    "ProfitFactor": null,
    "Slippage": 0,
    "WinRate": null,
    "Wins": 0
  }
}
```

## QA and reproduction

Run: `python scripts/run_source_cases_bybit.py --output data/reports/source_cases_bybit_2026_10_09`. Existing segments/results require `--resume-existing`: exact implementation/policy/input/artifact set and hashes or fail closed. Completed verification returns VERIFIED_COMPLETE_NO_MUTATION.

QA receipts/logs: `data/reports/source_case_qa_2026_10_09`. Compileall, targeted/full suite, RuffE9/F, mypy, real native prefix and future mutation, source evidence timestamps, scope/dedup/risk/cost ledger and safety checks are recorded there. Existing source scripts/tests/canonical strategy and prior historical artifacts are retained. No frozen research rerun. Original PDF reading/source certification remains blocked by actual shortcut uploads.

Additional real BTC nonempty READY prefix at2026-09-14T13:50UTC:96,088 native candles, 2exact READY signals,1exact cancellation,1,131exact global-flow generations and159exact Range audits. Changing the next8native candles in each of4TFs leaves all earlier source state/decisions unchanged. The cutoff is the latest emitted BTC READY timestamp, selected from source metadata rather than PnL. The registered March1 prefix also passes (14,293candles/172flows/20Range audits). These validate the implemented causal machine policy, not completeness of missing source methodology.

No robust-edge or LIVE-readiness conclusion follows from this already-inspected development sample. Numerical Range impulse/midpoint, exact-only equal pools and missing Advanced/Pro text limit source completeness.
