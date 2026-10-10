# RESOLVER_RE_ENTRY v1

Status: First vs repeat source distinction определено; eligibility некоторых повторов, new evidence identity и count notunique. CONTRACT_UNRESOLVED для полного repeated-entry engine.

## Relevant source passages

### S_OB_FIRST_TEST — SW9 p3–3

> 12/02/2023, 21:46                                 https://cryptology.courses/labs/torgovye-instrumenty-advancedtorgovi-instrumenti-advanced
> 
> 
> 
> 
>                       Графический пример медвежьего OB
> 
> 
> 
> 
>                       Как использовать OB в торговле?
> 
>                       В 90% случаев мы работаем исключительно от первого теста OB, только в
>                       некоторых случаях можно рассматривать повторный вход от OB, дожидаясь
>                       реакции на младшем ТФ.
> 
>                       Очень важно! OB должен находиться внутри структурного импульса и работать
>                       с ним необходимо по “тренду”.
> 
>                       Первый вариант
> 
>                              Выделяем диапазон OB.
>                              Выставляем лимитный ордер на границу диапазона. Для бычьего OB -
>                              верхняя граница, для медвежьего OB - нижняя. Также можно выставлять
>                              лимитные ордера внутри зоны ОВ.
>                              Стоп ставим за минимум/максимум OB. Либо за тень свечи, которая
>                              поглотила OB.
> 
> https://cryptology.courses/labs/torgovye-instrumenty-advancedtorgovi-instrumenti-advanced                                                     3/16

### S_OB_CONS_TRIGGER — SW9 p4–6

> 12/02/2023, 21:46                                 https://cryptology.courses/labs/torgovye-instrumenty-advancedtorgovi-instrumenti-advanced
> 
>                       Примеры:
> 
> 
> 
> 
>                       Второй вариант
> 
>                       Более сложный вариант, используется на OB образованных на ТФ 15M - 1D и т.д.
> 
>                              Выделяем диапазон OB на старшем таймфрейме.
>                              Переключаемся на ТФ ниже (1-15М).
>                              Ожидаем плавный структурный подход цены в диапазон OB.
>                              После реакции мы ожидаем слом структуры и формировании POI (зоны
>                              интереса).
> 
>                       Примеры:
> 
> 
> 
> 
> https://cryptology.courses/labs/torgovye-instrumenty-advancedtorgovi-instrumenti-advanced                                                     4/16
> 12/02/2023, 21:46                                 https://cryptology.courses/labs/torgovye-instrumenty-advancedtorgovi-instrumenti-advanced
> 
> 
> 
> 
>                       Цена сломала 4Н структуру, отмечаем POI на 4Н ТФ.
> 
> 
> 
> 
>                       Цена пришла в POI 4Н, переключаемся на ТФ ниже. Мы ожидаем слом структуры
>                       на младшем таймфрейме и формирования POI.
> 
> 
> 
> 
> https://cryptology.courses/labs/torgovye-instrumenty-advancedtorgovi-instrumenti-advanced                                                     5/16
> 12/02/2023, 21:46                                 https://cryptology.courses/labs/torgovye-instrumenty-advancedtorgovi-instrumenti-advanced
> 
> 
> 
> 
>                       Получили слом структуры на младшем таймфрейме и сформированное POI.
>                       Выставляем лимитный ордер на новую POI.
> 
> 
> 
> 
>                       Работая по второму варианту, вход не только более безопасен и консервативен,
>                       но также появляется возможность открытия сделки с крайне высоким RR.
> 
>                       Очень часто начинающие трейдеры используют каждое поглощение в качестве
>                       OB, не обращая внимания на IMB, а также выделяют OB, который не находится в
>                       структурном импульсе или зоне ОТЕ (соблюдение зон Premium и Discount).
> 
>                       Нарушение условий поиска Order Block.
> 
> 
> 
> 
> https://cryptology.courses/labs/torgovye-instrumenty-advancedtorgovi-instrumenti-advanced                                                     6/16

