# Source-permitted Bybit: physical trade-case validation — 2026-10-10

**Полный replay40 native Bybit серий /993575 свечей: 19448 physical READY → 16351 FILLED → 16333 CLOSED. Основная выборка: 50 уникальных FILLED+CLOSED.**

Первичные SW5/SW9/SW11/SW12/SW22:54 страницы полностью прочитаны; оригиналы/text/схемы и ZIP/DOCX сохранены. Canonical TP40/30/30, SL и cost-adjusted BE послеTP1 неизменны. Только BACKTEST/SHADOW, `trade_entry_allowed=false`; LIVE/private API отсутствуют.

2026 DEVELOPMENT уже просматривалась: это не OOS. Каждый case — независимый reference1170 USDT, planned risk2%=23.4 с fee.0006/slippage.0002 на сторону. Funding не моделируется. Это case validation без shared occupancy/NAV. Native5m даёт интервал fill, не точный tick; OHLC stop-first и фиксированный pessimistic limit/gap model сохранены. Первые50 выбираются по fill-интервалу; при одинаковом интервале используется заранее фиксированный tie order. Все Win/Loss/BE включены, OPEN/PENDING сохранены, endpoint не force-close.

## Funnel и source corrections

Полные candidate predicates всех15 paths сохранены до исполнения. Raw entry-candidate READY=137202; source-qualified raw READY=96954; SFP qualification={'REJECT_SFP_INVALID_BEFORE_READY': 40248, 'PASS_SFP_VALID_AT_READY': 47653}. После глобальных causal aliases union READY=19448, FILLED=16351, CLOSED=16333, OPEN=18, PENDING=118. Raw variants и rejected candidates не считаются отдельными physical trades.

| Source path | Source-valid raw READY |
|---|---|
| OB_DIRECT_FIRST_TEST | 1391 |
| OB_DIRECT_INSIDE | 1397 |
| OB_DIRECT_ENGULFING_STOP | 1391 |
| OB_DIRECT_INSIDE_ENGULFING_STOP | 1080 |
| OB_CONSERVATIVE_BOS_POI | 6180 |
| OB_ULTRA_CONSERVATIVE_CONF | 4194 |
| STB_BTS_EDGE | 4229 |
| STB_BTS_HALF | 5991 |
| BREAKER_CONSERVATIVE_STOP | 5094 |
| BREAKER_AGGRESSIVE_STOP | 5094 |
| DEMAND_SUPPLY | 3528 |
| RANGE_CONSERVATIVE_RETEST | 175 |
| RANGE_AGGRESSIVE_EXTERNAL_POI | 9557 |
| SFP_BOS_POI | 23841 |
| SFP_ATR_STOP | 23812 |

Detection gate event counts (повторные transitions не являются nested physical funnel): {"READY": 137202, "WAIT_ACTIVE_SOURCE_ORDER_FLOW": 406971, "WAIT_OB_INSIDE_PREEXISTING_HTF_POI": 531042, "WAIT_PREEXISTING_HIGHER_NATIVE_POI": 4220, "WAIT_RESTING_QUOTE_AND_AHEAD_TARGET": 13756, "WAIT_SOURCE_FIRST_HTF_FTA": 3126, "WAIT_SOURCE_REQUIRED_PD": 169369, "WAIT_SOURCE_STOP_EVIDENCE": 34, "WAIT_SOURCE_STRUCTURAL_IMPULSE": 621109}. Все native formations, raids, OF waits и gate transitions: `candidate_detection_funnel.json`.

OB direct edge/inside и OB/engulf wick stops; BOS/new POI без универсальногоCONF; отдельныйCONF; STB edge/half; breaker block/sweep stops; независимый multi-candle D/S; conservative/aggressive Range; самостоятельный SFP и frozen ATR-SFP. OF сохраняет реальные key HH/HL/LL/LH, liquidity work и fixed global destination; убран дополнительный post-raid body break. Нет универсального veto каждого внутреннего пула.

SFP broken old BOS level не является новым защищённым HL/LH. Нативное body-нарушение SFP до READY навсегда отвергает этот старый контекст; после READY primary pending life использует настоящие POI/pattern bodies. Ни будущийCLOSE, ни поздняя отмена не могут стереть раннийfill. Все quotes/SL/targets/READY/source risk остаются исходными. Global physical IDs назначаются причинно до family filtering и execution; один локальный first-test/контекст/известный native formation alias не увеличивает выборку вариантами.

Цель50 достигнута на всех40 ранее доступных сериях; дополнительные загрузки не требуются.

## Все метрики primary50

| Metric | Value |
|---|---|
| AvgHoldingSeconds | 15216 |
| AvgLoss | 22.795199 |
| AvgR | -0.50779771 |
| AvgWin | 22.674519 |
| BE | 0 |
| CLOSED | 50 |
| Expectancy | -11.882466 |
| Fees | 243.32621 |
| GrossAfterSlippageBeforeFees | -350.79711 |
| GrossPnL | -269.68838 |
| Losses | 38 |
| MaxDrawdown | 594.12332 |
| MaxDrawdownFraction | N/A |
| MaxLosingStreak | 10 |
| MaxWinningStreak | 3 |
| MedianR | -1 |
| NetPnL | -594.12332 |
| PayoffRatio | 0.99470593 |
| ProfitFactor | 0.31411766 |
| Slippage | 81.108725 |
| WinRate | 0.24 |
| Wins | 12 |
| drawdown_scope | CUMULATIVE_INDEPENDENT_CASE_NET_PNL_BY_EXIT_TIME; NOT_SHARED_NAV |

MaxDrawdown — cumulative independent-case net PnL в порядке exit time, не shared portfolio NAV. MaxDrawdownFraction=N/A. Streaks и first50 — в порядке fill-интервалов. GrossPnL — quote PnL до friction; Net=Gross−Slippage−Fees.

## Когорты: без выбора лучшей после PnL

