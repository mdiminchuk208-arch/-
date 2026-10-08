# Frozen Strategy Engine: robustness research

INSUFFICIENT SAMPLE. Отчёт сформирован 2026-10-09T04:24:46.129847+05:00 (Asia/Yekaterinburg). Рыночные timestamps — UTC.

Canonical `3a9632606f79b4454509a60674eeac3877f77bbf`, policy `0.4.21-causal-limit.3`, все 57 source/config SHA неизменны. TP 40/30/30, исходный SL, cost-adjusted BE после TP1, входы и risk model сохранены. Ни один исследовательский вариант не выбран. BACKTEST/SHADOW virtual only; trade_entry_allowed=false; LIVE отключён.

## DATA

История 2026 Bybit остаётся DEVELOPMENT: 27 974 setups → 40 READY → 7 entries → 7 CLOSED. Добавлены публичные зеркала, а не синтетические свечи. Прямые Bybit/Binance endpoints и официальные archives фактически проверены: proxy HTTP 403; GitHub/raw/public Git LFS доступны. Binance market type не подтверждён upstream endpoint, поэтому этот cohort не назван derivatives или spot. Он не объединяется с Bybit.

34 series, 8,354,318 сохранённых candles, включая производные TF; это не число независимых наблюдений. LINK/AVAX/LTC отсутствуют в новых найденных mirrors, их прежняя development-история сохранена. Binance: 628 public Git LFS Parquet objects, все size/SHA проверены; 5m bars с source_rows≠5 исключены; 15/60/240m получены только из полных UTC-aligned bins. Разрывы не заполнялись. Bybit: исходные 15m и согласованные complete aggregates; 202 расхождения с отдельно сохранёнными native HTF не замаскированы и полностью перечислены в [bybit_htf_independent_check.json](data/reports/robustness_research/bybit_htf_independent_check.json).

