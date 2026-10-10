# RESOLVER_BRANCH_PRIORITY v1

Status: Нет source total ordering/physical identity. До решения выдавать набор candidates с provenance и unresolved ownership; не исполнять ни один при materially conflicting plans.

## Relevant source passages

### S_OB_IMB — SW9 p2–2

> 12/02/2023, 21:46                                 https://cryptology.courses/labs/torgovye-instrumenty-advancedtorgovi-instrumenti-advanced
> 
>                       Order Block - это свечная формация, благодаря которой можно определить, где
>                       крупный игрок размещает свою позицию на покупку или продажу актива.
> 
>                       Графически данный инструмент состоит из свечи, которая сняла ликвидность.
>                       После этой свечи образуется агрессивная импульсная свеча, которая
>                       перекрывает предыдущую свечу.
> 
>                       Наиболее точным является сигнал, когда после поглощенной свечи образуется
>                       имбаланс.
> 
>                       Важно, чтобы при формировании ордерблока было получено дополнительное
>                       подтверждение – слом структуры. То есть смена движения на
>                       противоположное.
> 
>                       Формация обязательно должна находиться в зоне интереса старшего
>                       таймфрейма. Если это условие не выполнено, то с наибольшей вероятностью
>                       цена пойдет искать другой ордерблок с более сильными условиями
>                       формирования.
> 
>                       Схематический пример бычьего и медвежьего OB
> 
> 
> 
> 
>                       Для работы с OB выделяем всю свечу, которая была поглощена вместе с
>                       тенями. Для удобства можно использовать инструмент “Прямоугольник”.
> 
>                       Вы можете использовать OB на любых ТФ, главное, чтобы были соблюдены все
>                       вышеупомянутые условия.
> 
>                       Графический пример бычьего OB
> 
> 
> 
> 
> https://cryptology.courses/labs/torgovye-instrumenty-advancedtorgovi-instrumenti-advanced                                                     2/16

### S_OB_IMB — SW9 p6–7

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
> 12/02/2023, 21:46                                 https://cryptology.courses/labs/torgovye-instrumenty-advancedtorgovi-instrumenti-advanced
> 
> 
> 
> 
>                       В этом примере нижний ОВ в приоритете, так как под первым ОВ находится IMB
>                       второго. Впоследствии цена закрыла данный ценовой дисбаланс.
> 
>                       Если вы встретите такую ситуацию, вы можете попробовать работать по второму
>                       варианту, через подтверждение. Если вы работаете по первому варианту, для
>                       вас будет важен именно нижний OB после перекрытия IMB.
> 
> 
> 
> 
>                       3. Breaker Block (BR)
>                       Breaker Block - это тот же OB, который был пробит быстрым импульсным
>                       движением. Очень важно, чтобы импульсное движение было цельным, без
>                       проторговки в области OB.
> 
>                       Данный блок часто называют брейкером. Это зона на графике, в которой
>                       происходит слом структуры.
> 
>                       Несмотря на свое название, брейкерблок не обязательно является разворотной
>                       моделью, он может сигнализировать о продолжении тренда.
> 
>                       Для определения тенденции рынка нужно учитывать формирование
>                       повышающихся максимумов (HH) и повышающихся минимумов (HL) для бычьего
>                       тренда и понижающихся минимумов (LL) и максимумов (LH) для медвежьего.
>                       Брейкер образуется после образования нового HH или LL при импульсном
>                       пробитии ордерблока.
> 
>                       Схематический пример бычьего и медвежьего BR
> 
> 
> 
> 
> https://cryptology.courses/labs/torgovye-instrumenty-advancedtorgovi-instrumenti-advanced                                                     7/16

### S_OB_DIRECT_ENTRY — SW9 p3–3

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

### S_CONF — SW5 p6–7

