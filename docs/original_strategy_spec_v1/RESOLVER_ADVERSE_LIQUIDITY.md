# RESOLVER_ADVERSE_LIQUIDITY v1

Status: Source conditional blocker определён; единственный OHLC классификатор meaningful/adverse не восстанавливается. Need explicit causal annotations/normalization, не подбор thresholds. Resolver завершён документально, semantic gap остаётся.

## Relevant source passages

### S_ADVERSE_BLOCK — 03 word/document.xml:P0061–P0066

> Причина и следствие.
> Стоит подчеркнуть, логику работы с ликвидностью можно выразить через принцип Причинно следственной связи.
> Где билдинг ликвидности является причиной а движение к этой ликвидности следствием.
> Самы простым способом для определения предубеждения куда возможно пойдет цена это найти причину (Ликвидность)
> Открывать сделки при наличии ликвидности против сетапа категорически запрещено, с большой долей вероятности сделка потерпит неудачу.
> Начиная анализ рынка со стороны причины и следствия получаем максимально больше уверенности, так как в результате такого анализа понимается понимание куда будут доставлять цену.

### S_ADVERSE_WAIT — 14 word/document.xml:P0155–P0159

> Использование EQH/EQL
> EQH/EQL помогает найти цель для трейда, а также подсказывает, когда не стоит
> входить в позицию.
> Если ниже вашей точки входа есть EQH/EQL, тогда вход в позицию
> осуществляем после того, как цена их снимет.

### S_EQ_STRUCTURE — 14 word/document.xml:P0122–P0159

> EQH/EQL
> Равные максимумы и минимумы (EQH/EQL) - скопление ликвидности в виде
> большого количества стоп ордеров.
> Такой пул ликвидности будет являться сильным магнитом для цены. Происходит
> это по причине того, что большинство людей торгующих классический
> технический анализ ставят свои стоп ордера за такими видимыми уровнями.
> Крупный игрок намеренно оставляет эти зоны, чтобы в дальнейшем
> использовать скопившуюся ликвидность для дальнейшего движения.
> Схематический пример EQH/EQL
> Пример неправильного EQH/EQL на графике
> Пример правильного EQH/EQL на графике
> Пример EQH на графике
> Сформировав равные максимумы, цена начала двигаться в противоположном
> направлении, побуждая ритейл-трейдеров ставить стоп ордера за данный
> уровень.
> Накопившаяся ликвидность над сформировавшимся пулом послужила
> “топливом” для дальнейшего роста.
> Пример EQL на графике
> Сформировав равные минимумы, цена начала двигаться в противоположном
> Накопившаяся ликвидность под сформировавшимся пулом послужила
> “топливом” для дальнейшего падения.
> Обратите внимание:
> 1
> . EQH/EQL необязательно должны быть ровными как по линейке. Допускается
> отклонение в наклоне (в пределах разумного). Этот наклон должен
> соответствовать правилу:
> Для EQH - левый максимум выше правого.
> Для EQL - левый минимум ниже правого. (показано на схематическом и
> графическом примере выше).
> 2
> . Важно понимать, что EQH/EQL образуются между свингами
> субструктуры, а не между двумя свечами на графике.
> Неправильный пример
> Использование EQH/EQL
> EQH/EQL помогает найти цель для трейда, а также подсказывает, когда не стоит
> входить в позицию.
> Если ниже вашей точки входа есть EQH/EQL, тогда вход в позицию
> осуществляем после того, как цена их снимет.

### S_POOL_SCOPE — 14 word/document.xml:P0169–P0198