| Path/cohort | Cancel cohort | READY | FILLED | CLOSED all | WIN first50 | LOSS first50 | WR% | PF | ExpectancyUSDT | AvgR | NetUSDT |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BREAKER_AGGRESSIVE_STOP | CANCEL_SOURCE_POI_INVALIDATION | 3014 | 1927 | 1926 | 10 | 40 | 20 | 1.0803137 | 1.5034724 | 0.064250958 | 75.173621 |
| BREAKER_AGGRESSIVE_STOP | CANCEL_STRICT_STRUCTURE | 3014 | 935 | 935 | 11 | 39 | 22 | 0.79372716 | -3.7648919 | -0.16089282 | -188.2446 |
| BREAKER_CONSERVATIVE_STOP | CANCEL_SOURCE_POI_INVALIDATION | 3014 | 1928 | 1920 | 18 | 32 | 36 | 1.182313 | 2.7303198 | 0.11668033 | 136.51599 |
| BREAKER_CONSERVATIVE_STOP | CANCEL_STRICT_STRUCTURE | 3014 | 934 | 932 | 18 | 32 | 36 | 0.70308063 | -4.4466645 | -0.1900284 | -222.33323 |
| DEMAND_SUPPLY | CANCEL_SOURCE_POI_INVALIDATION | 3048 | 2584 | 2583 | 5 | 45 | 10 | 0.23189184 | -16.176358 | -0.69129734 | -808.81789 |
| DEMAND_SUPPLY | CANCEL_STRICT_STRUCTURE | 3048 | 739 | 739 | 5 | 45 | 10 | 0.65786324 | -7.2054002 | -0.30792309 | -360.27001 |
| OB_CONSERVATIVE_BOS_POI | CANCEL_SOURCE_POI_INVALIDATION | 3541 | 2700 | 2698 | 12 | 38 | 24 | 0.30381528 | -12.380949 | -0.52910039 | -619.04746 |
| OB_CONSERVATIVE_BOS_POI | CANCEL_STRICT_STRUCTURE | 3541 | 638 | 637 | 15 | 35 | 30 | 0.42461185 | -9.4248579 | -0.4027717 | -471.24289 |
| OB_DIRECT_ENGULFING_STOP | CANCEL_SOURCE_POI_INVALIDATION | 1102 | 582 | 582 | 7 | 43 | 14 | 0.36362545 | -12.806401 | -0.54728211 | -640.32007 |
| OB_DIRECT_ENGULFING_STOP | CANCEL_STRICT_STRUCTURE | 1102 | 93 | 93 | 5 | 45 | 10 | 0.28494042 | -15.059155 | -0.64355362 | -752.95773 |
| OB_DIRECT_FIRST_TEST | CANCEL_SOURCE_POI_INVALIDATION | 1102 | 583 | 583 | 10 | 40 | 20 | 0.45536587 | -10.195551 | -0.4357073 | -509.77755 |
| OB_DIRECT_FIRST_TEST | CANCEL_STRICT_STRUCTURE | 1102 | 93 | 93 | 8 | 42 | 16 | 0.29227528 | -13.911037 | -0.59448877 | -695.55186 |
| OB_DIRECT_INSIDE | CANCEL_SOURCE_POI_INVALIDATION | 1107 | 548 | 548 | 6 | 44 | 12 | 0.58593786 | -8.5263675 | -0.36437468 | -426.31838 |
| OB_DIRECT_INSIDE | CANCEL_STRICT_STRUCTURE | 1107 | 29 | 29 | 0 | 29 | 0 | 0 | -23.4 | -1 | -678.6 |
| OB_DIRECT_INSIDE_ENGULFING_STOP | CANCEL_SOURCE_POI_INVALIDATION | 859 | 437 | 437 | 3 | 47 | 6 | 0.33211765 | -14.69074 | -0.62780941 | -734.53701 |
| OB_DIRECT_INSIDE_ENGULFING_STOP | CANCEL_STRICT_STRUCTURE | 859 | 24 | 24 | 0 | 24 | 0 | 0 | -23.4 | -1 | -561.6 |
| OB_ULTRA_CONSERVATIVE_CONF | CANCEL_SOURCE_POI_INVALIDATION | 2222 | 1566 | 1564 | 17 | 33 | 34 | 0.78593966 | -3.3059478 | -0.14127982 | -165.29739 |
| OB_ULTRA_CONSERVATIVE_CONF | CANCEL_STRICT_STRUCTURE | 2222 | 762 | 761 | 19 | 31 | 38 | 1.4991752 | 7.2420337 | 0.30948862 | 362.10169 |
| RANGE_AGGRESSIVE_EXTERNAL_POI | CANCEL_SOURCE_POI_INVALIDATION | 3034 | 737 | 734 | 11 | 39 | 22 | 0.47690389 | -9.5475502 | -0.40801496 | -477.37751 |
| RANGE_AGGRESSIVE_EXTERNAL_POI | CANCEL_STRICT_STRUCTURE | 3034 | 48 | 48 | 15 | 33 | 31.25 | 0.4542273 | -8.7801184 | -0.37521873 | -421.44568 |
| RANGE_CONSERVATIVE_RETEST | CANCEL_SOURCE_POI_INVALIDATION | 72 | 31 | 31 | 11 | 20 | 35.483871 | 0.53805467 | -6.639399 | -0.283735 | -205.82137 |
| RANGE_CONSERVATIVE_RETEST | CANCEL_STRICT_STRUCTURE | 72 | 30 | 30 | 11 | 19 | 36.666667 | 0.56787908 | -6.0807123 | -0.2598595 | -182.42137 |
| SFP_ATR_STOP | CANCEL_SOURCE_POI_INVALIDATION | 10780 | 10633 | 10623 | 19 | 31 | 38 | 0.45513907 | -5.1415931 | -0.2197262 | -257.07965 |
| SFP_ATR_STOP | CANCEL_STRICT_STRUCTURE | 10780 | 1303 | 1302 | 27 | 23 | 54 | 0.87609879 | -0.9701318 | -0.041458624 | -48.50659 |
| SFP_BOS_POI | CANCEL_SOURCE_POI_INVALIDATION | 10785 | 10637 | 10629 | 15 | 35 | 30 | 0.38260367 | -9.8291662 | -0.42004984 | -491.45831 |
| SFP_BOS_POI | CANCEL_STRICT_STRUCTURE | 10785 | 1304 | 1303 | 25 | 25 | 50 | 1.0458413 | 0.51527278 | 0.022020204 | 25.763639 |
| SOURCE_CONF_STRICT | CANCEL_SOURCE_POI_INVALIDATION | 2222 | 1566 | 1564 | 17 | 33 | 34 | 0.78593966 | -3.3059478 | -0.14127982 | -165.29739 |
| SOURCE_CONF_STRICT | CANCEL_STRICT_STRUCTURE | 2222 | 762 | 761 | 19 | 31 | 38 | 1.4991752 | 7.2420337 | 0.30948862 | 362.10169 |
| SOURCE_CONSERVATIVE | CANCEL_SOURCE_POI_INVALIDATION | 3541 | 2700 | 2698 | 12 | 38 | 24 | 0.30381528 | -12.380949 | -0.52910039 | -619.04746 |
| SOURCE_CONSERVATIVE | CANCEL_STRICT_STRUCTURE | 3541 | 638 | 637 | 15 | 35 | 30 | 0.42461185 | -9.4248579 | -0.4027717 | -471.24289 |
| SOURCE_DIRECT | CANCEL_SOURCE_POI_INVALIDATION | 1107 | 588 | 588 | 10 | 40 | 20 | 0.45536587 | -10.195551 | -0.4357073 | -509.77755 |
| SOURCE_DIRECT | CANCEL_STRICT_STRUCTURE | 1107 | 94 | 94 | 7 | 43 | 14 | 0.23171398 | -15.460988 | -0.66072597 | -773.04939 |
| SOURCE_PERMITTED_UNION | CANCEL_SOURCE_POI_INVALIDATION | 19448 | 16351 | 16333 | 12 | 38 | 24 | 0.31411766 | -11.882466 | -0.50779771 | -594.12332 |
| SOURCE_PERMITTED_UNION | CANCEL_STRICT_STRUCTURE | 19448 | 3806 | 3803 | 20 | 30 | 40 | 0.46884245 | -7.2133059 | -0.30826094 | -360.6653 |
| STB_BTS_EDGE | CANCEL_SOURCE_POI_INVALIDATION | 3370 | 2854 | 2853 | 13 | 37 | 26 | 0.32890408 | -11.3314 | -0.48424786 | -566.56999 |
| STB_BTS_EDGE | CANCEL_STRICT_STRUCTURE | 3370 | 1167 | 1167 | 9 | 41 | 18 | 0.12599687 | -16.393605 | -0.70058142 | -819.68027 |
| STB_BTS_HALF | CANCEL_SOURCE_POI_INVALIDATION | 4622 | 3729 | 3726 | 10 | 40 | 20 | 0.78221711 | -4.0768956 | -0.17422631 | -203.84478 |
| STB_BTS_HALF | CANCEL_STRICT_STRUCTURE | 4622 | 444 | 443 | 5 | 45 | 10 | 0.33972808 | -13.905327 | -0.59424473 | -695.26634 |

SOURCE_DIRECT объединяет четыре directOB quote/stop варианта; SOURCE_CONSERVATIVE=BOS/POI, SOURCE_CONF_STRICT=CONF. Все19 source/family/union cohorts и оба cancel modes сохранены; их числа не складываются в уникальную выборку.

Полные primary50 и all-CLOSED метрики каждой когорты: `cohort_metrics.csv`. Все cohort case ledgers сохранены в final root, включая варианты, которые не вошли в union.

## Первые50: все сделки

Даты Asia/Yekaterinburg(+05). Полные physical IDs, READY/fill-known/exit, HTF/local POI, raid, OF, PD/OTE, source citations, targets/fills и расходы: [first50.csv](data/reports/source_permitted_analysis_2026_10_10/first50.csv). Все доступные union FILLED/OPEN без потери полей: [all_physical_union_cases.csv.gz](data/reports/source_permitted_analysis_2026_10_10/all_physical_union_cases.csv.gz); gzip сохраняет полный CSV и позволяет опубликовать его в GitHub.