> 12/02/2023, 21:09                                  https://cryptology.courses/labs/rynochnaya-struktura-advancedrinkova-struktura-advanced
> 
> 
> 
> 
>                       Conf (confirmation) - подтверждение (обновление) слома рыночной структуры.
>                       Обновление ключевого минимума/максимума новой структуры.
>                       Консервативным подходом к работе является поиск точки входа после conf.
>                       Структурное подтверждение даёт понимание того, что рынок полностью
>                       сменил приоритет и двигается в противоположном направлении. Это первый
>                       разворотный сигнал, дающий возможность работать с дальнейшим движением
>                       от самого его зарождения.
> 
>                       Схематическое изображение CONF восходящей структуры:
> 
> 
> 
> 
>                       Схематическое изображение CONF нисходящей структуры:
> 
> 
> 
> 
> https://cryptology.courses/labs/rynochnaya-struktura-advancedrinkova-struktura-advanced                                                      6/9
> 12/02/2023, 21:09                                  https://cryptology.courses/labs/rynochnaya-struktura-advancedrinkova-struktura-advanced
> 
> 
> 
> 
>                       Графическое изображение CONF восходящей структуры:
> 
> 
> 
> 
>                       Графическое изображение CONF нисходящей структуры:
> 
> 
> 
> 
> https://cryptology.courses/labs/rynochnaya-struktura-advancedrinkova-struktura-advanced                                                      7/9

### S_SFP_REFINE — 16 word/document.xml:P0084–P0087

> Как же использовать SFP в торговле?
> После завершения формирования паттерна, вы можете перейти на младший
> таймфрейм и дождаться слома структуры. После этого можно искать точку
> входа.

### S_STB_ENTRY — SW22 p3–4

> 12/02/2023, 23:10                                       https://cryptology.courses/labs/torgovye-instrumenty-pro--torgovi-instrumenti-pro
> 
> 
> 
> 
>                        Графический пример
> 
> 
> 
> 
>                        После того, как происходит слом структуры и поглощение всего движения BTS –
>                        у крупного игрока (умный капитал), остается открытой лонг позиция, которая
>                        является в моменте убыточной. В дальнейшем, чтобы закрыть данный минус или
>                        усреднить точку входа, крупному игроку нужно вернуть цену к значениям,
>                        зарождающим данное движение в шорт, чтобы полностью перекрыть свой
>                        убыток - тест зоны 0.5.
> 
>                        Мы можем использовать STB/BTS как вход в позицию. Точкой входа будет
>                        являться как верхняя часть (лонг)/нижняя часть (шорт), так и 0.5 всей зоны
>                        STB/BTS, но должны быть соблюдены следующие факторы:
> 
>                            1. Потенциальная позиция совпадает с основным трендом.
>                            2. Ценовое движение сняло пул ликвидности и полностью поглотило
>                               манипуляцию при развороте.
>                            3. Произошел слом, либо подтверждение структуры.
> 
> 
> 
> 
>                        3. Mitigation
> https://cryptology.courses/labs/torgovye-instrumenty-pro--torgovi-instrumenti-pro                                                           3/6
> 12/02/2023, 23:10                                       https://cryptology.courses/labs/torgovye-instrumenty-pro--torgovi-instrumenti-pro
> 
>                        Mitigation (test) - после удачной манипуляции и открытия лонг/шорт позиции,
>                        крупному игроку нужно закрыть свою шортовую/лонговую позицию так как она
>                        становится убыточной.
> 
>                        Итак, крупный игрок открывает еще одну позицию для того, чтобы доставить
>                        цену в нужный диапазон. Если следовать правилу Premium/ Discount цена
>                        должна протестировать зону 0.5, либо ниже/выше 0.5. Туда и будет
>                        сконцентрировано наше внимание.
> 
>                        Схематический пример
> 
> 
> 
> 
>                        Графический пример
> 
> 
> 
> 
> https://cryptology.courses/labs/torgovye-instrumenty-pro--torgovi-instrumenti-pro                                                           4/6

### S_RANGE_AGGRESSIVE — 06 word/document.xml:P0111–P0118

> . Агрессивный
> - на девиации и только при наличии POI под/над боковиком.
> Вероятность отработки вашего трейда будет увеличена присутствием факторов,
> которые указывают на слабость покупателя/продавца. Самый распространенный
> инструмент для этого - дивергенции (инструмент будет разбираться в
> следующих темах).
> Схематическое изображение
> Графическое изображение

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

### S_AMD — 19 word/document.xml:P0163–P0170