### S_SND_FORMATION — 18 word/document.xml:P0005–P0012

> Supply zone (Зона предложения) - Последнее восходящее движение которое может состоять как из одной свечи на старшем тф так и из нескольких последовательных свеч (чаще всего манипуляция BTS) на младшем таймфрейме
> В такой зоне алгоритм набирает шорт позицию за счет стоп ордеров ритейл трейдеров
> Demand zone ( Зона спроса ) - Последнее нисходящее движение которое может состоять как из одной свечи на старшем тф так и из нескольких последовательных свеч (чаще всего манипуляция STB) на младшем таймфрейме
> В такой зоне алгоритм набирает лонг позицию за счет стоп ордеров ритейл трейдеров.
> Важные правила для верного определения зон спроса и предложений которые нужно помнить :
> Движение которое формирует зону должно обязательно быть через рейд старой ликвидности.
> Зоны Supply и Demand являются не тестированными.
> Зоны Supply действительны для продаж в премиуме, зоны Demand для покупок расположены дискаунте.

### S_SFP_BODY_EXIT — SW12 p13–13

> 12/02/2023, 22:33                                        https://cryptology.courses/labs/indikatoryindikatori
> 
>                         Значения индикатора в пунктах цены можно узнать наведением курсора на
>                         свечу SFP.
> 
>                         Ордер на ограничение убытка позволяет трейдеру «пережить дубль»: иногда
>                         крупные игроки повторно тестируют зону потенциальных стопов, ликвидируя
>                         скальперов. Уровень защитного ордера не переставляется, но трейдер должен
>                         закрыть сделку вручную, если какая-либо свеча закроется ниже минимума (в
>                         случае с продажами – максимума) паттерна SFP. Тогда паттерн будет являтся
>                         неактуальным.
> 
>                         Таким образом, использовать ATR для размещения стоп-лоссов оптимально. Он
>                         позволяет разместить стоп-лосс максимально далеко и избежать любого
>                         рыночного шума, используя самый короткий из возможных для этого стоп
>                         ордеров.
> 
>                         Настройки ATR
> 
>                         Изменение настроек ATR влияет на его чувствительность.
> 
>                             1. Стандартное значение для ATR – 14, то есть, индикатор измеряет
>                                волатильность цены на основе 14 последних периодов времени. Как
>                                указано выше, обычно это 14 дней.
>                             2. Использование более низких значений означает меньшее количество
>                                данных для работы. Это делает индикатор гораздо более чувствительным к
>                                недавним ценовым движениям и позволяет быстрее получать информацию.
>                             3. Повышение значения оказывает противоположный эффект - линия
>                                скользящей средней становится сглаженной, сравнительно одинаковой на
>                                протяжении больших периодов времени.
> 
>                         На изображениях ниже показана разница того, как два варианта выглядят на
>                         графике. В первом случае ATR был установлен на 7, что составляет ровно
>                         половину от стандартного значения в 14. Это привело к достаточно неровной
>                         линии.
> 
> 
> 
> 
> https://cryptology.courses/labs/indikatoryindikatori                                                            13/15

### S_FLOW — SW22 p5–6