| # | Physical ID | Path | Symbol / side / HTF-LTF | Fill interval start(+05) | Entry reference | OriginalSL | Source targets | Exit known(+05) | W/L/BE | R | Net |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 4beb11bfcd78b366f0e1d34d | SFP_BOS_POI | ADAUSDT LONG 15/5 | 2026-01-26T00:15:00+05:00 | 0.33875 | 0.3379 | [0.3456] | 2026-01-26T00:20:00+05:00 | LOSS | -1 | -23.4 |
| 2 | e793ed795d604c40324fecdd | SFP_BOS_POI | ETHUSDT LONG 15/5 | 2026-01-26T03:20:00+05:00 | 2799.57 | 2788 | [2831.0] | 2026-01-26T04:05:00+05:00 | LOSS | -1 | -23.4 |
| 3 | 8fd9c5d1e344ee110f3b4582 | SFP_BOS_POI | LINKUSDT LONG 15/5 | 2026-01-26T03:50:00+05:00 | 11.407 | 11.354 | [11.538] | 2026-01-26T05:05:00+05:00 | WIN | 1.5818832 | 37.016067 |
| 4 | 83f33faadb7b679deef2d2c9 | SFP_BOS_POI | ETHUSDT SHORT 15/5 | 2026-01-26T05:05:00+05:00 | 2833.66 | 2944.44 | [2805.6] | 2026-01-26T20:15:00+05:00 | LOSS | -1 | -23.4 |
| 5 | de6b6f7d970dd7b829bbb09d | SFP_BOS_POI | BTCUSDT SHORT 15/5 | 2026-01-26T07:20:00+05:00 | 87622.8 | 87780.3 | [87230.0] | 2026-01-26T07:25:00+05:00 | LOSS | -1 | -23.4 |
| 6 | e3307ba6330fe00cecca532e | SFP_BOS_POI | BNBUSDT SHORT 15/5 | 2026-01-26T07:20:00+05:00 | 873.25 | 875.4 | [864.5] | 2026-01-26T13:25:00+05:00 | LOSS | -1 | -23.4 |
| 7 | efc4e1dbbac162e7e7e9040f | SFP_BOS_POI | ADAUSDT SHORT 15/5 | 2026-01-26T09:20:00+05:00 | 0.34815 | 0.3494 | [0.3434] | 2026-01-26T09:30:00+05:00 | LOSS | -1 | -23.4 |
| 8 | 0049eeedadea3b1885a3de41 | SFP_BOS_POI | LINKUSDT SHORT 15/5 | 2026-01-26T09:25:00+05:00 | 11.8155 | 11.859 | [11.754] | 2026-01-26T10:00:00+05:00 | WIN | 0.68297048 | 15.981509 |
| 9 | f198f5e0c7b24786005b65f2 | SFP_BOS_POI | XRPUSDT LONG 15/5 | 2026-01-26T10:05:00+05:00 | 1.87575 | 1.867 | [1.8932] | 2026-01-26T13:25:00+05:00 | WIN | 1.2291038 | 28.761029 |
| 10 | 73d1573cfcd6ec7ed62f5fd8 | SFP_BOS_POI | DOGEUSDT LONG 15/5 | 2026-01-26T11:00:00+05:00 | 0.121335 | 0.11842 | [0.12174] | 2026-01-26T11:55:00+05:00 | WIN | 0.067767399 | 1.5857571 |
| 11 | 79288829112c3becb295819d | SFP_BOS_POI | SOLUSDT SHORT 60/5 | 2026-01-26T11:05:00+05:00 | 122.55 | 123.57 | [119.5] | 2026-01-26T19:40:00+05:00 | LOSS | -1 | -23.4 |
| 12 | 8e6d539eed30b05fe8253e54 | SFP_BOS_POI | LINKUSDT SHORT 15/5 | 2026-01-26T11:25:00+05:00 | 11.774 | 11.824 | [11.716] | 2026-01-26T11:50:00+05:00 | LOSS | -1 | -23.4 |
| 13 | 316bff9b33cca2b7708de6a2 | SFP_BOS_POI | AVAXUSDT SHORT 15/5 | 2026-01-26T11:25:00+05:00 | 11.5985 | 11.647 | [11.547] | 2026-01-26T11:50:00+05:00 | LOSS | -1 | -23.4 |
| 14 | 7247656902341b57f63d3dfe | SFP_BOS_POI | LTCUSDT SHORT 15/5 | 2026-01-26T11:30:00+05:00 | 67.815 | 68.14 | [65.91] | 2026-01-26T12:20:00+05:00 | LOSS | -1 | -23.4 |
| 15 | 843e026e13b90f5c9772ef3d | SFP_BOS_POI | DOGEUSDT SHORT 60/5 | 2026-01-26T12:15:00+05:00 | 0.12185 | 0.12292 | [0.12061] | 2026-01-26T14:40:00+05:00 | WIN | 0.82636974 | 19.337052 |
| 16 | 29365509dea8948d4a3ba512 | RANGE_AGGRESSIVE_EXTERNAL_POI | AVAXUSDT SHORT 15/5 | 2026-01-26T12:15:00+05:00 | 11.69 | 11.743 | [11.547, 11.494000000000002] | 2026-01-26T13:25:00+05:00 | LOSS | -1 | -23.4 |
| 17 | 53afffe3d443f6237c2eb896 | DEMAND_SUPPLY | ADAUSDT LONG 15/5 | 2026-01-26T12:45:00+05:00 | 0.34765 | 0.3469 | [0.3521] | 2026-01-26T14:10:00+05:00 | LOSS | -1 | -23.4 |
| 18 | 8c7cc254519cde0b0f0439cd | SFP_BOS_POI | LINKUSDT SHORT 15/5 | 2026-01-26T12:50:00+05:00 | 11.846 | 11.876 | [11.8] | 2026-01-26T13:25:00+05:00 | LOSS | -1 | -23.4 |
| 19 | 95e70737fcb2b071038d15d0 | SFP_BOS_POI | AVAXUSDT SHORT 15/5 | 2026-01-26T12:50:00+05:00 | 11.6765 | 11.711 | [11.605] | 2026-01-26T13:25:00+05:00 | LOSS | -1 | -23.4 |
| 20 | d0775ec1ac6ec4f2a51711f8 | SFP_BOS_POI | DOGEUSDT SHORT 15/5 | 2026-01-26T13:20:00+05:00 | 0.12168 | 0.12197 | [0.12061] | 2026-01-26T13:25:00+05:00 | LOSS | -1 | -23.4 |
| 21 | 1cc45b6dd9433ba92cb0ddb7 | SFP_BOS_POI | XRPUSDT SHORT 60/5 | 2026-01-26T15:05:00+05:00 | 1.88725 | 1.8963 | [1.8516] | 2026-01-26T17:05:00+05:00 | LOSS | -1 | -23.4 |
| 22 | be24cce4206ea3d6ff74b390 | SFP_BOS_POI | BNBUSDT SHORT 60/5 | 2026-01-26T16:40:00+05:00 | 872.15 | 877.4 | [864.5] | 2026-01-26T20:15:00+05:00 | LOSS | -1 | -23.4 |
| 23 | dae36500f49f96a8cc8a041e | RANGE_AGGRESSIVE_EXTERNAL_POI | XRPUSDT SHORT 15/5 | 2026-01-26T17:00:00+05:00 | 1.897 | 1.9023 | [1.8842, 1.8752000000000002] | 2026-01-26T18:15:00+05:00 | LOSS | -1 | -23.4 |
| 24 | 0e736ed150b29a6cb52118c0 | SFP_BOS_POI | BTCUSDT SHORT 60/5 | 2026-01-26T17:00:00+05:00 | 87904.45 | 87999.8 | [86997.7] | 2026-01-26T18:35:00+05:00 | LOSS | -1 | -23.4 |
| 25 | ba31bd066aa070c984148fe5 | SFP_BOS_POI | ETHUSDT SHORT 15/5 | 2026-01-26T17:50:00+05:00 | 2900.435 | 2914.62 | [2877.12] | 2026-01-26T19:05:00+05:00 | LOSS | -1 | -23.4 |
| 26 | 2c91440ce2bbfa7f33abee58 | SFP_BOS_POI | BTCUSDT LONG 15/5 | 2026-01-26T18:05:00+05:00 | 87666.6 | 87555 | [87968.4] | 2026-01-26T18:35:00+05:00 | WIN | 0.64061391 | 14.990365 |
| 27 | 1f72b699fcf33115b65788a2 | SFP_BOS_POI | AVAXUSDT SHORT 60/15 | 2026-01-26T18:10:00+05:00 | 11.7055 | 11.779 | [11.46] | 2026-01-26T19:40:00+05:00 | LOSS | -1 | -23.4 |
| 28 | cf5e3a0f828f7e5953efb04f | SFP_BOS_POI | ADAUSDT SHORT 60/5 | 2026-01-26T18:55:00+05:00 | 0.3494 | 0.3516 | [0.3434] | 2026-01-26T19:40:00+05:00 | LOSS | -1 | -23.4 |
| 29 | 9940394c36fffeb7ba0d5fe7 | RANGE_AGGRESSIVE_EXTERNAL_POI | LINKUSDT SHORT 15/5 | 2026-01-26T19:30:00+05:00 | 11.867 | 11.885 | [11.759000000000002, 11.716] | 2026-01-26T19:35:00+05:00 | LOSS | -1 | -23.4 |
| 30 | 159fc85a1fe55eaf30b7fd48 | RANGE_AGGRESSIVE_EXTERNAL_POI | ETHUSDT SHORT 15/5 | 2026-01-26T20:10:00+05:00 | 2939.61 | 2944.44 | [2855.29, 2840.0000000000005] | 2026-01-26T20:15:00+05:00 | LOSS | -1 | -23.4 |
| 31 | 99561e776653761306e6ae3e | SFP_BOS_POI | ETHUSDT SHORT 60/5 | 2026-01-26T23:30:00+05:00 | 2928.5 | 2950 | [2836.33] | 2026-01-27T09:15:00+05:00 | LOSS | -1 | -23.4 |
| 32 | b1ed73ca2d0cd7a1e85967ae | SFP_BOS_POI | BTCUSDT SHORT 60/5 | 2026-01-26T23:35:00+05:00 | 88298.55 | 88827 | [86997.7] | 2026-01-27T08:00:00+05:00 | LOSS | -1 | -23.4 |
| 33 | 71a5c1ba9cf40d5e3ad7dcd5 | SFP_BOS_POI | SOLUSDT SHORT 60/5 | 2026-01-27T00:35:00+05:00 | 124.485 | 125.59 | [119.5] | 2026-01-27T21:10:00+05:00 | LOSS | -1 | -23.4 |
| 34 | bc0f366e14839dce975728cd | SFP_BOS_POI | AVAXUSDT LONG 15/5 | 2026-01-27T01:15:00+05:00 | 11.664 | 11.597 | [11.92] | 2026-01-27T19:50:00+05:00 | LOSS | -1 | -23.4 |
| 35 | 7cc1849b443c20d11d863c74 | SFP_BOS_POI | ETHUSDT LONG 15/5 | 2026-01-27T02:05:00+05:00 | 2895.9 | 2872.93 | [2917.61] | 2026-01-27T02:45:00+05:00 | WIN | 0.61842136 | 14.47106 |
| 36 | 97e07f2c264cd9a3a55a4846 | SFP_BOS_POI | BTCUSDT LONG 15/5 | 2026-01-27T02:20:00+05:00 | 87741 | 86923.3 | [87864.4] | 2026-01-27T02:30:00+05:00 | LOSS | -0.017843892 | -0.41754708 |
| 37 | 1018b68638584a429d2a7d4f | SFP_BOS_POI | ETHUSDT LONG 15/5 | 2026-01-27T02:20:00+05:00 | 2903.265 | 2883.89 | [2917.61] | 2026-01-27T02:45:00+05:00 | WIN | 0.40359976 | 9.4442343 |
| 38 | 9bd6c7524cd1a0324222be16 | SFP_BOS_POI | LTCUSDT SHORT 15/5 | 2026-01-27T02:40:00+05:00 | 69.455 | 69.89 | [65.91] | 2026-01-27T04:35:00+05:00 | LOSS | -1 | -23.4 |
| 39 | a8fc4081e49473119e2bf320 | SFP_BOS_POI | AVAXUSDT SHORT 15/5 | 2026-01-27T02:40:00+05:00 | 11.748 | 11.903 | [11.547] | 2026-01-27T21:45:00+05:00 | LOSS | -1 | -23.4 |
| 40 | 813b7645084f665dbd960889 | SFP_BOS_POI | BTCUSDT SHORT 15/5 | 2026-01-27T02:40:00+05:00 | 88135.55 | 88827 | [87604.0] | 2026-01-27T08:00:00+05:00 | LOSS | -1 | -23.4 |
| 41 | d8c64cffdb56e9a1a7873b1b | SFP_BOS_POI | LINKUSDT SHORT 60/5 | 2026-01-27T02:40:00+05:00 | 11.965 | 12.122 | [11.648] | 2026-01-27T21:15:00+05:00 | LOSS | -1 | -23.4 |
| 42 | e34f17a44562ee6d8c5f4309 | SFP_BOS_POI | LINKUSDT SHORT 15/5 | 2026-01-27T02:40:00+05:00 | 12.029 | 12.122 | [11.716] | 2026-01-27T21:15:00+05:00 | LOSS | -1 | -23.4 |
| 43 | c75eb5279f9e2d27bc145a6d | SFP_BOS_POI | SOLUSDT SHORT 15/5 | 2026-01-27T04:30:00+05:00 | 124.47 | 124.82 | [123.89] | 2026-01-27T05:10:00+05:00 | WIN | 0.69401134 | 16.239865 |
| 44 | dfb4329d2919bba9601d4606 | SFP_BOS_POI | BNBUSDT SHORT 60/5 | 2026-01-27T06:30:00+05:00 | 879.2 | 881.3 | [875.5] | 2026-01-27T07:05:00+05:00 | LOSS | -1 | -23.4 |
| 45 | 9cd9e46018545ec02ca4e2ed | SFP_BOS_POI | SOLUSDT SHORT 240/5 | 2026-01-27T07:35:00+05:00 | 124.89 | 125.59 | [121.5] | 2026-01-27T21:10:00+05:00 | LOSS | -1 | -23.4 |
| 46 | d208c71af5d1284f1fa5abae | RANGE_AGGRESSIVE_EXTERNAL_POI | LINKUSDT SHORT 15/5 | 2026-01-27T07:35:00+05:00 | 12.0135 | 12.04 | [11.979, 11.787000000000003] | 2026-01-27T07:45:00+05:00 | LOSS | -1 | -23.4 |
| 47 | 91e9ad2f57fbc175b0c30f83 | OB_CONSERVATIVE_BOS_POI | AVAXUSDT LONG 15/5 | 2026-01-27T08:45:00+05:00 | 11.784 | 11.682 | [11.92] | 2026-01-27T14:20:00+05:00 | LOSS | -1 | -23.4 |
| 48 | 1b27461ea78413e7eeb66160 | SFP_BOS_POI | DOGEUSDT SHORT 60/5 | 2026-01-27T09:10:00+05:00 | 0.12314 | 0.12381 | [0.1225] | 2026-01-27T09:55:00+05:00 | WIN | 0.51119005 | 11.961847 |
| 49 | 98a6a30dd7a75fdd02d36692 | SFP_BOS_POI | ADAUSDT SHORT 15/5 | 2026-01-27T09:10:00+05:00 | 0.354 | 0.355 | [0.3476] | 2026-01-27T18:50:00+05:00 | WIN | 3.7255745 | 87.178443 |
| 50 | 0a1a11208340cada8878d986 | SFP_BOS_POI | AVAXUSDT SHORT 15/5 | 2026-01-27T09:10:00+05:00 | 11.808 | 11.845 | [11.753] | 2026-01-27T09:55:00+05:00 | WIN | 0.64645301 | 15.127 |

