# Исследование реального historical pipeline

Это журнал продолжающейся разработки, а не итоговое подтверждение исторической готовности.

## Сохранённая база

Репозиторий `mdiminchuk208-arch/Zsfhjl-`, ветка `main`, исходный commit
`b0598444498906638559e22dd1e5770123bd8cd1`. Загруженный по последней выданной
GitHub-ссылке ZIP содержит ровно 765 файлов: Git blob hash, содержимое и режим
каждого файла совпали. ZIP comment содержит тот же commit. Повторный push дал
`Everything up-to-date`; исходная точка возврата остаётся в истории.

## Исходный полный аудит

В execution-журнале 60m/5m: 6 357 setups, 5 842 попытки automatic levels,
4 659 `NO_POST_BOS_OB_PATTERN`. В 3 342 случаях окно `BOS+2 .. anchor-1`
пустое; в 845 нет нужных цветов A/B; в 472 нет полного engulfing тела.
Сохранены BOS identity, protected level, timestamps, границы поиска и OHLC
каждого рассмотренного triple для **каждого из 4 659 случаев**.

Девять ранних OB-кандидатов имеют 51 preexisting overlapping HTF gap-POI;
все 51 действительно имели доступные предыдущие wick touches до A.
Отдельно записаны first touch, count, body overlap, close overlap, equality и
формирующие/предшествующие доступности свечи. `PREEXISTING + FRESH` не является
логическим противоречием, однако текущая gap-only политика ограничивает область поиска.

Все 7 667 Range episodes воспроизведены: 4 260 `CONSUMED_NO_SFP`,
3 393 `CLARITY_REVIEW_BLOCKED`, 14 ambiguous. Для каждого записаны sweep,
reclaim, next-open, range validation и состояние границ. Стратифицированная
выборка содержит **214** полных traces. В 3 393 случаях `detect_sfp` возвращает
valid, но ручная заглушка `UNREVIEWED` запрещает событие. Исторический индекс
дополнительно вообще не подключает Range events. Это внутренние блоки реализации.

## Этап 1: окно OB

`OB_CORE_001` требует sweep → engulfing displacement → BOS confirmation.
Подтверждение после формирования не требует, чтобы A открывалась **после** BOS.
Источник `OB_LTF_ENTRY_001` описывает ожидание BOS перед entry search/limit,
а не запрет проверять свечи, образовавшие подтверждённый импульс.

Окно теперь ограничено замороженным pre-BOS structural extreme и selected
impulse anchor; engulfing на самом anchor включён, C подтверждает IMB позднее.
Квалификация остаётся доступной только после закрытого BOS, IMB и geometry.
Ликвидность, aggression, POI, OTE, stop и targets продолжают проверяться.
Отсутствие causal origin имеет отдельную явную причину.

Регрессии: LONG/SHORT engulf causes BOS, earlier formation/later confirmation,
anchor endpoint, исключение чужого импульса и неизвестного origin.
Targeted 38 PASS; full 378 PASS; lint PASS; mypy PASS (51 files).
Полный 60m/5m BACKTEST/repeat совпадает побайтно, включая fingerprints;
prefix/future-mutation tests PASS. READY=0 остаётся результатом этого этапа.
Отказы без OB pattern уменьшились с 4 659 до 1 020; 279 setups достигли
supporting POI, один дошёл до targets. Эти перекрывающиеся counts не суммируются.

## Материалы и сеть

В репозитории сохранён `config/source_rules.json` с конкретными ссылками на
страницы первичных материалов и source-linked fixtures; оригинальных PDF/DOCX
в текущем workspace нет. Сопоставление с этим реестром не выдаётся за повторную
независимую проверку отсутствующих оригиналов.

Фактический PUBLIC запрос `https://api.bybit.com/v5/market/kline` без ключей
отклонён прокси: `Tunnel connection failed: 403 Forbidden`. Расширенная история
пока не получена; сохранён полный non-secret результат попытки.

## Этап 2: Range, доступность OB и точная freshness

Автоматическая ясность проверяет уже определённые правилами ordered confirmed
swing boundaries, midpoint reaction и отсутствие внутреннего BOS до validation.
Ручной `UNREVIEWED` больше не является обязательной заглушкой автоматического
pipeline. Явные manual overrides сохранены для аудита. Исторический индекс теперь
подключает Range SFP так же, как независимый prefix snapshot.

Те же 7 667 episodes дают 3 393 `SFP_FORMED`, 4 260 `CONSUMED_NO_SFP` и
14 ambiguous; `CLARITY_REVIEW_BLOCKED=0`. Все episodes и 214 подробных traces
сохранены в `data/reports/historical_blocker_investigation/stage2`.

Первый тест OB считается строго после полной доступности `max(C close, BOS close)`.
Сам BOS и более ранние свечи формирования не являются последующим касанием.
Freshness POI сохраняет inclusive wick overlap, исключение forming candle и
closed-candle cutoff. Интервальный индекс сравнен с независимым линейным сканированием;
будущие узлы не участвуют в запросе прошлого. Он сокращает время, не меняя правило.

Полная история 60m/5m: 6 367 setups, **5 READY**, 0 virtual entries.
Полная история 15m/5m: 12 656 setups, **25 READY**, 0 virtual entries.
LONG и SHORT найдены на реальных свечах. Повтор каждого запуска совпал побайтно
по всем logical reports. Full suite **394 PASS**, lint PASS, mypy PASS (51 files),
prefix/reference/future-mutation regressions PASS. Большие новые reports сохранены
без потерь в gzip с SHA исходного содержимого; старые artifacts не удалялись.

Этап ещё не доказывает работающий virtual lifecycle: следующий выявленный дефект —
портфель рассматривает только следующий OPEN, хотя исходное правило описывает
limit в POI. Внутрисвечное первое касание игнорируется, а на CLOSE уже отзывает OB.
Следующий этап завершает это исполнение с консервативной OHLC chronology,
проверяет точную воронку и реальные LONG/SHORT exits/accounting.

## Safety

`trade_entry_allowed=false`. EngineMode содержит только BACKTEST/SHADOW.
Private API, exchange credentials и real orders отсутствуют.
