"""Build a source-cited, outcome-free specification; never import a trading engine."""
from __future__ import annotations

import csv
import json
import posixpath
import re
import zipfile
from hashlib import sha256
from pathlib import Path
from xml.etree import ElementTree as ET

REPO = Path(__file__).resolve().parents[1]
SPEC = REPO / 'docs/original_strategy_spec_v1'
EVIDENCE = REPO / 'data/reports/original_strategy_spec_v1_2026_10_11'
AUDIT = REPO / 'data/reports/source_fidelity_2026_10_11'
AUDIT_COMMIT = 'c2d1e8cfb94637caaf150bb9c508cb011c3e85ba'
BASELINE = '19404ec0f4a7dd39b93c76240b6ad605278f0646'
NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
      'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, str):
        path.write_text(value.rstrip() + '\n', encoding='utf-8')
    else:
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def write_csv(path, rows):
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def source_index():
    materials = json.loads((AUDIT / 'source_inventory.json').read_text())['materials']
    result = {}
    media = []
    for material in materials:
        ident = material['source_id']
        text = (REPO / material['text']).read_text()
        units = {}
        if material['type'] == 'PDF':
            chunks = re.split(r'===== \w+ PAGE (\d+) =====', text)
            units = {int(chunks[i]): chunks[i + 1].strip() for i in range(1, len(chunks), 2)}
        else:
            main = text.split('PART word/document.xml\n', 1)[1].split('\nPART ', 1)[0]
            units = {int(m.group(1)): m.group(2) for m in re.finditer(r'^P(\d+) (.*)$', main, re.MULTILINE)}
            with zipfile.ZipFile(REPO / material['original']) as archive:
                rel = ET.fromstring(archive.read('word/_rels/document.xml.rels'))
                mapping = {element.attrib['Id']: posixpath.normpath('word/' + element.attrib['Target'])
                           for element in rel if element.attrib.get('TargetMode') != 'External'}
                xml = ET.fromstring(archive.read('word/document.xml'))
                mc = 'http://schemas.openxmlformats.org/markup-compatibility/2006'
                for alternate in xml.iter('{' + mc + '}AlternateContent'):
                    for child in list(alternate)[1:]:
                        alternate.remove(child)
                parents = {child: parent for parent in xml.iter() for child in parent}
                paragraph = 0
                seen = {}
                for element in xml.iter('{' + NS['w'] + '}p'):
                    own_text = []
                    for node in element.iter('{' + NS['w'] + '}t'):
                        owner = parents.get(node)
                        while owner is not None and owner.tag != '{' + NS['w'] + '}p':
                            owner = parents.get(owner)
                        if owner is element:
                            own_text.append(node.text or '')
                    value = ''.join(own_text).strip()
                    if value and value not in seen:
                        paragraph += 1
                        seen[value] = paragraph
                        assert units[paragraph] == value, (ident, paragraph)
                    for blip in element.findall('.//a:blip', NS):
                        member = mapping[blip.attrib['{' + NS['r'] + '}embed']]
                        image_hash = sha256(archive.read(member)).hexdigest()
                        media.append({'source_id': ident, 'member': member, 'sha256': image_hash,
                                      'after_paragraph': paragraph, 'next_paragraph': paragraph + 1,
                                      'ocr': f'data/source_materials/cryptology_2026_10_09/diagram_ocr/{image_hash}.txt'})
        result[ident] = {**material, 'units': units, 'text_sha256': digest(REPO / material['text'])}
    assert len(result) == 13
    save(EVIDENCE / 'diagram_anchor_index.json', media)
    save(EVIDENCE / 'source_review_index.json', [
        {k: v for k, v in material.items() if k != 'units'} for material in result.values()])
    return result, media


# Direct source meanings, never copied from MediumTermEngine policies.
# ID, citations (document, first, last), literal meaning, executable interpretation, applicability.
SOURCE_RULES = [
 ('S_FRACTAL', [('03',28,30),('11',113,115)], 'Top-down анализ фрактальной структуры; W1/D1 глобально, H1/H4 локально.', 'Хранить относительные TF роли; не требовать universal owner или AND четырёх TF.', 'context-dependent'),
 ('S_STRUCTURE', [('SW5',2,3),('19',53,73)], 'HH/HL вверх, LH/LL вниз; структура — фундамент анализа.', 'Направление устанавливается на выбранном контекстном TF по подтверждённым ключевым парам.', 'mandatory'),
 ('S_SWING', [('SW5',2,2)], 'Три последовательные свечи; экстремум центральной строго выше/ниже двух крайних.', 'high[i]>high[i-1],high[i+1] или low[i]<low[i-1],low[i+1]; известно после CLOSE правой свечи.', 'context-dependent'),
 ('S_BOS', [('SW5',4,5),('19',88,100)], 'BOS пробивает ключевой HL/LH с закреплением тела; новая структура развивается после слома.', 'Тело CLOSE за защищённым уровнем; прокол тенью не равен BOS.', 'context-dependent'),
 ('S_CONF', [('SW5',6,7)], 'CONF — обновление ключевого экстремума новой структуры; консервативно искать вход после CONF.', 'CONF не синоним любого BOS; отдельная source-permitted более консервативная ветвь.', 'context-dependent'),
 ('S_FLOW', [('SW22',5,6)], 'Актуальный Order Flow сочетает структуру, работу с ликвидностью и доставку в global POI.', 'Оценивать структурные пары, рейды и ещё не протестированную цель выбранного flow; после теста не продолжать старое flow автоматически.', 'context-dependent'),
 ('S_POI', [('SW9',10,11)], 'POI — диапазон ожидаемой реакции: OB, Breaker, манипуляции и другие элементы.', 'POI имеет происхождение, TF, границы и known_at; голая метка POI не подтверждает вход.', 'context-dependent'),
 ('S_LIQUIDITY_CONTEXT', [('14',113,120),('19',117,121)], 'Ликвидность — контекст и цель, не самостоятельный базовый сигнал; направление снятия заранее не гарантировано.', 'Классифицировать роль относительно setup, не считать каждый pool входом или blocker.', 'mandatory'),
 ('S_ADVERSE_BLOCK', [('03',61,66)], 'При ликвидности против сетапа вход категорически запрещён.', 'Если source-adverse установлено доказательствами — WAIT_SWEEP/REJECT; UNKNOWN классификации не превращать в NO_ADVERSE.', 'mandatory'),
 ('S_EQ_STRUCTURE', [('14',122,159)], 'EQH/EQL между свингами субструктуры; разумный наклон: EQH левый выше правого, EQL левый ниже правого.', 'Не собирать EQ из двух произвольных соседних свечей; tolerance и meaningful scope пока не заданы.', 'context-dependent'),
 ('S_ADVERSE_WAIT', [('14',155,159)], 'EQH/EQL под входом: вход после снятия; текст не задаёт зеркальный short алгоритм.', 'Доказанное adverse остаётся актуальным до причинно известного sweep; после sweep заново проверить setup.', 'context-dependent'),
 ('S_POOL_SCOPE', [('14',169,198)], 'Internal между границами импульса/range своего TF; external за границами/на structural extremes; любые TF.', 'Пул хранит native TF и исходный range/impulse; не применять бессрочный union всех TF.', 'context-dependent'),
 ('S_PREVIOUS_LEVELS', [('SW12',9,10)], 'PDH/PDL/PWH/PWL/PMH/PML — дополнительные liquidity ориентиры.', 'Использовать только завершённый предыдущий календарный период; standalone запрета из них нет.', 'optional'),
 ('S_OB_FORMATION', [('SW9',2,2)], 'Свеча снимает ликвидность, затем агрессивная импульсная свеча поглощает её; BOS и HTF POI обязательны.', 'Formation требует raid, engulf/displacement, structural break и вложенный higher-TF POI.', 'mandatory'),
 ('S_OB_ZONE', [('SW9',2,3)], 'Вся поглощённая свеча вместе с тенями — OB zone.', 'Границы OB = native low/high свечи, а не только тело.', 'mandatory'),
 ('S_OB_TREND', [('SW9',3,3),('SW9',16,16)], 'OB внутри структурного импульса; работать по его тренду.', 'Направление OB согласовано с относящимся к нему structural impulse; не вводить universal D1 same direction.', 'mandatory'),
 ('S_OB_IMB', [('SW9',2,2),('SW9',6,7)], 'IMB повышает точность; начинающие игнорируют IMB/структуру/OTE; пример нижнего OB имеет приоритет из-за IMB.', 'IMB — quality/confluence; в конкретной stacked ситуации учитывать незакрытый IMB; universal MUST IMB не доказан.', 'context-dependent'),
 ('S_OB_FIRST_TEST', [('SW9',3,3)], 'Обычно первый тест; иногда повторный вход после реакции на LTF.', 'Первая mitigation не допускает автоматический lifetime ban; повтор требует новой реакции и самостоятельной проверки.', 'context-dependent'),
 ('S_OB_DIRECT_ENTRY', [('SW9',3,3)], 'Лимит на верхней LONG/нижней SHORT границе OB или внутри зоны.', 'Граничная цена определена; внутризонная цена — source-permitted без однозначного выбора.', 'context-dependent'),
 ('S_OB_DIRECT_STOP', [('SW9',3,3)], 'SL за экстремумом OB либо за тенью поглотившей свечи.', 'Две source-permitted anchors; точный tick buffer — нормализация, не SOURCE_RULE.', 'context-dependent'),
 ('S_OB_CONS_TF', [('SW9',4,6)], 'HTF OB 15M–1D «и т.д.»; переключение на меньший TF 1–15M.', 'В указанном интервале HTF M15–D1, LTF M1–M15 и LTF<HTF; D1 не доказанный абсолютный верхний потолок.', 'mandatory'),
 ('S_OB_APPROACH', [('SW9',4,4)], 'Ожидать плавный структурный подход в HTF OB.', 'Нужна причинная smooth-approach оценка; числовая граница не содержится в source.', 'mandatory'),
 ('S_OB_CONS_TRIGGER', [('SW9',4,6)], 'После реакции — LTF BOS и новая POI; лимит на новую POI.', 'Последовательность approach→reaction→BOS→new POI→последующий тест; нельзя заполнить ретроспективным тестом.', 'mandatory'),
 ('S_BREAKER_FORMATION', [('SW9',7,8)], 'OB импульсно пробит цельным движением без проторговки; новый HH/LL, слом структуры.', 'Проверить prior OB, новое structural extreme, импульсный пробой и отсутствие chopping.', 'mandatory'),
 ('S_BREAKER_IMB_CHOCH', [('19',113,116)], 'В Методичке breaker обязательно прошит IMB, затем CHOCH.', 'Это более специфичная supplemental трактовка; совместимость с primary permissive определением отмечена, не скрыта.', 'context-dependent'),
 ('S_BREAKER_STOPS', [('SW9',9,10)], 'Aggressive SL за body broken OB; conservative за raid impulse extreme.', 'Нельзя автоматически расширить все branch SL до HTF extreme; alternatives сохраняются.', 'context-dependent'),
 ('S_FVG', [('16',51,60),('19',109,112)], 'IMB — gap по теням соседних свечей, equilibrium 0.5; full fill тоже возможен.', 'Геометрия трёх completed bars; 0.5/полная mitigation имеют разные lifecycle значения, resolver нужен.', 'context-dependent'),
 ('S_SFP_FORMATION', [('16',68,83),('19',157,162)], 'External structural/range liquidity raid, reclaim body CLOSE, следующая OPEN на reclaimed стороне.', 'LONG raid LOW/reclaim above; SHORT raid HIGH/reclaim below; source опечатка «ниже» не применяется к LONG буквально.', 'mandatory'),
 ('S_SFP_TF', [('16',102,106),('19',161,162)], 'SFP на любом TF, H1+ предпочтительно; нужен liquidity context.', 'M1/M15 не запретить по причине только отсутствия H1/H4 owner; preference не hard gate.', 'mandatory'),
 ('S_SFP_REFINE', [('16',84,87)], 'После formation можно перейти на LTF, дождаться BOS и искать entry.', 'Optional refinement variant; next OPEN formation не доказательство обязательного market fill на этой цене.', 'optional'),
 ('S_SFP_STOP', [('SW12',12,13)], 'ATR расстояние отсчитывается от extreme SFP; защитный ордер не переставляется.', 'ATR stop anchor at pattern extreme; ATR estimator/buffer требуют отдельной нормализации.', 'context-dependent'),
 ('S_SFP_BODY_EXIT', [('SW12',13,13)], 'Закрыть, если свеча закрылась за SFP minimum/maximum; паттерн неактуален.', 'На выбранном pattern TF completed CLOSE за extreme → exit decision, исполнение после известного CLOSE.', 'mandatory'),
 ('S_STB_FORMATION', [('SW22',2,3)], 'STB/BTS: основной тренд, raid, полное поглощение манипуляции, BOS либо CONF.', 'Все четыре evidence нужны; STB LONG/BTS SHORT; не обычная свеча engulf без raid.', 'mandatory'),
 ('S_STB_ENTRY', [('SW22',3,4)], 'Entry upper LONG/lower SHORT edge либо 0.5 STB/BTS; mitigation/Premium Discount.', 'Две прямо разрешённые точки; ветвь выбирает explicit variant, без P&L resolver.', 'context-dependent'),
 ('S_PD', [('SW22',4,4),('19',140,155)], '0.5 — справедливая цена; покупки discount, продажи premium в соответствующем dealing range.', 'P/D привязан к документированным causal anchors; выбор range owner не задан универсально.', 'context-dependent'),
 ('S_OTE', [('19',138,156)], 'OTE 0.705–0.79 — оптимальная зона; Fibonacci дополняет стратегию, особенно OB.', 'Диапазон ретрейсмента 70.5–79% на заданном impulse; не universal requirement для SFP/Range.', 'optional'),
 ('S_RANGE_FORMATION', [('06',37,72),('19',122,128)], 'Impulse конец и correction конец задают границы; реакция на 0.5; неясный range пропустить.', 'Использовать законченные causal endpoints и midpoint reaction; force range из каждой consolidation нельзя.', 'mandatory'),
 ('S_RANGE_DEVIATION', [('06',74,94),('19',125,130)], 'Deviation снимает внешнюю ликвидность; range trade после выхода за границы.', 'Нужен известный raid границы; внутренний CHOCH сам не создаёт эту ветвь.', 'mandatory'),
 ('S_RANGE_AGGRESSIVE', [('06',111,118)], 'Aggressive entry на deviation только с POI за range; divergence доп. фактор.', 'Outside POI в стороне deviation обязателен; exact entry в POI не определён.', 'context-dependent'),
 ('S_RANGE_CONSERVATIVE', [('06',124,129),('19',129,130)], 'Ждать external POI; если нет реакции — возврат/закрепление в range и тест границы/возвратной зоны.', 'Не входить внутри до похода в POI; затем acceptance/retest или CHOCH-return-zone style, не слить два стиля в AND.', 'context-dependent'),
 ('S_RANGE_EXIT', [('06',119,121)], '80% всегда внутри у границы, 20% можно оставить на true breakout.', '80/20 — Range-specific; 20% опционально, цена/событие закрытия остатка и «у» не заданы.', 'mandatory'),
 ('S_SND_FORMATION', [('18',5,12)], 'Последнее opposite move, old liquidity raid; Demand/Supply не тестированы; Demand discount, Supply premium.', 'Все условия образования нужны; одна HTF или несколько LTF свечей, formal owner не нужен.', 'mandatory'),
 ('S_SND_ROLE', [('18',13,13)], 'Материал задаёт определение зон для совершенствования стратегии.', 'Самостоятельный полный SnD entry/SL/exit не доказан; zone используется как POI в доказанной ветви.', 'context-dependent'),
 ('S_FTA', [('SW9',11,13),('SW9',16,16)], 'Первая opposing POI/проблемная зона; тренд и контртренд; старший contextual TF.', 'Ближайшее препятствие в направлении сделки на относящемся HTF; не произвольная третья далёкая цель.', 'mandatory'),
 ('S_FTA_EXIT_OPTIONS', [('SW9',11,11),('SW9',16,16)], 'FTA допускает full либо partial close, в том числе countertrend.', 'Сохранить две component alternatives; fraction и remainder при partial не определены.', 'context-dependent'),
 ('S_PLAN', [('SW11',2,4)], 'Entry, exit и TP точно определены до открытия; SL ограничивает убыток.', 'Неполный план → UNRESOLVED; не достраивать цель из будущего.', 'mandatory'),
 ('S_STOP_FIXED', [('SW11',8,8),('SW12',13,13)], 'Первичный запрет переносить стоп, SFP явно fixed stop.', 'ORIGINAL_SOURCE_STOP_POLICY=immutable initial protective stop в primary scope; manual invalidation exit отдельный event.', 'mandatory'),
 ('S_RISK_GUIDANCE', [('SW11',3,4)], 'Account risk 0.25–2%, position size зависит от расстояния SL; fee отдельно.', 'Source risk guidance отдельно от выбора exact project 2%/portfolio6%; это не stop price ±2%.', 'context-dependent'),
 ('S_INDICATORS_SUPPORT', [('SW12',2,2),('SW12',15,15)], 'Индикаторы только подтверждают идею; не дают standalone buy/sell сигнал.', 'RSI/volume/ATR без source setup не создают branch.', 'mandatory'),
 ('S_SUPPLEMENT_BE', [('20',276,277)], 'В дополнительной обучалке BE после +10–15% на цену entry.', 'Конфликт primary fixed stop; не cost-BE и не TP1-BE; оставлен в conflict registry вне primary tree.', 'context-dependent'),
 ('S_AMD', [('19',163,170)], 'AMD: локальная transition POI либо рискованная покупка manipulation; liquidity/volume context.', 'Тематический source concept; точный entry/SL/exit отсутствует, самостоятельная ветвь UNRESOLVED.', 'context-dependent'),
 ('S_MEDIUM_PREFERENCE', [('20',213,223)], 'H1 основной анализ medium, H4+ long в смешанном supplemental материале.', 'Классификация стиля, не formal H1/H4 owner gate оригинального SMC.', 'optional'),
]

