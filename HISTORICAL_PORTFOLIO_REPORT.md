# HISTORICAL PORTFOLIO — Crypto Bot / Strategy Engine

Версия `0.4.20-replay.3`, core/package `0.4.20`. Единый портфель $1170,
baseline risk 2%, Isolated x3, fee 0.06% и adverse slippage 0.02% на сторону.
`trade_entry_allowed=false`. Все действия — offline, виртуальные.

Исследование завершено: 180 дней и весь доступный общий период. На истории
не возникло ни одного READY-сигнала, поэтому входов, P&L и costs нет.
Это результат неизменённого экспериментального detector, а не доказательство
доходности или ошибочности стратегии. Финансовое сопровождение сделок проверено
на явно синтетических тестах; эти сделки не включены в историческую статистику.

## CHECK | STATUS | EVIDENCE

| CHECK | STATUS | EVIDENCE |
| --- | --- | --- |
| Baseline | PASS | 327 существующих тестов до изменений |
| Final tests / compile | PASS | 344 теста, final_tests.log; compileall exit 0 |
| Freeze | PASS | 27f0b7d9600ba046d26193894824f93238182e940c887aef3a20a63ced59c8f6 |
| Range / SFP / MTF lifecycle / geometry | PASS в тестах | Существующий suite + regression tests; source certification отдельно |
| Causality / lookahead | PASS в проверенных случаях | 6240 реальных префиксов; independent prefix snapshots; future_mutation_checks.json |
| Большой prefix replay | PASS | 120 дней совпали с префиксом 180 дней: 8923 signal/decision rows, 34560 equity points |
| Determinism | PASS | 180 и max выполнены дважды; все 7 исходных артефактов побайтно одинаковы |
| Offline SHADOW parity | PASS | Оба периода: отличается только mode; decisions/trades/equity побайтно одинаковы |
| Virtual accounting / risk | PASS в тестах | Compounding, decompounding, costs, unrealized, TP40/30/30, BE, caps, daily latch, gaps, BANKRUPT |
| Financial lifecycle на исторических сетапах | НЕ ИСПОЛНЕН | 0 READY, 0 entries; historical fills не подтверждены |
| Исторические inputs | PASS | 40 CSV SHA-256 совпали с загруженным архивом; 20 выбранных рядов healthy |
| HTF/LTF OHLC | PASS | 57590 часовых свечей совпали с агрегацией 5m, tolerance 1e-12 |
| 365 дней | НЕДОСТУПНО | Общее покрытие около 240 дней; данные не скачивались и не подменялись |
| Real execution safety | PASS | LIVE отклоняется; нет private API, API keys, реальных ордеров или production changes |
| Source-certified OB/POI / Range review | ОТКРЫТО | Auto levels экспериментальные; Range clarity UNREVIEWED; исходных PDF нет в архиве |

## Dataset и фиксированные параметры

| RUN | START UTC | END UTC | EXECUTION BARS (10 SYMBOLS) | UNIQUE SETUPS |
| --- | --- | --- | --- | --- |
| 180 дней | 2026-03-26T11:00:00+00:00 | 2026-09-22T11:00:00+00:00 | 518400 | 4710 |
| Весь доступный период | 2026-01-27T12:00:00+00:00 | 2026-09-22T11:00:00+00:00 | 685320 | 6357 |

Длительность max: 237.95833333 дня (237 дней 23 часа). Warmup 576 свечей 5m, два дня, анализ без сделок. HTF 60 / LTF 5. Все 10 монет используют один balance/equity, без сброса капитала между монетами или сделками. Auto-level body threshold 0.6, engulf ratio 1.0, OTE 0.705–0.79, OB/POI и построение целей сохранены.

Исправлено: balance оплачивает entry fee сразу; equity включает open P&L; допуски резервируют costs до проверки маржи/risk cap; entry fee не списывается повторно на выходе. Максимальный equity сделки включает closing fill. Для нового historical index добавлен запрет отката очереди при обнаружении старого OB-touch во время поздней geometry resolution. В accounting_bug_reproduction_before.json сохранены воспроизведения: старый equity 1170 против 1169.6368734324817 после входа с costs; старый trade peak 1244.88 против closing equity 1258.92.

## PORTFOLIO

| METRIC | RESULT |
| --- | --- |
| Initial capital | $1170.00 |
| Final balance | $1170.00 |
| Final equity / capital | $1170.00 |
| Realized / unrealized P&L | $0.00 / $0.00 |
| Net P&L | $0.00 |
| Return | 0.00% |
| Peak equity | $1170.00 |
| Lowest equity | $1170.00 |
| Max drawdown | $0.00 / 0.00% |
| Total fees | $0.00 |
| Total slippage | $0.00 |
| Allocated margin / aggregate stop risk | $0.00 / $0.00 |

## TRADING

