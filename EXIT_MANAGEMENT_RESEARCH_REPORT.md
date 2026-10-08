# Controlled exit management research

INSUFFICIENT SAMPLE. 2026-10-09T04:24:46.129847+05:00 (Asia/Yekaterinburg); market timestamps UTC.

Canonical TP1=40%, TP2=30%, TP3=30%; исходный SL и cost-adjusted breakeven после TP1 **не менялись**. Эксперименты зарегистрированы в [EXIT_RESEARCH_PROTOCOL.md](EXIT_RESEARCH_PROTOCOL.md), commit `c2fdce0`, до alternative exit runs. Ни один кандидат не выбран по текущему PnL.

## Dataset and pairing

Прежние Bybit2026 7 closed trades — DEVELOPMENT, 6 независимых mapping portfolios. New cohorts сохраняют frozen REFERENCE/VALIDATION/retrospective HOLDOUT periods. Часть их canonical outcomes уже была просмотрена до exit protocol; не называем весь этот dataset untouched exit validation. Отдельно заранее зарезервирован BTC-only Binance60/5 2019Q4: 395 observed setups → 0 READY → 0 entries. Reserve сохранён, но не даёт exit observations. Это calendar-selected retrospective reserve, не prospective OOS.

Full portfolio variants получают одинаковые incoming frozen signals/entry/risk rules. Exit cash/occupancy может изменить будущие admissions; это feedback, не изменение входов. Paired actual-entry replay использует actual earlier READY, исходные entry equity/quote/quantity/risk и original inherited admission. Реальные сигналы не hardcoded и новые сделки не выдуманы. Paired DD — индивидуальный trade NAV; full portfolio DD — отдельный 1170 account, эти величины не объединяются.

## Fixed variants

A40/30/30, B30/30/40, C25/25/50, D25/35/40 держат original immediate cost-adjusted BE после TP1. Отдельные A timing variants: later favourable completed LTF close → next-bar BE; original SL through TP1, BE after TP2; structural trailing using newly formed and SOURCE_CONSERVATIVE-confirmed protective LTF swing after TP1. Structural rule — declared experimental normalization, не source-approved replacement. Confirmation/ratchet исполняется с next bar, никакого retroactive stop на свече подтверждения. Same-bar OHLC ambiguity сохраняет pessimistic stop-first priority. Fractional exits оплачивают costs пропорционально original quantity.

## Results

Все active independent portfolio cases перечислены отдельно. TRADES означает CLOSED; open/censored entries и TP rates приведены в полном CSV. Значения PnL/AvgWin/AvgLoss/expectancy — USDT; max DD — full account mark-to-market NAV. Undefined PF/mean при отсутствии denominator отображается «—», не infinity. Zero-entry cases присутствуют для всех 7 variants в [exit_management_metrics.csv](data/reports/robustness_research/exit_management_metrics.csv).

### binance_15_5 / HOLDOUT_SEGMENT_10 — EXTERNAL

| EXIT VARIANT | TRADES | WIN RATE | AVG WIN | AVG LOSS | EXPECTANCY | PF | MAX DD | NET PNL |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A_40_30_30_BE_TP1 | 8 | 0.00% | — | 21.8259 | -21.8259 | 0.0000 | 14.92% | -174.6073 |
| B_30_30_40_BE_TP1 | 8 | 0.00% | — | 21.8259 | -21.8259 | 0.0000 | 14.92% | -174.6073 |
| C_25_25_50_BE_TP1 | 8 | 0.00% | — | 21.8259 | -21.8259 | 0.0000 | 14.92% | -174.6073 |
| D_25_35_40_BE_TP1 | 8 | 0.00% | — | 21.8259 | -21.8259 | 0.0000 | 14.92% | -174.6073 |
| A_BE_LATER_CLOSE | 8 | 0.00% | — | 21.8259 | -21.8259 | 0.0000 | 14.92% | -174.6073 |
| A_ORIGINAL_SL_UNTIL_TP2 | 8 | 0.00% | — | 21.8259 | -21.8259 | 0.0000 | 14.92% | -174.6073 |
| A_STRUCTURAL_AFTER_TP1 | 8 | 0.00% | — | 21.8259 | -21.8259 | 0.0000 | 14.92% | -174.6073 |