SOURCE_RULES.append((
    'S_SL_OFF_POOL', [('SW11',8,8)],
    'Не размещать стоп на уровне скопления ликвидности.',
    'После выбора initial SL проверить relation с known pool; exact beyond buffer отдельная normalization.',
    'mandatory',
))

POLICIES = [
 ('P_ANTI_SCALP','Anti-Scalp и edge_cost_ratio >= 3; fees/slippage viability','Pre-entry project admission только после source ALLOW; не universal source HTF-owner.'),
 ('P_RISK_TOTAL','Portfolio total risk 6%','Ограничение Crypto Bot после source decision; primary source задаёт per-trade guidance, не это число.'),
 ('P_DAILY_GUARD','Daily guard','Сохранённый project risk guard.'),
 ('P_CORRELATION','Correlation rules','Сохранённая project admission/risk policy.'),
 ('P_LEVERAGE','Leverage / margin limits','Операционная policy; не источник branch entry.'),
 ('P_CANONICAL_EXIT','TP 40/30/30','Сохранено отдельно для current baseline; не original source schedule.'),
 ('P_COST_BE','Cost-adjusted BE после TP1','CRYPTO_BOT_PROJECT_BE_POLICY; primary-source stop profile с ним конфликтует.'),
 ('P_EXCHANGE_SAFETY','trade_entry_allowed=false; BACKTEST/SHADOW; LIVE/private API forbidden','Непреодолимый внешний execution guard на этом этапе.'),
 ('P_ORDER_LAYER','SOURCE → PROJECT ADMISSION → RISK → MANAGEMENT → EXECUTION','Порядок, явно заданный текущим пользователем; unresolved source не допускается.'),
 ('P_RESOLVER_HIERARCHY','Explicit primary → specific → setup-specific → text/diagram → proven chronology','Метод восстановления задан пользователем; нет доказанной временной supersession смешанного DOC20.'),
 ('P_LIFETIME_DEDUP','Current one physical idea for lifetime','Сохранено только как current comparison; source repeat допускает, применение в new original не утверждено.'),
 ('P_FORMAL_OWNER','Current universal H1/H4 owner / extra higher macro object','EXTRA_RULE_NOT_IN_SOURCE; baseline сохраняется, original source tree не содержит.'),
]

NORMALIZATIONS = [
 ('N_BODY_EXIT_TF','SFP body exit candle TF','OPEN: pattern-chart TF принят как explicit diagnostic parameter; «какая-либо свеча» не задаёт complete multiple-TF arbitration.'),
 ('N_TIME','UTC, completed candles, event OPEN/CLOSE','KNOWN: input schema; no CLOSE/high/low at OPEN.'),
 ('N_KNOWN','known_at=max dependencies; swings after right CLOSE','KNOWN: causal envelope; source recognition нельзя backdate.'),
 ('N_SWING_TIES','Строгое неравенство 3-candle swings; equal highs отдельно','DEFINED by geometry; key/protected swing selection needs causal algorithm.'),
 ('N_PROTECTED','Какая структурная точка key/protected','OPEN: source examples задают смысл, не complete tie/transition algorithm.'),
 ('N_IMPULSE','Aggressive/whole impulse, no chopping','OPEN: no numerical displacement/body/ATR threshold in sources.'),
 ('N_APPROACH','Плавный структурный подход','OPEN: labelled geometric examples insufficient for unique numeric predicate.'),
 ('N_EQ_TOLERANCE','EQH/EQL reasonable tilt','OPEN: signed slope source-defined, numeric tolerance and separation not unique.'),
 ('N_ADVERSE_SCOPE','Meaningful liquidity scope/TF/context relation','OPEN: old union pool detector not uniquely source-correct; no distance cutoff supplied.'),
 ('N_ENTRY_PRICE','Цена внутри POI, target near-boundary offset','OPEN: border/0.5 alternatives exist, intrazone resolver and «у» offset absent.'),
 ('N_STOP_BUFFER','За уровнем: buffer/tick rounding','OPEN: beyond semantics known, exact buffer not uniquely specified.'),
 ('N_ATR','ATR estimator: smoothing, period, frozen value','OPEN:14 default supported; alternatives source-listed; exact estimator not prescribed.'),
 ('N_FVG_LIFECYCLE','0.5 equilibrium vs full-fill freshness/invalidation','OPEN: both concepts source-supported, permanent retirement event not universal.'),
 ('N_RANGE','Clear range, good midpoint reaction, acceptance','OPEN: no unique numeric reaction/clarity/reclaim duration.'),
 ('N_PHYSICAL_ID','Setup origin IDs, confluence/dedup identity','OPEN: audit logs/dedup are engineering; trading priority/lifetime source not supplied.'),
 ('N_EXECUTION','OHLC tie/gap fills, fees/slippage ledger','Existing engineering retained; spec does not choose new monetary model or test P&L.'),
 ('N_PARITY','Prefix/future mutation, deterministic replay, BACKTEST/SHADOW parity','DEFINED: same known inputs produce identical source decision/traces.'),
 ('N_IMMUTABILITY','Git-blob historical control + SHA256 frozen spec','DEFINED: no mutation of c2d1/audit/baseline files.'),
 ('N_UNKNOWN','Three-valued source evidence + global contract verdict','DEFINED: UNKNOWN→UNRESOLVED; source FAIL→REJECT; no fabricated ALLOW.'),
]


def citation(index, media, source, first, last):
    material = index[source]
    for number in range(first, last + 1):
        assert number in material['units'], (source, number)
    location = f'p{first}–{last}' if material['type'] == 'PDF' else f'word/document.xml:P{first:04d}–P{last:04d}'
    diagrams = ([{'original': material['original'], 'page': n, 'locator': f'PDF page {n} (text + all embedded figures)'}
                 for n in range(first, last + 1)] if material['type'] == 'PDF' else
                [row for row in media if row['source_id'] == source and first - 2 <= row['after_paragraph'] <= last + 2])
    return {'source_id': source, 'source_document': material['original'], 'source_sha256': material['sha256'],
            'text': material['text'], 'text_sha256': material['text_sha256'], 'page_or_paragraph': location,
            'first': first, 'last': last, 'literal_passage': '\n'.join(material['units'][n] for n in range(first, last + 1)),
            'diagrams': diagrams, 'diagram_scope': 'Context pages/adjacent media, not a claim that every image is an executable rule'}