## Breakdown primary50

```json
{
  "POI": {
    "DEMAND": {
      "AvgHoldingSeconds": 5100.0,
      "AvgLoss": 23.400000000000006,
      "AvgR": -1.0000000000000002,
      "AvgWin": null,
      "BE": 0,
      "CLOSED": 1,
      "Expectancy": -23.400000000000006,
      "Fees": 7.468738269211259,
      "GrossAfterSlippageBeforeFees": -15.931261730788744,
      "GrossPnL": -13.44168284538578,
      "Losses": 1,
      "MaxDrawdown": 23.400000000000006,
      "MaxDrawdownFraction": null,
      "MaxLosingStreak": 1,
      "MaxWinningStreak": 0,
      "MedianR": -1.0000000000000002,
      "NetPnL": -23.400000000000006,
      "PayoffRatio": null,
      "ProfitFactor": 0.0,
      "Slippage": 2.4895788854029646,
      "WinRate": 0.0,
      "Wins": 0,
      "drawdown_scope": "CUMULATIVE_INDEPENDENT_CASE_NET_PNL_BY_EXIT_TIME; NOT_SHARED_NAV"
    },
    "ORDER_BLOCK": {
      "AvgHoldingSeconds": 20100.0,
      "AvgLoss": 23.400000000000002,
      "AvgR": -1.0,
      "AvgWin": null,
      "BE": 0,
      "CLOSED": 1,
      "Expectancy": -23.400000000000002,
      "Fees": 2.727956071448382,
      "GrossAfterSlippageBeforeFees": -20.67204392855162,
      "GrossPnL": -19.76272602857818,
      "Losses": 1,
      "MaxDrawdown": 23.400000000000002,
      "MaxDrawdownFraction": null,
      "MaxLosingStreak": 1,
      "MaxWinningStreak": 0,
      "MedianR": -1.0,
      "NetPnL": -23.400000000000002,
      "PayoffRatio": null,
      "ProfitFactor": 0.0,
      "Slippage": 0.9093178999734428,
      "WinRate": 0.0,
      "Wins": 0,
      "drawdown_scope": "CUMULATIVE_INDEPENDENT_CASE_NET_PNL_BY_EXIT_TIME; NOT_SHARED_NAV"
    },
    "RANGE_POI": {
      "AvgHoldingSeconds": 1980.0,
      "AvgLoss": 23.400000000000002,
      "AvgR": -1.0,
      "AvgWin": null,
      "BE": 0,
      "CLOSED": 5,
      "Expectancy": -23.400000000000002,
      "Fees": 36.039374430683246,
      "GrossAfterSlippageBeforeFees": -80.96062556931676,
      "GrossPnL": -68.94750351699146,
      "Losses": 5,
      "MaxDrawdown": 117.00000000000003,
      "MaxDrawdownFraction": null,
      "MaxLosingStreak": 5,
      "MaxWinningStreak": 0,
      "MedianR": -1.0,
      "NetPnL": -117.0,
      "PayoffRatio": null,
      "ProfitFactor": 0.0,
      "Slippage": 12.013122052325294,
      "WinRate": 0.0,
      "Wins": 0,
      "drawdown_scope": "CUMULATIVE_INDEPENDENT_CASE_NET_PNL_BY_EXIT_TIME; NOT_SHARED_NAV"
    },
    "SFP": {
      "AvgHoldingSeconds": 16876.74418604651,
      "AvgLoss": 22.658630550915497,
      "AvgR": -0.42767175227431126,
      "AvgWin": 22.67451916166403,
      "BE": 0,
      "CLOSED": 43,
      "Expectancy": -10.007519003218885,
      "Fees": 197.0901398277488,
      "GrossAfterSlippageBeforeFees": -233.23317731066322,
      "GrossPnL": -167.53647073621337,
      "Losses": 31,
      "MaxDrawdown": 430.3233171384119,
      "MaxDrawdownFraction": null,
      "MaxLosingStreak": 7,
      "MaxWinningStreak": 3,
      "MedianR": -1.0,
      "NetPnL": -430.32331713841205,
      "PayoffRatio": 1.0007012167267935,
      "ProfitFactor": 0.3873682129265007,
      "Slippage": 65.69670657444986,
      "WinRate": 0.27906976744186046,
      "Wins": 12,
      "drawdown_scope": "CUMULATIVE_INDEPENDENT_CASE_NET_PNL_BY_EXIT_TIME; NOT_SHARED_NAV"
    }
  },
  "direction": {
    "LONG": {
      "AvgHoldingSeconds": 10100.0,
      "AvgLoss": 19.569591179730057,
      "AvgR": -0.0397045374433829,
      "AvgWin": 17.711418827379738,
      "BE": 0,
      "CLOSED": 12,
      "Expectancy": -0.9290861761751597,
      "Fees": 54.591336202303296,
      "GrossAfterSlippageBeforeFees": 43.44230208820137,
      "GrossPnL": 61.63941662120984,
      "Losses": 6,
      "MaxDrawdown": 46.80000000000001,
      "MaxDrawdownFraction": null,
      "MaxLosingStreak": 2,
      "MaxWinningStreak": 3,
      "MedianR": 0.024961753157410768,
      "NetPnL": -11.149034114101916,
      "PayoffRatio": 0.9050479728838182,
      "ProfitFactor": 0.9050479728838182,
      "Slippage": 18.19711453300847,
      "WinRate": 0.5,
      "Wins": 6,
      "drawdown_scope": "CUMULATIVE_INDEPENDENT_CASE_NET_PNL_BY_EXIT_TIME; NOT_SHARED_NAV"
    },
    "SHORT": {
      "AvgHoldingSeconds": 16831.57894736842,
      "AvgLoss": 23.400000000000002,
      "AvgR": -0.6556166025914418,
      "AvgWin": 27.63761949594832,
      "BE": 0,
      "CLOSED": 38,
      "Expectancy": -15.34142850063974,
      "Fees": 188.7348723967884,
      "GrossAfterSlippageBeforeFees": -394.2394106275217,
      "GrossPnL": -331.3277997483786,
      "Losses": 32,
      "MaxDrawdown": 582.9742830243098,
      "MaxDrawdownFraction": null,
      "MaxLosingStreak": 21,
      "MaxWinningStreak": 3,
      "MedianR": -1.0,
      "NetPnL": -582.9742830243101,
      "PayoffRatio": 1.1810948502542016,
      "ProfitFactor": 0.22145528442266282,
      "Slippage": 62.9116108791431,
      "WinRate": 0.15789473684210525,
      "Wins": 6,
      "drawdown_scope": "CUMULATIVE_INDEPENDENT_CASE_NET_PNL_BY_EXIT_TIME; NOT_SHARED_NAV"
    }
  },
  "mapping": {
    "15/5": {
      "AvgHoldingSeconds": 11866.666666666666,
      "AvgLoss": 22.51605950301463,
      "AvgR": -0.4090956982268166,
      "AvgWin": 24.079533089211004,
      "BE": 0,
      "CLOSED": 36,
      "Expectancy": -9.572839338507508,
      "Fees": 185.70957815456757,
      "GrossAfterSlippageBeforeFees": -158.91263803170276,
      "GrossPnL": -97.00944919389892,
      "Losses": 26,
      "MaxDrawdown": 361.6006589566788,
      "MaxDrawdownFraction": null,
      "MaxLosingStreak": 10,
      "MaxWinningStreak": 3,
      "MedianR": -1.0,
      "NetPnL": -344.6222161862703,
      "PayoffRatio": 1.0694381530652397,
      "ProfitFactor": 0.41132236656355375,
      "Slippage": 61.90318883780386,
      "WinRate": 0.2777777777777778,
      "Wins": 10,
      "drawdown_scope": "CUMULATIVE_INDEPENDENT_CASE_NET_PNL_BY_EXIT_TIME; NOT_SHARED_NAV"
    },
    "240/5": {
      "AvgHoldingSeconds": 48900.0,
      "AvgLoss": 23.400000000000002,
      "AvgR": -1.0,
      "AvgWin": null,
      "BE": 0,
      "CLOSED": 1,
      "Expectancy": -23.400000000000002,
      "Fees": 3.90582333483363,
      "GrossAfterSlippageBeforeFees": -19.49417666516637,
      "GrossPnL": -18.192236281245076,
      "Losses": 1,
      "MaxDrawdown": 23.400000000000002,
      "MaxDrawdownFraction": null,
      "MaxLosingStreak": 1,
      "MaxWinningStreak": 0,
      "MedianR": -1.0,
      "NetPnL": -23.400000000000002,
      "PayoffRatio": null,
      "ProfitFactor": 0.0,
      "Slippage": 1.301940383921295,
      "WinRate": 0.0,
      "Wins": 0,
      "drawdown_scope": "CUMULATIVE_INDEPENDENT_CASE_NET_PNL_BY_EXIT_TIME; NOT_SHARED_NAV"
    },
    "60/15": {
      "AvgHoldingSeconds": 5400.0,
      "AvgLoss": 23.4,
      "AvgR": -0.9999999999999999,
      "AvgWin": null,
      "BE": 0,
      "CLOSED": 1,
      "Expectancy": -23.4,
      "Fees": 3.5727720178675226,
      "GrossAfterSlippageBeforeFees": -19.827227982132477,
      "GrossPnL": -18.636304721629077,
      "Losses": 1,
      "MaxDrawdown": 23.4,
      "MaxDrawdownFraction": null,
      "MaxLosingStreak": 1,
      "MaxWinningStreak": 0,
      "MedianR": -0.9999999999999999,
      "NetPnL": -23.4,
      "PayoffRatio": null,
      "ProfitFactor": 0.0,
      "Slippage": 1.1909232605033995,
      "WinRate": 0.0,
      "Wins": 0,
      "drawdown_scope": "CUMULATIVE_INDEPENDENT_CASE_NET_PNL_BY_EXIT_TIME; NOT_SHARED_NAV"
    },
    "60/5": {
      "AvgHoldingSeconds": 23275.0,
      "AvgLoss": 23.400000000000002,
      "AvgR": -0.7218700176358324,
      "AvgWin": 15.64944952392915,
      "BE": 0,
      "CLOSED": 12,
      "Expectancy": -16.891758412678477,
      "Fees": 50.138035091822985,
      "GrossAfterSlippageBeforeFees": -152.56306586031874,
      "GrossPnL": -135.8503929303957,
      "Losses": 10,
      "MaxDrawdown": 222.03815293998403,
      "MaxDrawdownFraction": null,
      "MaxLosingStreak": 9,
      "MaxWinningStreak": 1,
      "MedianR": -1.0,
      "NetPnL": -202.70110095214173,
      "PayoffRatio": 0.6687798941850064,
      "ProfitFactor": 0.13375597883700127,
      "Slippage": 16.712672929923013,
      "WinRate": 0.16666666666666666,
      "Wins": 2,
      "drawdown_scope": "CUMULATIVE_INDEPENDENT_CASE_NET_PNL_BY_EXIT_TIME; NOT_SHARED_NAV"
    }
  },
  "path": {
    "DEMAND_SUPPLY": {
      "AvgHoldingSeconds": 5100.0,
      "AvgLoss": 23.400000000000006,
      "AvgR": -1.0000000000000002,
      "AvgWin": null,
      "BE": 0,
      "CLOSED": 1,
      "Expectancy": -23.400000000000006,
      "Fees": 7.468738269211259,
      "GrossAfterSlippageBeforeFees": -15.931261730788744,
      "GrossPnL": -13.44168284538578,
      "Losses": 1,
      "MaxDrawdown": 23.400000000000006,
      "MaxDrawdownFraction": null,
      "MaxLosingStreak": 1,
      "MaxWinningStreak": 0,
      "MedianR": -1.0000000000000002,
      "NetPnL": -23.400000000000006,
      "PayoffRatio": null,
      "ProfitFactor": 0.0,
      "Slippage": 2.4895788854029646,
      "WinRate": 0.0,
      "Wins": 0,
      "drawdown_scope": "CUMULATIVE_INDEPENDENT_CASE_NET_PNL_BY_EXIT_TIME; NOT_SHARED_NAV"
    },
    "OB_CONSERVATIVE_BOS_POI": {
      "AvgHoldingSeconds": 20100.0,
      "AvgLoss": 23.400000000000002,
      "AvgR": -1.0,
      "AvgWin": null,
      "BE": 0,
      "CLOSED": 1,
      "Expectancy": -23.400000000000002,
      "Fees": 2.727956071448382,
      "GrossAfterSlippageBeforeFees": -20.67204392855162,
      "GrossPnL": -19.76272602857818,
      "Losses": 1,
      "MaxDrawdown": 23.400000000000002,
      "MaxDrawdownFraction": null,
      "MaxLosingStreak": 1,
      "MaxWinningStreak": 0,
      "MedianR": -1.0,
      "NetPnL": -23.400000000000002,
      "PayoffRatio": null,
      "ProfitFactor": 0.0,
      "Slippage": 0.9093178999734428,
      "WinRate": 0.0,
      "Wins": 0,
      "drawdown_scope": "CUMULATIVE_INDEPENDENT_CASE_NET_PNL_BY_EXIT_TIME; NOT_SHARED_NAV"
    },
    "RANGE_AGGRESSIVE_EXTERNAL_POI": {
      "AvgHoldingSeconds": 1980.0,
      "AvgLoss": 23.400000000000002,
      "AvgR": -1.0,
      "AvgWin": null,
      "BE": 0,
      "CLOSED": 5,
      "Expectancy": -23.400000000000002,
      "Fees": 36.039374430683246,
      "GrossAfterSlippageBeforeFees": -80.96062556931676,
      "GrossPnL": -68.94750351699146,
      "Losses": 5,
      "MaxDrawdown": 117.00000000000003,
      "MaxDrawdownFraction": null,
      "MaxLosingStreak": 5,
      "MaxWinningStreak": 0,
      "MedianR": -1.0,
      "NetPnL": -117.0,
      "PayoffRatio": null,
      "ProfitFactor": 0.0,
      "Slippage": 12.013122052325294,
      "WinRate": 0.0,
      "Wins": 0,
      "drawdown_scope": "CUMULATIVE_INDEPENDENT_CASE_NET_PNL_BY_EXIT_TIME; NOT_SHARED_NAV"
    },
    "SFP_BOS_POI": {
      "AvgHoldingSeconds": 16876.74418604651,
      "AvgLoss": 22.658630550915497,
      "AvgR": -0.42767175227431126,
      "AvgWin": 22.67451916166403,
      "BE": 0,
      "CLOSED": 43,
      "Expectancy": -10.007519003218885,
      "Fees": 197.0901398277488,
      "GrossAfterSlippageBeforeFees": -233.23317731066322,
      "GrossPnL": -167.53647073621337,
      "Losses": 31,
      "MaxDrawdown": 430.3233171384119,
      "MaxDrawdownFraction": null,
      "MaxLosingStreak": 7,
      "MaxWinningStreak": 3,
      "MedianR": -1.0,
      "NetPnL": -430.32331713841205,
      "PayoffRatio": 1.0007012167267935,
      "ProfitFactor": 0.3873682129265007,
      "Slippage": 65.69670657444986,
      "WinRate": 0.27906976744186046,
      "Wins": 12,
      "drawdown_scope": "CUMULATIVE_INDEPENDENT_CASE_NET_PNL_BY_EXIT_TIME; NOT_SHARED_NAV"
    }
  },
  "setup": {
    "DEMAND_SUPPLY": {
      "AvgHoldingSeconds": 5100.0,
      "AvgLoss": 23.400000000000006,
      "AvgR": -1.0000000000000002,
      "AvgWin": null,
      "BE": 0,
      "CLOSED": 1,
      "Expectancy": -23.400000000000006,
      "Fees": 7.468738269211259,
      "GrossAfterSlippageBeforeFees": -15.931261730788744,
      "GrossPnL": -13.44168284538578,
      "Losses": 1,
      "MaxDrawdown": 23.400000000000006,
      "MaxDrawdownFraction": null,
      "MaxLosingStreak": 1,
      "MaxWinningStreak": 0,
      "MedianR": -1.0000000000000002,
      "NetPnL": -23.400000000000006,
      "PayoffRatio": null,
      "ProfitFactor": 0.0,
      "Slippage": 2.4895788854029646,
      "WinRate": 0.0,
      "Wins": 0,
      "drawdown_scope": "CUMULATIVE_INDEPENDENT_CASE_NET_PNL_BY_EXIT_TIME; NOT_SHARED_NAV"
    },
    "OB_BOS": {
      "AvgHoldingSeconds": 20100.0,
      "AvgLoss": 23.400000000000002,
      "AvgR": -1.0,
      "AvgWin": null,
      "BE": 0,
      "CLOSED": 1,
      "Expectancy": -23.400000000000002,
      "Fees": 2.727956071448382,
      "GrossAfterSlippageBeforeFees": -20.67204392855162,
      "GrossPnL": -19.76272602857818,
      "Losses": 1,
      "MaxDrawdown": 23.400000000000002,
      "MaxDrawdownFraction": null,
      "MaxLosingStreak": 1,
      "MaxWinningStreak": 0,
      "MedianR": -1.0,
      "NetPnL": -23.400000000000002,
      "PayoffRatio": null,
      "ProfitFactor": 0.0,
      "Slippage": 0.9093178999734428,
      "WinRate": 0.0,
      "Wins": 0,
      "drawdown_scope": "CUMULATIVE_INDEPENDENT_CASE_NET_PNL_BY_EXIT_TIME; NOT_SHARED_NAV"
    },
    "RANGE": {
      "AvgHoldingSeconds": 1980.0,
      "AvgLoss": 23.400000000000002,
      "AvgR": -1.0,
      "AvgWin": null,
      "BE": 0,
      "CLOSED": 5,
      "Expectancy": -23.400000000000002,
      "Fees": 36.039374430683246,
      "GrossAfterSlippageBeforeFees": -80.96062556931676,
      "GrossPnL": -68.94750351699146,
      "Losses": 5,
      "MaxDrawdown": 117.00000000000003,
      "MaxDrawdownFraction": null,
      "MaxLosingStreak": 5,
      "MaxWinningStreak": 0,
      "MedianR": -1.0,
      "NetPnL": -117.0,
      "PayoffRatio": null,
      "ProfitFactor": 0.0,
      "Slippage": 12.013122052325294,
      "WinRate": 0.0,
      "Wins": 0,
      "drawdown_scope": "CUMULATIVE_INDEPENDENT_CASE_NET_PNL_BY_EXIT_TIME; NOT_SHARED_NAV"
    },
    "SFP": {
      "AvgHoldingSeconds": 16876.74418604651,
      "AvgLoss": 22.658630550915497,
      "AvgR": -0.42767175227431126,
      "AvgWin": 22.67451916166403,
      "BE": 0,
      "CLOSED": 43,
      "Expectancy": -10.007519003218885,
      "Fees": 197.0901398277488,
      "GrossAfterSlippageBeforeFees": -233.23317731066322,
      "GrossPnL": -167.53647073621337,
      "Losses": 31,
      "MaxDrawdown": 430.3233171384119,
      "MaxDrawdownFraction": null,
      "MaxLosingStreak": 7,
      "MaxWinningStreak": 3,
      "MedianR": -1.0,
      "NetPnL": -430.32331713841205,
      "PayoffRatio": 1.0007012167267935,
      "ProfitFactor": 0.3873682129265007,
      "Slippage": 65.69670657444986,
      "WinRate": 0.27906976744186046,
      "Wins": 12,
      "drawdown_scope": "CUMULATIVE_INDEPENDENT_CASE_NET_PNL_BY_EXIT_TIME; NOT_SHARED_NAV"
    }
  },
  "symbol": {
    "ADAUSDT": {
      "AvgHoldingSeconds": 8700.0,
      "AvgLoss": 23.400000000000006,
      "AvgR": -0.05488510452642235,
      "AvgWin": 87.17844277040861,
      "BE": 0,
      "CLOSED": 5,
      "Expectancy": -1.2843114459182814,
      "Fees": 29.56390756316926,
      "GrossAfterSlippageBeforeFees": 23.142350333577856,
      "GrossPnL": 32.99698750784559,
      "Losses": 4,
      "MaxDrawdown": 93.60000000000002,
      "MaxDrawdownFraction": null,
      "MaxLosingStreak": 4,
      "MaxWinningStreak": 1,
      "MedianR": -1.0,
      "NetPnL": -6.421557229591407,
      "PayoffRatio": 3.7255744773678883,
      "ProfitFactor": 0.9313936193419721,
      "Slippage": 9.854637174267731,
      "WinRate": 0.2,
      "Wins": 1,
      "drawdown_scope": "CUMULATIVE_INDEPENDENT_CASE_NET_PNL_BY_EXIT_TIME; NOT_SHARED_NAV"
    },
    "AVAXUSDT": {
      "AvgHoldingSeconds": 21450.0,
      "AvgLoss": 23.400000000000002,
      "AvgR": -0.7941933739213929,
      "AvgWin": 15.12700040191524,
      "BE": 0,
      "CLOSED": 8,
      "Expectancy": -18.584124949760596,
      "Fees": 33.56088079984747,
      "GrossAfterSlippageBeforeFees": -115.1121187982373,
      "GrossPnL": -103.92516268862963,
      "Losses": 7,
      "MaxDrawdown": 148.67299959808477,
      "MaxDrawdownFraction": null,
      "MaxLosingStreak": 7,
      "MaxWinningStreak": 1,
      "MedianR": -1.0,
      "NetPnL": -148.67299959808477,
      "PayoffRatio": 0.6464530086288564,
      "ProfitFactor": 0.09235042980412234,
      "Slippage": 11.186956109607674,
      "WinRate": 0.125,
      "Wins": 1,
      "drawdown_scope": "CUMULATIVE_INDEPENDENT_CASE_NET_PNL_BY_EXIT_TIME; NOT_SHARED_NAV"
    },
    "BNBUSDT": {
      "AvgHoldingSeconds": 12300.0,
      "AvgLoss": 23.400000000000002,
      "AvgR": -1.0,
      "AvgWin": null,
      "BE": 0,
      "CLOSED": 3,
      "Expectancy": -23.400000000000002,
      "Fees": 17.657094678313797,
      "GrossAfterSlippageBeforeFees": -52.54290532168621,
      "GrossPnL": -46.65720896187082,
      "Losses": 3,
      "MaxDrawdown": 70.20000000000002,
      "MaxDrawdownFraction": null,
      "MaxLosingStreak": 3,
      "MaxWinningStreak": 0,
      "MedianR": -1.0,
      "NetPnL": -70.20000000000002,
      "PayoffRatio": null,
      "ProfitFactor": 0.0,
      "Slippage": 5.885696359815386,
      "WinRate": 0.0,
      "Wins": 0,
      "drawdown_scope": "CUMULATIVE_INDEPENDENT_CASE_NET_PNL_BY_EXIT_TIME; NOT_SHARED_NAV"
    },
    "BTCUSDT": {
      "AvgHoldingSeconds": 9650.0,
      "AvgLoss": 18.803509415676068,
      "AvgR": -0.5628716638077487,
      "AvgWin": 14.990365479772425,
      "BE": 0,
      "CLOSED": 6,
      "Expectancy": -13.171196933101319,
      "Fees": 37.79305558815574,
      "GrossAfterSlippageBeforeFees": -41.23412601045218,
      "GrossPnL": -28.636441959859027,
      "Losses": 5,
      "MaxDrawdown": 79.02718159860791,
      "MaxDrawdownFraction": null,
      "MaxLosingStreak": 3,
      "MaxWinningStreak": 1,
      "MedianR": -1.0,
      "NetPnL": -79.02718159860791,
      "PayoffRatio": 0.7972110497243291,
      "ProfitFactor": 0.15944220994486583,
      "Slippage": 12.597684050593152,
      "WinRate": 0.16666666666666666,
      "Wins": 1,
      "drawdown_scope": "CUMULATIVE_INDEPENDENT_CASE_NET_PNL_BY_EXIT_TIME; NOT_SHARED_NAV"
    },
    "DOGEUSDT": {
      "AvgHoldingSeconds": 3750.0,
      "AvgLoss": 23.400000000000002,
      "AvgR": 0.10133179673082751,
      "AvgWin": 10.96155205800182,
      "BE": 0,
      "CLOSED": 4,
      "Expectancy": 2.3711640435013637,
      "Fees": 14.817487249001653,
      "GrossAfterSlippageBeforeFees": 24.30214342300711,
      "GrossPnL": 29.24130700899286,
      "Losses": 1,
      "MaxDrawdown": 23.400000000000002,
      "MaxDrawdownFraction": null,
      "MaxLosingStreak": 1,
      "MaxWinningStreak": 2,
      "MedianR": 0.28947872192656293,
      "NetPnL": 9.484656174005455,
      "PayoffRatio": 0.46844239564110335,
      "ProfitFactor": 1.40532718692331,
      "Slippage": 4.939163585985749,
      "WinRate": 0.75,
      "Wins": 3,
      "drawdown_scope": "CUMULATIVE_INDEPENDENT_CASE_NET_PNL_BY_EXIT_TIME; NOT_SHARED_NAV"
    },
    "ETHUSDT": {
      "AvgHoldingSeconds": 14442.857142857143,
      "AvgLoss": 23.400000000000002,
      "AvgR": -0.5682826969642002,
      "AvgWin": 11.957647118632005,
      "BE": 0,
      "CLOSED": 7,
      "Expectancy": -13.297815108962284,
      "Fees": 28.103338409797786,
      "GrossAfterSlippageBeforeFees": -64.98136735293821,
      "GrossPnL": -55.613590107550095,
      "Losses": 5,
      "MaxDrawdown": 93.6,
      "MaxDrawdownFraction": null,
      "MaxLosingStreak": 5,
      "MaxWinningStreak": 2,
      "MedianR": -0.9999999999999999,
      "NetPnL": -93.084705762736,
      "PayoffRatio": 0.5110105606252994,
      "ProfitFactor": 0.20440422425011975,
      "Slippage": 9.36777724538811,
      "WinRate": 0.2857142857142857,
      "Wins": 2,
      "drawdown_scope": "CUMULATIVE_INDEPENDENT_CASE_NET_PNL_BY_EXIT_TIME; NOT_SHARED_NAV"
    },
    "LINKUSDT": {
      "AvgHoldingSeconds": 18112.5,
      "AvgLoss": 23.400000000000002,
      "AvgR": -0.46689328734669033,
      "AvgWin": 26.498788304349787,
      "BE": 0,
      "CLOSED": 8,
      "Expectancy": -10.925302923912554,
      "Fees": 42.7668658113056,
      "GrossAfterSlippageBeforeFees": -44.63555757999484,
      "GrossPnL": -30.37993685809262,
      "Losses": 6,
      "MaxDrawdown": 140.4,
      "MaxDrawdownFraction": null,
      "MaxLosingStreak": 6,
      "MaxWinningStreak": 2,
      "MedianR": -1.0,
      "NetPnL": -87.40242339130043,
      "PayoffRatio": 1.1324268506132387,
      "ProfitFactor": 0.37747561687107956,
      "Slippage": 14.255620721902222,
      "WinRate": 0.25,
      "Wins": 2,
      "drawdown_scope": "CUMULATIVE_INDEPENDENT_CASE_NET_PNL_BY_EXIT_TIME; NOT_SHARED_NAV"
    },
    "LTCUSDT": {
      "AvgHoldingSeconds": 4950.0,
      "AvgLoss": 23.4,
      "AvgR": -1.0,
      "AvgWin": null,
      "BE": 0,
      "CLOSED": 2,
      "Expectancy": -23.4,
      "Fees": 7.980608199142098,
      "GrossAfterSlippageBeforeFees": -38.8193918008579,
      "GrossPnL": -36.15919051417825,
      "Losses": 2,
      "MaxDrawdown": 46.8,
      "MaxDrawdownFraction": null,
      "MaxLosingStreak": 2,
      "MaxWinningStreak": 0,
      "MedianR": -1.0,
      "NetPnL": -46.8,
      "PayoffRatio": null,
      "ProfitFactor": 0.0,
      "Slippage": 2.660201286679658,
      "WinRate": 0.0,
      "Wins": 0,
      "drawdown_scope": "CUMULATIVE_INDEPENDENT_CASE_NET_PNL_BY_EXIT_TIME; NOT_SHARED_NAV"
    },
    "SOLUSDT": {
      "AvgHoldingSeconds": 39075.0,
      "AvgLoss": 23.400000000000002,
      "AvgR": -0.5764971641388222,
      "AvgWin": 16.239865436606244,
      "BE": 0,
      "CLOSED": 4,
      "Expectancy": -13.490033640848441,
      "Fees": 15.782292219589571,
      "GrossAfterSlippageBeforeFees": -38.17784234380419,
      "GrossPnL": -32.91707958729158,
      "Losses": 3,
      "MaxDrawdown": 53.960134563393765,
      "MaxDrawdownFraction": null,
      "MaxLosingStreak": 2,
      "MaxWinningStreak": 1,
      "MedianR": -1.0,
      "NetPnL": -53.960134563393765,
      "PayoffRatio": 0.6940113434447113,
      "ProfitFactor": 0.23133711448157038,
      "Slippage": 5.2607627565126105,
      "WinRate": 0.25,
      "Wins": 1,
      "drawdown_scope": "CUMULATIVE_INDEPENDENT_CASE_NET_PNL_BY_EXIT_TIME; NOT_SHARED_NAV"
    },
    "XRPUSDT": {
      "AvgHoldingSeconds": 7900.0,
      "AvgLoss": 23.400000000000006,
      "AvgR": -0.2569654012635784,
      "AvgWin": 28.7610288312968,
      "BE": 0,
      "CLOSED": 3,
      "Expectancy": -6.012990389567736,
      "Fees": 15.300678080768733,
      "GrossAfterSlippageBeforeFees": -2.7382930879344727,
      "GrossPnL": 2.361933033464794,
      "Losses": 2,
      "MaxDrawdown": 46.80000000000001,
      "MaxDrawdownFraction": null,
      "MaxLosingStreak": 2,
      "MaxWinningStreak": 1,
      "MedianR": -1.0,
      "NetPnL": -18.038971168703206,
      "PayoffRatio": 1.2291037962092648,
      "ProfitFactor": 0.6145518981046324,
      "Slippage": 5.100226121399272,
      "WinRate": 0.3333333333333333,
      "Wins": 1,
      "drawdown_scope": "CUMULATIVE_INDEPENDENT_CASE_NET_PNL_BY_EXIT_TIME; NOT_SHARED_NAV"
    }
  }
}
```