### binance_15_5 / REFERENCE_SEGMENT_05 — EXTERNAL

| EXIT VARIANT | TRADES | WIN RATE | AVG WIN | AVG LOSS | EXPECTANCY | PF | MAX DD | NET PNL |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A_40_30_30_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 4.13% | -23.4000 |
| B_30_30_40_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 4.13% | -23.4000 |
| C_25_25_50_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 4.13% | -23.4000 |
| D_25_35_40_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 4.13% | -23.4000 |
| A_BE_LATER_CLOSE | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 4.13% | -23.4000 |
| A_ORIGINAL_SL_UNTIL_TP2 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 4.13% | -23.4000 |
| A_STRUCTURAL_AFTER_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 4.13% | -23.4000 |

### binance_15_5 / REFERENCE_SEGMENT_07 — EXTERNAL

| EXIT VARIANT | TRADES | WIN RATE | AVG WIN | AVG LOSS | EXPECTANCY | PF | MAX DD | NET PNL |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A_40_30_30_BE_TP1 | 2 | 0.00% | — | 23.1660 | -23.1660 | 0.0000 | 4.38% | -46.3320 |
| B_30_30_40_BE_TP1 | 2 | 0.00% | — | 23.1660 | -23.1660 | 0.0000 | 4.38% | -46.3320 |
| C_25_25_50_BE_TP1 | 2 | 0.00% | — | 23.1660 | -23.1660 | 0.0000 | 4.38% | -46.3320 |
| D_25_35_40_BE_TP1 | 2 | 0.00% | — | 23.1660 | -23.1660 | 0.0000 | 4.38% | -46.3320 |
| A_BE_LATER_CLOSE | 2 | 0.00% | — | 23.1660 | -23.1660 | 0.0000 | 4.38% | -46.3320 |
| A_ORIGINAL_SL_UNTIL_TP2 | 2 | 0.00% | — | 23.1660 | -23.1660 | 0.0000 | 4.38% | -46.3320 |
| A_STRUCTURAL_AFTER_TP1 | 2 | 0.00% | — | 23.1660 | -23.1660 | 0.0000 | 4.38% | -46.3320 |

### binance_15_5 / REFERENCE_SEGMENT_08 — EXTERNAL

| EXIT VARIANT | TRADES | WIN RATE | AVG WIN | AVG LOSS | EXPECTANCY | PF | MAX DD | NET PNL |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A_40_30_30_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 4.02% | -23.4000 |
| B_30_30_40_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 4.02% | -23.4000 |
| C_25_25_50_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 4.02% | -23.4000 |
| D_25_35_40_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 4.02% | -23.4000 |
| A_BE_LATER_CLOSE | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 4.02% | -23.4000 |
| A_ORIGINAL_SL_UNTIL_TP2 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 4.02% | -23.4000 |
| A_STRUCTURAL_AFTER_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 4.02% | -23.4000 |

### binance_15_5 / REFERENCE_SEGMENT_09 — EXTERNAL

| EXIT VARIANT | TRADES | WIN RATE | AVG WIN | AVG LOSS | EXPECTANCY | PF | MAX DD | NET PNL |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A_40_30_30_BE_TP1 | 6 | 33.33% | 30.3118 | 23.5986 | -5.6285 | 0.6422 | 11.46% | -33.7708 |
| B_30_30_40_BE_TP1 | 6 | 33.33% | 22.7103 | 23.3751 | -8.0133 | 0.4858 | 12.56% | -48.0798 |
| C_25_25_50_BE_TP1 | 6 | 33.33% | 18.9154 | 23.2635 | -9.2039 | 0.4065 | 13.11% | -55.2232 |
| D_25_35_40_BE_TP1 | 6 | 33.33% | 18.9154 | 23.2635 | -9.2039 | 0.4065 | 13.11% | -55.2232 |
| A_BE_LATER_CLOSE | 6 | 33.33% | 30.3118 | 23.5986 | -5.6285 | 0.6422 | 11.46% | -33.7708 |
| A_ORIGINAL_SL_UNTIL_TP2 | 6 | 16.67% | 41.3859 | 20.3166 | -10.0329 | 0.4074 | 13.52% | -60.1974 |
| A_STRUCTURAL_AFTER_TP1 | 6 | 33.33% | 64.3633 | 24.5999 | 5.0545 | 1.3082 | 8.78% | 30.3271 |