> BSL/SSL могут являться:
> Уровни открытия/закрытия торговых сессий.
> Уровни открытия/закрытия прошлого дня/недели/месяца.
> Внутренняя и внешняя ликвидность.
> Первые два пункта относятся к более продвинутым будущим темам, для которых
> нужно понимать контекст. В данной теме мы будем разбирать внутреннюю и
> внешнюю ликвидность.
> Внутренняя и внешняя ликвидность
> Внутренняя ликвидность (internal) расположена внутри бокового движения или
> образованного импульса, между структурным максимумом и минимумом, на
> соответствующем ТФ.
> Внешняя ликвидность (external) расположена за границами бокового движения
> и на структурных максимумах и минимумах соответствующего ТФ.
> Пример внутренней и внешней ликвидности на графике
> Внутри структурного импульса цена ходит от ликвидности к ликвидности. Во
> время снятия “старой” ликвидности образуется “новая” и т.д. Так продолжается
> до тех пор, пока цена не снимет одну из внешних.
> Цена, поработав с внутренней ликвидностью, сняла внешнюю
> и сделала
> обновление структуры.
> Внешняя и внутренняя ликвидность на примере бокового движения
> Механика работы с боковым движением будет разбираться в уроке “Боковое
> движение”.
> Сначала цена поработала с внутренней ликвидностью, затем сняла внешнюю.
> Была оставлена подсказка в виде открытой ликвидности внутри и
> снаружи ренджа.
> После работы с локальной внешней и внутренней
> ликвидностью боковика, цена идет снимать значимую внешнюю ликвидность.
> Правила работы с ликвидностью действительны для всех ТФ (от 1 секунды до 1
> месяца).

### S_LIQUIDITY_CONTEXT — 14 word/document.xml:P0113–P0120

> Как ликвидность используется в торговле?
> Ликвидность не является точкой входа в позицию (только при продвинутой
> работе, которая рассматривается в пакете “Advanced” и “Pro”).
> Мы никогда не знаем, послужит ли ликвидность “топливом” или обратными
> заявками для набора позиции.
> Мы не можем утверждать, за какой именно ликвидностью пойдет цена.
> Мы будем использовать ликвидность как цель трейда, в которой позиция будет
> фиксироваться.

### S_LIQUIDITY_CONTEXT — 19 word/document.xml:P0117–P0121

> LIQUIDITY(ликвидность - стопы игроков)
> Ликвидность выступает как цель вашего трейда
> Ликвидность-это инструменты Тех Анализа, которыми мы должны сманипулировать
> Equal lows/equal highs(одинаковые хаи или лои)
> Trendline liquidity(трендовая ликвидность)

### S_PREVIOUS_LEVELS — SW12 p9–10

> 12/02/2023, 22:33                                      https://cryptology.courses/labs/indikatoryindikatori
> 
> 
> 
> 
>                         Резкое увеличение объёма торгов указывает на возросшую вероятность
>                         изменения цены.
> 
>                         Как правило, увеличение объема можно наблюдать во время новостных
>                         событий. Сильные трендовые движения идут рука об руку с увеличением
>                         объемов торгов, поэтому его рассматривают как признак силы.
> 
>                         Можно ожидать высокий объем покупок на уровне поддержки и высокий объем
>                         продаж на уровне сопротивления.
> 
>                         Большинство трейдеров используют объемы в сочетании с торговыми
>                         инструментами для подтверждения.
> 
> 
> 
> 
>                         5. Cryptology PDH/PDL
>                         Вспомогательный индикатор, используется как дополнительный фактор при
>                         работе с концепцией Smart Money. Показывает уровни максимума/минимума
>                         дня, недели, месяца.
> 
>                         Индикатор и инструкции по установке можно найти тут.
> 
> 
> 
> 
> https://cryptology.courses/labs/indikatoryindikatori                                                          9/15
> 12/02/2023, 22:33                                      https://cryptology.courses/labs/indikatoryindikatori
> 
> 
> 
> 
>                         PMH/PML - уровни максимум/минимум месяца.
> 
>                         PWH/PWL - уровни максимум/минимум недели.
> 
>                         PDH/PDL - уровни максимум/минимум дня.
> 
>                         Эти ценовые уровни, также известные как «PDL» и «PDH», служат важными
>                         ориентирами для определения важных ценовых уровней, помогающих
>                         подтвердить торговые идеи.
> 
>                         PDH/PDL - уровни максимум/минимум дня, это также основные пулы
>                         ликвидности предыдущего дня, ритейл трейдеры прошлого дня выставляют
>                         свои стоп ордера, за данные уровни.
> 
>                         Цена PDH/PDL может быть важным фактором при построении торгового плана
>                         на день.
> 
> 
> 
> 
>                         6. ATR
>                         Средний истинный диапазон (англ. The Average True Range, АTR) - это
>                         инструмент, используемый в техническом анализе для измерения уровня
>                         волатильности.
> 
>                         В отличие от других современных популярных индикаторов, ATR не
>                         используется для выявления направления движения цены. Он используется
> 
> https://cryptology.courses/labs/indikatoryindikatori                                                          10/15