| METRIC | RESULT |
| --- | --- |
| Setups | 6357 |
| Signals — state changes | 17752 |
| Ready signals | 0 |
| Entries / completed trades | 0 / 0 |
| Wins / losses / breakevens | 0 / 0 / 0 |
| Win / loss / breakeven rate | Не определены — нет закрытых сделок |
| Gross profit / gross loss | $0.00 / $0.00 |
| Profit factor | Не определён |
| Expectancy | Не определена |
| Average R / median R | Не определены |
| Longest win / loss streak | 0 / 0 |

Signals означают изменения состояния, а не обещание входа. Неизменённые WAITING сообщения не дублируются. Неопределённые статистики сохраняются как JSON null.

## RISK

| METRIC | RESULT |
| --- | --- |
| Configured risk / first nominal budget | 2% / $23.40 |
| Configured aggregate cap / initial budget | 6% / $70.20 |
| Daily loss limit / initial budget | 4% / $46.80; UTC rollover, latched |
| Leverage | Isolated x3; hard maximum x5 |
| Average realized trade risk % | Не определён — нет входов |
| Maximum single-trade allocated risk | $0.00 |
| Maximum aggregate allocated risk | $0.00 / 0.00% |
| Daily-loss blocks | 0 |
| Margin blocks | 0 |
| Score / re-entry blocks | 0 / 0 |
| TP1 cost blocks | 0 |

Quantity рассчитывается от SL-loss с entry/exit fee и adverse slippage; новый risk = current equity × 2%. Equity на входе использует синхронные OPEN marks до current-bar CLOSE outcomes. Risk cap и margin проверяются после резервирования входных costs. Это admission policy: экстремальные gaps/последующие рыночные движения могут превысить номинальный бюджет. BANKRUPT — явное состояние, новые входы блокируются, убыток не обрезается.

## LONG / SHORT

| SIDE | TRADES | WINS | LOSSES | NET P&L | PF | EXPECTANCY | AVG R |
| --- | --- | --- | --- | --- | --- | --- | --- |
| LONG | 0 | 0 | 0 | $0.00 | — | — | — |
| SHORT | 0 | 0 | 0 | $0.00 | — | — | — |

## BY SYMBOL

| SYMBOL | SETUPS | ENTRIES | TRADES | WIN RATE | P&L | PF | EXPECTANCY | DD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ADAUSDT | 560 | 0 | 0 | — | $0.00 | — | — | $0.00 |
| AVAXUSDT | 622 | 0 | 0 | — | $0.00 | — | — | $0.00 |
| BNBUSDT | 567 | 0 | 0 | — | $0.00 | — | — | $0.00 |
| BTCUSDT | 676 | 0 | 0 | — | $0.00 | — | — | $0.00 |
| DOGEUSDT | 673 | 0 | 0 | — | $0.00 | — | — | $0.00 |
| ETHUSDT | 675 | 0 | 0 | — | $0.00 | — | — | $0.00 |
| LINKUSDT | 639 | 0 | 0 | — | $0.00 | — | — | $0.00 |
| LTCUSDT | 600 | 0 | 0 | — | $0.00 | — | — | $0.00 |
| SOLUSDT | 638 | 0 | 0 | — | $0.00 | — | — | $0.00 |
| XRPUSDT | 707 | 0 | 0 | — | $0.00 | — | — | $0.00 |

DD монеты — спад накопленного realized P&L contribution в USDT. Общий DD — спад equity единого портфеля.

## SCORE BUCKETS

| SCORE | TRADES | WIN RATE | P&L | PF | EXPECTANCY | AVG R |
| --- | --- | --- | --- | --- | --- | --- |
| 75-79 | 0 | — | $0.00 | — | — | — |
| 80-84 | 0 | — | $0.00 | — | — | — |
| 85-89 | 0 | — | $0.00 | — | — | — |
| 90-94 | 0 | — | $0.00 | — | — | — |
| 95-100 | 0 | — | $0.00 | — | — | — |
| <75 | 0 | — | $0.00 | — | — | — |

## BEST / WORST

Best/worst symbol, LONG/SHORT side и Score bucket не определены: закрытых сделок нет.

## BLOCKER FUNNEL

| STAGE / STATUS | COUNT |
| --- | --- |
| Execution LTF bars, 10 symbols | 685320 |
| Structure/BOS/CONF events, including warmup | 92262 |
| HTF SFP formations, including warmup | 10124 |
| SFP → BOS raw links, including warmup | 7062 |
| Unique setups observed in execution | 6357 |
| Ever WAITING_FOR_ENTRY_GEOMETRY | 4966 |
| Ever WAITING_FOR_AUTO_LEVELS | 5842 |
| Ever WAITING_FOR_SOURCE_LEVELS | 0 |
| Ever REJECTED_ENTRY_GEOMETRY | 53 |
| Ever SOURCE_CONTEXT_BLOCKED | 0 |
| Ever INVALIDATED | 6145 |
| Qualified automatic OB / target-selection stage reached | 0 |
| READY | 0 |
| Next-open fills | 0 |
| Closed trades | 0 |