### binance_15_5 / VALIDATION_SEGMENT_10 — EXTERNAL

| EXIT VARIANT | TRADES | WIN RATE | AVG WIN | AVG LOSS | EXPECTANCY | PF | MAX DD | NET PNL |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A_40_30_30_BE_TP1 | 4 | 25.00% | 7.0802 | 22.9823 | -15.4667 | 0.1027 | 6.41% | -61.8668 |
| B_30_30_40_BE_TP1 | 4 | 25.00% | 5.3101 | 22.9705 | -15.9004 | 0.0771 | 6.56% | -63.6014 |
| C_25_25_50_BE_TP1 | 4 | 25.00% | 4.4251 | 22.9646 | -16.1172 | 0.0642 | 6.63% | -64.4688 |
| D_25_35_40_BE_TP1 | 4 | 25.00% | 4.4251 | 22.9646 | -16.1172 | 0.0642 | 6.63% | -64.4688 |
| A_BE_LATER_CLOSE | 4 | 25.00% | 7.0802 | 22.9823 | -15.4667 | 0.1027 | 6.41% | -61.8668 |
| A_ORIGINAL_SL_UNTIL_TP2 | 4 | 0.00% | — | 18.7703 | -18.7703 | 0.0000 | 7.53% | -75.0811 |
| A_STRUCTURAL_AFTER_TP1 | 4 | 25.00% | 15.8481 | 23.0408 | -13.3186 | 0.2293 | 5.68% | -53.2743 |

### binance_240_15 / HOLDOUT_SEGMENT_10 — EXTERNAL

| EXIT VARIANT | TRADES | WIN RATE | AVG WIN | AVG LOSS | EXPECTANCY | PF | MAX DD | NET PNL |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A_40_30_30_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 7.36% | -23.4000 |
| B_30_30_40_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 7.36% | -23.4000 |
| C_25_25_50_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 7.36% | -23.4000 |
| D_25_35_40_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 7.36% | -23.4000 |
| A_BE_LATER_CLOSE | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 7.36% | -23.4000 |
| A_ORIGINAL_SL_UNTIL_TP2 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 7.36% | -23.4000 |
| A_STRUCTURAL_AFTER_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 7.36% | -23.4000 |

### binance_240_60 / REFERENCE_SEGMENT_09 — EXTERNAL

| EXIT VARIANT | TRADES | WIN RATE | AVG WIN | AVG LOSS | EXPECTANCY | PF | MAX DD | NET PNL |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A_40_30_30_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 6.89% | -23.4000 |
| B_30_30_40_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 6.89% | -23.4000 |
| C_25_25_50_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 6.89% | -23.4000 |
| D_25_35_40_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 6.89% | -23.4000 |
| A_BE_LATER_CLOSE | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 6.89% | -23.4000 |
| A_ORIGINAL_SL_UNTIL_TP2 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 6.89% | -23.4000 |
| A_STRUCTURAL_AFTER_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 6.89% | -23.4000 |

### binance_60_15 / HOLDOUT_SEGMENT_10 — EXTERNAL

| EXIT VARIANT | TRADES | WIN RATE | AVG WIN | AVG LOSS | EXPECTANCY | PF | MAX DD | NET PNL |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A_40_30_30_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 3.45% | -23.4000 |
| B_30_30_40_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 3.45% | -23.4000 |
| C_25_25_50_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 3.45% | -23.4000 |
| D_25_35_40_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 3.45% | -23.4000 |
| A_BE_LATER_CLOSE | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 3.45% | -23.4000 |
| A_ORIGINAL_SL_UNTIL_TP2 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 3.45% | -23.4000 |
| A_STRUCTURAL_AFTER_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 3.45% | -23.4000 |

### binance_60_15 / REFERENCE_SEGMENT_09 — EXTERNAL