## Сравнение сохранённых этапов

| Stage / metric sample | READY | FILLED | CLOSED all | W/L evaluated | WR | PF | ExpectancyUSDT | AvgR | NetUSDT |
|---|---|---|---|---|---|---|---|---|---|
| OLD7 / independent mappings | 40 | 7 | 7 | 2/5 | 28.571429% | 0.17938437 | -13.742184 | -0.58590946 | -96.195286 |
| fc61f35 / flawed old source policy | 647 | 14 | 13 | 2/11 | 15.3846% | 0.14037608 | -15.416649 | -0.71226448 | -200.41643 |
| 74a6f8d / no primary PDFs | 3 | 0 | 0 | 0/0 | N/A | N/A | N/A | N/A | 0 |
| STRICT_CONSERVATIVE_D46646F | 9 | 0 | 0 | 0/0 | N/A | N/A | N/A | N/A | 0 |
| SOURCE_PERMITTED_UNION / metrics first50 | 19448 | 16351 | 16333 | 12/38 | 24% | 0.31411766 | -11.882466 | -0.50779771 | -594.12332 |

OLD7, fc61f35 и new cases имеют разные entries/exits/risk-account conventions; это не matched profitability uplift. Strict9zero — узкая source-интерпретация, не окончательная оценка всех PDF paths. Архив105 strict artifacts, исходные trades и все старые losses неизменны.