| COHORT | SYMBOL | TF MIN | START | END EXCLUSIVE | CANDLES | STORED SHA256 |
| --- | --- | --- | --- | --- | --- | --- |
| bybit | BTCUSDT | 15 | 2020-03-25T10:30:00+00:00 | 2025-12-05T23:30:00+00:00 | 199828 | 5d3fe4a4eb1d147c5f5516944bdbc45a21fb483d0bc667b5a92ed206aa8a6fc9 |
| bybit | BTCUSDT | 60 | 2020-03-25T11:00:00+00:00 | 2025-12-05T23:00:00+00:00 | 49956 | b9ca9cbb33b6e9f72ab03d2d037159bef928ce6c01edcfe41890d2b9704e8cc4 |
| bybit | BTCUSDT | 240 | 2020-03-25T12:00:00+00:00 | 2025-12-05T20:00:00+00:00 | 12488 | e564bd0d869911a0e566623592a2fcbdc2852527098546dad94980ec55a5df47 |
| bybit | ETHUSDT | 15 | 2021-03-15T00:00:00+00:00 | 2025-12-05T23:30:00+00:00 | 165790 | 94c8f3f414ae3bbbe08bc5180f3da88d72c699f8ff88fd8093062078260449f8 |
| bybit | ETHUSDT | 60 | 2021-03-15T00:00:00+00:00 | 2025-12-05T23:00:00+00:00 | 41447 | 1f89f9e0c5bec92772222fb098dceb85ebb3197fbc7921d5c3bbc0032e4771dd |
| bybit | ETHUSDT | 240 | 2021-03-15T00:00:00+00:00 | 2025-12-05T20:00:00+00:00 | 10361 | a69e1afa98f66e56e9a126840f226533598b4853148f988dd8b89865cae8d98e |
| binance | ADAUSDT | 5 | 2018-04-17T04:05:00+00:00 | 2026-01-01T00:00:00+00:00 | 809775 | 36f46ac2caec3fdf0f0e1b8903da7b4e5cb99e8e2cabad33515fa8c65806a140 |
| binance | ADAUSDT | 15 | 2018-04-17T04:15:00+00:00 | 2026-01-01T00:00:00+00:00 | 269920 | f23e3619e50a9d02a4c74a8e0bb9d9e6e8278fba4c9f8839f684be404866ebc1 |
| binance | ADAUSDT | 60 | 2018-04-17T05:00:00+00:00 | 2026-01-01T00:00:00+00:00 | 67470 | 341a852d8b7969cfa50f1b77d2b22c69a8917895b896db48e9ca15defcb3d5c2 |
| binance | ADAUSDT | 240 | 2018-04-17T08:00:00+00:00 | 2026-01-01T00:00:00+00:00 | 16845 | baa499bce6487b46ed4b79c2664a252da91228be884c77c3d44db7e2405f886f |
| binance | BNBUSDT | 5 | 2017-11-06T03:55:00+00:00 | 2026-01-01T00:00:00+00:00 | 855968 | 92746b965bec3c9edc325bc7eac581a398d50b31d2a4e6c1739999d4964445ae |
| binance | BNBUSDT | 15 | 2017-11-06T04:00:00+00:00 | 2026-01-01T00:00:00+00:00 | 285315 | b485e4507cfa75c4f4631dcffc481ca341bda1c7d2c9433298337bb9186e8bd6 |
| binance | BNBUSDT | 60 | 2017-11-06T04:00:00+00:00 | 2026-01-01T00:00:00+00:00 | 71316 | 2d56538e1f9b0822e5974e47ab2a2be1b7b1f296ad7a3857267ed6a5795774e2 |
| binance | BNBUSDT | 240 | 2017-11-06T04:00:00+00:00 | 2026-01-01T00:00:00+00:00 | 17802 | f9af6db868b8dc70241eee277200f04a078cbc8fb2f39ccbb089d636ae07ab9f |
| binance | BTCUSDT | 5 | 2017-08-17T04:00:00+00:00 | 2026-01-01T00:00:00+00:00 | 879211 | c38108e7c9b6e7373eeb0215fb8f6931ec5680b292a32f849860f3ecbccfc684 |
| binance | BTCUSDT | 15 | 2017-08-17T04:00:00+00:00 | 2026-01-01T00:00:00+00:00 | 293063 | 4b0cdd201871bdf017db0f98bd9ffc65fc6f0259ea918ed67046e990005010f6 |
| binance | BTCUSDT | 60 | 2017-08-17T04:00:00+00:00 | 2026-01-01T00:00:00+00:00 | 73253 | 076258bcb69bca42589fbf457ee03b851295541467aec2bf98b873a39746b897 |
| binance | BTCUSDT | 240 | 2017-08-17T04:00:00+00:00 | 2026-01-01T00:00:00+00:00 | 18286 | 7bc3534f0d6c5c12383c9d25b6a5e3d8e55a7e9744f8f647f8d92a76e923a2c4 |
| binance | DOGEUSDT | 5 | 2019-07-05T12:00:00+00:00 | 2026-01-01T00:00:00+00:00 | 682372 | 95c27dc5edfa987507c9c2f93580626a3bdb5d25a256f8a69e9f17e16badac13 |
| binance | DOGEUSDT | 15 | 2019-07-05T12:00:00+00:00 | 2026-01-01T00:00:00+00:00 | 227454 | 44d5e9bdc2891f8fc6e5cf8401ea0b3d1056b9218a510e94ec5ebb009ef815be |
| binance | DOGEUSDT | 60 | 2019-07-05T12:00:00+00:00 | 2026-01-01T00:00:00+00:00 | 56856 | 2ef45f810d7cc4da1425ce09a4370509fc5cb341dd545b2d6a3c65737bd48b89 |
| binance | DOGEUSDT | 240 | 2019-07-05T12:00:00+00:00 | 2026-01-01T00:00:00+00:00 | 14198 | c768f884435c3208a038f5e19323e30b72e114885d41c7f0a1c161ee8ccf3ce9 |
| binance | ETHUSDT | 5 | 2017-08-17T04:00:00+00:00 | 2026-01-01T00:00:00+00:00 | 879211 | cc72df1e0f08ba4ac8ab1c1c8c04145269cad1db40f320690a91dc1b7d956d84 |
| binance | ETHUSDT | 15 | 2017-08-17T04:00:00+00:00 | 2026-01-01T00:00:00+00:00 | 293063 | a2be8bd9ceedb61e11e3b162157e6783dc8c801917fb4c95eb580554fcd68b65 |
| binance | ETHUSDT | 60 | 2017-08-17T04:00:00+00:00 | 2026-01-01T00:00:00+00:00 | 73253 | 440918b3463cbd3662176b8d45ec407f1ede160762efa29f8bae0f7cd2162ec0 |
| binance | ETHUSDT | 240 | 2017-08-17T04:00:00+00:00 | 2026-01-01T00:00:00+00:00 | 18286 | aa6ffc48492a61005156417f77edc3b1983a3c2980558042273e1123d0fded05 |
| binance | SOLUSDT | 5 | 2020-08-11T06:00:00+00:00 | 2026-01-01T00:00:00+00:00 | 566710 | 5bb949fd4dd0d8d3cefd33ecdf9c4d4ab2e3416537780d4a301cb65ac27d62c4 |
| binance | SOLUSDT | 15 | 2020-08-11T06:00:00+00:00 | 2026-01-01T00:00:00+00:00 | 188902 | c5eea456844626d282249f163e1b2b7c44187fa307f701fea28713bc4a667a3a |
| binance | SOLUSDT | 60 | 2020-08-11T06:00:00+00:00 | 2026-01-01T00:00:00+00:00 | 47222 | 1d914af8428e996da307099777f5f41fb31e8b40157c82a2cf43f814883a2b3b |
| binance | SOLUSDT | 240 | 2020-08-11T08:00:00+00:00 | 2026-01-01T00:00:00+00:00 | 11796 | ca9a857c611968e7f656ae2137c7da1639130918980f4f62a7e4813e326aa756 |
| binance | XRPUSDT | 5 | 2018-05-04T08:15:00+00:00 | 2026-01-01T00:00:00+00:00 | 804829 | 9125797c90f5c82dec43a95df45229c9b8781f3bd27a118738f2e22a59f54cec |
| binance | XRPUSDT | 15 | 2018-05-04T08:15:00+00:00 | 2026-01-01T00:00:00+00:00 | 268272 | 9b02abc8cab0cb5417c516a497870b25d58bdf970a14938d5723421557765480 |
| binance | XRPUSDT | 60 | 2018-05-04T09:00:00+00:00 | 2026-01-01T00:00:00+00:00 | 67058 | 57d4f00210a737903b73dfa9274ce92d522880061b5e8472652b8ff7050f978c |
| binance | XRPUSDT | 240 | 2018-05-04T12:00:00+00:00 | 2026-01-01T00:00:00+00:00 | 16742 | fa5f73e0133570181837638d48648f742d90900985103e76d0eb91e0bffd9d01 |