def registry(index, media):
    rules = []
    normalization_for = {
        'S_STRUCTURE':['N_PROTECTED'], 'S_BOS':['N_PROTECTED'], 'S_CONF':['N_PROTECTED'],
        'S_OB_FORMATION':['N_IMPULSE'], 'S_BREAKER_FORMATION':['N_IMPULSE'],
        'S_OB_APPROACH':['N_APPROACH'], 'S_ADVERSE_BLOCK':['N_ADVERSE_SCOPE','N_EQ_TOLERANCE'],
        'S_EQ_STRUCTURE':['N_EQ_TOLERANCE'], 'S_ADVERSE_WAIT':['N_ADVERSE_SCOPE'],
        'S_OB_DIRECT_ENTRY':['N_ENTRY_PRICE'], 'S_OB_DIRECT_STOP':['N_STOP_BUFFER'],
        'S_OB_CONS_TRIGGER':['N_ENTRY_PRICE'], 'S_BREAKER_STOPS':['N_STOP_BUFFER'],
        'S_SFP_STOP':['N_ATR','N_STOP_BUFFER'], 'S_SFP_BODY_EXIT':['N_BODY_EXIT_TF'],
        'S_FTA':['N_ENTRY_PRICE'], 'S_RANGE_FORMATION':['N_RANGE'],
        'S_RANGE_CONSERVATIVE':['N_RANGE'], 'S_OB_FIRST_TEST':['N_PHYSICAL_ID'],
        'S_FVG':['N_FVG_LIFECYCLE'], 'S_OTE':['N_PROTECTED'],
    }
    conflict_for = {
        'S_STOP_FIXED':['C_STOP_BE'], 'S_SUPPLEMENT_BE':['C_STOP_BE'], 'S_OB_IMB':['C_OB_IMB'],
        'S_BREAKER_FORMATION':['C_BREAKER_IMB'], 'S_BREAKER_IMB_CHOCH':['C_BREAKER_IMB'],
        'S_SFP_FORMATION':['C_SFP_SYMMETRY','C_SFP_CANDLE_COUNT'],
        'S_RANGE_FORMATION':['C_RANGE_CLARITY'], 'S_CONF':['C_CONF_SCOPE'],
        'S_OB_CONS_TF':['C_TF_UPPER_BOUND'], 'S_OTE':['C_OTE_ANCHORS'],
        'S_FTA_EXIT_OPTIONS':['C_EXIT_UNSPECIFIED'], 'S_ADVERSE_BLOCK':['C_ADVERSE_MEANING'],
        'S_ADVERSE_WAIT':['C_ADVERSE_SHORT_SCOPE'],
    }
    for ident, refs, literal, executable, scope in SOURCE_RULES:
        rules.append({'rule_id': ident, 'category':'SOURCE_RULE',
                      'source_document':[index[ref[0]]['original'] for ref in refs],
                      'page_diagram':[citation(index, media, *ref) for ref in refs],
                      'literal_meaning':literal, 'executable_interpretation':executable,
                      'confidence':'HIGH_LITERAL; CONDITIONAL_EXECUTABILITY',
                      'conflicts':conflict_for.get(ident, []),
                      'normalization_dependencies':normalization_for.get(ident, []),
                      'known_at_semantics':'Only after all referenced formation/confirmation bars complete; next-open facts at OPEN; invalidation at native CLOSE.',
                      'applicability':scope, 'automatic_ohlc_detector_proven':False})
    for category, records in [('PROJECT_POLICY', POLICIES),('TECHNICAL_NORMALIZATION', NORMALIZATIONS)]:
        for record in records:
            ident, literal, executable = record
            rules.append({'rule_id':ident,'category':category,'source_document':[], 'page_diagram':[],
                          'authority':'User/project' if category == 'PROJECT_POLICY' else 'Explicit engineering formalization',
                          'literal_meaning':literal,'executable_interpretation':executable,
                          'confidence':'OPEN' if executable.startswith('OPEN:') else 'EXPLICIT_CLASSIFICATION',
                          'conflicts':[], 'known_at_semantics':'Before dependent decision; never future outcome/duration.',
                          'applicability':'context-dependent'})
    save(SPEC / 'original_strategy_rule_registry_v1.json', {'version':1,'audit_commit':AUDIT_COMMIT,
        'categories':['SOURCE_RULE','PROJECT_POLICY','TECHNICAL_NORMALIZATION'], 'rules':rules})
    return {rule['rule_id']:rule for rule in rules}


CONFLICTS = [
 ('C_STOP_BE','S_STOP_FIXED / S_SUPPLEMENT_BE','PRIMARY_SCOPE_RESOLVED', 'SW11 p8 и SFP SW12 p13 fixed stop; DOC20 P0277 mixed futures advice BE 10–15%. Primary explicit/setup-specific prevails for primary spec. Chronological supersession не доказана. DOC20 остаётся отдельным supplemental profile, не TP1/cost-BE.'),
 ('C_OB_IMB','S_OB_IMB','UNRESOLVED_SCOPE', 'SW9 p2 most accurate с IMB, p6–7 предупреждает игнорирование; DOC19 P0103 определяет OB перед IMB. Universal no-IMB prohibition не однозначен. Stacked-OB diagram priority конкретен, не ranking всех branches.'),
 ('C_BREAKER_IMB','S_BREAKER_FORMATION / S_BREAKER_IMB_CHOCH','UNRESOLVED_SCOPE', 'Primary цельный impulse/new HH/LL vs DOC19 mandatory IMB+CHOCH. Можно задать усиленный DOC19 profile, но не автоматически объявить его единственным original.'),
 ('C_SFP_SYMMETRY','S_SFP_FORMATION','GEOMETRY_RESOLVED', 'SW8 next OPEN «ниже» написано для short; текст/диаграммы LONG требуют reclaimed side above LOW. Это явно описанная симметрия, не alpha filter.'),
 ('C_SFP_CANDLE_COUNT','S_SFP_FORMATION','SETUP_SPECIFIC_PRIMARY_PREVAILS', 'DOC19 три/четыре свечи vs SW8 raid CLOSE + next OPEN. Нельзя требовать universal дополнительную четвёртую свечу для primary SFP; уточнение точного execution остаётся открытым.'),
 ('C_RANGE_CLARITY','S_RANGE_FORMATION','SETUP_SPECIFIC_PRIMARY_PREVAILS', 'DOC19 P0085 допускает нечеткие края как рыночное состояние; DOC06 P0069–72 рекомендует такие торговые ситуации пропускать. Range entry требует clear range; numeric clarity OPEN.'),
 ('C_CONF_SCOPE','S_CONF / S_OB_CONS_TRIGGER','SOURCE_VARIANTS_PRESERVED', 'SW5 conservative CONF, SW9 second OB method BOS+new POI. CONF более поздний style, не обязательная замена SW9 BOS во всех entries.'),
 ('C_TF_UPPER_BOUND','S_OB_CONS_TF','UNRESOLVED_OUTSIDE_EXPLICIT_RANGE', 'SW9 M15–D1 «и т.д.»: LTF1–15M определён; D1 не абсолютный запрет W1. Вне явно описанного HTF интервала вернуть UNRESOLVED, не source FAIL.'),
 ('C_OTE_ANCHORS','S_OTE','UNRESOLVED_NORMALIZATION', 'DOC19 P0153 ошибочно повторяет направление high→low для двух sides; diagram и retracement дают смысл, но causal impulse owner/tie выбор не полный.'),
 ('C_EXIT_UNSPECIFIED','S_FTA_EXIT_OPTIONS / S_RANGE_EXIT','SOURCE_VARIANTS_PRESERVED', 'Full/partial FTA прямо разрешены, partial amount/remainder нет. Range80/20 не переносится в non-Range; near-edge offset и остаток не определены.'),
 ('C_ADVERSE_MEANING','S_ADVERSE_BLOCK','UNRESOLVED_NORMALIZATION', 'SOURCE запрет против setup определён; meaningful TF/scope/tilt/distance классификация не однозначна. Старые751flags не дают право на удаление.'),
 ('C_ADVERSE_SHORT_SCOPE','S_ADVERSE_WAIT','UNRESOLVED_SCOPE', 'DOC14 P0158 «ниже вашей точки входа» не задаёт симметричный universal SHORT blocker. Зеркальная модель plausible normalization, требует маркировки/решения.'),
]

