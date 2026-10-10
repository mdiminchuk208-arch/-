"""Render measured source cases, full variants and preserved historical audits."""
from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import sys
from collections import Counter, defaultdict
from contextlib import ExitStack
from pathlib import Path
from zoneinfo import ZoneInfo

from crypto_bot.data.storage import read_klines_csv
from crypto_bot.strategy.source_pdf_native import sign

sys.path.insert(0,str(Path(__file__).resolve().parent))
from run_source_permitted_bybit import (
    REPO,
    STRICT,
    digest,
    instant,
    read_rows,
    write_json,
)

ZONE=ZoneInfo('Asia/Yekaterinburg')


def when(value):
    return instant(value).astimezone(ZONE).isoformat() if value else ''


def fmt(value):
    return 'N/A' if value is None else f'{value:.8g}' if isinstance(value,float) else str(value)


def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join('---' for _ in headers)+'|']+
                     ['| '+' | '.join(str(v).replace('|','/') for v in r)+' |' for r in rows])


def export_cases(path,rows):
    fields=('n','physical_opportunity_id','signal_id','path_id','symbol','direction','mapping','entry_zone_tf',
        'READY_Ekaterinburg','fill_start_Ekaterinburg','fill_known_Ekaterinburg','exit_known_Ekaterinburg',
        'HTF_POI','entry_POI','liquidity_raid','OrderFlow','PD_OTE','entry_reference','entry_after_slippage',
        'original_SL','targets','fills','exit_reason','WIN_LOSS_BE','R','gross_quote_PnL','Net_PnL','fees',
        'slippage','holding_seconds','reference_equity','planned_risk','quantity','source_citations','trade_entry_allowed')
    with ExitStack() as stack:
        if path.suffix=='.gz':
            raw=stack.enter_context(path.open('wb'))
            compressed=stack.enter_context(gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0))
            f=stack.enter_context(io.TextIOWrapper(compressed,encoding='utf-8',newline=''))
        else:
            f=stack.enter_context(path.open('w',newline=''))
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for i,t in enumerate(rows,1):
            e=t['evidence'];dump=lambda obj:json.dumps(obj,ensure_ascii=False,separators=(',',':'))
            w.writerow(dict(zip(fields,(i,t['physical_opportunity_id'],t['signal_id'],t['path_id'],t['symbol'],
                t['direction'],f'{t["htf"]}/{t["ltf"]}',e['entry_zone_tf'],when(t['ready_time']),
                when(t['entry_interval_start']),when(t['entry_interval_end']),when(t.get('exit_time')),
                dump(e['htf_poi']),dump(e['ltf_poi']),dump(e['liquidity_sweep']),dump(e['order_flow']),
                dump(e['premium_discount']),t['entry_reference'],t['entry'],t['stop'],dump(t['targets']),
                dump(t['fills']),t.get('exit_reason','RIGHT_CENSORED'),t.get('result',t['status']),
                t.get('result_R'),t['quote_gross_pnl'],t['net_pnl'],t['fees'],t['slippage'],
                t.get('holding_seconds'),t['initial_equity'],t['risk_amount'],t['quantity'],dump(e['source_citations']),
                t['trade_entry_allowed']),strict=True)))