Source repositories, pinned commits, URLs, raw/logical SHA и exclusions: [bybit_dataset_manifest.json](data/reports/robustness_research/bybit_dataset_manifest.json); [binance_dataset_manifest.json](data/reports/robustness_research/binance_dataset_manifest.json).

## SAMPLE / IS-OOS

Правила и chronological splits зафиксированы до внешних результатов. 2026 исключён из external primary. Новая более ранняя история — retrospective frozen-rule holdout, не prospective OOS. Ни в REFERENCE, ни в VALIDATION параметры не обучались и не подбирались.

| COHORT | PERIOD | START | END |
| --- | --- | --- | --- |
| bybit | REFERENCE | 2021-04-08T00:00:00+00:00 | 2024-01-24T00:00:00+00:00 |
| bybit | VALIDATION | 2024-01-24T00:00:00+00:00 | 2024-12-29T00:00:00+00:00 |
| bybit | HOLDOUT | 2024-12-29T00:00:00+00:00 | 2025-12-05T00:00:00+00:00 |
| binance | REFERENCE | 2020-09-05T00:00:00+00:00 | 2023-11-15T00:00:00+00:00 |
| binance | VALIDATION | 2023-11-15T00:00:00+00:00 | 2024-12-08T00:00:00+00:00 |
| binance | HOLDOUT | 2024-12-08T00:00:00+00:00 | 2026-01-01T00:00:00+00:00 |