# Each resolver has topical excerpts + every page/nearby embedded diagram for those excerpts.
RESOLVERS = {
 'EXIT': {
  'rules':['S_FTA','S_FTA_EXIT_OPTIONS','S_RANGE_EXIT','S_SFP_BODY_EXIT','S_LIQUIDITY_CONTEXT','S_FLOW','S_PLAN'],
  'allowed':'Non-Range: full или partial у ближайшей contextual FTA. Range:80% inside у opposite boundary, optional20% true breakout. SFP: независимый body-invalid exit на pattern TF. Liquidity — source target при известном контексте.',
  'forbidden':'SOURCE не даёт разрешения держать SFP после известной body invalidation; не пропускать first trouble ради произвольно выбранной далёкой цели. TP40/30/30, universal3targets, проценты+3/+5/+8 не source rules.',
  'priority':'Setup-specific Range/body exit выше universal exit assumption. SW9 FTA остаётся первым препятствием; порядок tie FTA/body/stop на одной OHLC свече — TECHNICAL_NORMALIZATION.',
  'conflict':'Full/partial — разрешённые alternatives, не противоречие. Нельзя объявить один победителем. Range final20% не определён. Context target TF — относительный HTF, не только H4/D1.',
  'deterministic':'Частично: FTA meaning, Range80%, SFP body invalidation. Не полностью: FTA owner selection, offset, full/partial style, partial fractions, remainder event/price. Verdict NOT_IDENTIFIABLE.',
  'decisions':['SOURCE_PERMITTED_VARIANT_A: FULL_FTA, для non-Range; не точная готовая стратегия.', 'SOURCE_PERMITTED_VARIANT_B: PARTIAL_FTA, только с отдельно определяемыми fraction/remainder.', 'Range80/20 сохраняется branch-specific; optional20% нельзя бесконечно держать в искусственном backtest.'],
 },
 'STOP_BREAKEVEN': {
  'rules':['S_STOP_FIXED','S_SUPPLEMENT_BE','S_OB_DIRECT_STOP','S_BREAKER_STOPS','S_SFP_STOP','S_SFP_BODY_EXIT','S_RISK_GUIDANCE','S_PLAN'],
  'allowed':'Primary: protective initial SL фиксирован. OB: за OB extreme или engulf wick. Breaker: aggressive за body OB, conservative за raid impulse extreme. SFP: ATR от pattern extreme; manual native body invalidation exit. Account risk sizing не заменяет price SL.',
  'forbidden':'В primary scope перенос protective stop запрещён SW11p8/SW12p13. Нет primary TP1→BE. Stop widening до parent extreme для всех branches не доказан. Source risk2% не означает price stop2%.',
  'priority':'Explicit primary и SFP-specific выше общего mixed supplemental совета. Proven chronology недостаточна: capture12Feb2023, смешанный DOC20 содержит March posts, но нет утверждения о supersession метода.',
  'conflict':'DOC20 допускает entry-price BE after10–15%; это реально иной advice profile. Сохранён, исключён из primary tree. CRYPTO_BOT_PROJECT_BE_POLICY TP1 costBE отдельно; composition с primary fixed-stop конфликтует и требует отдельного labelled project variant.',
  'deterministic':'ORIGINAL_SOURCE_STOP_POLICY=FIXED_INITIAL_STOP в объявленном primary scope разрешается source hierarchy. Exact anchor alternatives, tick buffer, ATR estimator и stop для неполных ветвей OPEN. Это не fully identifiable Original A.',
  'decisions':['PRIMARY_NO_MOVE: поддержан двумя primary passages; перенос STOP в costBE не часть Original.', 'OB_STOP_A=OB extreme; OB_STOP_B=engulf extreme. BR_STOP_A=body aggressive; BR_STOP_B=raid extreme conservative. Обе пары source-supported.'],
 },
 'BRANCH_PRIORITY': {
  'rules':['S_OB_IMB','S_OB_DIRECT_ENTRY','S_OB_CONS_TRIGGER','S_CONF','S_SFP_REFINE','S_STB_ENTRY','S_RANGE_AGGRESSIVE','S_RANGE_CONSERVATIVE','S_AMD'],
  'allowed':'OB direct и confirmation styles; STB edge и0.5; Range aggressive/conservative; SFP optional LTF refinement. Одна ситуация может иметь несколько source аргументов.',
  'forbidden':'Источник не задаёт total ordering SFP>OB>BR>Range; нельзя считать порядок Python loops истиной или умножать все confluent tags на trades.',
  'priority':'Единственный конкретный OB priority SW9p7: нижний OB при незакрытом IMB под верхним; локальное исключение, не глобальный resolver.',
  'conflict':'Методички описывают toolbox и личный стиль (DOC03P0004/P0007), не immutable ordered strategy. SFP+OB может быть setup+trigger, не две независимые идеи.',
  'deterministic':'Нет source total ordering/physical identity. До решения выдавать набор candidates с provenance и unresolved ownership; не исполнять ни один при materially conflicting plans.',
  'decisions':['Не выбирать branch по старым67.68%, current WR, частоте или losses.', 'SOURCE_PERMITTED components не доказывают произвольную комбинацию или simultaneous portfolio trades.'],
 },
 'TF_MAPPING': {
  'rules':['S_FRACTAL','S_SFP_TF','S_SFP_REFINE','S_OB_FORMATION','S_OB_CONS_TF','S_POOL_SCOPE','S_MEDIUM_PREFERENCE','S_FTA'],
  'allowed':'W1/D1 global; H1/H4 local; M15 HTF OB/POI относительно M1/M5 и LTF refinement относительно H1/H4. SFP любой TF, H1+ preference. OB обязательный higher POI, не обязательный H1/H4 owner.',
  'forbidden':'Conservative OB triggerH1 против SW9 LTF1–15M; LTF>=HTF не lower. Нет source universal D1→H4→H1→M15 AND. Доступность данных не означает source prohibition других TF.',
  'priority':'Setup-specific conservative mapping ограничивает эту ветвь. SFP allTF explicit выше H1+ preference. Глобальная картина не unconditional directional permission для каждого countertrend setup (SW9p13/16).',
  'conflict':'SW9 «15M–1D и т.д.» не hard D1 ceiling. Fixed list/context owner selection source не задаёт. H3 example SW12 показывает отсутствие общей H1/H4-only сетки.',
  'deterministic':'Роли и conservative LTF bounds определены. Выбор обследуемых setup/context TF и conflict multiple higher contexts — TECHNICAL_NORMALIZATION/PROJECT_POLICY, unresolved, не unique original ladder.',
  'decisions':['Не блокировать lowerTF solely missing formal H1/H4 owner.', 'Outside conservative explicit HTF band >D1: UNRESOLVED allowance, а не SOURCE_REJECT.'],
 },
 'ADVERSE_LIQUIDITY': {
  'rules':['S_ADVERSE_BLOCK','S_ADVERSE_WAIT','S_EQ_STRUCTURE','S_POOL_SCOPE','S_LIQUIDITY_CONTEXT','S_PREVIOUS_LEVELS','S_FTA','S_FLOW'],
  'allowed':'Structural swings/EQ pools и internal/external liquidity своего context. EQ между substructure swings, tilted orientation source-defined. В направлении trade liquidity может быть target/fuel, opposing POI — FTA; против setup нужна задержка до sweep.',
  'forbidden':'Не превращать любой unswept LOW behind LONG или HIGH behind SHORT на всех TF в uniquely proven blocker. Не удалить751audit trades. UNKNOWN meaning != no adverse; направление топлива заранее неизвестно.',
  'priority':'DOC03P0065 категорический запрет относится к liquidity ПРОТИВ SETUP; DOC14P0113–20/155–59 различает target и ожидание. Они совместимы после contextual classification, не blanket removal.',
  'conflict':'Meaningful — operational term audit, не literal numerical source criterion. «Ниже точки входа» DOC14 не уточняет short/scope/distance. Slope reasonable и structural relevance качественны.',
  'deterministic':'Source conditional blocker определён; единственный OHLC классификатор meaningful/adverse не восстанавливается. Need explicit causal annotations/normalization, не подбор thresholds. Resolver завершён документально, semantic gap остаётся.',
  'decisions':['ADVERSE_PROVEN→WAIT_SWEEP, target/FTA не blocker; UNKNOWN→UNRESOLVED.', 'После известного sweep старого pool blocker исчезает для него, но новая liquidity/слом setup требуют повторной оценки.'],
 },
 'RE_ENTRY': {
  'rules':['S_OB_FIRST_TEST','S_OB_CONS_TRIGGER','S_SND_FORMATION','S_SFP_BODY_EXIT','S_FLOW','S_RANGE_CONSERVATIVE'],
  'allowed':'OB первый тест преимущественно; некоторые repeat после новой LTF reaction. SnD исходная zone untapped; повторный тест не удовлетворяет этому определению. New SFP после новых source facts возможен как новый setup, lifetime rule отсутствует.',
  'forbidden':'Source не разрешает автоматический repeat старого OB без реакции; не разрешает объявить tested SnD untapped. One physical idea forever не SOURCE_RULE; ratio90% не случайная квота entries.',
  'priority':'Typed-zone lifecycle выше универсального lifetime dedup. SFP native body failure прекращает актуальность старого pattern; flow destination test требует нового контекста.',
  'conflict':'90% descriptive, «в некоторых случаях» исключения качественны. Нет max retries, cooldown, count-per-origin, simultaneous ownership и portfolio reset source rule.',
  'deterministic':'First vs repeat source distinction определено; eligibility некоторых повторов, new evidence identity и count notunique. CONTRACT_UNRESOLVED для полного repeated-entry engine.',
  'decisions':['OB_FIRST_TEST_ONLY и OB_REPEAT_NEW_REACTION — source-permitted style components.', 'Baseline lifetime retention сохранён для comparison, в source contract не перенесён.'],
 },
}


def render_resolvers(rules):
    for name, item in RESOLVERS.items():
        passages = []
        figures = []
        for ident in item['rules']:
            for ref in rules[ident]['page_diagram']:
                passages.append(f"### {ident} — {ref['source_id']} {ref['page_or_paragraph']}\n\n"
                                + '\n'.join('> ' + line for line in ref['literal_passage'].splitlines()))
                for diagram in ref['diagrams']:
                    if 'page' in diagram:
                        figures.append(f"- {ref['source_id']} PDF page {diagram['page']}: `{diagram['original']}`; вся страница, включая схемы.")
                    else:
                        figures.append(f"- {diagram['source_id']} `{diagram['member']}`, SHA256 `{diagram['sha256']}`; после P{diagram['after_paragraph']:04d}, OCR `{diagram['ocr']}`.")
        body = f"# RESOLVER_{name} v1\n\nStatus: {item['deterministic']}\n\n" + '\n\n'.join([
            '## Relevant source passages\n\n' + '\n\n'.join(dict.fromkeys(passages)),
            '## Все диаграммы в relevant source scope\n\n' + '\n'.join(dict.fromkeys(figures)) + '\n\n'
            'Полный inventory всех122 unique DOCX diagrams и195 media occurrences сохранён в прежнем audit. '
            'Новый diagram_anchor_index сопоставляет inline image с deduplicated paragraph IDs. '
            'PDF locators указывают оригинальные страницы; screenshot не добавляет неизвестный numerical cutoff. '
            'До/после P locator — приблизительный textual anchor, не заявка на авторский номер рисунка.',
            '## Варианты трактовки и прямо разрешённое\n\n' + item['allowed'],
            '## Прямо запрещённое / отдельно не доказанное\n\n' + item['forbidden'],
            '## Приоритет и source hierarchy\n\n' + item['priority'],
            '## Конфликты и отсутствие единственного выбора\n\n' + item['conflict'],
            '## Deterministic rule без добавления стратегии\n\n' + item['deterministic'],
            '## Зафиксированные решения\n\n' + '\n'.join('- ' + d for d in item['decisions']),
            ('## Known_at\n\nFormation после native completed CLOSE всех dependencies; swing после правой свечи. '
            'Next open известен в OPEN без будущего high/low/close. Sweep/POI test/failure изменяют состояние только '
            'с causal event; repeated reaction не backdated. Setup plan до entry, invalidation после completed native CLOSE. '
            'Фактическое время жизни сделки и финансовый outcome не доступны resolver.'),
        ])
        save(SPEC / f'RESOLVER_{name}.md', body)
        if name == 'ADVERSE_LIQUIDITY':
            save(SPEC / 'ADVERSE_LIQUIDITY_SOURCE_RESOLVER.md', body + '''

## Ответы по meaningful adverse liquidity

| Вопрос | Source meaning / предел знания |
|---|---|
| Meaningful | Structural/EQ, visible стоповый pool, отношение к причине движения; source не даёт min size/tolerance/ATR distance. Не каждый machine pool. |
| TF | На corresponding setup/range/impulse TF; все TF source-valid, universal включение всех higher pools не следует. |
| Относительно setup | Плановое направление, context structural leg/range, уже снятая и оставшаяся liquidity; owner relation должен быть записан. |
| Adverse | Неотработанная contextual причина движения против intended setup, не просто геометрический уровень. DOC14 пример ниже entry относится к контексту примера. |
| Запрет | Proven adverse: до снятия entry запрещён. Это conditional delay, не вечная дисквалификация зоны. |
| Target/FTA | Pool в цели source delivery может быть target/fuel. Opposing POI впереди ограничивает цель как FTA; это не автоматически liquidity against setup. |
| Distance | Числовой cutoff отсутствует. Current contextual-leg containment лишь кандидат TECHNICAL_NORMALIZATION; нельзя принимать его за единственный source. |
| Structure/flow | Да, liquidity определяется внутри/вне impulse/range и актуального flow; после destination test прежнее flow не продолжается автоматически. |
| Перестаёт adverse | Proven pool sweep известен после соответствующего event; пересчитать context и новые pools. Не удалять историю регистрации. |
| Tilted EQ | EQH left higher right; EQL left lower right; substructure swings, reasonable tilt неизвестен численно. Не две arbitrary candles. |
| Known_at | max native swing/pool formation dependencies, context recognition, last completed sweep; no future label. |
| SHORT symmetry | Геометрическая mirror интерпретация возможна, но textual «ниже» не определяет её исчерпывающе; маркировать normalization, не новую цитату. |

Этот resolver завершает source analysis, но не устраняет qualitative identification gap.
Ни одна из751 отмеченных старых сделок здесь не удалена и не пересчитана.
''')
    save(SPEC / 'source_conflict_registry.json', {'conflicts':[
        {'conflict_id':ident,'rules':rule,'status':status,'resolution':meaning} for ident,rule,status,meaning in CONFLICTS],
        'hierarchy':'User-specified resolver procedure; primary specificity, not unproved chronological supersession'})