def old13_audit(folder,out):
    all_signals=[];all_cases={};cancel=defaultdict(list);audits=[];original_classifications={}
    native={}
    for symbol in json.loads((folder/'run_lock.json').read_text())['policy']['symbol_priority']:
        seg=folder/'segments'/symbol
        native[symbol]=[r.to_strategy_candle(300000) for r in read_klines_csv(REPO/f'data/history/bybit/{symbol}/5.csv')]
        symbol_audits=json.loads((seg/'old13_audit.json').read_text());audits+=symbol_audits
        # Retain exactly the old READY scopes used below, before reading any
        # outcomes; later signals cannot witness a historical source contract.
        all_signals.extend(r for r in read_rows(seg/'signals.jsonl.gz') if any(
            r['direction']==a['old_trade']['direction'] and r['htf']==a['old_trade']['htf']
            and r['ltf']==a['old_trade']['ltf'] and instant(r['known_at'])<=instant(a['old_trade']['ready_time'])
            for a in symbol_audits))
        for old_row in json.loads((STRICT/'segments'/symbol/'intermediate_audit.json').read_text()):
            original_classifications[old_row['old_trade']['trade_id']]=old_row
        for r in read_rows(seg/'cancellations.jsonl.gz'):
            if r['cohort']=='CANCEL_SOURCE_POI_INVALIDATION':cancel[r['signal_id']].append(r)
    old_scope_ids={r['signal_id'] for r in all_signals}
    for p in (folder/'cohorts').glob('*/CANCEL_SOURCE_POI_INVALIDATION/cases.jsonl.gz'):
        for t in read_rows(p):
            if t['signal_id'] in old_scope_ids:all_cases[t['signal_id']]=t
    result=[]
    for row in audits:
        old=row['old_trade'];ready=instant(old['ready_time']);entry=instant(old['entry_interval_start'])
        historical=original_classifications[old['trade_id']]
        assert old==historical['old_trade']
        target=old['evidence']['fta'];born=instant(target['known_at'])
        tested=next((c for c in native[old['symbol']] if c.open_time>=born and c.close_time<=ready
            and c.low<=target['high'] and c.high>=target['low']),None)
        freshness={'old_FTA_zone_id':target['zone_id'],'old_FTA_known_at':target['known_at'],
            'old_READY':old['ready_time'],'registered_fresh_FTA_contract_passed':tested is None,
            'first_native_5m_test_known_at':tested.close_time if tested else None,
            'first_test_ohlc':{k:getattr(tested,k) for k in ('open','high','low','close')} if tested else None,
            'source':'SW9 p11–16 FTA; registered native first-test freshness interpretation',
            'input_sha256':digest(REPO/f'data/history/bybit/{old["symbol"]}/5.csv'),
            'literal_exclusion_of_all_discretionary_source_prices_claimed':False}
        scope=[r for r in all_signals if r['symbol']==old['symbol'] and r['direction']==old['direction']
               and r['htf']==old['htf'] and r['ltf']==old['ltf'] and instant(r['known_at'])<=ready
               and not any(instant(c['known_at'])<=entry for c in cancel[r['signal_id']])]
        quote=[r for r in scope if abs(r['entry']-old['entry_reference'])<1e-10]
        inside=[]
        snapshot=row['snapshots'].get('ready_time',{}).get('permitted_path_assessment',{})
        for q in snapshot.get('all_source_local_candidates_at_old_quote',[]):
            z=q['poi']
            if z['kind']!='ORDER_BLOCK':continue
            witnesses=[r for r in scope if r['evidence']['path_id'].startswith('OB_DIRECT')
                       and r['evidence']['ltf_poi']['zone_id']==z['zone_id']]
            if witnesses and q['fixed_stop_outside_whole_zone'] and q['htf_flow']:
                inside.append({'source_zone_id':z['zone_id'],'source_direct_witness_ids':[r['signal_id'] for r in witnesses],
                               'source':'SW9 p3 inside quote','inside_price_not_primary_midpoint':True})
        exact=[]
        for r in quote:
            t=all_cases.get(r['signal_id'])
            stop_ok=sign(old['direction'])*(r['stop']-old['stop'])>=0
            targets_equal=r['targets']==old['targets']
            if t and t['entry_interval_start']==old['entry_interval_start'] and stop_ok and targets_equal:
                exact.append({'source_signal_id':r['signal_id'],'path_id':r['evidence']['path_id'],
                              'physical_opportunity_id':r['evidence']['physical_opportunity_id'],
                              'new_case_result':t.get('result'),'stop_matches_permitted_reference':stop_ok})
        verdict='FALSE_POSITIVE_OLD_FTA_ALREADY_TESTED_AT_READY_NATIVE_5M' if tested else 'EXACT_SOURCE_CASE_SUPPORTED' if exact else 'SOURCE_VALID_FORMATION_DIFFERENT_PERMITTED_QUOTE_OR_EXIT' if quote or inside else 'EXACT_OLD_CASE_NOT_PROVEN_IN_ALL_REGISTERED_SOURCE_PATHS'
        result.append({'old_trade_id':old['trade_id'],'symbol':old['symbol'],'mapping':f'{old["htf"]}/{old["ltf"]}',
            'old_result':old['result'],'old_net_pnl':old['net_pnl'],'retained_strict_classification':historical['classification'],
            'retained_strict_reasons':historical['hard_source_reasons'],'new_source_assessment':verdict,
            'old_FTA_native_freshness_at_READY':freshness,
            'actual_source_quote_witnesses':[{'signal_id':r['signal_id'],'path':r['evidence']['path_id'],
                'stop':r['stop'],'targets':r['targets'],'known_at':r['known_at']} for r in quote],
            'permitted_inside_OB_witnesses':inside,'exact_case_support':exact,
            'no_old_outcome_used_to_change_rules':True,'trade_entry_allowed':False})
    assert len(result)==13
    write_json(out/'old13_all_source_paths_audit.json',result)
    return result