> 12/02/2023, 23:10                                       https://cryptology.courses/labs/torgovye-instrumenty-pro--torgovi-instrumenti-pro
> 
> 
> 
> 
>                        4. Поток приказов (Order Flow)
>                        Поток приказов - ордера маркетмейкера на покупку/продажу, доставляющие
>                        цену в зоны интереса (POI) глобального значения.
> 
>                        Основным отличием Order Flow от классического тренда является обязательная
>                        работа с ликвидностью. Для движения по структурному движению необходимо,
>                        чтобы крупный игрок проводил работу с ликвидностью ритейл-трейдеров и тем
>                        самым продолжал набирать свою позицию.
> 
>                        Схематический пример
> 
> 
> 
> 
>                        Восходящий Order Flow - более высокие минимумы и максимумы.
> 
>                        Графический пример
> 
> 
> 
> 
>                        Нисходящий Order Flow - более низкие максимумы и минимумы.
> 
> 
> https://cryptology.courses/labs/torgovye-instrumenty-pro--torgovi-instrumenti-pro                                                           5/6
> 12/02/2023, 23:10                                       https://cryptology.courses/labs/torgovye-instrumenty-pro--torgovi-instrumenti-pro
> 
>                        Графический пример
> 
> 
> 
> 
>                        Пока цена совершает движение в зону интереса маркетмейкера, тем поток
>                        приказов остается актуальным, благодаря тестам ключевых минимумов/
>                        максимумов и пробоям ключевых максимумов/минимумов. Как только зона
>                        интереса маркетмейкера будет протестирована, поток приказов нарушается и
>                        меняется на противоположный. Работать нужно в направлении актуального
>                        потока приказов. Тем самым, мы повторяем действия маркетмейкера и делаем
>                        нашу сделку максимально безопасной.
> 
> 
> 
> 
>                        5. Выводы
>                        Рыночное движение - это большая система состоящая из небольших
>                        манипуляций, которые крупный игрок использует для набора/фиксации позиции.
>                        Следить за этими манипуляциями помогает понимание инструмента STB/BTS.
> 
>                        Последовательность закрепления этих манипуляций и конечная цель
>                        фиксируется в рамках Order Flow.
> 
> 
> 
> 
> https://cryptology.courses/labs/torgovye-instrumenty-pro--torgovi-instrumenti-pro                                                           6/6

### S_RANGE_CONSERVATIVE — 06 word/document.xml:P0124–P0129

> . Консервативный
> - Наличие POI сверху/снизу всегда выступает сильным
> магнитом для цены, поэтому мы ожидаем поход цены в ту зону, до этого позиции
> внутри ренджа не открываем, если цена не дает реакцию на poi, входим
> консервативно, после возврата и закрепления цены внутри боковика, на тесте
> границ.

### S_RANGE_CONSERVATIVE — 19 word/document.xml:P0129–P0130

> Один из сетапов который мы используем для торговли боковых движений :
> Возврат цены после девиации - с последующим тестом зоны , которая отправила цену обратно в ренж , сделав choch.

## Все диаграммы в relevant source scope