QUESTIONS = [
 {'id':'Q_EXIT','material':'entry target / full-partial / remainder',
  'question':'Для non-Range выбрать full FTA или partial FTA? Для partial и optional Range20% задайте fraction, остаточную target/exit rule и точный смысл «у границы».',
  'source_option_A':'FULL_FTA: весь объём у первой contextual FTA (SW9 p11/16).',
  'source_option_B':'PARTIAL_FTA: часть у FTA (SW9 p11/16); Range80% внутри, optional20% breakout (DOC06 P0119–21).',
  'logical_consequences':'A завершает non-Range trade на FTA; B оставляет остаток и требует отдельного complete plan. Range остаётся отдельным.',
  'recommendation':None,'why_unresolved':'Source разрешает оба, не задаёт fraction/остаточный lifecycle/near offset.'},
 {'id':'Q_STOP','material':'SL anchor / ATR / beyond buffer',
  'question':'Как выбирать source SL anchor по ветвям: OB extreme или engulf wick; Breaker body или raid extreme? Для SFP подтвердите ATR construction, период и beyond-level buffer; для STB/Range отдельный structural stop.',
  'source_option_A':'OB extreme (SW9 p3), Breaker aggressive body (p9), technical SL (SW11 p4).',
  'source_option_B':'OB engulf wick (SW9 p3), Breaker conservative raid extreme (p9); SFP ATR beyond pattern extreme (SW12 p12–13).',
  'logical_consequences':'Меняется initial invalidation price и sizing; initial protective stop primary profile остаётся фиксированным.',
  'recommendation':'Primary fixed initial stop лучше подтверждён SW11p8 и SFP-specific SW12p13; между разрешёнными anchors приоритета нет.',
  'why_unresolved':'Нет общего selector и buffers; source risk account percent не выбирает price anchor.'},
 {'id':'Q_BRANCH_ENTRY','material':'ownership / branch styles / POI entry price',
  'question':'Какой стиль entry выбрать для OB direct vs LTF-confirmed, STB edge vs0.5, Range aggressive vs return/retest? Если несколько setups описывают один эпизод — какая ветвь владеет entry и какой causal physical-id/selection rule?',
  'source_option_A':'Direct OB border/intrazone (SW9 p3), STB edge (SW22p3), Range deviation with outside POI (DOC06 P0111–18).',
  'source_option_B':'OB reaction→LTF BOS→new POI (SW9 p4–6), STB0.5 (SW22p3), Range reclaim/retest (DOC06 P0124–29 / DOC19P0130).',
  'logical_consequences':'Разные trigger timing и planned entry price; confluence не доказывает несколько независимых trades.',
  'recommendation':None,'why_unresolved':'Source перечисляет styles, но не total ordering/ownership. SFP formation nextOPEN сама не задаёт market-fill contract.'},
 {'id':'Q_TF','material':'scanned TF set / selected contextual TF / FTA owner',
  'question':'Как выбирать обследуемые TF и contextual TF/FTA owner среди нескольких валидных контекстов? Нужен explicit mapping по setup, без universal owner gate.',
  'source_option_A':'SFP/structure all TF (DOC16P0102–06, DOC19P0060/P0161); относительный HTF→LTF (DOC03P0028–30).',
  'source_option_B':'Конкретный conservative OB HTF M15–D1 и LTF M1–M15 (SW9p4–6); SFP H1+ preferred, не запрет ниже.',
  'logical_consequences':'Определяется пространство поиска и выбор context; эти source scopes совместимы, A/B не глобально взаимоисключающие ladders.',
  'recommendation':'Сохранить доказанные conservative LTF bounds и allTF SFP permission. Source не рекомендует единый selector остальных TF.',
  'why_unresolved':'Роли известны, deterministic TF selection нет; W1 conservative allowance за «и т.д.» не исчерпывающе задан.'},
 {'id':'Q_LIQUIDITY_NORMALIZATION','material':'meaningful adverse / geometric normalization',
  'question':'Нужны causal LONG/SHORT размеченные примеры или явное правило для meaningful liquidity относительно setup, её TF/scope, reasonable EQ tilt и снятия. Также задайте smooth approach/whole impulse/range clarity/ключевые structural endpoints; source числовых thresholds не даёт.',
  'source_option_A':'Liquidity против setup → запрет до sweep; EQ example под entry (DOC03P0065, DOC14P0155–59).',
  'source_option_B':'Liquidity в направлении source delivery → target/fuel; opposing POI впереди → FTA (DOC14P0113–20, SW9p11–16).',
  'logical_consequences':'A и B — разные роли, не две конкурирующие стратегии. Требуется правило классификации, а не blanket запрет всех unswept pools.',
  'recommendation':'Категорический запрет только после доказанной contextual adverse classification; unknown scope оставлять UNRESOLVED.',
  'why_unresolved':'Источник не определяет единственный classifier. Ни один numeric cutoff или old751 removal не авторизован. Числовые решения будут TECHNICAL_NORMALIZATION, не SOURCE_RULE.'},
 {'id':'Q_REENTRY','material':'typed lifecycle / repeat eligibility / duplicate identity',
  'question':'Использовать только первый OB test или разрешать некоторые повторные входы после новой LTF reaction? Для repeat нужны eligibility, new-evidence identity, simultaneous ownership и max retries/cooldown, если они нужны проекту.',
  'source_option_A':'Работа исключительно от первого OB test как основной стиль (SW9p3, «в90% случаев»).',
  'source_option_B':'Некоторые повторные OB entries после LTF reaction (SW9p3).',
  'logical_consequences':'A исключает repeat style; B требует новую reaction и полную повторную валидацию. Tested SnD не превращается в новую untapped zone.',
  'recommendation':None,'why_unresolved':'90% не квота/random gate; «некоторые» не формальный resolver. Lifetime dedup не источник.'},
]

# Tuple: ID, function in methodology, ordered source tests, complete 11-stage description.
BRANCHES = [
 ('SFP','TRADE_SETUP',[
  ('context','S_LIQUIDITY_CONTEXT','liquidity_context'),('formation','S_SFP_FORMATION','sfp_geometry'),
  ('next_open','S_SFP_FORMATION','sfp_next_open'),('tf','S_SFP_TF','sfp_tf'),
 ],[
  'Causal structural/range external liquidity; source-valid любой TF, H1+ preference.',
  'Wick raid old external level + body reclaim; не foreknowledge pattern.',
  'Следующая native OPEN на reclaimed стороне; optional LTF BOS refinement отдельно.',
  'Pattern raid zone и последующая contextual POI при refinement; точная POI price не задана.',
  'Formation сама не равна приказу market entry; LTF BOS optional разрешён.',
  'На source-confirmed POI/паттерне; exact quote/order type unresolved.',
  'OTE не обязательна; применима только если выбранный impulse/POI confluence доказан.',
  'Native pattern-TF body close за raid extreme делает pattern неактуальным.',
  'SFP ATR beyond extreme, fixed protective SL; estimator/buffer unresolved.',
  'Nearest contextual FTA/liquidity; full/partial unresolved; body failure — separate exit.',
  'После failure нельзя reuse старый SFP; новый formation — новая evidence, retry selector unresolved.',
 ]),
 ('OB_DIRECT','TRADE_SETUP',[
  ('formation','S_OB_FORMATION','ob_formation'),('higher_poi','S_OB_FORMATION','higher_poi'),
  ('trend','S_OB_TREND','trend_aligned'),('test','S_OB_FIRST_TEST','ob_test_eligible'),
 ],[
  'OB внутри structural impulse своего направления и mandatory higher-TF POI.',
  'Raid candle + aggressive engulf + BOS; весь native candle with wicks — zone.',
  'BOS; CONF более поздний optional style, не universal direct prerequisite.',
  'Untested/first-test OB; repeat requires new LTF reaction и unresolved eligibility.',
  'Последующий приход в OB; first test причинно после формирования.',
  'LONG upper boundary, SHORT lower boundary либо внутри zone (SW9p3).',
  'OB+OTE0.705–0.79 source confluence; IMB quality/stacked priority, не universal all-branch gate.',
  'Слом required structure/POI логики; exact body/wick retirement threshold OPEN.',
  'За OB extreme либо engulf wick; selector и buffer unresolved; fixed primary stop.',
  'Первый contextual opposing POI/FTA; full/partial plan unresolved.',
  'First primarily; repeat only fresh LTF reaction; no proven lifetime physical ban.',
 ]),
 ('OB_CONSERVATIVE','TRADE_SETUP',[
  ('formation','S_OB_FORMATION','ob_formation'),('higher_poi','S_OB_FORMATION','higher_poi'),
  ('trend','S_OB_TREND','trend_aligned'),('tf','S_OB_CONS_TF','conservative_tf'),
  ('approach','S_OB_APPROACH','smooth_approach'),('trigger','S_OB_CONS_TRIGGER','reaction_bos_new_poi'),
  ('test','S_OB_FIRST_TEST','ob_test_eligible'),
 ],[
  'Qualifying HTF OB M15–D1 явно, «и т.д.» не hard D1 ceiling; LTF1–15M, strictly lower.',
  'HTF raid/engulf/BOS inside higher POI and impulse; IMB/P-D/OTE relationships recorded.',
  'Smooth approach→reaction→LTF body BOS→new POI; SW5 afterCONF alternative separate.',
  'Именно новая LTF POI, после known BOS; range/delivery context recorded.',
  'Retest новой LTF POI после её known_at; нельзя retrospective touch fill.',
  'Limit at new POI; border/internal price selector не определён.',
  'OTE confluence, если related impulse anchors causal; не substitute для reaction/BOS.',
  'HTF setup or LTF trigger invalidation; source exact zone-retirement rule не complete.',
  'SW9p3 anchors применяются к OB; универсальное «conservative OB=SLзаHTFraid» не доказано: p9 относится к Breaker. Local vs parent stop OPEN.',
  'Nearest contextual FTA, не mandatory3 H4/D1 targets; full/partial unresolved.',
  'Повтор HTF OB требует новой valid reaction/LTF evidence; numerical approach/eligibility OPEN.',
 ]),
 ('BREAKER','TRADE_SETUP',[
  ('context','S_STRUCTURE','market_context'),('formation','S_BREAKER_FORMATION','breaker_formation'),
  ('flow','S_FLOW','flow_context'),('poi','S_POI','poi_reaction'),
 ],[
  'Structural direction/new HH/LL; может reversal или continuation; актуальное context flow.',
  'Prior qualifying OB цельно impulsively пробит без chopping; новая structure.',
  'BOS в primary; supplemental DOC19 требует IMB затем CHOCH — конфликт scope открыт.',
  'Broken OB zone как BR POI, body boundaries vs full candle stop distinct.',
  'Реакция/тест BR; exact timing method source examples not exhaustive.',
  'BR POI test, точная order/quote selection unresolved.',
  'Optional FVG/OTE confluence не fitted gate.',
  'Adverse structural change/BR failure; exact retired object lifecycle OPEN.',
  'Body aggressive или raid impulse extreme conservative (SW9p9–10), fixed thereafter.',
  'Nearest contextual FTA; full/partial unresolved.',
  'Typed BR repeat algorithm отсутствует, нельзя inherit lifetime policy как source.',
 ]),
 ('STB_BTS','TRADE_SETUP',[
  ('trend','S_STB_FORMATION','trend_aligned'),('formation','S_STB_FORMATION','stb_raid_absorption_structure'),
  ('flow','S_FLOW','flow_context'),('pd','S_PD','pd_context'),
 ],[
  'Основной относящийся trend/active flow, global delivery destination; TF fixed list не задан.',
  'STB LONG/BTS SHORT raid ликвидности и full absorption всей manipulation.',
  'BOS либо CONF, не оба универсально AND.',
  'Whole STB/BTS zone и0.5; source описывает mitigation.',
  'Retest entry edge или0.5; source разрешает обе точки.',
  'LONG upper/SHORT lower zone edge либо midpoint0.5.',
  'P/D0.5 manipulation/dealing range; exact range owner selection unresolved.',
  'Нарушение manipulation/structure/flow target test; exact technical zone failure OPEN.',
  'Source не задаёт unique STB stop price; general technical primary stop fixed.',
  'Flow destination/global POI + first contextual FTA; allocation unresolved.',
  'Mitigation объясняет retest, но не max entries; repeat identity OPEN.',
 ]),
 ('RANGE_AGGRESSIVE','TRADE_SETUP',[
  ('range','S_RANGE_FORMATION','clear_range'),('deviation','S_RANGE_DEVIATION','range_deviation'),
  ('poi','S_RANGE_AGGRESSIVE','outside_poi'),
 ],[
  'После impulse/correction clear range с midpoint reaction, внешний POI.',
  'Первый конец impulse и законченная correction задают edges; liquidity inside/outside.',
  'Known deviation снимает external liquidity; weakness/divergence optional.',
  'Outside POI below LONG deviation/above SHORT, не arbitrary LTF standalone signal.',
  'На deviation с outside POI; не ждать будущий возврат для заднего entry.',
  'Цена в outside POI; exact quote/order unresolved.',
  'Range midpoint/P-D/context; OTE не universal range gate.',
  'Range/POI/context failure; acceptance breakout qualitative OPEN.',
  'General technical stop beyond invalidator; branch-specific exact anchor/buffer OPEN.',
  '80% внутри у opposite boundary;20% optional breakout; offset/remainder OPEN.',
  'Новая deviation/evidence требует recheck range; unlimited recycling не source.',
 ]),
 ('RANGE_CONSERVATIVE','TRADE_SETUP',[
  ('range','S_RANGE_FORMATION','clear_range'),('deviation','S_RANGE_DEVIATION','range_deviation'),
  ('poi','S_RANGE_AGGRESSIVE','outside_poi'),('retest','S_RANGE_CONSERVATIVE','range_reclaim_retest'),
 ],[
  'Outside POI magnet; до похода в неё внутри range не открывать.',
  'Clear impulse/correction range,0.5 reaction, known deviation.',
  'Если external POI не дала reaction: return/acceptance inside range.',
  'Boundary retest после reclaim; DOC19 return-CHOCH-zone отдельный style.',
  'Causal return/acceptance затем новый retest (не все из будущих extrema).',
  'Boundary тест, точная near-offset/order unresolved.',
  'Midpoint confirms range; OTE optional confluence не prerequisite.',
  'Выход/нарушение range premise и structural context; thresholds OPEN.',
  'General fixed technical protective stop, exact anchor OPEN.',
  'Range80% внутри opposite boundary;optional20% true breakout plan OPEN.',
  'Повтор требует new evidence; count/identity unresolved.',
 ]),
 ('RANGE_RETURN_CHOCH','TRADE_SETUP',[
  ('range','S_RANGE_FORMATION','clear_range'),('deviation','S_RANGE_DEVIATION','range_deviation'),
  ('return','S_RANGE_CONSERVATIVE','return_choch_zone'),
 ],[
  'DOC19 Range context + возврат после deviation; не universal trend-only.',
  'Range edges и midpoint reaction known; deviation outside old boundary.',
  'Return-driving zone сделала CHOCH; после return новый тест зоны.',
  'Именно zone, отправившая обратно в range; не обязательно сама граница.',
  'Retest return-zone after known CHOCH.',
  'Zone entry exact quote selection OPEN.',
  'Range0.5 confirmation, FVG/OTE optional при доказанном confluence.',
  'Return premise/zone failure; source lifecycle incomplete.',
  'Fixed primary protective SL, exact anchor OPEN.',
  'Range80/20 branch-specific applies; nearest FTA mapping explicit plan needed.',
  'Fresh return evidence required; no universal lifetime ban.',
 ]),
 ('DEMAND_SUPPLY_POI','POI_COMPONENT',[
  ('formation','S_SND_FORMATION','snd_old_raid_untested'),('pd','S_SND_FORMATION','pd_context'),
 ],[
  'Native HTF one candle/LTF multi-candle context; range P/D.',
  'Последний opposite move through old liquidity raid; untested Demand/Supply.',
  'POI definition не самостоятельный trade confirmation.',
  'Demand/Supply eligible только при untapped/P-D.',
  'Trigger должен поступить из доказанной trade branch; independent trigger OPEN.',
  'Exact independent entry price не source-defined.',
  'Demand discount / Supply premium обязательны для зоны.',
  'After test исходное untapped определение больше не выполнено.',
  'Independent SnD SL отсутствует; используйте parent branch contract после его closure.',
  'Independent SnD exit отсутствует; zone может opposing FTA в другой ветви.',
  'Нельзя считать touched old zone новой untapped; новая causal formation отдельна.',
 ]),
 ('FVG_POI','POI_COMPONENT',[('formation','S_FVG','fvg_geometry')],[
  'Inefficiency внутри source context; не standalone indicator signal.',
  'Три completed candles; gap по wick соседей.',
  'Context/доказанная branch создаёт trade, gap сам не создаёт permission.',
  'Gap bounds, equilibrium0.5, full-fill distinct.',
  'Mitigation как confluence/POI; standalone trigger undefined.',
  '0.5/fullfill source concepts, price selector outside parent branch OPEN.',
  '0.5 equilibrium, OTE иной impulse retracement не одно и то же.',
  'Какой fill permanently retires gap не universal source rule.',
  'Нет независимого FVG source SL.',
  'Может быть contextual FTA; собственного exit schedule нет.',
  'Freshness/identity должна быть явно нормализована.',
 ]),
 ('OTE_CONFLUENCE','CONFLUENCE_COMPONENT',[('formation','S_OTE','ote_geometry')],[
  'Selected causal completed impulse, source POI/structure.',
  'Retracement0.705–0.79, не fitted thresholds.',
  'Fib дополняет strategy, не самостоятельный сигнал.',
  'OB+OTE confluence, anchors обязаны быть known.',
  'Parent source branch trigger; OTE alone не entry.',
  'OTE zone границы определены для заданного impulse; exact quote parent-dependent.',
  'Optimal zone именно70.5–79%.',
  'Слом selected impulse/context; exact owner selection OPEN.',
  'Независимого OTE stop нет.',
  'Независимого OTE exit schedule нет.',
  'Confluence не новый trade и не повторный entry permission.',
 ]),
 ('AMD_CONTEXT','CONTEXT_COMPONENT',[('context','S_AMD','amd_context')],[
  'Accumulation→manipulation→distribution narrative, old liquidity/volume.',
  'Manipulation/transition contextual annotation; unique algorithm absent.',
  'Local POI transition или risky manipulation style explicitly different.',
  'Local zones suggested, exact formation selector absent.',
  'Independent complete AMD trigger not supplied.',
  'Independent order/quote absent.',
  'Source says observe reclaim speed/liquidity/volume, not numeric gate.',
  'Independent complete invalidation absent.',
  'Independent complete protective stop absent.',
  'Independent complete exit absent.',
  'Independent lifecycle absent; use only as context until closed contract.',
 ]),
]

