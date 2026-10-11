# ORIGINAL v1.1 first financial backtest

Первый frozen result: **ZERO_EXPOSURE_SOURCE_EVIDENCE_BLOCKED**. Это не доказательство нулевого edge: нет ни одного evidence-complete case. Missing annotation не означает отсутствие setup.

PRE-OUTCOME commit: `008b80d97cf008e14af94d4271c12188257a926f`. Strategy: `43e9d7addcd427650ff856dd1fa99f78ee5c06f7`.
Strategy freeze SHA256: `dca962ff1f829887d0787a6329112e77f4ce714023bee85f666ed37843f2ecbb`.
Exact trading interval UTC: 2023-01-01T00:00:00+00:00 — 2025-12-05T23:30:00+00:00. BTCUSDT/ETHUSDT; M15/H1/H4/D1. Warm-up2022 сохранён отдельно, trading interval не расширен.

## Funnel

| Stage | Count |
| --- | ---: |
| RAW_CANDIDATES | 176365 |
| EVIDENCE_COMPLETE | 0 |
| SOURCE_PASS | 0 |
| SOURCE_WAIT | 176365 |
| SOURCE_REJECT | 0 |
| SOURCE_ALLOW | 0 |
| ORDERS | 0 |
| FILLED | 0 |
| CLOSED | 0 |
| OPEN_CENSORED | 0 |
| PENDING_UNFILLED | 0 |

RAW count — preregistered OHLC proposals, не число доказанных source setups. Enumeration не является исчерпывающим detector discretionary patterns; реальные сетапы могли существовать без annotation или вне этой RAW convention. Максимум реальных source-valid trades не доказан.

## Financial accounting

| Metric | Independent cases | Shared portfolio |
| --- | ---: | ---: |
| closed | 0 | 0 |
| WIN | 0 | 0 |
| LOSS | 0 | 0 |
| win_rate_percent | N/A | N/A |
| gross_pnl | 0.0 | 0.0 |
| fees | 0.0 | 0.0 |
| slippage | 0.0 | 0.0 |
| net_pnl | 0.0 | 0.0 |
| profit_factor | N/A | N/A |
| expectancy | N/A | N/A |
| average_R | N/A | N/A |
| median_R | N/A | N/A |
| average_win | N/A | N/A |
| average_loss_magnitude | N/A | N/A |
| payoff_ratio | N/A | N/A |
| breakeven_WR_percent | N/A | N/A |
| max_drawdown | 0.0 | 0.0 |
| max_loss_streak | 0 | 0 |
| average_holding_seconds | N/A | N/A |
| median_holding_seconds | N/A | N/A |

PnL/costs и DD равны0 из-за отсутствия экспозиции; WR/PF/R/expectancy/holding N/A из-за пустого denominator. Капитал1170 USDT; sizing2% accounting normalization, не source rule. Fees6bps/leg, slippage2bps/leg — заранее объявленные modeled notional debits; ни одна execution leg не возникла. Funding отсутствует в данных и исключён: это не утверждение funding=0. Shared chronology/sizing и реальный fill/exit path не были exercised; synthetic unit QA не заменяет их историческую проверку. Нет investor-ready portfolio или прибыльности стратегии.

## Evidence coverage / WAIT

Нет historical source_validated qualitative annotations и причинной исторической tick metadata. Первый frozen blocker — WAIT_UNRESOLVED_INSTRUMENT_METADATA. SOURCE predicates после него NOT_EVALUATED; они не помечены FAIL. Статусы WAIT/REJECT раздельные.

Exclusive primary reasons: `{"MISSING_QUALITATIVE_EVIDENCE":0,"WAIT_BRANCH_CONFLICT":0,"WAIT_INTRABAR_ORDER":0,"WAIT_NO_AVAILABLE_LOWER_TF":0,"WAIT_UNRESOLVED_INSTRUMENT_METADATA":176365,"WAIT_UNRESOLVED_LIQUIDITY_CONTEXT":0,"WAIT_UNRESOLVED_STOP_GEOMETRY":0}`.

Overlapping evidence blockers: `{"MISSING_QUALITATIVE_EVIDENCE":176365,"WAIT_BRANCH_CONFLICT":0,"WAIT_INTRABAR_ORDER":0,"WAIT_NO_AVAILABLE_LOWER_TF":45266,"WAIT_UNRESOLVED_LIQUIDITY_CONTEXT":176365,"WAIT_UNRESOLVED_STOP_GEOMETRY":176365}`.

Дефициты: meaningful liquidity/smooth approach/whole impulse/range clarity/structural endpoints/branch confirmation, source POI/stop/FTA/identity. M15 OB/SFP требует strictly-lowerTF, которого нет в замороженном universe. Не активировали M1/M5 и не изобрели numeric classifiers.

## Baseline C comparison

| Metric | Baseline C | v1.1 shared |
| --- | ---: | ---: |
| closed | 880 | 0 |
| win_rate_percent | 38.40909090909091 | N/A |
| gross_pnl | -231.83894809071938 | 0.0 |
| fees | 636.8008335167013 | 0.0 |
| slippage | 212.26693523198855 | 0.0 |
| net_pnl | -1080.9067168394095 | 0.0 |
| profit_factor | 0.7422047615415776 | N/A |
| expectancy | -1.2283030873175107 | N/A |
| average_R | -0.12992932917345448 | N/A |
| max_drawdown_fraction | 0.9329808668639642 | 0.0 |
| average_holding_seconds | 89117.38636363637 | N/A |
| median_holding_seconds | 33300.0 | N/A |

Baseline READY signals: 6760; admitted entries: 880.

Old880 source re-evaluation: `{"REJECT":102,"WAIT":778}`.
Reasons: `{"REJECT_INACTIVE_PROFILE_BRANCH":102,"WAIT_UNRESOLVED_INSTRUMENT_METADATA":778}`.

Новые FILLED, отсутствующие в baseline:0. Matched new fills:0. Inactive direct/aggressive/component styles отвергнуты именно как old entry branch в executable profile; остальные missing-evidence случаи WAIT. Это не утверждение, что source запрещает эти inactive alternatives или последующий confirmed setup.

Baseline Gross восстановлен до costs как old gross_pnl+slippage, чтобы не вычесть slippage дважды. Состав cohort, admission, exits, accounting и evidence availability различаются. Без matched fills нельзя приписать различия одному удалённому gate или оценить effect size.

Gates не применялись: `["universal_H1_H4_owner","mandatory_D1_H4_context_objects","old_NO_HTF_CONTEXT","H4_D1_only_FTA","old_adverse751_446","fitted_68pct_tree","AntiScalp_ratio3","canonical40_30_30","TP1_BE","cost_BE","project_totalrisk_daily_correlation_leverage"]`.

## Artifacts and QA

Artifacts: `data/reports/original_v1_1_first_financial_backtest_2026_10_11/result`; preregistration: `original_v1_1_financial_backtest_preregistration.json`; dataset manifest: `data/reports/original_v1_1_first_financial_backtest_2026_10_11/preregistration/dataset_manifest.json`. QA receipts лежат рядом с result и входят в result manifest.

Funnel/metrics/branch-TF-symbol-direction-year-month breakdowns; all candidates/WAIT/REJECT/ALLOW; per-candidate source/evidence trace; all-trades CSV и cost ledger с заголовками (пустые); baseline880 per-case decisions. No optimisation/no new thresholds/no strategy mutations.

Source v1.1 и более ранние frozen namespaces не менялись. `trade_entry_allowed=false`. LIVE/private API запрещены. После первого frozen result STOP.