| EXIT VARIANT | TRADES | WIN RATE | AVG WIN | AVG LOSS | EXPECTANCY | PF | MAX DD | NET PNL |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A_40_30_30_BE_TP1 | 3 | 0.00% | — | 22.9351 | -22.9351 | 0.0000 | 13.22% | -68.8054 |
| B_30_30_40_BE_TP1 | 3 | 0.00% | — | 22.9351 | -22.9351 | 0.0000 | 13.22% | -68.8054 |
| C_25_25_50_BE_TP1 | 3 | 0.00% | — | 22.9351 | -22.9351 | 0.0000 | 13.22% | -68.8054 |
| D_25_35_40_BE_TP1 | 3 | 0.00% | — | 22.9351 | -22.9351 | 0.0000 | 13.22% | -68.8054 |
| A_BE_LATER_CLOSE | 3 | 0.00% | — | 22.9351 | -22.9351 | 0.0000 | 13.22% | -68.8054 |
| A_ORIGINAL_SL_UNTIL_TP2 | 3 | 0.00% | — | 22.9351 | -22.9351 | 0.0000 | 13.22% | -68.8054 |
| A_STRUCTURAL_AFTER_TP1 | 3 | 0.00% | — | 22.9351 | -22.9351 | 0.0000 | 13.22% | -68.8054 |

### binance_60_15 / REFERENCE_SEGMENT_10 — EXTERNAL

| EXIT VARIANT | TRADES | WIN RATE | AVG WIN | AVG LOSS | EXPECTANCY | PF | MAX DD | NET PNL |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A_40_30_30_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 2.00% | -23.4000 |
| B_30_30_40_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 2.00% | -23.4000 |
| C_25_25_50_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 2.00% | -23.4000 |
| D_25_35_40_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 2.00% | -23.4000 |
| A_BE_LATER_CLOSE | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 2.00% | -23.4000 |
| A_ORIGINAL_SL_UNTIL_TP2 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 2.00% | -23.4000 |
| A_STRUCTURAL_AFTER_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 2.00% | -23.4000 |

### binance_60_15 / VALIDATION_SEGMENT_10 — EXTERNAL

| EXIT VARIANT | TRADES | WIN RATE | AVG WIN | AVG LOSS | EXPECTANCY | PF | MAX DD | NET PNL |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A_40_30_30_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 3.78% | -23.4000 |
| B_30_30_40_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 3.78% | -23.4000 |
| C_25_25_50_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 3.78% | -23.4000 |
| D_25_35_40_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 3.78% | -23.4000 |
| A_BE_LATER_CLOSE | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 3.78% | -23.4000 |
| A_ORIGINAL_SL_UNTIL_TP2 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 3.78% | -23.4000 |
| A_STRUCTURAL_AFTER_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 3.78% | -23.4000 |

### binance_60_5 / HOLDOUT_SEGMENT_10 — EXTERNAL

| EXIT VARIANT | TRADES | WIN RATE | AVG WIN | AVG LOSS | EXPECTANCY | PF | MAX DD | NET PNL |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A_40_30_30_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 3.96% | -23.4000 |
| B_30_30_40_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 3.96% | -23.4000 |
| C_25_25_50_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 3.96% | -23.4000 |
| D_25_35_40_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 3.96% | -23.4000 |
| A_BE_LATER_CLOSE | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 3.96% | -23.4000 |
| A_ORIGINAL_SL_UNTIL_TP2 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 3.96% | -23.4000 |
| A_STRUCTURAL_AFTER_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 3.96% | -23.4000 |

### binance_60_5 / VALIDATION_SEGMENT_10 — EXTERNAL

| EXIT VARIANT | TRADES | WIN RATE | AVG WIN | AVG LOSS | EXPECTANCY | PF | MAX DD | NET PNL |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A_40_30_30_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 4.00% | -23.4000 |
| B_30_30_40_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 4.00% | -23.4000 |
| C_25_25_50_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 4.00% | -23.4000 |
| D_25_35_40_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 4.00% | -23.4000 |
| A_BE_LATER_CLOSE | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 4.00% | -23.4000 |
| A_ORIGINAL_SL_UNTIL_TP2 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 4.00% | -23.4000 |
| A_STRUCTURAL_AFTER_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 4.00% | -23.4000 |

### bybit_240_15 / REFERENCE_SEGMENT_00 — EXTERNAL