STAGES = ['CONTEXT','SETUP FORMATION','CONFIRMATION','POI','TRIGGER','ENTRY ZONE',
          'OPTIMAL ENTRY','INVALIDATION','SL','TARGET/FTA','RE-ENTRY']

BRANCH_SUPPORT = {
    'SFP':['S_SFP_FORMATION','S_SFP_TF','S_SFP_REFINE','S_SFP_STOP','S_SFP_BODY_EXIT','S_LIQUIDITY_CONTEXT'],
    'OB_DIRECT':['S_OB_FORMATION','S_OB_ZONE','S_OB_TREND','S_OB_IMB','S_OB_FIRST_TEST','S_OB_DIRECT_ENTRY','S_OB_DIRECT_STOP','S_OTE'],
    'OB_CONSERVATIVE':['S_OB_FORMATION','S_OB_ZONE','S_OB_TREND','S_OB_IMB','S_OB_FIRST_TEST','S_OB_CONS_TF','S_OB_APPROACH','S_OB_CONS_TRIGGER','S_OB_DIRECT_STOP','S_CONF','S_OTE'],
    'BREAKER':['S_BREAKER_FORMATION','S_BREAKER_IMB_CHOCH','S_BREAKER_STOPS','S_POI','S_BOS','S_FLOW'],
    'STB_BTS':['S_STB_FORMATION','S_STB_ENTRY','S_FLOW','S_PD'],
    'RANGE_AGGRESSIVE':['S_RANGE_FORMATION','S_RANGE_DEVIATION','S_RANGE_AGGRESSIVE','S_RANGE_EXIT'],
    'RANGE_CONSERVATIVE':['S_RANGE_FORMATION','S_RANGE_DEVIATION','S_RANGE_AGGRESSIVE','S_RANGE_CONSERVATIVE','S_RANGE_EXIT'],
    'RANGE_RETURN_CHOCH':['S_RANGE_FORMATION','S_RANGE_DEVIATION','S_RANGE_CONSERVATIVE','S_RANGE_EXIT'],
    'DEMAND_SUPPLY_POI':['S_SND_FORMATION','S_SND_ROLE','S_PD'],
    'FVG_POI':['S_FVG','S_INDICATORS_SUPPORT'],
    'OTE_CONFLUENCE':['S_OTE','S_PD'],
    'AMD_CONTEXT':['S_AMD','S_LIQUIDITY_CONTEXT'],
}

RULE_STAGE_ROLES = {
    'S_STRUCTURE':['CONTEXT'], 'S_LIQUIDITY_CONTEXT':['CONTEXT','TARGET/FTA'],
    'S_FLOW':['CONTEXT','INVALIDATION','TARGET/FTA','RE-ENTRY'],
    'S_SFP_FORMATION':['SETUP FORMATION','CONFIRMATION'], 'S_SFP_TF':['CONTEXT'],
    'S_SFP_REFINE':['TRIGGER','ENTRY ZONE'], 'S_SFP_STOP':['SL'], 'S_SFP_BODY_EXIT':['INVALIDATION'],
    'S_OB_FORMATION':['CONTEXT','SETUP FORMATION','CONFIRMATION'], 'S_OB_ZONE':['POI'],
    'S_OB_TREND':['CONTEXT'], 'S_OB_IMB':['POI','OPTIMAL ENTRY'], 'S_OB_FIRST_TEST':['POI','RE-ENTRY'],
    'S_OB_DIRECT_ENTRY':['TRIGGER','ENTRY ZONE'], 'S_OB_DIRECT_STOP':['SL'],
    'S_OB_CONS_TF':['CONTEXT'], 'S_OB_APPROACH':['TRIGGER'],
    'S_OB_CONS_TRIGGER':['CONFIRMATION','POI','TRIGGER','ENTRY ZONE'], 'S_CONF':['CONFIRMATION'],
    'S_OTE':['OPTIMAL ENTRY'], 'S_BREAKER_FORMATION':['SETUP FORMATION','CONFIRMATION','POI'],
    'S_BREAKER_IMB_CHOCH':['SETUP FORMATION','CONFIRMATION'], 'S_BREAKER_STOPS':['SL'],
    'S_POI':['POI','TRIGGER'], 'S_BOS':['CONFIRMATION','INVALIDATION'],
    'S_STB_FORMATION':['CONTEXT','SETUP FORMATION','CONFIRMATION'],
    'S_STB_ENTRY':['TRIGGER','ENTRY ZONE','OPTIMAL ENTRY'], 'S_PD':['OPTIMAL ENTRY'],
    'S_RANGE_FORMATION':['CONTEXT','SETUP FORMATION','CONFIRMATION'],
    'S_RANGE_DEVIATION':['SETUP FORMATION','CONFIRMATION'],
    'S_RANGE_AGGRESSIVE':['POI','TRIGGER','ENTRY ZONE'],
    'S_RANGE_CONSERVATIVE':['POI','CONFIRMATION','TRIGGER','ENTRY ZONE'],
    'S_RANGE_EXIT':['TARGET/FTA'], 'S_SND_FORMATION':['CONTEXT','SETUP FORMATION','POI','OPTIMAL ENTRY'],
    'S_SND_ROLE':['TRIGGER','ENTRY ZONE'], 'S_FVG':['SETUP FORMATION','POI','OPTIMAL ENTRY'],
    'S_INDICATORS_SUPPORT':['CONTEXT','TRIGGER'], 'S_AMD':['CONTEXT','SETUP FORMATION','TRIGGER'],
    'S_ADVERSE_BLOCK':['CONTEXT','TRIGGER'], 'S_PLAN':['ENTRY ZONE','INVALIDATION','SL','TARGET/FTA'],
    'S_STOP_FIXED':['SL'], 'S_SL_OFF_POOL':['SL'], 'S_FTA':['TARGET/FTA'], 'S_FTA_EXIT_OPTIONS':['TARGET/FTA'],
}