> AMD(accumulation-manipulation- distribution) цикл
> Накопление - период аккумуляции позиций участниками рынками по завышенным ценам.
> Манипуляция - этап участия "умных денег" , которые штучно двигают цену вниз , заставляя участников рынка убыточно закрывать позиции , тем самым , откупать актив по минимальной цене для его дальнейшей реализации по завышенной цене. 3)Распределение - этап продажи активов "умными деньгами" остальным участникам рынка по сверх высокой цене.
> Рассматривают два основных варианта набора позиций в цикле:
> Работа с локальными зонами интереса , в месте перехода цены из зоны манипуляции в зону распределения.
> Покупка актива в зоне манипуляции. Рискованный вариант - так как на этом этапе цена не может показать настрой покупателей ( момент перехода в зону распределения , когда цена обновляет локальный максимум ). Поэтому покупка производится на свой страх и риск. Стоит обратить внимание на :
> Как быстро цена зашла в ренж после ухода из зоны накопления Зоны ликвидности сверху + снятие низов на этапе манипуляции
> Повышение объемов при покупке = зеленых свечах ( в сравнении с красными ) на этапе манипуляции

## Все диаграммы в relevant source scope

- SW9 PDF page 2: `data/source_materials/primary_pdf_2026_10_09/SW9.pdf`; вся страница, включая схемы.
- SW9 PDF page 6: `data/source_materials/primary_pdf_2026_10_09/SW9.pdf`; вся страница, включая схемы.
- SW9 PDF page 7: `data/source_materials/primary_pdf_2026_10_09/SW9.pdf`; вся страница, включая схемы.
- SW9 PDF page 3: `data/source_materials/primary_pdf_2026_10_09/SW9.pdf`; вся страница, включая схемы.
- SW9 PDF page 4: `data/source_materials/primary_pdf_2026_10_09/SW9.pdf`; вся страница, включая схемы.
- SW9 PDF page 5: `data/source_materials/primary_pdf_2026_10_09/SW9.pdf`; вся страница, включая схемы.
- SW5 PDF page 6: `data/source_materials/primary_pdf_2026_10_09/SW5.pdf`; вся страница, включая схемы.
- SW5 PDF page 7: `data/source_materials/primary_pdf_2026_10_09/SW5.pdf`; вся страница, включая схемы.
- 16 `word/media/image7.jpg`, SHA256 `93a10874acd06810bec4fcc1ac9745c1ff80e51d135b2f90503330a9ec51b59a`; после P0089, OCR `data/source_materials/cryptology_2026_10_09/diagram_ocr/93a10874acd06810bec4fcc1ac9745c1ff80e51d135b2f90503330a9ec51b59a.txt`.
- SW22 PDF page 3: `data/source_materials/primary_pdf_2026_10_09/SW22.pdf`; вся страница, включая схемы.
- SW22 PDF page 4: `data/source_materials/primary_pdf_2026_10_09/SW22.pdf`; вся страница, включая схемы.
- 06 `word/media/image13.jpg`, SHA256 `c81dbbc3ef15ca3755864ed0f987d58bb9e9cc6becf2199c313ac5be824cb423`; после P0129, OCR `data/source_materials/cryptology_2026_10_09/diagram_ocr/c81dbbc3ef15ca3755864ed0f987d58bb9e9cc6becf2199c313ac5be824cb423.txt`.
- 06 `word/media/image14.jpg`, SHA256 `beaa8047c54bd2c988b4c264bf596d1ac3be1a7a683f9ac67982e709a1de6cb7`; после P0129, OCR `data/source_materials/cryptology_2026_10_09/diagram_ocr/beaa8047c54bd2c988b4c264bf596d1ac3be1a7a683f9ac67982e709a1de6cb7.txt`.
- 06 `word/media/image15.jpg`, SHA256 `bace8d0ac14330586507f1ce4fd2f1821fd78ae390261804adcb7f68841b5e5c`; после P0129, OCR `data/source_materials/cryptology_2026_10_09/diagram_ocr/bace8d0ac14330586507f1ce4fd2f1821fd78ae390261804adcb7f68841b5e5c.txt`.
- 19 `word/media/image23.jpg`, SHA256 `4ea93e8e697f85283eb708642ebb84decbe11ebd0d1819a607f2d4b66eee01ae`; после P0130, OCR `data/source_materials/cryptology_2026_10_09/diagram_ocr/4ea93e8e697f85283eb708642ebb84decbe11ebd0d1819a607f2d4b66eee01ae.txt`.
- 19 `word/media/image27.jpg`, SHA256 `106a333c1872c3eee633c8ccd1f9eb173cce540b08a25bae8ebac5975a2b5eb6`; после P0162, OCR `data/source_materials/cryptology_2026_10_09/diagram_ocr/106a333c1872c3eee633c8ccd1f9eb173cce540b08a25bae8ebac5975a2b5eb6.txt`.
- 19 `word/media/image28.jpg`, SHA256 `1dc91d46f479024a5345b2293700773e22668e66c44f0d21294ef90b23702db6`; после P0162, OCR `data/source_materials/cryptology_2026_10_09/diagram_ocr/1dc91d46f479024a5345b2293700773e22668e66c44f0d21294ef90b23702db6.txt`.
- 19 `word/media/image29.jpg`, SHA256 `ed986805f2e8590404509a6a927fa6fc15b42c2b80a3f5f9f46132706d8657af`; после P0165, OCR `data/source_materials/cryptology_2026_10_09/diagram_ocr/ed986805f2e8590404509a6a927fa6fc15b42c2b80a3f5f9f46132706d8657af.txt`.
- 19 `word/media/image30.jpg`, SHA256 `ad134475265a0f03b2c84ccf408d42f39650ba2830e8f3e9fc15265f1294f1ac`; после P0165, OCR `data/source_materials/cryptology_2026_10_09/diagram_ocr/ad134475265a0f03b2c84ccf408d42f39650ba2830e8f3e9fc15265f1294f1ac.txt`.
- 19 `word/media/image31.jpg`, SHA256 `3c298df9dd4a5dd2600f025a15c4b1acb9da326192dff3e47a56a80417089bd9`; после P0165, OCR `data/source_materials/cryptology_2026_10_09/diagram_ocr/3c298df9dd4a5dd2600f025a15c4b1acb9da326192dff3e47a56a80417089bd9.txt`.

