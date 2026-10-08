"""Publish complete, unselected research tables; never pool independent capital."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime
import gzip
import json
from pathlib import Path
from random import Random

from crypto_bot.data.models import MarketCandle
from crypto_bot.strategy.portfolio_statistics import trade_statistics
from import_public_research_data import aggregate
from research_exit_management import EXIT_VARIANTS
from research_inventory import complete_study
from research_support import check_baseline, read_compressed, regime
from research_variants import STRUCTURAL_VARIANTS
from run_historical_portfolio import canonical

MAPPINGS={'bybit':[(60,15),(240,15),(240,60)],
          'binance':[(15,5),(60,5),(60,15),(240,5),(240,15),(240,60)]}
PERIODS=('REFERENCE','VALIDATION','HOLDOUT')
ROOT=Path(__file__).resolve().parents[1]


def json_rows(path):
    with (gzip.open(path,'rt') if path.suffix=='.gz' else path.open()) as handle:
        return [json.loads(line) for line in handle]


def write_csv(path,rows):
    keys=list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=keys);writer.writeheader()
        for row in rows:
            writer.writerow({k:canonical(v) if isinstance(v,(dict,list,tuple)) else v for k,v in row.items()})


def flat_performance(receipt):
    p=receipt['performance']
    return {k:v for k,v in p.items() if not isinstance(v,(dict,list))}


def daily_history(cohort,symbol):
    rows=read_compressed(ROOT/f'data/history/public_research/{cohort}_mirror/{symbol}/240.csv.gz',240)
    candles=[MarketCandle(cohort.upper(),symbol,'240',int(c.open_time.timestamp()*1000),c.open,c.high,c.low,c.close) for c in rows]
    days,_=aggregate(candles,240,1440)
    return [c.to_strategy_candle(86400000) for c in days]


def record_inventory(report,partial):
    missing=[];inventory=[]
    for cohort,mappings in MAPPINGS.items():
        split=json.loads((report/f'{cohort}_temporal_split.json').read_text())
        for htf,ltf in mappings:
            folder=report/'canonical'/f'{cohort}_{htf}_{ltf}'
            ok,receipt=complete_study(folder,split)
            inventory.append(dict(study=folder.name,complete=ok,evidence=receipt))
            if not ok:missing.append(folder.name)
    split=json.loads((report/'binance_temporal_split.json').read_text())
    for variant in STRUCTURAL_VARIANTS:
        folder=report/'structural_sensitivity'/variant
        ok,receipt=complete_study(folder,split,['VALIDATION'])
        inventory.append(dict(study='structural_'+variant,complete=ok,evidence=receipt))
        if not ok:missing.append('structural_'+variant)
    for cohort,mappings in MAPPINGS.items():
        for htf,ltf in mappings:
            mapping=f'{cohort}_{htf}_{ltf}'
            scenarios=report/'execution_sensitivity'/mapping
            canonical_study=report/'canonical'/mapping
            expected={p.parent.name for p in canonical_study.glob('*/summary.json') if json.loads(p.read_text())['window']['name']!='REFERENCE'}
            available=set()
            if (scenarios/'results.json').exists():
                available={(r['scenario'],f"{r['window']}_SEGMENT_{r['segment']:02}") for r in json.loads((scenarios/'results.json').read_text())}
            required={(s,case) for s in ('BASE_VERIFY','COST_150','COST_200','RISK_021','RISK_025','REENTRY_SCORE_80') for case in expected}
            ok=bool(expected) and available==required
            if not ok:missing.append('execution_'+mapping)
            inventory.append(dict(study='execution_'+mapping,complete=ok,expected_cases=len(required),saved_cases=len(available)))
    exit_sources={f'development_{h}_{l}':None for h,l in MAPPINGS['binance']}
    exit_sources.update({f'{c}_{h}_{l}':report/'canonical'/f'{c}_{h}_{l}' for c,ms in MAPPINGS.items() for h,l in ms})
    exit_sources['exit_untouched_btc_2019']=report/'exit_reserve/canonical_btc_2019'
    for study,source in exit_sources.items():
        folder=report/'exit_management'/study
        cases=[p.parent for p in folder.glob('*/results.json')]
        expected={p.parent.name for p in source.glob('*/summary.json') if json.loads(p.read_text())['window']['name'] in (*PERIODS,'EXIT_HOLDOUT')} if source else {p.name for p in cases}
        ok=bool(cases) and {p.name for p in cases}==expected
        for case in cases:
            ok=ok and {r['variant'] for r in json.loads((case/'results.json').read_text())}==set(EXIT_VARIANTS)
            ok=ok and (case/'paired_actual_entries.json').exists() and (case/'post_be_follow.json').exists() and (case/'exit_real_causality.json').exists()
        if not ok:missing.append('exit_'+study)
        inventory.append(dict(study='exit_'+study,complete=ok,expected_cases=len(expected),saved_cases=len(cases)))
    (report/'research_completion_inventory.json').write_text(canonical(dict(complete=not missing,missing=missing,studies=inventory))+'\n')
    if missing and not partial:
        raise ValueError('Research is not complete: '+', '.join(missing))
    return not missing


def summarize(partial=False):
    report=ROOT/'data/reports/robustness_research';check_baseline(ROOT)
    complete=record_inventory(report,partial)
    windows=[];frequency=[];performance_groups=[];sample_groups=defaultdict(dict);daily={}
    for cohort,mappings in MAPPINGS.items():
        symbols=json.loads((report/f'{cohort}_temporal_split.json').read_text())['symbols']
        for htf,ltf in mappings:
            folder=report/'canonical'/f'{cohort}_{htf}_{ltf}'
            if not (folder/'results.json').exists():continue
            for row in json.loads((folder/'results.json').read_text()):
                context=dict(cohort=cohort,htf=htf,ltf=ltf,window=row['window'],segment=row['segment'],status=row['status'])
                if row['status']!='REPLAY_COMPLETE':
                    windows.append(context);continue
                case=folder/f"{row['window']}_SEGMENT_{row['segment']:02}"
                source=json.loads((case/'summary.json').read_text())
                windows.append(dict(context,start=source['start'],end=source['end'],**flat_performance(source)))
                ready=json_rows(case/'ready_outcomes.jsonl')
                for dimension,values in dict(symbol=symbols,direction=['LONG','SHORT'],ready_regime=['BULL','BEAR','SIDEWAYS','UNKNOWN'],ready_volatility_bucket=['LOW','MEDIUM','HIGH','UNKNOWN']).items():
                    for value in values:
                        subset=[r for r in ready if r[dimension]==value];filled=sum(r['filled'] for r in subset)
                        frequency.append(dict(context,dimension=dimension,value=value,ready=len(subset),filled=filled,
                            fill_rate=filled/len(subset) if subset else None,
                            first_outcomes=dict(Counter(r['entry_outcome'] for r in subset))))
                trades=json_rows(case/'trades.jsonl')
                labels={}
                for t in trades:
                    key=(cohort,t['symbol'])
                    if key not in daily:daily[key]=daily_history(*key)
                    labels[t['trade_id']]=regime(daily[key],datetime.fromisoformat(t['entry_interval_start']))
                    if row['window'] in PERIODS and t['status']=='CLOSED':
                        identity=(t['signal_id'],t['entry_interval_start'])
                        sample_groups[(cohort,htf,ltf)][identity]=t
                dimensions={'direction':['LONG','SHORT'],'symbol':symbols,'entry_regime':['BULL','BEAR','SIDEWAYS','UNKNOWN'],
                            'entry_volatility':['LOW','MEDIUM','HIGH','UNKNOWN']}
                for dimension,values in dimensions.items():
                    for value in values:
                        subset=[t for t in trades if (t[dimension] if dimension in ('direction','symbol') else labels[t['trade_id']][0 if dimension=='entry_regime' else 1])==value]
                        stats=trade_statistics(subset)
                        performance_groups.append(dict(context,dimension=dimension,value=value,entries=len(subset),**stats,
                            drawdown_policy='REALIZED_SUBGROUP_CONTRIBUTION_NOT_FULL_PORTFOLIO_NAV'))
    write_csv(report/'canonical_window_metrics.csv',windows)
    write_csv(report/'fill_frequency_groups.csv',frequency)
    write_csv(report/'performance_groups.csv',performance_groups)
    sensitivity=[]
    for category in ('structural_sensitivity','execution_sensitivity'):
        for path in sorted((report/category).glob('**/summary.json')):
            d=json.loads(path.read_text())
            sensitivity.append(dict(category=category,cohort=d['cohort'],htf=d['htf'],ltf=d['ltf'],
                experiment=d.get('variant',d.get('scenario')),window=d['window']['name'],segment=d['segment'],
                start=d['start'],end=d['end'],**flat_performance(d)))
    write_csv(report/'registered_sensitivity_metrics.csv',sensitivity)
    target_cases={}
    for path in (report/'structural_sensitivity/BASE').glob('*/target_availability_qualification_only.jsonl.gz'):
        for r in json_rows(path):
            key=(r['symbol'],r['direction'],r['bos_time'],r['bos_level_price'])
            target_cases[key]=max(target_cases.get(key,0),r['distinct_fresh_opposing_pois'])
    qualification=[dict(minimum_targets=n,qualified_ob_cases_with_sufficient_distinct_opposing_pois=sum(v>=n for v in target_cases.values()),
        qualified_ob_cases=len(target_cases),qualification_only=True,not_ready_or_execution_count=True) for n in (2,3,4)]
    (report/'target_availability_qualification.json').write_text(canonical(qualification)+'\n')
    exit_rows=[];follow=[];paired=[]
    for path in sorted((report/'exit_management').glob('*/*/results.json')):
        for d in json.loads(path.read_text()):
            exit_rows.append(dict(study=path.parent.parent.name,case=path.parent.name,role=d['role'],cohort=d['cohort'],
                htf=d['htf'],ltf=d['ltf'],start=d['start'],end=d['end'],variant=d['variant'],
                allocation=d['allocation'],stop_policy=d['stop_policy'],**flat_performance(d),
                baseline_a_exact_match=d['baseline_a_exact_trade_decision_equity_match'],
                same_frozen_entry_signals=True,not_a_pooled_portfolio=True))
        if (path.parent/'post_be_follow.json').exists():
            follow.extend(dict(study=path.parent.parent.name,case=path.parent.name,**r) for r in json.loads((path.parent/'post_be_follow.json').read_text()))
        if (path.parent/'paired_actual_entries.json').exists():
            for pair in json.loads((path.parent/'paired_actual_entries.json').read_text()):
                for v in pair['variants']:
                    t=v['trade']
                    paired.append(dict(study=path.parent.parent.name,case=path.parent.name,variant=v['variant'],
                        signal_id=pair['signal_id'],symbol=t['symbol'],direction=t['direction'],status=t['status'],
                        entry=t['entry_time'],exit=t.get('exit_time'),net_pnl=t['net_pnl'],R=t['result_R'],
                        fees=t['fees_total'],slippage=t['slippage_total'],quantity=t['quantity'],risk=t['risk_amount'],
                        individual_trade_nav_max_drawdown=v['individual_trade_nav_max_drawdown'],
                        paired_shadow_match=v['backtest_shadow_trade_nav_match'],fills=t['fills']))
    write_csv(report/'exit_management_metrics.csv',exit_rows)
    write_csv(report/'post_be_follow.csv',follow)
    write_csv(report/'paired_exit_actual_entries.csv',paired)
    regime_coverage=[]
    for cohort in MAPPINGS:
        split=json.loads((report/f'{cohort}_temporal_split.json').read_text())
        for symbol in split['symbols']:
            key=(cohort,symbol)
            if key not in daily:daily[key]=daily_history(*key)
            for period in split['periods']:
                begin,end=(datetime.fromisoformat(period[k]) for k in ('start','end'))
                labels=Counter(regime(daily[key],c.close_time) for c in daily[key] if begin<c.close_time<=end)
                for market in ('BULL','BEAR','SIDEWAYS','UNKNOWN'):
                    for volatility in ('LOW','MEDIUM','HIGH','UNKNOWN'):
                        regime_coverage.append(dict(cohort=cohort,symbol=symbol,period=period['name'],
                            regime=market,volatility=volatility,complete_daily_observations=labels[(market,volatility)],
                            calendar_coverage_not_a_strategy_signal_count=True))
    write_csv(report/'causal_regime_calendar_coverage.csv',regime_coverage)
    mc=[]
    for cohort,mappings in MAPPINGS.items():
        for htf,ltf in mappings:
            trades=list(sample_groups[(cohort,htf,ltf)].values());n=len(trades)
            record=dict(cohort=cohort,htf=htf,ltf=ltf,unique_comparable_closed=n,
                        excluded_overlapping_walk_replays=True,independent_cohorts_never_pooled=True)
            if n<50:
                record['status']='WITHHELD_BELOW_50_COMPARABLE_CLOSED_TRADES'
            else:
                rng=Random(20261008);rr=[t['result_R'] for t in sorted(trades,key=lambda t:t['exit_time'])]
                outcomes=[]
                for method in ('BOOTSTRAP','SHUFFLE'):
                    for iteration in range(2000):
                        sample=rng.choices(rr,k=n) if method=='BOOTSTRAP' else rng.sample(rr,k=n)
                        equity=peak=1.0;dd=0.0;streak=maximum=0
                        for r in sample:
                            equity*=max(0,1+.02*r);peak=max(peak,equity);dd=max(dd,1-equity/peak)
                            streak=streak+1 if r< -1e-9 else 0;maximum=max(maximum,streak)
                        outcomes.append(dict(method=method,iteration=iteration,max_dd=dd,losing_streak=maximum,final_equity_multiple=equity))
                write_csv(report/f'monte_carlo_{cohort}_{htf}_{ltf}.csv',outcomes)
                record.update(status='DESCRIPTIVE_OBSERVED_R_SEQUENCES',iterations_per_method=2000,seed=20261008,
                    limitation='HYPOTHETICAL_2_PERCENT_COMPOUNDED_TRADE_R_SEQUENCE_NOT_OVERLAPPING_PORTFOLIO_REPLAY_OR_MARKET_GUARANTEE')
            mc.append(record)
    (report/'monte_carlo_sample_gate.json').write_text(canonical(mc)+'\n')
    (report/'table_generation_receipt.json').write_text(canonical(dict(complete=complete,canonical_rows=len(windows),
        frequency_rows=len(frequency),performance_group_rows=len(performance_groups),sensitivity_rows=len(sensitivity),
        exit_rows=len(exit_rows),paired_rows=len(paired),post_be_follow_rows=len(follow),
        no_variant_selected=True,baseline_hash_guard='PASS',trade_entry_allowed=False))+'\n')
    print('Tables generated:',len(windows),'canonical rows;',len(exit_rows),'exit rows; complete =',complete)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-partial',action='store_true',help='Provisional tables only; final completeness is never asserted.')
    summarize(parser.parse_args().allow_partial)