def build_contracts(rules):
    result = []
    for ident, role, steps, descriptions in BRANCHES:
        assert len(descriptions) == len(STAGES)
        refs = list(dict.fromkeys(BRANCH_SUPPORT[ident] + [rule for _,rule,_ in steps]
                                 + ['S_STRUCTURE','S_LIQUIDITY_CONTEXT','S_ADVERSE_BLOCK','S_PLAN','S_STOP_FIXED','S_SL_OFF_POOL']))
        if ident.startswith('RANGE'):
            refs.append('S_RANGE_EXIT')
        else:
            refs.extend(['S_FTA','S_FTA_EXIT_OPTIONS'])
        contract = {'branch_id':ident,'role':role,'status':'PARTIAL_SOURCE_CONTRACT_NOT_IDENTIFIABLE',
                    'source_rules':refs,'tests':[{'name':name,'rule_id':rule,'predicate':predicate}
                                               for name,rule,predicate in steps],
                    'stages':dict(zip(STAGES,descriptions,strict=True)),
                    'stage_source_support':{stage:[{'rule_id':rid,'citations':[
                        {'source_id':ref['source_id'],'page_or_paragraph':ref['page_or_paragraph'],
                         'source_document':ref['source_document'],'source_sha256':ref['source_sha256']}
                        for ref in rules[rid]['page_diagram']]}
                        for rid in refs if stage in RULE_STAGE_ROLES[rid]] for stage in STAGES},
                    'stage_support_scope':'Branch contextual support list; exact unsupplied entry/SL/lifecycle is OPEN, not a new literal rule',
                    'material_gaps':[q['id'] for q in QUESTIONS],
                    'automatic_market_recognition':'NOT_IMPLEMENTED; source facts/qualitative annotations only'}
        result.append(contract)
        citations = '\n'.join('- ' + rid + ': ' + '; '.join(ref['source_id'] + ' ' + ref['page_or_paragraph']
                             for ref in rules[rid]['page_diagram']) for rid in refs)
        save(SPEC / 'branch_contracts' / f'{ident}.md',f'# {ident}\n\nRole: `{role}`. Status: `{contract["status"]}`.\n\n'
             + '\n\n'.join(f'## {stage}\n\n{description}\n\nSource support: '
                              + (', '.join(ref['rule_id'] for ref in contract['stage_source_support'][stage])
                                 or 'OPEN: unique source algorithm absent; no fabricated rule.')
                              for stage,description in zip(STAGES,descriptions,strict=True))
             + '\n\n## Source rule citations\n\n' + citations
             + '\n\nKnown_at: все formation/confirmation/POI dependencies после native CLOSE; entry не раньше causal trigger. '
               'POI-component и confluence-component не получают самостоятельный ALLOW. Все материальные questions '
               'в UNRESOLVED_QUESTIONS.md; отсутствие цены/SL/target не заполняется current engine.\n')
    save(SPEC / 'branch_contracts.json', {'branches':result})
    return result


def build_tree(rules, branches):
    nodes = []
    paths = {}
    for branch in branches:
        ident = branch['branch_id']
        steps = [('context','S_STRUCTURE','market_context')] + [
            (p['name'],p['rule_id'],p['predicate']) for p in branch['tests']]
        if branch['role']=='TRADE_SETUP':
            steps += [('adverse','S_ADVERSE_BLOCK','no_adverse_proven'),('plan','S_PLAN','source_plan_complete'),
                      ('stop','S_STOP_FIXED','fixed_stop_plan')]
            exit_rule = 'S_RANGE_EXIT' if ident.startswith('RANGE') else 'S_FTA'
            steps += [('sl_liquidity','S_SL_OFF_POOL','sl_off_liquidity'),
                      ('target',exit_rule,'range_exit_plan' if ident.startswith('RANGE') else 'fta_plan')]
        ids = [ident + ':' + str(n) for n in range(len(steps))]
        paths[ident] = ids[0]
        for i,(stage,rid,predicate) in enumerate(steps):
            nodes.append({'node_id':ids[i],'branch_id':ident,'stage':stage,'rule_id':rid,
                          'source_citation':rules[rid]['page_diagram'],
                          'known_at':rules[rid]['known_at_semantics'],'predicate':predicate,
                          'PASS':ids[i+1] if i+1<len(ids) else 'SOURCE_CONDITIONS_PASS',
                          'FAIL':'SOURCE_REJECT','UNKNOWN':'SOURCE_UNRESOLVED'})
    tree = {'version':1,'verdict':'NOT_IDENTIFIABLE','scope':'Primary methodology with explicitly unresolved source styles',
            'START':'Select a source branch; no source total branch priority is asserted',
            'branch_start_nodes':paths,'branch_roles':{b['branch_id']:b['role'] for b in branches},'nodes':nodes,
            'SOURCE_CONDITIONS_PASS':'CONTRACT_UNRESOLVED until all material contract gaps resolved and new spec frozen',
            'ALLOW_enabled':False,'global_material_questions':[q['id'] for q in QUESTIONS],
            'excluded_rule_categories':['PROJECT_POLICY','TECHNICAL_NORMALIZATION'],
            'engineering_envelope':'Known_at/OPEN schema applied outside source decision nodes',
            'financial_outcome_access':False,'production_integration':False}
    save(SPEC / 'ORIGINAL_STRATEGY_DECISION_TREE_v1.json',tree)
    lines = ['# ORIGINAL_STRATEGY_DECISION_TREE_v1', '',
             ('**NOT_IDENTIFIABLE**. Исполнимо как проверка переданных source evidence. '
             'Автоматическое распознавание качественных source concepts из OHLC не реализовано.'), '',
             ('START → выбранная source branch → контекст → formation/confirmation → POI/entry '
             '→ invalidation/SL/target plan → lifecycle. Source priority между branches неизвестен.'), '',
             ('Каждый SOURCE node: PASS → следующий; FAIL → SOURCE_REJECT; UNKNOWN → SOURCE_UNRESOLVED. '
             'Завершение пути означает только SOURCE_CONDITIONS_PASS. Глобальный verdict блокирует ALLOW '
             'и PROJECT_ADMISSION до закрытия material gaps и следующего freeze.'), '',
             ('После source path: global contract gap gate entry/invalidation/lifecycle → CONTRACT_UNRESOLVED. '
             'Он не маскируется под дополнительный SOURCE_RULE node. Engineering envelope отдельно проверяет timestamps/completed-only. Даже semantic PASS '
             'не создаёт fills, portfolio или financial results.'), '']
    for branch in branches:
        ident = branch['branch_id']
        lines += [f'## {ident} ({branch["role"]})','',
                  '| Node | Stage | Rule / citation | Known_at | PASS → | FAIL / UNKNOWN |',
                  '|---|---|---|---|---|---|']
        for node in nodes:
            if node['branch_id'] != ident:
                continue
            citations = '; '.join(r['source_id']+' '+r['page_or_paragraph'] for r in node['source_citation'])
            lines.append(f'| {node["node_id"]} | {node["stage"]} | {node["rule_id"]}: {citations} '
                         f'| dependencies ≤ decision; OPEN только open | {node["PASS"]} | REJECT / UNRESOLVED |')
        lines.append('')
    save(SPEC / 'ORIGINAL_STRATEGY_DECISION_TREE_v1.md','\n'.join(lines))


def tf_matrix():
    rows = []
    for tf, minutes in [('M1',1),('M3',3),('M5',5),('M15',15),('M30',30),('H1',60),
                        ('H3',180),('H4',240),('D1',1440),('W1',10080),('MN1','calendar')]:
        allowed = 'Fractal structure, liquidity, SFP; OB с relative higher POI; contextual POI'
        preferred = 'Нет доказанного обязательного предпочтения'
        prohibited = 'Нет universal prohibition; indicator-only entry недопустим'
        if isinstance(minutes,int) and minutes<=15:
            allowed += '; conservative OB refinement если строго ниже HTF'
        elif isinstance(minutes,int) and minutes<=1440:
            prohibited += '; conservative OB refinement вне M1–M15'
        else:
            prohibited += '; conservative OB refinement вне M1–M15'
        if minutes == 15:
            allowed += '; conservative HTF OB относительно M1–M5; M15 LTF относительно H1/H4'
        elif isinstance(minutes,int) and 15<minutes<=1440:
            allowed += '; conservative HTF OB в явно указанном SW9 диапазоне'
        if tf in ('H1','H4'):
            preferred = 'Локальная structure; SFP H1+ preference'
        elif tf in ('D1','W1'):
            preferred = 'Глобальная картина; SFP H1+ preference'
        elif tf == 'H3':
            preferred = 'Source SFP ATR example; H1+ preference'
        elif tf == 'MN1':
            preferred = 'Liquidity context; universal entry priority не задан'
        certainty = 'HIGH role permissions; deterministic TF selector OPEN'
        if tf in ('W1','MN1'):
            certainty += '; conservative HTF >D1 не запрещён однозначно, «и т.д.» scope OPEN'
        rows.append({'TF':tf,'allowed_roles':allowed,'preferred_roles':preferred,
                     'prohibited_roles':prohibited,'source_evidence':'DOC03P0028–30/P0052; DOC11P0113–15; '
                     'DOC16P0102–06; DOC14P0197–98; SW9p2/p4–6; SW12p12–13 exampleH3',
                     'certainty':certainty})
    write_csv(SPEC / 'TF_ROLE_MATRIX.csv',rows)


def variants(rules):
    entries = [
        ('FTA','SOURCE_PERMITTED_VARIANT_A','FULL_FTA','S_FTA_EXIT_OPTIONS','Non-Range contextual FTA','Target owner/quote unresolved'),
        ('FTA','SOURCE_PERMITTED_VARIANT_B','PARTIAL_FTA','S_FTA_EXIT_OPTIONS','Non-Range contextual FTA','Fraction and remainder unresolved'),
        ('OB_ENTRY','A','BORDER_OR_INSIDE','S_OB_DIRECT_ENTRY','OB direct','Inside quote/selection unresolved'),
        ('OB_ENTRY','B','LTF_REACTION_BOS_POI','S_OB_CONS_TRIGGER','Conservative qualifying OB','Smooth approach/POI quote unresolved'),
        ('OB_STOP','A','OB_EXTREME','S_OB_DIRECT_STOP','OB direct','Beyond buffer unresolved'),
        ('OB_STOP','B','ENGULF_WICK','S_OB_DIRECT_STOP','OB direct','Beyond buffer unresolved'),
        ('BREAKER_STOP','A','BODY_AGGRESSIVE','S_BREAKER_STOPS','Breaker','Beyond buffer unresolved'),
        ('BREAKER_STOP','B','RAID_EXTREME_CONSERVATIVE','S_BREAKER_STOPS','Breaker','Beyond buffer unresolved'),
        ('STB_ENTRY','A','EDGE','S_STB_ENTRY','STB/BTS','Owner/P-D/stop selection unresolved'),
        ('STB_ENTRY','B','MIDPOINT','S_STB_ENTRY','STB/BTS','Owner/P-D/stop selection unresolved'),
        ('RANGE_ENTRY','A','DEVIATION_OUTSIDE_POI','S_RANGE_AGGRESSIVE','Clear Range','Exact quote/SL unresolved'),
        ('RANGE_ENTRY','B','RECLAIM_RETEST','S_RANGE_CONSERVATIVE','Clear Range','Acceptance/retest normalization unresolved'),
        ('OB_REPEAT','A','FIRST_TEST_STYLE','S_OB_FIRST_TEST','OB','First-test predominantly, not random90% quota'),
        ('OB_REPEAT','B','REPEAT_NEW_REACTION','S_OB_FIRST_TEST','OB','Which exceptions qualify unresolved'),
    ]
    save(SPEC / 'source_permitted_variants.json', {'type':'COMPONENT_VARIANTS_NOT_COMPLETE_STRATEGIES',
        'selected_winner':None,'outcomes_used':False,'entries':[
            {'resolver':group,'variant_id':variant,'name':name,'rule_id':rid,
             'source_citation':rules[rid]['page_diagram'],'applicability':scope,'material_ambiguity':True,
             'remaining':gap,'financial_run_allowed':False} for group,variant,name,rid,scope,gap in entries]})