Полный inventory всех122 unique DOCX diagrams и195 media occurrences сохранён в прежнем audit. Новый diagram_anchor_index сопоставляет inline image с deduplicated paragraph IDs. PDF locators указывают оригинальные страницы; screenshot не добавляет неизвестный numerical cutoff. До/после P locator — приблизительный textual anchor, не заявка на авторский номер рисунка.

## Варианты трактовки и прямо разрешённое

OB direct и confirmation styles; STB edge и0.5; Range aggressive/conservative; SFP optional LTF refinement. Одна ситуация может иметь несколько source аргументов.

## Прямо запрещённое / отдельно не доказанное

Источник не задаёт total ordering SFP>OB>BR>Range; нельзя считать порядок Python loops истиной или умножать все confluent tags на trades.

## Приоритет и source hierarchy

Единственный конкретный OB priority SW9p7: нижний OB при незакрытом IMB под верхним; локальное исключение, не глобальный resolver.

## Конфликты и отсутствие единственного выбора

Методички описывают toolbox и личный стиль (DOC03P0004/P0007), не immutable ordered strategy. SFP+OB может быть setup+trigger, не две независимые идеи.

## Deterministic rule без добавления стратегии

Нет source total ordering/physical identity. До решения выдавать набор candidates с provenance и unresolved ownership; не исполнять ни один при materially conflicting plans.

## Зафиксированные решения

- Не выбирать branch по старым67.68%, current WR, частоте или losses.
- SOURCE_PERMITTED components не доказывают произвольную комбинацию или simultaneous portfolio trades.

## Known_at

Formation после native completed CLOSE всех dependencies; swing после правой свечи. Next open известен в OPEN без будущего high/low/close. Sweep/POI test/failure изменяют состояние только с causal event; repeated reaction не backdated. Setup plan до entry, invalidation после completed native CLOSE. Фактическое время жизни сделки и финансовый outcome не доступны resolver.