- SW9 PDF page 3: `data/source_materials/primary_pdf_2026_10_09/SW9.pdf`; вся страница, включая схемы.
- SW9 PDF page 4: `data/source_materials/primary_pdf_2026_10_09/SW9.pdf`; вся страница, включая схемы.
- SW9 PDF page 5: `data/source_materials/primary_pdf_2026_10_09/SW9.pdf`; вся страница, включая схемы.
- SW9 PDF page 6: `data/source_materials/primary_pdf_2026_10_09/SW9.pdf`; вся страница, включая схемы.
- 18 `word/media/image1.jpg`, SHA256 `791e77aa79b5b3fc60599e1b5e74c702a78e162656444c2cd970878f569fe0a2`; после P0006, OCR `data/source_materials/cryptology_2026_10_09/diagram_ocr/791e77aa79b5b3fc60599e1b5e74c702a78e162656444c2cd970878f569fe0a2.txt`.
- 18 `word/media/image2.jpg`, SHA256 `2d36c9353ddf74575bf9c51573b2dda98d5b7025a2ee9eccb66b8b726f904d9c`; после P0008, OCR `data/source_materials/cryptology_2026_10_09/diagram_ocr/2d36c9353ddf74575bf9c51573b2dda98d5b7025a2ee9eccb66b8b726f904d9c.txt`.
- SW12 PDF page 13: `data/source_materials/primary_pdf_2026_10_09/SW12.pdf`; вся страница, включая схемы.
- SW22 PDF page 5: `data/source_materials/primary_pdf_2026_10_09/SW22.pdf`; вся страница, включая схемы.
- SW22 PDF page 6: `data/source_materials/primary_pdf_2026_10_09/SW22.pdf`; вся страница, включая схемы.
- 06 `word/media/image13.jpg`, SHA256 `c81dbbc3ef15ca3755864ed0f987d58bb9e9cc6becf2199c313ac5be824cb423`; после P0129, OCR `data/source_materials/cryptology_2026_10_09/diagram_ocr/c81dbbc3ef15ca3755864ed0f987d58bb9e9cc6becf2199c313ac5be824cb423.txt`.
- 06 `word/media/image14.jpg`, SHA256 `beaa8047c54bd2c988b4c264bf596d1ac3be1a7a683f9ac67982e709a1de6cb7`; после P0129, OCR `data/source_materials/cryptology_2026_10_09/diagram_ocr/beaa8047c54bd2c988b4c264bf596d1ac3be1a7a683f9ac67982e709a1de6cb7.txt`.
- 06 `word/media/image15.jpg`, SHA256 `bace8d0ac14330586507f1ce4fd2f1821fd78ae390261804adcb7f68841b5e5c`; после P0129, OCR `data/source_materials/cryptology_2026_10_09/diagram_ocr/bace8d0ac14330586507f1ce4fd2f1821fd78ae390261804adcb7f68841b5e5c.txt`.
- 19 `word/media/image23.jpg`, SHA256 `4ea93e8e697f85283eb708642ebb84decbe11ebd0d1819a607f2d4b66eee01ae`; после P0130, OCR `data/source_materials/cryptology_2026_10_09/diagram_ocr/4ea93e8e697f85283eb708642ebb84decbe11ebd0d1819a607f2d4b66eee01ae.txt`.

Полный inventory всех122 unique DOCX diagrams и195 media occurrences сохранён в прежнем audit. Новый diagram_anchor_index сопоставляет inline image с deduplicated paragraph IDs. PDF locators указывают оригинальные страницы; screenshot не добавляет неизвестный numerical cutoff. До/после P locator — приблизительный textual anchor, не заявка на авторский номер рисунка.

## Варианты трактовки и прямо разрешённое

OB первый тест преимущественно; некоторые repeat после новой LTF reaction. SnD исходная zone untapped; повторный тест не удовлетворяет этому определению. New SFP после новых source facts возможен как новый setup, lifetime rule отсутствует.

## Прямо запрещённое / отдельно не доказанное

Source не разрешает автоматический repeat старого OB без реакции; не разрешает объявить tested SnD untapped. One physical idea forever не SOURCE_RULE; ratio90% не случайная квота entries.

## Приоритет и source hierarchy

Typed-zone lifecycle выше универсального lifetime dedup. SFP native body failure прекращает актуальность старого pattern; flow destination test требует нового контекста.

## Конфликты и отсутствие единственного выбора

90% descriptive, «в некоторых случаях» исключения качественны. Нет max retries, cooldown, count-per-origin, simultaneous ownership и portfolio reset source rule.

## Deterministic rule без добавления стратегии

First vs repeat source distinction определено; eligibility некоторых повторов, new evidence identity и count notunique. CONTRACT_UNRESOLVED для полного repeated-entry engine.

## Зафиксированные решения

- OB_FIRST_TEST_ONLY и OB_REPEAT_NEW_REACTION — source-permitted style components.
- Baseline lifetime retention сохранён для comparison, в source contract не перенесён.

## Known_at

Formation после native completed CLOSE всех dependencies; swing после правой свечи. Next open известен в OPEN без будущего high/low/close. Sweep/POI test/failure изменяют состояние только с causal event; repeated reaction не backdated. Setup plan до entry, invalidation после completed native CLOSE. Фактическое время жизни сделки и финансовый outcome не доступны resolver.