def overview(rules, branches):
    for category, filename in [('PROJECT_POLICY','project_policy_registry.json'),
                               ('TECHNICAL_NORMALIZATION','technical_normalization_registry.json')]:
        save(SPEC / filename,{'category':category,'rules':[r for r in rules.values() if r['category']==category]})
    save(SPEC / 'UNRESOLVED_QUESTIONS.json',{'verdict':'NOT_IDENTIFIABLE','questions':QUESTIONS,
                                          'no_profitability_comparison':True})
    qtext = ['# Минимальный пакет решений пользователя','',
             ('Шесть групп материальных решений. Это вопросы о логике, не запрос approval backtest. '
             'A/B ниже — source scopes/варианты, а не обещание двух готовых стратегий. '
             'Где source не даёт алгоритма, требуются annotations или явно маркированная normalization.'),'']
    for q in QUESTIONS:
        qtext += [f'## {q["id"]}','',q['question'],'',f'- Source option A: {q["source_option_A"]}',
                  f'- Source option B: {q["source_option_B"]}',f'- Логические последствия: {q["logical_consequences"]}',
                  f'- Рекомендация: {q["recommendation"] or "Нет source-приоритета между разрешёнными стилями."}',
                  f'- Gap: {q["why_unresolved"]}','']
    save(SPEC / 'UNRESOLVED_QUESTIONS.md','\n'.join(qtext))
    save(SPEC / 'IDENTIFIABILITY_VERDICT.json',{
        'verdict':'NOT_IDENTIFIABLE','fully_defined_original_A':False,'executable_market_strategy':False,
        'executable_partial_evidence_checker':True,'new_financial_backtest_started':False,
        'resolved_by_sources':['Conservative LTF M1–M15 and lower than HTF','SFP anyTF, H1+ only preference',
                               'Primary fixed stop profile over mixed supplemental BE; conflict preserved',
                               'OB wick zone, full vs partial FTA both permitted',
                               'Range80/20 is setup-specific; fixed40/30/30 not original',
                               'Typed first/repeat OB distinction; no source lifetime ban',
                               'EQ uses substructure swings and signed tilt; no numerical tolerance'],
        'material_question_ids':[q['id'] for q in QUESTIONS],
        'audit_conclusions_changed':False,'trade_entry_allowed':False})
    source_table = '\n'.join(f'| {r["rule_id"]} | {r["applicability"]} | {r["literal_meaning"]} |'
                             for r in rules.values() if r['category']=='SOURCE_RULE')
    branch_table = '\n'.join(f'| [{b["branch_id"]}](branch_contracts/{b["branch_id"]}.md) | {b["role"]} | '
                             f'{b["status"]} |' for b in branches)
    body = f'''# ORIGINAL_STRATEGY_SPEC_v1

**Verdict: NOT_IDENTIFIABLE.** Из13 уникальных source documents восстановлен
максимально faithful частичный контракт; единственная полностью определённая
исполняемая original trading strategy из этих материалов не идентифицируется.
Нельзя утверждать готовность Original A/B или запускать её financial backtest.
Offline evidence checker исполним, но не распознаёт все qualitative concepts
из OHLC и не создаёт торговых приказов. Spec v1 замораживает также его holes.

Основание: пользовательский запрос, `ORIGINAL_STRATEGY_SPEC_PROTOCOL.md`,
audit `{AUDIT_COMMIT}`. Baseline `{BASELINE}` и все результаты audit неизменны.
Текущий MediumTermEngine используется только как ранее сохранённое comparison;
не импортируется builder/interpreter. Новые trades, P&L и financial comparisons
не создавались. Старые67.6768% не являются целевым результатом или source tree.

## Evidence и source hierarchy

8 DOCX +5 настоящих PDF; literal passages, SHA256 и page/paragraph locators
сохранены в registry. Изображения122unique/195media occurrences и54PDFpages
сохраняются в source originals и прежних visual review receipts; новый anchor
index привязывает inline diagrams к textual context. Все13text были полностью
прочитаны в предыдущем audit; этот этап повторно сверяет relevant passages и
diagrams, не выдаёт OCR за отдельный original source. SW7 доступен только как
.lnk; OTE цитируется по DOC19, не по непрочитанному SW7.

Resolver order задан пользователем: explicit primary rule → более конкретное
→ setup-specific → text/diagram consistency → доказанная chronology.
Capture dates и March посты DOC20 не доказывают, что он отменяет primary SMC.
В DOC03P0004/P0007 автор описывает toolbox/менторство для развития личного
стиля; complete branch-priority/price/lifecycle таблицы в наборе нет.
Все шесть resolver-документов сохраняют варианты, conflicts и предел знания.

## Три слоя

SOURCE_RULE имеет original document, literal excerpt, page/diagram, applicability,
known_at. PROJECT_POLICY имеет authority User/project; TECHNICAL_NORMALIZATION
имеет явную числовую/алгоритмическую трактовку или статус OPEN. B/C не SOURCE.
Confidence HIGH_LITERAL не утверждает уникальность executable normalization.
Фиксированные технические правила времени/immutability обеспечивают correctness,
а не создают alpha. Качественный source факт требует provenance annotation;
отсутствие annotation даёт UNKNOWN, не PASS.

## TF_ROLE_MATRIX

[CSV](TF_ROLE_MATRIX.csv): W1/D1 global, H1/H4 local; M15 relative HTF POI/OB и
relative LTF refinement. SFP allTF; H1+ preference. Conservative OB LTF1–15M,
строго ниже HTF; M15–D1 явно перечислены как HTF, «и т.д.» оставляет allowance
выше D1 не исчерпывающе определённым. Нельзя считать D1 абсолютным source ceiling.
Нет universal H1/H4 owner, обязательной четырёхTF conjunction или universal D1
directional gate. Source context/relative higher POI там, где его требует setup,
не исчезает при удалении лишнего owner gate. Unavailable dataset TF — не source prohibition.

## Контракты branches и место концептов

| Branch | Role | Contract status |
|---|---|---|
{branch_table}

Каждый contract задаёт CONTEXT→FORMATION→CONFIRMATION→POI→TRIGGER→ENTRY ZONE
→OPTIMAL ENTRY→INVALIDATION→SL→TARGET/FTA→RE-ENTRY с citations и holes.
Market Structure определяет structural context/BOS/CONF; Order Flow добавляет
raid/liquidity и destination. Liquidity даёт setup cause/target/adverse role.
SFP external raid/reclaim — formation, а не обещание future reversal.
BOS/CHOCH меняет structure; CONF — update новой structure, не синоним BOS.
OB/FVG/SnD/Breaker/STB дают typed POI; FVG и OTE не отдельный trade сигнал.
OTE0.705–0.79 — optional confluence selected causal impulse; P/D — midpoint
относящегося range, обязательный для SnD definition. Range имеет собственные
deviation/reclaim/80–20 styles. FTA ограничивает ближайшее препятствие.

## Conservative OB: точные source границы

SW9p2–6: raid, engulf, BOS, higher POI, structural impulse direction;
zone вся свеча с wicks, первый тест преимущественно. IMB strongest-quality
и stacked-OB priority конкретны; universal no-IMB prohibition не доказан.
HTF15M–1D examples → LTF1–15M → smooth structural approach → reaction → BOS
→new POI →limit. Smooth не заменяется fitted ATR/candle-count filter.
SW5 послеCONF — отдельный более поздний conservative style, не extra AND
в каждой SW9 entry. OTE/P-D confluence учитывается с явными impulse anchors;
universal OTE для всех branches source не требует. SL choices SW9p3 относятся
к OB; p9 aggressive/conservative stops относятся к Breaker и не доказывают
универсальный HTF raid stop для conservative OB. Entry quote, approach metric,
local-vs-parent stop и invalidation lifecycle остаются OPEN.

## Adverse liquidity

[Полный resolver](ADVERSE_LIQUIDITY_SOURCE_RESOLVER.md) отвечает на meaningful,
TF, setup relation, distance, flow, target vs blocker, sweep и tilted EQ.
Source conditional запрет установлен; uniquely correct автоматический classifier
не установлен. Proven ADVERSE→WAIT_SWEEP, TARGET/FTA не automatic blocker,
UNKNOWN→UNRESOLVED. После sweep переоценить актуальный setup, не выдать
автоматический entry. Старые751flags/446LOSS не удалены; точные audit conclusions
и3680ENGINE_EXTRA_REJECTION сохранены без нового исхода или reinterpretation.

## STOP и EXIT

ORIGINAL_SOURCE_STOP_POLICY=FIXED_INITIAL_PROTECTIVE_STOP в primary scope.
SW11p8 + SFP-specific SW12p13 выше mixed DOC20BE10–15%; conflict не скрыт.
Source manual SFP body-invalid exit отделён от protective stop move.
CRYPTO_BOT_PROJECT_BE_POLICY=costBE after TP1 только отдельный project overlay.
Его применение меняет source stop management, поэтому требует маркировки
project-managed variant; оно не доказывает Original fidelity.
SL anchors: OB extreme/engulf; Breaker body/raid; SFP ATR-from-extreme.
Buffer/ATR-estimator/branch-specific отсутствующие stops нельзя брать молча
из current engine. Source0.25–2% account risk не stop-distance процент.

Non-Range FTA допускает full/partial; эти две alternatives записаны как
SOURCE_PERMITTED_VARIANT_A/B. Они **компоненты**, не две готовые стратегии:
partial fraction/remainder и contextual target owner/quote не определены.
Range80/20 отдельно;20% optional, остаточный выход OPEN. Canonical40/30/30
не original. Ни одно source-permitted сочетание не выбиралось по outcomes.

## Decision tree и causal semantics

[JSON](ORIGINAL_STRATEGY_DECISION_TREE_v1.json) и [human tree](ORIGINAL_STRATEGY_DECISION_TREE_v1.md).
Каждый node имеет source rule/citation/known_at/PASS/FAIL/UNKNOWN/next.
No fitted ML thresholds. PASS по evidence не равен executable ALLOW.
Unresolved material contract блокирует admission глобально. Synthetic LONG/SHORT
показывают удовлетворение/нарушение literal constraints; они не закрывают
source-normalization gaps и не создают trades.
Engineering envelope: completed candles, OPEN-only открытие, known_at не позже
decision time; swings только после right CLOSE; prefix/future mutation/replay
и BACKTEST/SHADOW parity на offline checker. Future holding-time/P&L поля не
используются. Source detection causality из предыдущего audit остаётся отдельным
сохранённым evidence; synthetic QA не выдаётся за новый real-history detector QA.

## Project overlays и composition

SOURCE STRATEGY → PROJECT ADMISSION → RISK ENGINE → POSITION MANAGEMENT → EXECUTION.
Anti-Scalp, edge_cost_ratio3, cost viability, total risk6%, daily/correlation,
leverage,40/30/30,costBE,exchange safety находятся в project_policy_registry.
Они сохранены и не интегрированы в source decision. PROJECT_ADMISSION может
получить только source ALLOW; сейчас ALLOW disabled. Production baseline сохраняется
целиком; новый project wiring не реализуется до identifiable/frozen version.
trade_entry_allowed=false; BACKTEST/SHADOW only; LIVE/private API forbidden.

## Material unresolved и freeze

[Шесть конкретных групп вопросов](UNRESOLVED_QUESTIONS.md): exit/remainder,
stop anchor/normalization, branch/entry selection, TF/context selection,
meaningful liquidity и qualitative geometry, re-entry identity/eligibility.
Source разрешённые варианты сохраняются; решения пользователя будут
PROJECT_POLICY/TECHNICAL_NORMALIZATION, если не предоставлена новая source evidence.
После ответа нужен новый version/freeze; старый spec с holes не переписывается.

Freeze SHA256 включает spec, citations, resolver decisions, builder/checker/tests
и source dependencies. Audit c2d1 tree проверяется побайтно. Profitability
backtest на этом этапе не запускался и при verdict NOT_IDENTIFIABLE заблокирован.

## SOURCE_RULE summary

| Rule | Applicability | Literal meaning |
|---|---|---|
{source_table}
'''
    save(SPEC / 'ORIGINAL_STRATEGY_SPEC_v1.md',body)


def main():
    if (SPEC / 'freeze_manifest.json').exists():
        raise SystemExit('Spec is frozen; use verify_original_strategy_spec_v1.py --resume-existing')
    index, media = source_index()
    rules = registry(index,media)
    render_resolvers(rules)
    branches = build_contracts(rules)
    build_tree(rules,branches)
    tf_matrix()
    variants(rules)
    overview(rules,branches)
    print('SPEC_BUILT',len(rules),'rules',len(branches),'contracts; NOT_IDENTIFIABLE; no financial run')


if __name__ == '__main__':
    main()