### S_FTA — SW9 p11–13

> 12/02/2023, 21:46                                 https://cryptology.courses/labs/torgovye-instrumenty-advancedtorgovi-instrumenti-advanced
> 
>                       POI - это общее название для рабочих инструментов, которыми могут выступать
>                       манипуляции, ордерблоки, брейкеры и другие торговые элементы.
> 
>                       Мы выделяем данные зоны и при подходе цены к ним рассматриваем реакцию
>                       на на эту зону. На основе реакции принимается решение о входе в сделку.
> 
>                       Схематический пример POI
> 
> 
> 
> 
>                       5. First Trouble Area (FTA)
>                       FTA (First Trouble Area) - это первая проблемная зона после смены характера
>                       движения. В качестве FTA могут использоваться различные POI, которые
>                       находятся в противоположном направлении от вашего входа. Так как вход может
>                       осуществляться как по тренду, так и против него, зона FTA может находиться в
>                       разных местах.
> 
>                       Работа по тренду
> 
>                       После слома младшего ТФ и перехода коррекционного движения в импульсное
>                       движение, рыночный тренд находится в синхронизации (к примеру, старший и
>                       младший ТФ - нисходящий). Если вы открываете сделку по тренду, то ваш тейк-
>                       профит (полный, либо частичный) будет находиться у первой проблемной зоны
>                       (FTA).
> 
>                       Схематический пример FTA
> 
> 
> 
> 
> https://cryptology.courses/labs/torgovye-instrumenty-advancedtorgovi-instrumenti-advanced                                                     11/16
> 12/02/2023, 21:46                                 https://cryptology.courses/labs/torgovye-instrumenty-advancedtorgovi-instrumenti-advanced
> 
> 
> 
> 
>                       Графический пример FTA
> 
> 
> 
> 
> https://cryptology.courses/labs/torgovye-instrumenty-advancedtorgovi-instrumenti-advanced                                                     12/16
> 12/02/2023, 21:46                                 https://cryptology.courses/labs/torgovye-instrumenty-advancedtorgovi-instrumenti-advanced
> 
> 
> 
> 
>                       Работа в контртренд
> 
>                       После слома младшего ТФ и перехода импульсного движения в коррекционное,
>                       рыночный тренд находится в рассинхронизации (к примеру, старший ТФ
>                       восходящий, а младший - нисходящий). Если вы открываете контртрендовую
>                       сделку, то ваш тейк-профит будет находиться у первой проблемной зоны (FTA).
> 
>                       Схематический пример FTA
> 
> 
> 
> 
>                       Графический пример FTA
> 
> 
> 
> 
> https://cryptology.courses/labs/torgovye-instrumenty-advancedtorgovi-instrumenti-advanced                                                     13/16

### S_FTA — SW9 p16–16