| EXIT VARIANT | TRADES | WIN RATE | AVG WIN | AVG LOSS | EXPECTANCY | PF | MAX DD | NET PNL |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A_40_30_30_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 2.00% | -23.4000 |
| B_30_30_40_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 2.00% | -23.4000 |
| C_25_25_50_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 2.00% | -23.4000 |
| D_25_35_40_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 2.00% | -23.4000 |
| A_BE_LATER_CLOSE | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 2.00% | -23.4000 |
| A_ORIGINAL_SL_UNTIL_TP2 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 2.00% | -23.4000 |
| A_STRUCTURAL_AFTER_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 2.00% | -23.4000 |

### bybit_240_60 / REFERENCE_SEGMENT_00 — EXTERNAL

| EXIT VARIANT | TRADES | WIN RATE | AVG WIN | AVG LOSS | EXPECTANCY | PF | MAX DD | NET PNL |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A_40_30_30_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 2.00% | -23.4000 |
| B_30_30_40_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 2.00% | -23.4000 |
| C_25_25_50_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 2.00% | -23.4000 |
| D_25_35_40_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 2.00% | -23.4000 |
| A_BE_LATER_CLOSE | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 2.00% | -23.4000 |
| A_ORIGINAL_SL_UNTIL_TP2 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 2.00% | -23.4000 |
| A_STRUCTURAL_AFTER_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 2.00% | -23.4000 |

### bybit_60_15 / HOLDOUT_SEGMENT_00 — EXTERNAL

| EXIT VARIANT | TRADES | WIN RATE | AVG WIN | AVG LOSS | EXPECTANCY | PF | MAX DD | NET PNL |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A_40_30_30_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 6.78% | -23.4000 |
| B_30_30_40_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 6.78% | -23.4000 |
| C_25_25_50_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 6.78% | -23.4000 |
| D_25_35_40_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 6.78% | -23.4000 |
| A_BE_LATER_CLOSE | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 6.78% | -23.4000 |
| A_ORIGINAL_SL_UNTIL_TP2 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 6.78% | -23.4000 |
| A_STRUCTURAL_AFTER_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 6.78% | -23.4000 |

### bybit_60_15 / REFERENCE_SEGMENT_00 — EXTERNAL

| EXIT VARIANT | TRADES | WIN RATE | AVG WIN | AVG LOSS | EXPECTANCY | PF | MAX DD | NET PNL |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A_40_30_30_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 2.00% | -23.4000 |
| B_30_30_40_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 2.00% | -23.4000 |
| C_25_25_50_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 2.00% | -23.4000 |
| D_25_35_40_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 2.00% | -23.4000 |
| A_BE_LATER_CLOSE | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 2.00% | -23.4000 |
| A_ORIGINAL_SL_UNTIL_TP2 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 2.00% | -23.4000 |
| A_STRUCTURAL_AFTER_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 2.00% | -23.4000 |

### development_15_5 / limit_15_5 — DEVELOPMENT

| EXIT VARIANT | TRADES | WIN RATE | AVG WIN | AVG LOSS | EXPECTANCY | PF | MAX DD | NET PNL |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A_40_30_30_BE_TP1 | 1 | 100.00% | 9.8622 | — | 9.8622 | — | 3.06% | 9.8622 |
| B_30_30_40_BE_TP1 | 1 | 100.00% | 7.3966 | — | 7.3966 | — | 3.27% | 7.3966 |
| C_25_25_50_BE_TP1 | 1 | 100.00% | 6.1639 | — | 6.1639 | — | 3.49% | 6.1639 |
| D_25_35_40_BE_TP1 | 1 | 100.00% | 6.1639 | — | 6.1639 | — | 3.49% | 6.1639 |
| A_BE_LATER_CLOSE | 1 | 100.00% | 9.8622 | — | 9.8622 | — | 3.06% | 9.8622 |
| A_ORIGINAL_SL_UNTIL_TP2 | 1 | 0.00% | — | 4.1778 | -4.1778 | 0.0000 | 3.96% | -4.1778 |
| A_STRUCTURAL_AFTER_TP1 | 1 | 100.00% | 20.7576 | — | 20.7576 | — | 3.06% | 20.7576 |

### development_240_15 / final_240_15 — DEVELOPMENT