## Полный179 OF bottleneck

```json
{
  "all_original_179_accounted": true,
  "first_old_rejection_reasons": {
    "WAIT_ACTIVE_HTF_ORDER_FLOW": 170,
    "READY": 5,
    "WAIT_FIRST_OPPOSING_POI_FTA": 4
  },
  "new_active_flow_at_same_native_close": 29
}
```

Все179 original liquidity/POI contexts со всеми reason changes и causal old/new OF snapshots сохранены: [strict179_OF_audit.json](data/reports/source_permitted_analysis_2026_10_10/strict179_OF_audit.json). Extra body-break/adverse-pool gates помечены interpretations, не универсальными SOURCE_RULE.

## Все9 старых отмен: fixed quote/SL/targets

| Signal | Symbol/map | Strict known/reason | Classification at strict cancel | Source native cancel |
|---|---|---|---|---|
| a2ce1597eb140da12d811ab2 | SOLUSDT 15/5 | 2026-07-07T17:30:00+00:00 FLOW_DESTINATION_TESTED | SOURCE_INTERPRETATION_GENERIC_LTF_OR_NON_GLOBAL_FTA | {'classification': 'SOURCE_RULE_WITH_DECLARED_BODY_TOUCH_INTERPRETATION', 'cohort': 'CANCEL_SOURCE_POI_INVALIDATION', 'known_at': '2026-07-07T19:00:00+00:00', 'reason': 'SOURCE_POI_OR_FROZEN_HTF_THESIS_INVALIDATED', 'signal_id': 'a2ce1597eb140da12d811ab2', 'source': 'SW9 p2–10; SW5 p3–5; SW22 p6'} |
| 18435abb9bf479f85cb2d2f7 | SOLUSDT 15/5 | 2026-09-03T01:50:00+00:00 CONFIRMED_LTF_STRUCTURE_BROKEN | SOURCE_INTERPRETATION_GENERIC_LTF_OR_NON_GLOBAL_FTA | {'classification': 'SOURCE_RULE_WITH_DECLARED_BODY_TOUCH_INTERPRETATION', 'cohort': 'CANCEL_SOURCE_POI_INVALIDATION', 'known_at': '2026-09-03T15:00:00+00:00', 'reason': 'FIXED_GLOBAL_DESTINATION_TESTED', 'signal_id': '18435abb9bf479f85cb2d2f7', 'source': 'SW9 p2–10; SW5 p3–5; SW22 p6'} |
| 26ebd579151eabf9cc29764e | XRPUSDT 15/5 | 2026-05-27T04:50:00+00:00 CONFIRMED_LTF_STRUCTURE_BROKEN | SOURCE_INTERPRETATION_GENERIC_LTF_OR_NON_GLOBAL_FTA | {'classification': 'SOURCE_RULE_WITH_DECLARED_BODY_TOUCH_INTERPRETATION', 'cohort': 'CANCEL_SOURCE_POI_INVALIDATION', 'known_at': '2026-05-27T06:45:00+00:00', 'reason': 'SOURCE_POI_OR_FROZEN_HTF_THESIS_INVALIDATED', 'signal_id': '26ebd579151eabf9cc29764e', 'source': 'SW9 p2–10; SW5 p3–5; SW22 p6'} |
| 0429a4616fcdc8c1715dc056 | DOGEUSDT 15/5 | 2026-07-07T17:30:00+00:00 GLOBAL_ORDER_FLOW_INACTIVE | SOURCE_INTERPRETATION_GENERIC_LTF_OR_NON_GLOBAL_FTA | {'classification': 'SOURCE_RULE_WITH_DECLARED_BODY_TOUCH_INTERPRETATION', 'cohort': 'CANCEL_SOURCE_POI_INVALIDATION', 'known_at': '2026-07-07T19:00:00+00:00', 'reason': 'SOURCE_POI_OR_FROZEN_HTF_THESIS_INVALIDATED', 'signal_id': '0429a4616fcdc8c1715dc056', 'source': 'SW9 p2–10; SW5 p3–5; SW22 p6'} |
| 3031446d683902755d235932 | DOGEUSDT 15/5 | 2026-08-17T16:45:00+00:00 CONFIRMED_LTF_STRUCTURE_BROKEN | SOURCE_INTERPRETATION_GENERIC_LTF_OR_NON_GLOBAL_FTA | {'classification': 'SOURCE_RULE_WITH_DECLARED_BODY_TOUCH_INTERPRETATION', 'cohort': 'CANCEL_SOURCE_POI_INVALIDATION', 'known_at': '2026-08-17T20:15:00+00:00', 'reason': 'SOURCE_POI_OR_FROZEN_HTF_THESIS_INVALIDATED', 'signal_id': '3031446d683902755d235932', 'source': 'SW9 p2–10; SW5 p3–5; SW22 p6'} |
| 03f04beb4424d34ddc690938 | AVAXUSDT 15/5 | 2026-05-20T16:25:00+00:00 CONFIRMED_LTF_STRUCTURE_BROKEN | SOURCE_INTERPRETATION_GENERIC_LTF_OR_NON_GLOBAL_FTA | {'classification': 'SOURCE_RULE_WITH_DECLARED_BODY_TOUCH_INTERPRETATION', 'cohort': 'CANCEL_SOURCE_POI_INVALIDATION', 'known_at': '2026-05-20T22:15:00+00:00', 'reason': 'SOURCE_POI_OR_FROZEN_HTF_THESIS_INVALIDATED', 'signal_id': '03f04beb4424d34ddc690938', 'source': 'SW9 p2–10; SW5 p3–5; SW22 p6'} |
| 18400ffd6f66057d5f2900c7 | AVAXUSDT 60/15 | 2026-05-30T00:15:00+00:00 CONFIRMED_LTF_STRUCTURE_BROKEN | SOURCE_INTERPRETATION_GENERIC_LTF_OR_NON_GLOBAL_FTA | {'classification': 'SOURCE_RULE_WITH_DECLARED_BODY_TOUCH_INTERPRETATION', 'cohort': 'CANCEL_SOURCE_POI_INVALIDATION', 'known_at': '2026-05-30T02:45:00+00:00', 'reason': 'SOURCE_POI_OR_FROZEN_HTF_THESIS_INVALIDATED', 'signal_id': '18400ffd6f66057d5f2900c7', 'source': 'SW9 p2–10; SW5 p3–5; SW22 p6'} |
| 6c344f059a7c60a550543e0f | ETHUSDT 15/5 | 2026-04-05T04:50:00+00:00 CONFIRMED_LTF_STRUCTURE_BROKEN | SOURCE_INTERPRETATION_GENERIC_LTF_OR_NON_GLOBAL_FTA | {'classification': 'SOURCE_RULE_WITH_DECLARED_BODY_TOUCH_INTERPRETATION', 'cohort': 'CANCEL_SOURCE_POI_INVALIDATION', 'known_at': '2026-04-05T05:30:00+00:00', 'reason': 'SOURCE_POI_OR_FROZEN_HTF_THESIS_INVALIDATED', 'signal_id': '6c344f059a7c60a550543e0f', 'source': 'SW9 p2–10; SW5 p3–5; SW22 p6'} |
| 04fb0127b7b01c6e66209bb7 | BTCUSDT 15/5 | 2026-09-14T16:20:00+00:00 FLOW_DESTINATION_TESTED | SOURCE_INTERPRETATION_GENERIC_LTF_OR_NON_GLOBAL_FTA | {'classification': 'SOURCE_RULE_WITH_DECLARED_BODY_TOUCH_INTERPRETATION', 'cohort': 'CANCEL_SOURCE_POI_INVALIDATION', 'known_at': '2026-09-15T05:15:00+00:00', 'reason': 'SOURCE_POI_OR_FROZEN_HTF_THESIS_INVALIDATED', 'signal_id': '04fb0127b7b01c6e66209bb7', 'source': 'SW9 p2–10; SW5 p3–5; SW22 p6'} |