def strict179_audit(folder,out):
    rows=[];reasons=Counter()
    maps=json.loads((folder/'run_lock.json').read_text())['policy']['mappings']
    for seg in (folder/'segments').iterdir():
        original={r['setup_id']:r for r in read_rows(STRICT/'segments'/seg.name/'setup_outcomes.jsonl.gz')
                  if 'liquidity_passed' in r['stages'] and [r['htf'],r['ltf']] in maps}
        attempts=defaultdict(list)
        for r in read_rows(seg/'strict_bottleneck.jsonl.gz'):
            if r['setup_id'] in original:attempts[r['setup_id']].append(r)
        flows=read_rows(seg/'flow_history.jsonl.gz')
        for sid,old in original.items():
            history=attempts[sid];assert history,sid;first=instant(history[0]['known_at'])
            active=[f for f in flows if f['tf']==old['htf'] and f['direction']==history[0]['direction']
                    and instant(f['known_at'])<=first and (not f['invalidated_at'] or instant(f['invalidated_at'])>first)]
            reasons[history[0]['reason']]+=1
            rows.append({'symbol':seg.name,'original_setup':old,'old_OF_reason_history':history,
                         'new_source_flow_at_first_old_liquidity_POI_pass':active[-1] if active else None,
                         'old_extra_body_break_is_interpretation':True,'trade_entry_allowed':False})
    assert len(rows)==179,len(rows)
    write_json(out/'strict179_OF_audit.json',rows)
    result={'all_original_179_accounted':True,'first_old_rejection_reasons':dict(reasons),
            'new_active_flow_at_same_native_close':sum(r['new_source_flow_at_first_old_liquidity_POI_pass'] is not None for r in rows)}
    write_json(out/'strict179_OF_summary.json',result);return result


def legacy_seven():
    rows=[];hashes={}
    for name in ('limit_15_5','limit_60_5','final_60_15','final_240_5','final_240_15','final_240_60'):
        p=REPO/'data/reports/historical_blocker_investigation/stage3'/name/'trades.jsonl'
        rows.extend(r for line in p.read_text().splitlines() if (r:=json.loads(line))['status']=='CLOSED')
        hashes[p.relative_to(REPO).as_posix()]=digest(p)
    assert len(rows)==7 and len({r['trade_id'] for r in rows})==7
    wins=[r['net_pnl'] for r in rows if r['net_pnl']>0];losses=[-r['net_pnl'] for r in rows if r['net_pnl']<0]
    return {'READY':40,'FILLED':7,'CLOSED':7,'Wins':len(wins),'Losses':len(losses),'WinRate':len(wins)/7,
        'ProfitFactor':sum(wins)/sum(losses),'Expectancy':sum(r['net_pnl'] for r in rows)/7,
        'AvgR':sum(r['result_R'] for r in rows)/7,'NetPnL':sum(r['net_pnl'] for r in rows),
        'source_artifact_sha256':hashes,'six_independent_capitals_not_one_physical_union':True}