| COHORT | MAPPING | PERIOD | OBSERVED SETUPS | READY | ENTRIES | CLOSED | LONG | SHORT | FILL RATE |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bybit | 60/15 | REFERENCE | 3651 | 2 | 1 | 1 | 1 | 0 | 50.00% |
| bybit | 60/15 | VALIDATION | 1468 | 2 | 0 | 0 | 0 | 0 | 0.00% |
| bybit | 60/15 | HOLDOUT | 1449 | 5 | 1 | 1 | 1 | 0 | 20.00% |
| bybit | 240/15 | REFERENCE | 1488 | 1 | 1 | 1 | 1 | 0 | 100.00% |
| bybit | 240/15 | VALIDATION | 635 | 1 | 0 | 0 | 0 | 0 | 0.00% |
| bybit | 240/15 | HOLDOUT | 601 | 0 | 0 | 0 | 0 | 0 | — |
| bybit | 240/60 | REFERENCE | 900 | 2 | 1 | 1 | 1 | 0 | 50.00% |
| bybit | 240/60 | VALIDATION | 390 | 0 | 0 | 0 | 0 | 0 | — |
| bybit | 240/60 | HOLDOUT | 368 | 0 | 0 | 0 | 0 | 0 | — |
| binance | 15/5 | REFERENCE | 39612 | 52 | 10 | 10 | 4 | 6 | 19.23% |
| binance | 15/5 | VALIDATION | 15282 | 37 | 4 | 4 | 1 | 3 | 10.81% |
| binance | 15/5 | HOLDOUT | 17770 | 43 | 8 | 8 | 2 | 6 | 18.60% |
| binance | 60/5 | REFERENCE | 19624 | 5 | 0 | 0 | 0 | 0 | 0.00% |
| binance | 60/5 | VALIDATION | 7919 | 6 | 1 | 1 | 1 | 0 | 16.67% |
| binance | 60/5 | HOLDOUT | 8457 | 8 | 1 | 1 | 1 | 0 | 12.50% |
| binance | 60/15 | REFERENCE | 13082 | 7 | 4 | 4 | 2 | 2 | 57.14% |
| binance | 60/15 | VALIDATION | 5227 | 4 | 1 | 1 | 1 | 0 | 25.00% |
| binance | 60/15 | HOLDOUT | 4957 | 5 | 1 | 1 | 1 | 0 | 20.00% |
| binance | 240/5 | REFERENCE | 7161 | 0 | 0 | 0 | 0 | 0 | — |
| binance | 240/5 | VALIDATION | 3024 | 0 | 0 | 0 | 0 | 0 | — |
| binance | 240/5 | HOLDOUT | 3017 | 0 | 0 | 0 | 0 | 0 | — |
| binance | 240/15 | REFERENCE | 5520 | 2 | 0 | 0 | 0 | 0 | 0.00% |
| binance | 240/15 | VALIDATION | 2335 | 1 | 0 | 0 | 0 | 0 | 0.00% |
| binance | 240/15 | HOLDOUT | 2102 | 1 | 1 | 1 | 0 | 1 | 100.00% |
| binance | 240/60 | REFERENCE | 3237 | 1 | 1 | 1 | 1 | 0 | 100.00% |
| binance | 240/60 | VALIDATION | 1399 | 1 | 0 | 0 | 0 | 0 | 0.00% |
| binance | 240/60 | HOLDOUT | 1401 | 0 | 0 | 0 | 0 | 0 | — |

Setups/READY — наблюдаемые состояния каждого replay, включая уже известные warmup states. Сумма строк не означает global unique setups. Walk replays пересекаются с primary periods и не увеличивают независимый sample. Bybit 5m отсутствует: 15/5, 60/5, 240/5 для этого нового cohort UNAVAILABLE, не нулевой результат стратегии.

## PERFORMANCE / MAPPING

Каждый mapping/period/continuous segment начинает самостоятельный virtual portfolio с 1170. PnL независимых капиталов не суммируется в один account. Все нулевые сегменты сохранены в [canonical_window_metrics.csv](data/reports/robustness_research/canonical_window_metrics.csv). Ниже только сегменты с entries; max DD — mark-to-market NAV, поэтому TP1→BE прибыльная сделка может иметь существенную просадку от unrealized peak.