Фиксированные старые9 планы воспроизведены в двух cancel modes; case outcomes и actual native proof сохранены в [old9_fixed_plan_cancellation_audit.json](data/reports/source_permitted_analysis_2026_10_10/old9_fixed_plan_cancellation_audit.json). Они отдельная controlled sensitivity, не дополнительная primary выборка.

## Все13 fc61f35 cases и старые losses

Прежние10 из11 LOSS остаются false positives именно STRICT_CONSERVATIVE registered projection. Это не переносится автоматически на весь новый source universe. Каждый старый случай проверен на точных old READY/entry cutoffs и всех новых source-valid paths; изменённый допустимый quote/exit не является доказательством source false positive. PnL не использован для подбора правил.

DOGE240/15 `c1bc1cb68a185d4492c8b9e6`: исходная FTA0.09156–0.09271 уже протестирована native5m при CLOSE2026-04-12T20:45UTC, до READY21:00UTC. Старый HTF-only clock сохранил ошибочную freshness. Поэтому точный старый план окончательно false positive registered fresh-FTA contract; допустимая другая formation/quote/FTA остаётся отдельным вариантом, не исправлением старого LOSS задним числом. Прежний verdict UNCERTAIN сохранён в историческом архиве.

| Old ID | Symbol/map | Old W/L Net | Retained strict class | New all-path assessment |
|---|---|---|---|---|
| ca98f11190187b5877332b3a | BTCUSDT 15/5 | LOSS -22.023893 | FALSE_POSITIVE_REGISTERED_SOURCE_IMPLEMENTATION | EXACT_OLD_CASE_NOT_PROVEN_IN_ALL_REGISTERED_SOURCE_PATHS |
| c0eb9c4daf48e1f3e98d72f8 | ETHUSDT 60/15 | LOSS -23.4 | FALSE_POSITIVE_REGISTERED_SOURCE_IMPLEMENTATION | EXACT_OLD_CASE_NOT_PROVEN_IN_ALL_REGISTERED_SOURCE_PATHS |
| 235e7ba6c224826bf8e64cd2 | XRPUSDT 240/15 | LOSS -21.151747 | FALSE_POSITIVE_REGISTERED_SOURCE_IMPLEMENTATION | EXACT_OLD_CASE_NOT_PROVEN_IN_ALL_REGISTERED_SOURCE_PATHS |
| 3fa88b97bdbbf06988a7684b | XRPUSDT 240/5 | WIN 3.7220675 | UNCERTAIN_OR_DIFFERENT_PERMITTED_VARIANT | EXACT_OLD_CASE_NOT_PROVEN_IN_ALL_REGISTERED_SOURCE_PATHS |
| 07b320b636a8d15d4ed8af6d | XRPUSDT 15/5 | WIN 29.005818 | FALSE_POSITIVE_REGISTERED_SOURCE_IMPLEMENTATION | EXACT_OLD_CASE_NOT_PROVEN_IN_ALL_REGISTERED_SOURCE_PATHS |
| c8d326347c6830f75b573f88 | DOGEUSDT 15/5 | LOSS -22.47336 | FALSE_POSITIVE_REGISTERED_SOURCE_IMPLEMENTATION | EXACT_OLD_CASE_NOT_PROVEN_IN_ALL_REGISTERED_SOURCE_PATHS |
| c1bc1cb68a185d4492c8b9e6 | DOGEUSDT 240/15 | LOSS -21.583415 | UNCERTAIN_OR_DIFFERENT_PERMITTED_VARIANT | FALSE_POSITIVE_OLD_FTA_ALREADY_TESTED_AT_READY_NATIVE_5M |
| 25faa78ab0a2eea4d4c48c20 | DOGEUSDT 240/60 | LOSS -20.728712 | FALSE_POSITIVE_REGISTERED_SOURCE_IMPLEMENTATION | EXACT_OLD_CASE_NOT_PROVEN_IN_ALL_REGISTERED_SOURCE_PATHS |
| 9c181eee25ee9e39d8b5a523 | LINKUSDT 60/5 | LOSS -22.932 | FALSE_POSITIVE_REGISTERED_SOURCE_IMPLEMENTATION | EXACT_OLD_CASE_NOT_PROVEN_IN_ALL_REGISTERED_SOURCE_PATHS |
| b58c6bbb565b806e85fa6798 | LINKUSDT 240/15 | LOSS -19.907855 | FALSE_POSITIVE_REGISTERED_SOURCE_IMPLEMENTATION | EXACT_OLD_CASE_NOT_PROVEN_IN_ALL_REGISTERED_SOURCE_PATHS |
| d6b7416116c201f0a70c378c | LINKUSDT 240/15 | LOSS -19.509698 | FALSE_POSITIVE_REGISTERED_SOURCE_IMPLEMENTATION | EXACT_OLD_CASE_NOT_PROVEN_IN_ALL_REGISTERED_SOURCE_PATHS |
| fd05901bf55ee3c53409bed9 | LINKUSDT 240/15 | LOSS -19.119504 | FALSE_POSITIVE_REGISTERED_SOURCE_IMPLEMENTATION | EXACT_OLD_CASE_NOT_PROVEN_IN_ALL_REGISTERED_SOURCE_PATHS |
| d5cd448d6c02f037d76c9d35 | LTCUSDT 60/15 | LOSS -20.314137 | FALSE_POSITIVE_REGISTERED_SOURCE_IMPLEMENTATION | EXACT_OLD_CASE_NOT_PROVEN_IN_ALL_REGISTERED_SOURCE_PATHS |