> 12/02/2023, 21:46                                 https://cryptology.courses/labs/torgovye-instrumenty-advancedtorgovi-instrumenti-advanced
> 
> 
> 
> 
>                       7. Выводы
>                       Ордерблок является хорошим фактором для входа, но должны быть соблюдены
>                       все необходимые условия. Вход в позицию должен осуществляться только по
>                       тренду. Импульсно пробитый ордерблок становится брейкером.
> 
>                       FTA называют первой проблемной зоной, которой может быть любая POI со
>                       старшего ТФ. При открытии контртрендовой сделки, у зоны FTA мы производим
>                       частичную или полную фиксацию позиции.
> 
> 
> 
> 
> https://cryptology.courses/labs/torgovye-instrumenty-advancedtorgovi-instrumenti-advanced                                                     16/16

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

## Все диаграммы в relevant source scope

- 03 `word/media/image8.jpg`, SHA256 `6ef5085099d24f3ac754239fb4b2926659723e4c4d3de6fdd1259a955bc3988a`; после P0060, OCR `data/source_materials/cryptology_2026_10_09/diagram_ocr/6ef5085099d24f3ac754239fb4b2926659723e4c4d3de6fdd1259a955bc3988a.txt`.
- 03 `word/media/image9.jpg`, SHA256 `47df695ba6dff8519e11718f2a29db40e6fb9e3df9290e821766e3a211561f2f`; после P0064, OCR `data/source_materials/cryptology_2026_10_09/diagram_ocr/47df695ba6dff8519e11718f2a29db40e6fb9e3df9290e821766e3a211561f2f.txt`.
- 14 `word/media/image17.jpg`, SHA256 `a502b49e4de5b69ddb8b108f909136676c51d51ee91b52a0f97e79083e30d310`; после P0153, OCR `data/source_materials/cryptology_2026_10_09/diagram_ocr/a502b49e4de5b69ddb8b108f909136676c51d51ee91b52a0f97e79083e30d310.txt`.
- 14 `word/media/image9.jpg`, SHA256 `9ce1fe30fadf5d8fdec5bad051f4740566df5cc060655f4ab5a179eec4ced5fe`; после P0120, OCR `data/source_materials/cryptology_2026_10_09/diagram_ocr/9ce1fe30fadf5d8fdec5bad051f4740566df5cc060655f4ab5a179eec4ced5fe.txt`.
- 14 `word/media/image10.jpg`, SHA256 `981814945630bfbbda961523b0b3b7201cdb255b0c6d0380ff3f1c53421bbffa`; после P0120, OCR `data/source_materials/cryptology_2026_10_09/diagram_ocr/981814945630bfbbda961523b0b3b7201cdb255b0c6d0380ff3f1c53421bbffa.txt`.
- 14 `word/media/image11.jpg`, SHA256 `eddc080738697fe504a48e21bd5de00a1ce05ccfed5476dc7c2cfdeb08b00e22`; после P0131, OCR `data/source_materials/cryptology_2026_10_09/diagram_ocr/eddc080738697fe504a48e21bd5de00a1ce05ccfed5476dc7c2cfdeb08b00e22.txt`.
- 14 `word/media/image12.jpg`, SHA256 `f503218d2329d39aa09d0b123a32242aa95bd27b7ff7431eca7e760b70e9acf8`; после P0131, OCR `data/source_materials/cryptology_2026_10_09/diagram_ocr/f503218d2329d39aa09d0b123a32242aa95bd27b7ff7431eca7e760b70e9acf8.txt`.
- 14 `word/media/image13.jpg`, SHA256 `6ad7370c26fb588150a6834bd5bb03962e4b785e49b9a6e0de1c0b8cb20501a4`; после P0133, OCR `data/source_materials/cryptology_2026_10_09/diagram_ocr/6ad7370c26fb588150a6834bd5bb03962e4b785e49b9a6e0de1c0b8cb20501a4.txt`.
- 14 `word/media/image14.jpg`, SHA256 `644e579249138b9453eda6f9cca2d8e5c94980afb7cf046e8bd23f4764ff0496`; после P0133, OCR `data/source_materials/cryptology_2026_10_09/diagram_ocr/644e579249138b9453eda6f9cca2d8e5c94980afb7cf046e8bd23f4764ff0496.txt`.
- 14 `word/media/image15.jpg`, SHA256 `6fd5e5b5f21429dfa1556e1795eb97843258278a1bd2596447eaa1f9e33fae8f`; после P0139, OCR `data/source_materials/cryptology_2026_10_09/diagram_ocr/6fd5e5b5f21429dfa1556e1795eb97843258278a1bd2596447eaa1f9e33fae8f.txt`.
- 14 `word/media/image16.jpg`, SHA256 `5f39b7bdf1daa813f472a5dabc27004ba096a3a49d953343f5ab67a8830d90e6`; после P0139, OCR `data/source_materials/cryptology_2026_10_09/diagram_ocr/5f39b7bdf1daa813f472a5dabc27004ba096a3a49d953343f5ab67a8830d90e6.txt`.
- 14 `word/media/image18.jpg`, SHA256 `16f964b5837fc6b01442de8875966e7e7104401d6468ea42d2740058846448ae`; после P0169, OCR `data/source_materials/cryptology_2026_10_09/diagram_ocr/16f964b5837fc6b01442de8875966e7e7104401d6468ea42d2740058846448ae.txt`.
- 14 `word/media/image19.jpg`, SHA256 `a8cab84e55b2b294f33932d4e83b7d86af51df4edc60e38cfa7589a824c3dab0`; после P0185, OCR `data/source_materials/cryptology_2026_10_09/diagram_ocr/a8cab84e55b2b294f33932d4e83b7d86af51df4edc60e38cfa7589a824c3dab0.txt`.
- 14 `word/media/image20.jpg`, SHA256 `624cac30cd122a63d60b409f0b46748c78d9dc09bf1e3aa5ee1601f6aae021cf`; после P0185, OCR `data/source_materials/cryptology_2026_10_09/diagram_ocr/624cac30cd122a63d60b409f0b46748c78d9dc09bf1e3aa5ee1601f6aae021cf.txt`.
- 14 `word/media/image21.jpg`, SHA256 `b937eef65e2e345e548dc8e2f8a3509dc535727348c5ebb16236f2df222415fd`; после P0191, OCR `data/source_materials/cryptology_2026_10_09/diagram_ocr/b937eef65e2e345e548dc8e2f8a3509dc535727348c5ebb16236f2df222415fd.txt`.
- 14 `word/media/image22.jpg`, SHA256 `b01e58717548c695111e2fdd287031dff0be3bba32b01e8d0d8b1a423c0afec6`; после P0191, OCR `data/source_materials/cryptology_2026_10_09/diagram_ocr/b01e58717548c695111e2fdd287031dff0be3bba32b01e8d0d8b1a423c0afec6.txt`.
- 19 `word/media/image17.jpg`, SHA256 `a8c09fb5da019793b8600dff2a056a6124601a0094a19c5f82cb62724d2b6c4e`; после P0116, OCR `data/source_materials/cryptology_2026_10_09/diagram_ocr/a8c09fb5da019793b8600dff2a056a6124601a0094a19c5f82cb62724d2b6c4e.txt`.
- 19 `word/media/image18.jpg`, SHA256 `174ba866f4b37de25264eedeed18b251c3954b04ac3b825b7a39253bf9a5cc6f`; после P0116, OCR `data/source_materials/cryptology_2026_10_09/diagram_ocr/174ba866f4b37de25264eedeed18b251c3954b04ac3b825b7a39253bf9a5cc6f.txt`.
- 19 `word/media/image19.jpg`, SHA256 `6f9d5563da2857954e14bf989484fe6d2d51d409951b7eaa3e3dfbf889ad82a2`; после P0121, OCR `data/source_materials/cryptology_2026_10_09/diagram_ocr/6f9d5563da2857954e14bf989484fe6d2d51d409951b7eaa3e3dfbf889ad82a2.txt`.
- 19 `word/media/image20.jpg`, SHA256 `4931d9ea03e48c73d0f37aeee9edcf22e110b4eee4586fd86c258f5f8078d5cd`; после P0121, OCR `data/source_materials/cryptology_2026_10_09/diagram_ocr/4931d9ea03e48c73d0f37aeee9edcf22e110b4eee4586fd86c258f5f8078d5cd.txt`.
- SW12 PDF page 9: `data/source_materials/primary_pdf_2026_10_09/SW12.pdf`; вся страница, включая схемы.
- SW12 PDF page 10: `data/source_materials/primary_pdf_2026_10_09/SW12.pdf`; вся страница, включая схемы.
- SW9 PDF page 11: `data/source_materials/primary_pdf_2026_10_09/SW9.pdf`; вся страница, включая схемы.
- SW9 PDF page 12: `data/source_materials/primary_pdf_2026_10_09/SW9.pdf`; вся страница, включая схемы.
- SW9 PDF page 13: `data/source_materials/primary_pdf_2026_10_09/SW9.pdf`; вся страница, включая схемы.
- SW9 PDF page 16: `data/source_materials/primary_pdf_2026_10_09/SW9.pdf`; вся страница, включая схемы.
- SW22 PDF page 5: `data/source_materials/primary_pdf_2026_10_09/SW22.pdf`; вся страница, включая схемы.
- SW22 PDF page 6: `data/source_materials/primary_pdf_2026_10_09/SW22.pdf`; вся страница, включая схемы.