| EXIT VARIANT | TRADES | WIN RATE | AVG WIN | AVG LOSS | EXPECTANCY | PF | MAX DD | NET PNL |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A_40_30_30_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 2.00% | -23.4000 |
| B_30_30_40_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 2.00% | -23.4000 |
| C_25_25_50_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 2.00% | -23.4000 |
| D_25_35_40_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 2.00% | -23.4000 |
| A_BE_LATER_CLOSE | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 2.00% | -23.4000 |
| A_ORIGINAL_SL_UNTIL_TP2 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 2.00% | -23.4000 |
| A_STRUCTURAL_AFTER_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 2.00% | -23.4000 |

### development_240_5 / final_240_5 — DEVELOPMENT

| EXIT VARIANT | TRADES | WIN RATE | AVG WIN | AVG LOSS | EXPECTANCY | PF | MAX DD | NET PNL |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A_40_30_30_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 7.77% | -23.4000 |
| B_30_30_40_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 7.77% | -23.4000 |
| C_25_25_50_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 7.77% | -23.4000 |
| D_25_35_40_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 7.77% | -23.4000 |
| A_BE_LATER_CLOSE | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 7.77% | -23.4000 |
| A_ORIGINAL_SL_UNTIL_TP2 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 7.77% | -23.4000 |
| A_STRUCTURAL_AFTER_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 7.77% | -23.4000 |

### development_240_60 / final_240_60 — DEVELOPMENT

| EXIT VARIANT | TRADES | WIN RATE | AVG WIN | AVG LOSS | EXPECTANCY | PF | MAX DD | NET PNL |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A_40_30_30_BE_TP1 | 2 | 50.00% | 11.1659 | 23.6233 | -6.2287 | 0.4727 | 5.89% | -12.4575 |
| B_30_30_40_BE_TP1 | 2 | 50.00% | 8.3744 | 23.5675 | -7.5965 | 0.3553 | 6.51% | -15.1931 |
| C_25_25_50_BE_TP1 | 2 | 50.00% | 6.9787 | 23.5396 | -8.2805 | 0.2965 | 6.83% | -16.5609 |
| D_25_35_40_BE_TP1 | 2 | 50.00% | 6.9787 | 23.5396 | -8.2805 | 0.2965 | 6.83% | -16.5609 |
| A_BE_LATER_CLOSE | 2 | 50.00% | 11.1659 | 23.6233 | -6.2287 | 0.4727 | 5.89% | -12.4575 |
| A_ORIGINAL_SL_UNTIL_TP2 | 2 | 0.00% | — | 13.1083 | -13.1083 | 0.0000 | 7.01% | -26.2167 |
| A_STRUCTURAL_AFTER_TP1 | 2 | 50.00% | 45.1601 | 24.3032 | 10.4284 | 1.8582 | 3.14% | 20.8569 |

### development_60_15 / final_60_15 — DEVELOPMENT

| EXIT VARIANT | TRADES | WIN RATE | AVG WIN | AVG LOSS | EXPECTANCY | PF | MAX DD | NET PNL |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A_40_30_30_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 2.32% | -23.4000 |
| B_30_30_40_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 2.32% | -23.4000 |
| C_25_25_50_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 2.32% | -23.4000 |
| D_25_35_40_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 2.32% | -23.4000 |
| A_BE_LATER_CLOSE | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 2.32% | -23.4000 |
| A_ORIGINAL_SL_UNTIL_TP2 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 2.32% | -23.4000 |
| A_STRUCTURAL_AFTER_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 2.32% | -23.4000 |

### development_60_5 / limit_60_5 — DEVELOPMENT

| EXIT VARIANT | TRADES | WIN RATE | AVG WIN | AVG LOSS | EXPECTANCY | PF | MAX DD | NET PNL |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A_40_30_30_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 6.54% | -23.4000 |
| B_30_30_40_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 6.54% | -23.4000 |
| C_25_25_50_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 6.54% | -23.4000 |
| D_25_35_40_BE_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 6.54% | -23.4000 |
| A_BE_LATER_CLOSE | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 6.54% | -23.4000 |
| A_ORIGINAL_SL_UNTIL_TP2 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 6.54% | -23.4000 |
| A_STRUCTURAL_AFTER_TP1 | 1 | 0.00% | — | 23.4000 | -23.4000 | 0.0000 | 6.54% | -23.4000 |