Полные witnesses и exact-case matching: [old13_all_source_paths_audit.json](data/reports/source_permitted_analysis_2026_10_10/old13_all_source_paths_audit.json). No matching fixed cohort значит exact old case не доказан; это не универсальное отрицание всех discretionary inside prices.

## QA / воспроизводимость / сохранность

548 tests PASS перед final execution, dedicated15paths + physical + source-body tests; compileall/Ruff changed files/mypy PASS. Full-tree Ruff555 inherited findings byte/diagnostic-identical to d466, zero new; old code не переписан ради lint. Реальный nonempty prefix14293bars/all15paths, future mutation4TF; source body qualification и physical mapping также prefix-causal. Independent cross-TF OHLC302362bars:0mismatches. Итоговый ledger/no-lookahead/cost/risk/selection/preservation и exact-resume receipts находятся в `data/reports/source_permitted_qa_2026_10_10`.

Registry7c47621, implementation7f9782f, exact performance parityc8263dd, global physical424d663, native SFP validity/lifecycled87edb1 опубликованы до final outcomes. Все завершённые robustness/controlled-exit/frozen artifacts сохранены без повторного перерасчёта. Final native40 detector manifest и final physical manifest неизменяемы; SHA каждого source/code/data/artifact проверяется.

Все40 detector segments завершены. Последующая provisional all-symbol aggregation остановлена лимитом памяти32GiB до outcomes; исходный log и все artifacts сохранены. Base manifest честно сертифицирует только COMPLETE DETECTOR CORPUS. Primary execution выполнен отдельно с bounded-memory scheduling, опубликованным в096e225: source selection/replay/risk/exits не менялись. На реальном prefix все196 сравниваемых artifacts/38cohorts побайтно совпали с оригинальным исполнителем. См. `BOUNDED_SOURCE_EXECUTION_PROTOCOL.md` и `bounded_execution_real_parity.json`.

```bash
python scripts/run_source_permitted_bybit.py --output data/reports/source_permitted_bybit_2026_10_10 --resume-existing --workers 4
python scripts/run_source_permitted_physical_union.py --source data/reports/source_permitted_bybit_2026_10_10 --output data/reports/source_permitted_physical_bybit_2026_10_10 --resume-existing
```