Полный inventory всех122 unique DOCX diagrams и195 media occurrences сохранён в прежнем audit. Новый diagram_anchor_index сопоставляет inline image с deduplicated paragraph IDs. PDF locators указывают оригинальные страницы; screenshot не добавляет неизвестный numerical cutoff. До/после P locator — приблизительный textual anchor, не заявка на авторский номер рисунка.

## Варианты трактовки и прямо разрешённое

Structural swings/EQ pools и internal/external liquidity своего context. EQ между substructure swings, tilted orientation source-defined. В направлении trade liquidity может быть target/fuel, opposing POI — FTA; против setup нужна задержка до sweep.

## Прямо запрещённое / отдельно не доказанное

Не превращать любой unswept LOW behind LONG или HIGH behind SHORT на всех TF в uniquely proven blocker. Не удалить751audit trades. UNKNOWN meaning != no adverse; направление топлива заранее неизвестно.

## Приоритет и source hierarchy

DOC03P0065 категорический запрет относится к liquidity ПРОТИВ SETUP; DOC14P0113–20/155–59 различает target и ожидание. Они совместимы после contextual classification, не blanket removal.

## Конфликты и отсутствие единственного выбора

Meaningful — operational term audit, не literal numerical source criterion. «Ниже точки входа» DOC14 не уточняет short/scope/distance. Slope reasonable и structural relevance качественны.

## Deterministic rule без добавления стратегии

Source conditional blocker определён; единственный OHLC классификатор meaningful/adverse не восстанавливается. Need explicit causal annotations/normalization, не подбор thresholds. Resolver завершён документально, semantic gap остаётся.

## Зафиксированные решения

- ADVERSE_PROVEN→WAIT_SWEEP, target/FTA не blocker; UNKNOWN→UNRESOLVED.
- После известного sweep старого pool blocker исчезает для него, но новая liquidity/слом setup требуют повторной оценки.

## Known_at

Formation после native completed CLOSE всех dependencies; swing после правой свечи. Next open известен в OPEN без будущего high/low/close. Sweep/POI test/failure изменяют состояние только с causal event; repeated reaction не backdated. Setup plan до entry, invalidation после completed native CLOSE. Фактическое время жизни сделки и финансовый outcome не доступны resolver.