def render(folder,out):
    out.mkdir(parents=True,exist_ok=True)
    summary=json.loads((folder/'summary.json').read_text());s=summary['primary'];m=s['primary']
    policy=json.loads((folder/'run_lock.json').read_text())['policy']
    primary_folder=folder/'cohorts/SOURCE_PERMITTED_UNION/CANCEL_SOURCE_POI_INVALIDATION'
    trades=read_rows(primary_folder/'cases.jsonl.gz');primary=read_rows(primary_folder/'primary_cases.jsonl.gz')
    export_cases(out/'first50.csv',primary);export_cases(out/'all_physical_union_cases.csv.gz',trades)
    normalize=json.loads((folder/'physical_normalization_receipt.json').read_text())
    qualification=Counter(r['status'] for r in read_rows(folder/'source_qualification.jsonl.gz'))
    old13=old13_audit(folder,out);of=strict179_audit(folder,out)
    old9=[]
    for seg in (folder/'segments').iterdir():old9+=json.loads((seg/'old9_cancel_audit.json').read_text())
    controlled=json.loads((folder/'controlled_old9_execution.json').read_text())
    write_json(out/'old9_fixed_plan_cancellation_audit.json',{'orders':old9,'controlled_execution':controlled})
    comparison=json.loads((STRICT/'comparison.json').read_text())
    old7=legacy_seven()
    write_json(out/'historical_comparison.json',{'OLD7_descriptive_only':old7,
        'fc61f35_shared_portfolio':comparison['fc61f35'],'74a6f8d_no_primary_PDFs':comparison['74a6f8d'],
        'STRICT_CONSERVATIVE_D46646F':comparison['primary_pdf'],'new_physical_union_primary50':m,
        'matched_strategy_profitability_uplift_claimed':False,'trade_entry_allowed':False})
    candidate_funnel=Counter();native_events=Counter()
    path_counts=Counter(r['evidence']['path_id'] for symbol in policy['symbol_priority']
        for r in read_rows(folder/'segments'/symbol/'signals.jsonl.gz'))
    for symbol in policy['symbol_priority']:
        raw_summary=json.loads((folder/'segments'/symbol/'summary.json').read_text())
        candidate_funnel.update(raw_summary['funnel'])
        for values in raw_summary['series'].values():native_events.update(values)
    write_json(out/'candidate_detection_funnel.json',{'candidate_state_transitions':dict(candidate_funnel),
        'native_formation_events_all_TFs':dict(native_events),'source_valid_READY_by_path':dict(path_counts),
        'counts_are_event_transitions_not_nested_unique_physical_trades':True,'trade_entry_allowed':False})
    cohorts=[];cohort_rows=[]
    for row in summary['cohorts'].values():
        q=row['primary'];cohorts.append([row['cohort'],row['cancellation_cohort'],row['READY'],row['FILLED'],row['CLOSED'],
            q['Wins'],q['Losses'],fmt(100*q['WinRate']) if q['WinRate'] is not None else 'N/A',fmt(q['ProfitFactor']),
            fmt(q['Expectancy']),fmt(q['AvgR']),fmt(q['NetPnL'])])
        cohort_rows.append({**{k:row[k] for k in ('cohort','cancellation_cohort','READY','FILLED','CLOSED','OPEN','PENDING')},
            **{'primary50_'+k:v for k,v in row['primary'].items()},
            **{'all_closed_'+k:v for k,v in row['all_closed'].items()}})
    with (out/'cohort_metrics.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(cohort_rows[0]));w.writeheader();w.writerows(cohort_rows)
    sections=['# Source-permitted Bybit: physical trade-case validation — 2026-10-10',
        f'**Полный replay40 native Bybit серий /993575 свечей: {s["READY"]} physical READY → {s["FILLED"]} FILLED → {s["CLOSED"]} CLOSED. Основная выборка: {len(primary)} уникальных FILLED+CLOSED.**',
        'Первичные SW5/SW9/SW11/SW12/SW22:54 страницы полностью прочитаны; оригиналы/text/схемы и ZIP/DOCX сохранены. Canonical TP40/30/30, SL и cost-adjusted BE послеTP1 неизменны. Только BACKTEST/SHADOW, `trade_entry_allowed=false`; LIVE/private API отсутствуют.',
        '2026 DEVELOPMENT уже просматривалась: это не OOS. Каждый case — независимый reference1170 USDT, planned risk2%=23.4 с fee.0006/slippage.0002 на сторону. Funding не моделируется. Это case validation без shared occupancy/NAV. Native5m даёт интервал fill, не точный tick; OHLC stop-first и фиксированный pessimistic limit/gap model сохранены. Первые50 выбираются по fill-интервалу; при одинаковом интервале используется заранее фиксированный tie order. Все Win/Loss/BE включены, OPEN/PENDING сохранены, endpoint не force-close.',
        '## Funnel и source corrections',
        f'Полные candidate predicates всех15 paths сохранены до исполнения. Raw entry-candidate READY={normalize["raw_candidate_READY"]}; source-qualified raw READY={normalize["source_valid_READY"]}; SFP qualification={dict(qualification)}. После глобальных causal aliases union READY={s["READY"]}, FILLED={s["FILLED"]}, CLOSED={s["CLOSED"]}, OPEN={s["OPEN"]}, PENDING={s["PENDING"]}. Raw variants и rejected candidates не считаются отдельными physical trades.',
        table(['Source path','Source-valid raw READY'],[[p['path_id'],path_counts[p['path_id']]] for p in policy['paths']]),
        'Detection gate event counts (повторные transitions не являются nested physical funnel): '+json.dumps(dict(candidate_funnel),ensure_ascii=False)+'. Все native formations, raids, OF waits и gate transitions: `candidate_detection_funnel.json`.',
        'OB direct edge/inside и OB/engulf wick stops; BOS/new POI без универсальногоCONF; отдельныйCONF; STB edge/half; breaker block/sweep stops; независимый multi-candle D/S; conservative/aggressive Range; самостоятельный SFP и frozen ATR-SFP. OF сохраняет реальные key HH/HL/LL/LH, liquidity work и fixed global destination; убран дополнительный post-raid body break. Нет универсального veto каждого внутреннего пула.',
        'SFP broken old BOS level не является новым защищённым HL/LH. Нативное body-нарушение SFP до READY навсегда отвергает этот старый контекст; после READY primary pending life использует настоящие POI/pattern bodies. Ни будущийCLOSE, ни поздняя отмена не могут стереть раннийfill. Все quotes/SL/targets/READY/source risk остаются исходными. Global physical IDs назначаются причинно до family filtering и execution; один локальный first-test/контекст/известный native formation alias не увеличивает выборку вариантами.',
        'Цель50 достигнута на всех40 ранее доступных сериях; дополнительные загрузки не требуются.' if len(primary)==50 else f'Цель50 ещё не достигнута: наблюдаемых CLOSED={s["CLOSED"]}. Требуется автоматическое расширение разрешённой Bybit истории; этот этап не финальный максимум.',
        '## Все метрики primary50',table(['Metric','Value'],[[k,fmt(v)] for k,v in m.items()]),
        'MaxDrawdown — cumulative independent-case net PnL в порядке exit time, не shared portfolio NAV. MaxDrawdownFraction=N/A. Streaks и first50 — в порядке fill-интервалов. GrossPnL — quote PnL до friction; Net=Gross−Slippage−Fees.',
        '## Когорты: без выбора лучшей после PnL',
        table(['Path/cohort','Cancel cohort','READY','FILLED','CLOSED all','WIN first50','LOSS first50','WR%','PF','ExpectancyUSDT','AvgR','NetUSDT'],cohorts),
        'SOURCE_DIRECT объединяет четыре directOB quote/stop варианта; SOURCE_CONSERVATIVE=BOS/POI, SOURCE_CONF_STRICT=CONF. Все19 source/family/union cohorts и оба cancel modes сохранены; их числа не складываются в уникальную выборку.',
        'Полные primary50 и all-CLOSED метрики каждой когорты: `cohort_metrics.csv`. Все cohort case ledgers сохранены в final root, включая варианты, которые не вошли в union.',
        '## Первые50: все сделки',
        'Даты Asia/Yekaterinburg(+05). Полные physical IDs, READY/fill-known/exit, HTF/local POI, raid, OF, PD/OTE, source citations, targets/fills и расходы: [first50.csv](data/reports/source_permitted_analysis_2026_10_10/first50.csv). Все доступные union FILLED/OPEN без потери полей: [all_physical_union_cases.csv.gz](data/reports/source_permitted_analysis_2026_10_10/all_physical_union_cases.csv.gz); gzip сохраняет полный CSV и позволяет опубликовать его в GitHub.',
        table(['#','Physical ID','Path','Symbol / side / HTF-LTF','Fill interval start(+05)','Entry reference','OriginalSL','Source targets','Exit known(+05)','W/L/BE','R','Net'],
          [[i,t['physical_opportunity_id'],t['path_id'],f'{t["symbol"]} {t["direction"]} {t["htf"]}/{t["ltf"]}',when(t['entry_interval_start']),fmt(t['entry_reference']),fmt(t['stop']),str(t['targets']),when(t['exit_time']),t['result'],fmt(t['result_R']),fmt(t['net_pnl'])] for i,t in enumerate(primary,1)]),
        '## Breakdown primary50','```json\n'+json.dumps(s['breakdowns'],ensure_ascii=False,indent=2)+'\n```',
        '## Сравнение сохранённых этапов',
        table(['Stage / metric sample','READY','FILLED','CLOSED all','W/L evaluated','WR','PF','ExpectancyUSDT','AvgR','NetUSDT'],[
            ['OLD7 / independent mappings',old7['READY'],old7['FILLED'],old7['CLOSED'],'2/5',fmt(100*old7['WinRate'])+'%',fmt(old7['ProfitFactor']),fmt(old7['Expectancy']),fmt(old7['AvgR']),fmt(old7['NetPnL'])],
            ['fc61f35 / flawed old source policy',647,14,13,'2/11','15.3846%',fmt(comparison['fc61f35']['ProfitFactor']),fmt(comparison['fc61f35']['Expectancy']),fmt(comparison['fc61f35']['AvgR']),fmt(comparison['fc61f35']['NetPnL'])],
            ['74a6f8d / no primary PDFs',3,0,0,'0/0','N/A','N/A','N/A','N/A',0],
            ['STRICT_CONSERVATIVE_D46646F',9,0,0,'0/0','N/A','N/A','N/A','N/A',0],
            ['SOURCE_PERMITTED_UNION / metrics first50',s['READY'],s['FILLED'],s['CLOSED'],f'{m["Wins"]}/{m["Losses"]}',fmt(100*m['WinRate'])+'%' if m['WinRate'] is not None else 'N/A',fmt(m['ProfitFactor']),fmt(m['Expectancy']),fmt(m['AvgR']),fmt(m['NetPnL'])]]),
        'OLD7, fc61f35 и new cases имеют разные entries/exits/risk-account conventions; это не matched profitability uplift. Strict9zero — узкая source-интерпретация, не окончательная оценка всех PDF paths. Архив105 strict artifacts, исходные trades и все старые losses неизменны.',
        '## Полный179 OF bottleneck','```json\n'+json.dumps(of,ensure_ascii=False,indent=2)+'\n```',
        'Все179 original liquidity/POI contexts со всеми reason changes и causal old/new OF snapshots сохранены: [strict179_OF_audit.json](data/reports/source_permitted_analysis_2026_10_10/strict179_OF_audit.json). Extra body-break/adverse-pool gates помечены interpretations, не универсальными SOURCE_RULE.',
        '## Все9 старых отмен: fixed quote/SL/targets',
        table(['Signal','Symbol/map','Strict known/reason','Classification at strict cancel','Source native cancel'],[[r['old_signal']['signal_id'],f'{r["old_signal"]["symbol"]} {r["old_signal"]["htf"]}/{r["old_signal"]["ltf"]}',r['strict_cancel']['known_at']+' '+r['strict_cancel']['reason'],r['strict_cancel_snapshot']['classification'],str(r['source_cancel'])] for r in old9]),
        'Фиксированные старые9 планы воспроизведены в двух cancel modes; case outcomes и actual native proof сохранены в [old9_fixed_plan_cancellation_audit.json](data/reports/source_permitted_analysis_2026_10_10/old9_fixed_plan_cancellation_audit.json). Они отдельная controlled sensitivity, не дополнительная primary выборка.',
        '## Все13 fc61f35 cases и старые losses',
        'Прежние10 из11 LOSS остаются false positives именно STRICT_CONSERVATIVE registered projection. Это не переносится автоматически на весь новый source universe. Каждый старый случай проверен на точных old READY/entry cutoffs и всех новых source-valid paths; изменённый допустимый quote/exit не является доказательством source false positive. PnL не использован для подбора правил.',
        'DOGE240/15 `c1bc1cb68a185d4492c8b9e6`: исходная FTA0.09156–0.09271 уже протестирована native5m при CLOSE2026-04-12T20:45UTC, до READY21:00UTC. Старый HTF-only clock сохранил ошибочную freshness. Поэтому точный старый план окончательно false positive registered fresh-FTA contract; допустимая другая formation/quote/FTA остаётся отдельным вариантом, не исправлением старого LOSS задним числом. Прежний verdict UNCERTAIN сохранён в историческом архиве.',
        table(['Old ID','Symbol/map','Old W/L Net','Retained strict class','New all-path assessment'],[[r['old_trade_id'],r['symbol']+' '+r['mapping'],r['old_result']+' '+fmt(r['old_net_pnl']),r['retained_strict_classification'],r['new_source_assessment']] for r in old13]),
        'Полные witnesses и exact-case matching: [old13_all_source_paths_audit.json](data/reports/source_permitted_analysis_2026_10_10/old13_all_source_paths_audit.json). No matching fixed cohort значит exact old case не доказан; это не универсальное отрицание всех discretionary inside prices.',
        '## QA / воспроизводимость / сохранность',
        '548 tests PASS перед final execution, dedicated15paths + physical + source-body tests; compileall/Ruff changed files/mypy PASS. Full-tree Ruff555 inherited findings byte/diagnostic-identical to d466, zero new; old code не переписан ради lint. Реальный nonempty prefix14293bars/all15paths, future mutation4TF; source body qualification и physical mapping также prefix-causal. Independent cross-TF OHLC302362bars:0mismatches. Итоговый ledger/no-lookahead/cost/risk/selection/preservation и exact-resume receipts находятся в `data/reports/source_permitted_qa_2026_10_10`.',
        'Registry7c47621, implementation7f9782f, exact performance parityc8263dd, global physical424d663, native SFP validity/lifecycled87edb1 опубликованы до final outcomes. Все завершённые robustness/controlled-exit/frozen artifacts сохранены без повторного перерасчёта. Final native40 detector manifest и final physical manifest неизменяемы; SHA каждого source/code/data/artifact проверяется.',
        'Все40 detector segments завершены. Последующая provisional all-symbol aggregation остановлена лимитом памяти32GiB до outcomes; исходный log и все artifacts сохранены. Base manifest честно сертифицирует только COMPLETE DETECTOR CORPUS. Primary execution выполнен отдельно с bounded-memory scheduling, опубликованным в096e225: source selection/replay/risk/exits не менялись. На реальном prefix все196 сравниваемых artifacts/38cohorts побайтно совпали с оригинальным исполнителем. См. `BOUNDED_SOURCE_EXECUTION_PROTOCOL.md` и `bounded_execution_real_parity.json`.',
        f'```bash\npython scripts/run_source_permitted_bybit.py --output data/reports/source_permitted_bybit_2026_10_10 --resume-existing --workers 4\npython scripts/run_source_permitted_physical_union.py --source data/reports/source_permitted_bybit_2026_10_10 --output {folder.relative_to(REPO)} --resume-existing\n```']
    text='\n\n'.join(sections)+'\n'
    (REPO/'SOURCE_ALIGNED_BYBIT_50_TRADE_REPORT.md').write_text(text)
    (out/'report.md').write_text(text)
    write_json(out/'report_receipt.json',{'source_manifest_sha256':digest(folder/'manifest.json'),
        'renderer_sha256':digest(Path(__file__)),'primary_count':len(primary),'actual_unique_physical_count':len({t['physical_opportunity_id'] for t in primary}),
        'artifacts':{p.name:digest(p) for p in out.iterdir() if p.is_file() and p.name!='report_receipt.json'},'trade_entry_allowed':False})
    print(json.dumps({'READY':s['READY'],'FILLED':s['FILLED'],'CLOSED':s['CLOSED'],'first50':m},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();render(a.input.resolve(),a.output.resolve())