| COHORT | MAP | PERIOD/SEG | CLOSED/OPEN | WIN RATE | PF | EXPECTANCY | AVG R | MEDIAN R | MAX DD | NET CLOSED PNL | EQUITY PNL |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bybit | 60/15 | REFERENCE/0 | 1/0 | 0.00% | 0.0000 | -23.4000 | -1.0000 | -1.0000 | 2.00% | -23.4000 | -23.4000 |
| bybit | 60/15 | HOLDOUT/0 | 1/0 | 0.00% | 0.0000 | -23.4000 | -1.0000 | -1.0000 | 6.78% | -23.4000 | -23.4000 |
| bybit | 240/15 | REFERENCE/0 | 1/0 | 0.00% | 0.0000 | -23.4000 | -1.0000 | -1.0000 | 2.00% | -23.4000 | -23.4000 |
| bybit | 240/60 | REFERENCE/0 | 1/0 | 0.00% | 0.0000 | -23.4000 | -1.0000 | -1.0000 | 2.00% | -23.4000 | -23.4000 |
| binance | 15/5 | REFERENCE/5 | 1/0 | 0.00% | 0.0000 | -23.4000 | -1.0000 | -1.0000 | 4.13% | -23.4000 | -23.4000 |
| binance | 15/5 | REFERENCE/7 | 2/0 | 0.00% | 0.0000 | -23.1660 | -1.0000 | -1.0000 | 4.38% | -46.3320 | -46.3320 |
| binance | 15/5 | REFERENCE/8 | 1/0 | 0.00% | 0.0000 | -23.4000 | -1.0000 | -1.0000 | 4.02% | -23.4000 | -23.4000 |
| binance | 15/5 | REFERENCE/9 | 6/0 | 33.33% | 0.6422 | -5.6285 | -0.2279 | -1.0000 | 11.46% | -33.7708 | -33.7708 |
| binance | 15/5 | VALIDATION/10 | 4/0 | 25.00% | 0.1027 | -15.4667 | -0.6712 | -1.0000 | 6.41% | -61.8668 | -61.8668 |
| binance | 15/5 | HOLDOUT/10 | 8/0 | 0.00% | 0.0000 | -21.8259 | -1.0000 | -1.0000 | 14.92% | -174.6073 | -174.6073 |
| binance | 60/5 | VALIDATION/10 | 1/0 | 0.00% | 0.0000 | -23.4000 | -1.0000 | -1.0000 | 4.00% | -23.4000 | -23.4000 |
| binance | 60/5 | HOLDOUT/10 | 1/0 | 0.00% | 0.0000 | -23.4000 | -1.0000 | -1.0000 | 3.96% | -23.4000 | -23.4000 |
| binance | 60/15 | REFERENCE/9 | 3/0 | 0.00% | 0.0000 | -22.9351 | -1.0000 | -1.0000 | 13.22% | -68.8054 | -68.8054 |
| binance | 60/15 | REFERENCE/10 | 1/0 | 0.00% | 0.0000 | -23.4000 | -1.0000 | -1.0000 | 2.00% | -23.4000 | -23.4000 |
| binance | 60/15 | VALIDATION/10 | 1/0 | 0.00% | 0.0000 | -23.4000 | -1.0000 | -1.0000 | 3.78% | -23.4000 | -23.4000 |
| binance | 60/15 | HOLDOUT/10 | 1/0 | 0.00% | 0.0000 | -23.4000 | -1.0000 | -1.0000 | 3.45% | -23.4000 | -23.4000 |
| binance | 240/15 | HOLDOUT/10 | 1/0 | 0.00% | 0.0000 | -23.4000 | -1.0000 | -1.0000 | 7.36% | -23.4000 | -23.4000 |
| binance | 240/60 | REFERENCE/9 | 1/0 | 0.00% | 0.0000 | -23.4000 | -1.0000 | -1.0000 | 6.89% | -23.4000 | -23.4000 |

