"""Offline historical virtual portfolio, with compounding and reproducible reports."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, replace
from datetime import datetime, timedelta
from hashlib import sha256
import json
from pathlib import Path

from crypto_bot.data.storage import read_klines_csv
from crypto_bot.data.qa import audit_klines
from crypto_bot.strategy.auto_levels import AutoLevelPolicy
from crypto_bot.strategy.historical_replay import indexed_signal_updates
from crypto_bot.strategy.portfolio_statistics import portfolio_statistics
from crypto_bot.strategy.replay import EngineMode, STRATEGY_VERSION
from crypto_bot.strategy.virtual_portfolio import VirtualPortfolio, SimulationPolicy

SYMBOLS='BTCUSDT ETHUSDT SOLUSDT XRPUSDT BNBUSDT DOGEUSDT ADAUSDT LINKUSDT AVAXUSDT LTCUSDT'.split()


def encode(value):
    if isinstance(value,datetime):
        return value.isoformat()
    raise TypeError(type(value).__name__)


def canonical(value):
    return json.dumps(value,sort_keys=True,default=encode,allow_nan=False)


def _index_job(job):
    symbol,histories,htf,ltf,mode=job
    updates,metadata=indexed_signal_updates(histories,symbol=symbol,htf_minutes=htf,
        ltf_minutes=ltf,mode=mode,auto_level_policy=AutoLevelPolicy())
    return symbol,updates,metadata


def simulate(execution,updates,*,initial_capital=1170.0,mode='BACKTEST'):
    """One portfolio across all symbols; updates are observed at their own close."""
    symbols=sorted(execution)
    clock=[c.close_time for c in execution[symbols[0]]]
    if not clock or any([c.close_time for c in execution[s]]!=clock for s in symbols):
        raise ValueError('all execution symbols need identical contiguous clocks')
    by_time=defaultdict(list)
    first_close=clock[0]
    # Warmup supplies analysis, not portfolio entries. Initialize each latest
    # already-known state at the first execution close, just like snapshot replay.
    warmup={}
    for signal in sorted(updates,key=lambda s:(s.event_time,s.symbol,s.bos_time,s.signal_id)):
        if signal.event_time<=first_close:
            warmup[signal.signal_id]=replace(signal,event_time=first_close)
        elif signal.event_time<=clock[-1]:
            by_time[signal.event_time].append(signal)
    by_time[first_close].extend(warmup.values())
    p=VirtualPortfolio(equity=initial_capital,mode=mode,policy=SimulationPolicy())
    observed=[]
    for i,when in enumerate(clock):
        signals=sorted(by_time[when],key=lambda s:(s.symbol,s.bos_time,s.direction.value,s.signal_id))
        p.step({s:execution[s][i] for s in symbols},signals)
        observed.extend(signals)
    return p,observed


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root',type=Path,default=Path('data/history/bybit'))
    parser.add_argument('--report-root',type=Path,default=Path('data/reports/historical_portfolio'))
    parser.add_argument('--symbols',nargs='+',default=SYMBOLS)
    parser.add_argument('--htf',type=int,default=60)
    parser.add_argument('--ltf',type=int,default=5)
    parser.add_argument('--days',default='180',help='positive whole days, or max available with warmup')
    parser.add_argument('--start',help='explicit timezone-aware execution open; keeps prefix warmup fixed')
    parser.add_argument('--end',help='explicit timezone-aware execution close')
    parser.add_argument('--warmup-bars',type=int,default=576)
    parser.add_argument('--initial-capital',type=float,default=1170.0)
    parser.add_argument('--mode',choices=[m.value for m in EngineMode],default='BACKTEST')
    parser.add_argument('--workers',type=int,default=1)
    args=parser.parse_args(argv)
    symbols=sorted(s.strip().upper() for s in args.symbols)
    if (not symbols or len(set(symbols))!=len(symbols) or not all(symbols) or
        not 0<args.ltf<args.htf or args.warmup_bars<0 or not 1<=args.workers<=4):
        parser.error('unique symbols, valid timeframes, nonnegative warmup and 1-4 workers required')
    try:
        VirtualPortfolio(equity=args.initial_capital)
        days=None if args.days=='max' else int(args.days)
        if days is not None and days<=0:
            raise ValueError('days must be positive')
        explicit_start=datetime.fromisoformat(args.start) if args.start else None
        explicit_end=datetime.fromisoformat(args.end) if args.end else None
        if any(t is not None and t.utcoffset() is None for t in (explicit_start,explicit_end)):
            raise ValueError('explicit start/end must have timezones')
    except ValueError as exc:
        parser.error(str(exc))
    data,hashes,quality={}, {}, {}
    for symbol in symbols:
        data[symbol]={}
        for tf in (args.ltf,args.htf):
            path=args.data_root/symbol/f'{tf}.csv'
            rows=read_klines_csv(path)
            qa=audit_klines(rows,tf*60000)
            if not rows or not qa.is_healthy or any(r.exchange!='BYBIT' or r.symbol!=symbol or r.interval!=str(tf) for r in rows):
                raise ValueError(f'invalid historical series: {path}')
            data[symbol][tf]=[r.to_strategy_candle(tf*60000) for r in rows]
            hashes[f'{symbol}/{tf}.csv']=sha256(path.read_bytes()).hexdigest()
            quality[f'{symbol}/{tf}.csv']=dict(rows=len(rows),first_open=data[symbol][tf][0].open_time,
                last_close=data[symbol][tf][-1].close_time,healthy=True)
    available_end=min(cs[-1].close_time for ds in data.values() for cs in ds.values())
    available_start=max(cs[0].open_time for ds in data.values() for cs in ds.values())
    end=explicit_end or available_end
    start=explicit_start or (end-timedelta(days=days) if days is not None else
                             available_start+timedelta(minutes=args.warmup_bars*args.ltf))
    warmup_start=start-timedelta(minutes=args.warmup_bars*args.ltf)
    if end>available_end or warmup_start<available_start or start>=end:
        raise ValueError('requested period/warmup exceeds common available coverage; no data was substituted')
    if any(int(t.timestamp()*1000)%(args.ltf*60000) for t in (start,end)):
        raise ValueError('execution start/end must align to LTF')
    execution={}
    for symbol in symbols:
        execution[symbol]=[c for c in data[symbol][args.ltf] if start<=c.open_time and c.close_time<=end]
        if not execution[symbol] or execution[symbol][0].open_time!=start or execution[symbol][-1].close_time!=end:
            raise ValueError('incomplete execution coverage')
        data[symbol]={tf:[c for c in cs if c.open_time>=warmup_start and c.close_time<=end]
                      for tf,cs in data[symbol].items()}
    jobs=[(s,data[s],args.htf,args.ltf,args.mode) for s in symbols]
    metadata,updates={},[]
    if args.workers>1:
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            for symbol,signals,meta in executor.map(_index_job,jobs):
                metadata[symbol]=meta
                updates.extend(signals)
                print(f'Indexed {symbol}: {len(signals)} signal changes; {meta["automatic_evaluations"]} level evaluations',flush=True)
    else:
        for job in jobs:
            symbol,signals,meta=_index_job(job)
            metadata[symbol]=meta
            updates.extend(signals)
            print(f'Indexed {symbol}: {len(signals)} signal changes; {meta["automatic_evaluations"]} level evaluations',flush=True)
    p,observed=simulate(execution,updates,initial_capital=args.initial_capital,mode=args.mode)
    latest={s.signal_id:s for s in observed}
    ever=defaultdict(set)
    blockers=defaultdict(set)
    for s in observed:
        ever[s.status].add(s.signal_id)
        for reason in s.level_blocking_reasons:
            blockers[reason].add(s.signal_id)
    funnel=dict(market_bars=sum(len(cs) for cs in execution.values()),
        raw_structure_events_including_warmup={s:metadata[s]['structure_events'] for s in symbols},
        sfp_bos_links_including_warmup=sum(m['sfp_bos_links'] for m in metadata.values()),
        unique_setups=len(latest),signal_state_changes=len(observed),
        latest_status_counts=dict(Counter(s.status for s in latest.values())),
        ever_status_unique_setup_counts={k:len(v) for k,v in sorted(ever.items())},
        ever_auto_blocker_unique_setup_counts={k:len(v) for k,v in sorted(blockers.items())},
        status_count_policy='EVER_COUNTS_OVERLAP_LATEST_COUNTS_DO_NOT',
        entries=len(p.trades),completed_trades=sum(t['status']=='CLOSED' for t in p.trades.values()))
    for status in ('WAITING_FOR_ENTRY_GEOMETRY','WAITING_FOR_SOURCE_LEVELS','WAITING_FOR_AUTO_LEVELS',
                   'REJECTED_ENTRY_GEOMETRY','SOURCE_CONTEXT_BLOCKED','INVALIDATED','READY_FOR_VIRTUAL_ENTRY'):
        funnel['ever_status_unique_setup_counts'].setdefault(status,0)
        funnel['latest_status_counts'].setdefault(status,0)
    funnel['blocker_categories_unique_setups']={label:len(set().union(*(blockers[reason] for reason in reasons)))
        for label,reasons in {
            'missing_OB':('NO_POST_BOS_OB_PATTERN','NO_ELIGIBLE_POST_BOS_OB','RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND'),
            'missing_HTF_POI':('FRESH_PREEXISTING_HTF_POI_NOT_FOUND',),
            'missing_three_targets':('THREE_DISTINCT_FRESH_OPPOSING_POIS_NOT_FOUND',),
            'OTE_mismatch':('OB_OUTSIDE_OTE_OR_STRUCTURAL_IMPULSE','OB_STOP_DOES_NOT_PROTECT_ENTIRE_OTE'),
            'stale_evidence':('OB_FIRST_TEST_ALREADY_CONSUMED',),
        }.items()}
    admission_counts=Counter(d.reason for d in p.journal if d.action=='VIRTUAL_ENTRY_BLOCKED')
    funnel['admission_blocks']={reason:admission_counts[reason] for reason in (
        'TP1_NOT_POSITIVE_AFTER_COSTS','ISOLATED_MARGIN_BUDGET','TOTAL_RISK_CAP_6_PERCENT',
        'DAILY_LOSS_LIMIT_LATCHED','REENTRY_SCORE_BELOW_75','PREVIOUS_POSITION_STILL_OPEN',
        'COST_ADJUSTED_FILL_GEOMETRY','INVALID_QUANTITY','EQUITY_EXHAUSTED')}
    root=Path(__file__).resolve().parent.parent
    files=[*sorted((root/'src').rglob('*.py')),*sorted((root/'scripts').glob('*.py')),
           root/'config/source_rules.json',root/'pyproject.toml']
    code_hashes={f.relative_to(root).as_posix():sha256(f.read_bytes()).hexdigest() for f in files}
    payload=dict(strategy_version=STRATEGY_VERSION,mode=args.mode,trade_entry_allowed=False,
        analysis_mode='SOURCE_CONSERVATIVE',symbols=symbols,htf_minutes=args.htf,ltf_minutes=args.ltf,
        execution_start=start,execution_end=end,days=(end-start).total_seconds()/86400,
        warmup_start=warmup_start,warmup_bars=args.warmup_bars,
        common_available_start=available_start,common_available_end=available_end,
        coverage_365_days=False if (available_end-available_start).days<365 else True,
        input_hashes=hashes,input_code_hashes=code_hashes,input_quality=quality,
        initial_capital=args.initial_capital,policy=asdict(p.policy),automatic_level_policy=asdict(AutoLevelPolicy()),
        funnel=funnel,portfolio=portfolio_statistics(p,observed,symbols),
        pending_setups=len(p.pending),index_metadata=metadata,
        limitations=['AUTO_LEVELS_EXPERIMENTAL_NOT_SOURCE_CERTIFIED','RANGE_BOUNDARIES_UNREVIEWED',
            'FRACTIONAL_LINEAR_COIN_QUANTITY_NO_HISTORICAL_EXCHANGE_LOT_FILTERS',
            'FUNDING_LIQUIDATION_NOT_MODELLED','OHLC_ORDER_CONSERVATIVE',
            'MFE_MAE_FULL_BAR_ENVELOPE_CAN_INCLUDE_POST_EXIT_EXTREMES',
            'EQUITY_CURVE_AND_DRAWDOWN_SAMPLED_AT_BAR_CLOSE',
            'OPEN_POSITIONS_MARKED_NOT_FORCED_CLOSED_AT_END','NO_PUBLIC_LIVE_OR_EXECUTION'])
    args.report_root.mkdir(parents=True,exist_ok=True)
    outputs={'summary.json':json.dumps(payload,sort_keys=True,indent=2,default=encode,allow_nan=False)+'\n',
        'signals.jsonl':''.join(canonical({**asdict(s),'direction':s.direction.name})+'\n' for s in observed),
        'decisions.jsonl':''.join(canonical(asdict(d))+'\n' for d in p.journal),
        'trades.jsonl':''.join(canonical(t)+'\n' for _,t in sorted(p.trades.items())),
        'equity_curve.jsonl':''.join(canonical(point)+'\n' for point in p.equity_curve)}
    output_hashes={}
    for name,contents in outputs.items():
        (args.report_root/name).write_text(contents,encoding='utf-8',newline='\n')
        output_hashes[name]=sha256(contents.encode()).hexdigest()
    digest=sha256(canonical(output_hashes).encode()).hexdigest()
    (args.report_root/'fingerprint.sha256').write_text(digest+'\n',encoding='utf-8')
    (args.report_root/'artifact_hashes.json').write_text(json.dumps(output_hashes,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(f'{args.mode}: ${p.starting_balance:.2f} -> equity ${p.equity:.2f}; '
          f'{len(latest)} setups; {len(p.trades)} entries; '
          f'trade_entry_allowed=false; fingerprint={digest}',flush=True)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