## TP / BE / costs

[exit_management_metrics.csv](data/reports/robustness_research/exit_management_metrics.csv) содержит mean/median R, losing streak, TP1/2/3 hit rate, post-TP1 BE exits, fees/slippage, realized and equity PnL. Hit rate denominator — entries; censored open trades не объявлены неудачами. «После BE потом дошло до target» — price path counterfactual, не доказанный profit. Exit-bar wick chronology неизвестна: только close доказывает движение после intrabar BE; subsequent bars идут stop-first. 30-day follow clipped contiguous original endpoint; right-censoring и ambiguity сохранены.

| STUDY | SIGNAL | LATER TP2 TOUCH | LATER TP3 TOUCH | TP2 BEFORE ORIGINAL SL | TP3 BEFORE ORIGINAL SL | RIGHT CENSORED | AMBIGUOUS TP2/TP3 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| binance_15_5 | 13805e51dfbbaac6a5b789c7 | True | True | False | False | False | False/False |
| binance_15_5 | 3c18b83161b1150a52905a91 | True | True | False | False | False | False/False |
| binance_15_5 | 332459bdcc550afa69fac362 | True | True | False | False | True | False/False |
| development_15_5 | 7f9ef0e73c09c10eac6a738f | False | False | False | False | True | False/False |
| development_240_60 | 562f49bbf510d68fc4d4c67c | True | False | False | False | False | False/False |

[paired_exit_actual_entries.csv](data/reports/robustness_research/paired_exit_actual_entries.csv) сохраняет цены/количество/risk/costs/fills для matched experiments. Case JSON `paired_actual_entries.json` проверяет real BACKTEST/SHADOW, `exit_real_causality.json` — future-prefix для actual TP1 case либо явно NO_CANONICAL_TP1_EVENT; vacuous check не называется доказательством exit path. Baseline A exact trades/decisions/NAV подтверждён на всех saved canonical cases.

## Answers

1. **Является ли 40/30/30 экономически слабым?** По имеющейся выборке это не установлено. Веса сами по себе не определяют expectancy: важны реальные target distances, probabilities, remaining-stop outcomes и costs. Отрицательная observed expectancy малых cases описывает dataset, а не доказывает intrinsically weak allocation.

2. **Основная проблема win rate или маленький AvgWin?** В development оба фактора присутствуют: 5 SL losses и только 2 TP1→BE winners среди 7 closed replay instances. Но это разные mapping portfolios; pooled PnL и устойчивый global win rate не утверждаются. Внутри 240/60 N=2: win rate 50%, AvgWin11.1659 против AvgLoss23.6233; observed expectancy−6.2287. Descriptive break-even win rate ≈67.91%, но две сделки не оценивают истинную вероятность.

3. **Слишком рано ли BE?** Недостаточно post-TP1 episodes и незавершённых 30-day observations. Таблица later target touches не превращается в profit без original SL/cost/ordering checks. Более прибыльный structural outcome одной уже использованной сделки не доказывает, что early BE ошибочен.

4. **Какой вариант устойчивее OOS?** Никакой не подтверждён достаточным untouched sample. Main retrospective holdout partly unblinded для exit research; separate preregistered reserve имеет 0 entries. В случаях SL до TP1 все 7 variants закономерно совпадают и не дают сравнительного exit evidence.

5. **Достаточна ли выборка для изменения canonical?** Нет: gate ≥100 comparable OOS closed trades/mapping и ≥30 post-TP1 events не достигнут. Требуется отдельный ещё не использованный период с достаточными actual admitted trades и подтверждением costs/causality. До этого baseline40/30/30 остаётся неизменным.

## Safety and publication

trade_entry_allowed=false; LIVE/private API/credentials/real orders отключены. No entry rule changes; no optimization or candidate selection. Canonical rollback остаётся доступен. Актуальные tests/lint/mypy/guards — [continuation_stage_checks.json](data/reports/robustness_research/continuation_stage_checks.json). Reports/scripts/diagnostics/history сохраняются в GitHub main; ZIP content correspondence проверяется после final push.