Полные costs, gross edge, payoff, drawdown duration, losing streak, union exposure, holding time, monthly frequency, unrealized/realized account PnL — в CSV. Gross profit/loss в trade_statistics означает положительные/отрицательные **net** исходы; gross_edge_before_fees выделен отдельно. Fees as % gross edge не определён при неположительном gross edge. Gross PnL использует уже проскользнувшие fill prices; slippage_total показан отдельно и не вычитается повторно из net PnL. Exposure от начала entry bar является upper bound, holding от известного entry close — lower bound для intrabar fills. В конце окна/gap open trades цензурируются, не закрываются искусственно.

## LONG/SHORT / SYMBOL / REGIME

[performance_groups.csv](data/reports/robustness_research/performance_groups.csv) содержит каждый symbol, оба направления и causal entry regime/volatility buckets, включая группы с нулевым sample. Subgroup DD — realized contribution, не fictitious separate full account NAV. Классификация использует только 31 preceding complete consecutive UTC daily closes: 30-day return ±10%, daily σ <2% / 2–4% / >4%. Недостаток history/gaps → UNKNOWN. Derived 1D — research label, не новый strategy input. Покрытие режимов по календарю: [causal_regime_calendar_coverage.csv](data/reports/robustness_research/causal_regime_calendar_coverage.csv). Наличие рыночного режима не означает достаточное число сделок в нём.

## READY → FILL

Development 33 unfilled: 17 OB first test consumed before limit touch, 11 isolated margin, 4 first-terminal target evidence withdrawals, 1 data-end censor. Это exclusive first-outcome ledger; 8 ever-observed target withdrawals из прежнего audit не добавляются как ещё 8 независимых отказов. На первом OB touch цена могла не дойти до executable quote; hindsight fill не создаётся. При cost-aware risk 2% и leverage 3x узкий stop может требовать margin больше account equity. Fresh target может быть реально затронут до limit fill и поэтому withdrawn. Сохраняются exact quote/SL/target audits, и эти естественные outcomes не исправлялись ради входов. Полный ledger [development_fill_frequency.json](data/reports/robustness_research/development_fill_frequency.json); external groups [fill_frequency_groups.csv](data/reports/robustness_research/fill_frequency_groups.csv).

## WALK-FORWARD

90 calendar days reference → 90 evaluation, step 90; final partial retained. 18 Bybit windows/mapping и 21 Binance windows/mapping, вместе с period runs и всеми gap segments. Insufficient warmup/no execution segments присутствуют явно. Все window fingerprints/SHA проверены: [research_completion_inventory.json](data/reports/robustness_research/research_completion_inventory.json). Анализ использует до 90 preceding days context при минимум 576 LTF warmup bars; это расширенный input context, а не новое значение trading threshold. Сравнение с прежним development replay на ином количестве warmup bars не является matched parameter test.

## COST / PARAMETER SENSITIVITY

Значения перечислены до результатов в [RESEARCH_PROTOCOL.md](RESEARCH_PROTOCOL.md). Structural one-at-a-time: только фиксированный Binance60/5 VALIDATION. Costs/risk/reentry: все 9 доступных cohort/mappings, VALIDATION/HOLDOUT и walk windows. Base fee .0006/slippage .0002, stress1.5x/2x. Initial READY Score=100; 75→80 — reentry-only, не новый фильтр source setup. Costs/risk могут изменить quantity, margin eligibility и следующие admissions; сравнивается полный portfolio, а не искусственно одинаковый closed-trade список. Свежесть BODY/exclusive wick относится только к POI, original OB touch semantics неизменны. Все результаты [registered_sensitivity_metrics.csv](data/reports/robustness_research/registered_sensitivity_metrics.csv). Никакого best-value selection.