Ever counts относятся к уникальным signal ID и могут пересекаться при смене состояния. Raw events включают двухдневный warmup; execution bars его не включают. На последнем close: 6145 INVALIDATED, 210 WAITING_FOR_AUTO_LEVELS, 2 REJECTED_ENTRY_GEOMETRY.

| AUTO BLOCKER | UNIQUE SETUPS EVER |
| --- | --- |
| AGGRESSIVE_IMPULSE_THRESHOLD_NOT_MET | 453 |
| DIRECTIONAL_IMBALANCE_NOT_CONFIRMED | 570 |
| FRESH_PREEXISTING_HTF_POI_NOT_FOUND | 9 |
| NO_ELIGIBLE_POST_BOS_OB | 1183 |
| NO_POST_BOS_OB_PATTERN | 4659 |
| OB_OUTSIDE_OTE_OR_STRUCTURAL_IMPULSE | 398 |
| RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND | 62 |

| BLOCKER CATEGORY | UNIQUE SETUPS |
| --- | --- |
| OTE_mismatch | 398 |
| missing_HTF_POI | 9 |
| missing_OB | 5842 |
| missing_three_targets | 0 |
| stale_evidence | 0 |

| ADMISSION BLOCK | COUNT |
| --- | --- |
| COST_ADJUSTED_FILL_GEOMETRY | 0 |
| DAILY_LOSS_LIMIT_LATCHED | 0 |
| EQUITY_EXHAUSTED | 0 |
| INVALID_QUANTITY | 0 |
| ISOLATED_MARGIN_BUDGET | 0 |
| PREVIOUS_POSITION_STILL_OPEN | 0 |
| REENTRY_SCORE_BELOW_75 | 0 |
| TOTAL_RISK_CAP_6_PERCENT | 0 |
| TP1_NOT_POSITIVE_AFTER_COSTS | 0 |

Missing three targets, stale evidence и admission blocks равны нулю, поскольку нужные стадии не достигнуты. Это не PASS этих стадий на реальных исторических сделках. Фильтры не ослаблялись ради появления входов; убыточные сделки не удалялись.

## EQUITY CURVE И ЖУРНАЛ

Полный max-прогон: data/reports/historical_portfolio_audit/backtest_max/. equity_curve.jsonl содержит 68532 chronological points; equity_curve.csv — экспорт того же ряда. Каждая точка сохраняет timestamp, balance, unrealized, equity, peak, DD, open positions, used margin, available equity, stop risk, fees, slippage, daily P&L и status. signals.jsonl и decisions.jsonl содержат переходы состояния. trades.jsonl пуст: реальных historical entries нет.

Trade schema содержит identity, LONG/SHORT, timeframe, Score, availability times, theoretical/actual entry, zone, SL, three TP, initial equity, risk, quantity/notional/margin/leverage, risk before/after, fees/slippage, partial fill details, BE, P&L, R, duration, exit reason, equity after trade и MFE/MAE. MFE/MAE — full closed-bar envelopes в единицах цены: extrema exit-bar могут быть после intrabar fill. DD измерен на bar close. Funding/liquidation и исторические exchange lot filters отсутствуют; quantity — fractional linear coin units. Open trades не закрываются принудительно в конце.

## ВОСПРОИЗВЕДЕНИЕ

```powershell
$env:PYTHONPATH = "src"
py -m unittest discover -s tests -v
py scripts/run_historical_portfolio.py --days 180 --workers 4 --mode BACKTEST --report-root data/reports/local_180
py scripts/run_historical_portfolio.py --days max --workers 4 --mode BACKTEST --report-root data/reports/local_max
py scripts/run_historical_portfolio.py --days max --workers 4 --mode SHADOW --report-root data/reports/local_shadow
```

В Windows можно открыть VERIFY_PROJECT.cmd для локальных тестов или
RUN_HISTORICAL_CHECK.cmd для тестов и 180-day BACKTEST/SHADOW. Все перечисленные
облачные исследования уже выполнены; локальное повторение дополнительно.

180 BACKTEST fingerprint: `e3e40f670e5f2529dc121b0aabe9b04ecca4111de7ceeab9c0e1fdc4c0d21122`

180 SHADOW fingerprint: `cd998d801704cbc89b569e81016aba94c092576215d8a435d8aaaeeeba85a582`

max BACKTEST fingerprint: `068ad4d384521e0447c543634b141932e17c01cd71ba1e911b98dc6000a39ecf`

max SHADOW fingerprint: `29948a72f1d35a44fd1d35c922abc709aaf377fbe5fe9821b2d0084621495b2e`

## FINAL VERDICT

`READY FOR OFFLINE SHADOW`

Offline pipeline, determinism и semantic parity подтверждены в указанном объёме.
На реальной истории не получено виртуальных fills, поэтому historical execution
performance и связь Score с результатами не оценены. Source certification OB/POI,
manual Range clarity и current-market observation/execution constraints остаются
отдельными gates. Переход к public-live shadow в этом этапе не выполнен.
`trade_entry_allowed=false`; реальные деньги и реальные ордера не включены.