| VARIANT | SETUPS | READY | ENTRIES | CLOSED | NET PNL | MAX DD |
| --- | --- | --- | --- | --- | --- | --- |
| AGGRESSION_055 | 7919 | 6 | 1 | 1 | -23.4000 | 4.00% |
| AGGRESSION_065 | 7919 | 6 | 1 | 1 | -23.4000 | 4.00% |
| BASE | 7919 | 6 | 1 | 1 | -23.4000 | 4.00% |
| ENGULF_105 | 7919 | 6 | 1 | 1 | -23.4000 | 4.00% |
| FRESH_BODY | 7919 | 9 | 2 | 2 | -46.3320 | 4.00% |
| FRESH_EXCLUSIVE_WICK | 7919 | 6 | 1 | 1 | -23.4000 | 4.00% |
| LIMIT_INTERIOR_MIDPOINT | 7919 | 6 | 0 | 0 | 0.0000 | 0.00% |
| OTE_DEEP_0785 | 7919 | 6 | 1 | 1 | -23.4000 | 4.00% |
| OTE_DEEP_0795 | 7919 | 6 | 1 | 1 | -23.4000 | 4.00% |
| OTE_SHALLOW_0700 | 7919 | 6 | 1 | 1 | -23.4000 | 4.00% |
| OTE_SHALLOW_0710 | 7919 | 6 | 1 | 1 | -23.4000 | 4.00% |

| MIN TARGETS | QUALIFIED OB CASES | ENOUGH DISTINCT OPPOSING POIS | MEANING |
| --- | --- | --- | --- |
| 2 | 7 | 6 | QUALIFICATION ONLY; NOT READY/ENTRIES |
| 3 | 7 | 6 | QUALIFICATION ONLY; NOT READY/ENTRIES |
| 4 | 7 | 5 | QUALIFICATION ONLY; NOT READY/ENTRIES |

Fixed three-TP contract исключает честное execution сравнение с двумя/четырьмя targets без нового exit model. Поэтому этот counterfactual не выдаётся за сделки и не hardcodes READY.

## CAUSALITY / EXECUTION

[external_real_causality_parity.json](data/reports/robustness_research/external_real_causality_parity.json): actual canonical READY reproduced; full/prefix/future-mutated/repeat/SHADOW и ускоренные варианты дают одинаковые 633 прошлых signals. BACKTEST/SHADOW одинаковы по реальным trade/decisions/NAV. [research_adapter_equivalence.json](data/reports/robustness_research/research_adapter_equivalence.json): optimized/full-reader common coverage совпадает; immutable source/config guard PASS. Все actual fills/availability/partial fees/accounting/entry-bar conservative semantics проверены в [external_execution_audit.json](data/reports/robustness_research/external_execution_audit.json). BASE_VERIFY cost replay и exit A точно воспроизводят saved canonical trades/journal/equity для каждого case. Exit paired real entries дополнительно проверяют 7 variants BACKTEST/SHADOW и nonvacuous future-prefix там, где actual TP1 был.

## LIMITATIONS / VERDICT

INSUFFICIENT SAMPLE. До ≥100 comparable closed trades/mapping нет положительного edge verdict. Sharpe/Sortino/Calmar withheld при <90 full daily returns или <30 closed trades; 365-day UTC sampling, RF=0. Monte Carlo sample gates: [monte_carlo_sample_gate.json](data/reports/robustness_research/monte_carlo_sample_gate.json). Пересекающиеся walk windows и отдельные mapping/cohorts не объединены для достижения порога.

Public mirror integrity подтверждена source object SHA, но это не independent exchange authenticity certification. Binance instrument ambiguity и Bybit native HTF discrepancies ограничивают переносимость вывода на Bybit execution. Baseline содержит явно обозначенные BACKTEST_PARAMETER POI/displacement/target normalizations, а не source-approved геометрию всех блоков. Прежние source audits сохранены в HISTORICAL_PIPELINE_FINAL_REPORT.md. Fee/slippage model сохранён; funding, order-book queue и реальные fills этой virtual проверкой не измерены. Мало закрытых сделок и post-TP1 episodes: нельзя отделить устойчивый edge от случайности, выбрать profitable symbol/параметр или менять baseline по этим данным. Практическая жизнеспособность не доказана; LIVE запрещён.

## TESTS / GIT

Актуальные tests/lint/mypy и protected SHA — [continuation_stage_checks.json](data/reports/robustness_research/continuation_stage_checks.json); полный test log — [continuation_full_tests.log](data/reports/robustness_research/continuation_full_tests.log). Frozen rollback tag `research-baseline-2026-10-08` → starting canonical commit. Repository `mdiminchuk208-arch/-`, branch `main`; commits опубликованы обычным push без force. Итоговый commit и content-equivalence ZIP receipt сообщаются после публикации, чтобы не создавать self-referential commit hash.
