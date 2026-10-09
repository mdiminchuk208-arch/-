"""Run offline BACKTEST/SHADOW observation and optional virtual management on CSV history."""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timedelta
from hashlib import sha256
import json
from pathlib import Path

from crypto_bot.data.storage import read_klines_csv
from crypto_bot.strategy.auto_levels import AutoLevelPolicy
from crypto_bot.strategy.replay import EngineMode, QualifiedLevels, SourceQualification, STRATEGY_VERSION, evaluate_snapshot
from crypto_bot.strategy.virtual_portfolio import VirtualPortfolio


def encode(value):
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"unsupported report value: {type(value).__name__}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', type=Path, default=Path('data/history/bybit'))
    parser.add_argument('--report-root', type=Path, default=Path('data/reports/strategy_replay'))
    parser.add_argument('--symbols', nargs='+', default=['BTCUSDT'])
    parser.add_argument('--htf', type=int, default=60)
    parser.add_argument('--ltf', type=int, default=5)
    parser.add_argument('--bars', type=int, default=288)
    parser.add_argument('--warmup-bars', type=int, default=576)
    parser.add_argument('--initial-capital', type=float, default=1170.0)
    parser.add_argument('--mode', choices=[m.value for m in EngineMode], default='BACKTEST')
    level_source = parser.add_mutually_exclusive_group()
    level_source.add_argument('--qualified-levels', type=Path,
                        help='JSON signal_id -> levels plus explicit source_qualification context; no automatic qualification')
    level_source.add_argument('--auto-levels', action='store_true',
                              help='opt-in experimental OB/HTF-gap selection; research evidence only, not source certification')
    parser.add_argument('--min-ob-body-fraction', type=float, default=0.6)
    parser.add_argument('--min-engulf-body-ratio', type=float, default=1.0)
    args = parser.parse_args()
    if args.bars <= 0 or args.warmup_bars < 0 or not 0 < args.ltf < args.htf:
        parser.error('positive bars, nonnegative warmup and 0 < LTF < HTF required')
    symbols = [s.strip().upper() for s in args.symbols]
    if not all(symbols) or len(set(symbols)) != len(symbols):
        parser.error('symbols must be nonempty and unique')
    qualified = {}
    try:
        auto_policy = (AutoLevelPolicy(min_body_fraction=args.min_ob_body_fraction,
                                      min_engulf_body_ratio=args.min_engulf_body_ratio)
                       if args.auto_levels else None)
    except ValueError as exc:
        parser.error(str(exc))
    if not args.auto_levels and (args.min_ob_body_fraction != 0.6 or args.min_engulf_body_ratio != 1.0):
        parser.error('OB thresholds require --auto-levels')
    if args.qualified_levels:
        payload = json.loads(args.qualified_levels.read_text(encoding='utf-8'))
        for key, row in payload.items():
            qrow = row.get('source_qualification')
            qualification = None
            if qrow is not None:
                reaction_known_at = qrow.get('repeat_test_ltf_reaction_known_at')
                qualification = SourceQualification(
                    known_at=datetime.fromisoformat(qrow['known_at']),
                    poi_kind=qrow['poi_kind'],
                    entry_path=qrow['entry_path'],
                    poi_source=qrow['poi_source'],
                    structure_path_confirmed=qrow['structure_path_confirmed'],
                    order_flow_aligned=qrow['order_flow_aligned'],
                    opposing_liquidity_cleared=qrow['opposing_liquidity_cleared'],
                    premium_discount_valid=qrow['premium_discount_valid'],
                    fresh_untested=qrow['fresh_untested'],
                    evidence=tuple(qrow['evidence']),
                    repeat_test_ltf_reaction_confirmed=qrow.get('repeat_test_ltf_reaction_confirmed', False),
                    repeat_test_ltf_reaction_known_at=(
                        datetime.fromisoformat(reaction_known_at) if reaction_known_at is not None else None
                    ),
                    repeat_test_ltf_reaction_evidence=tuple(qrow.get('repeat_test_ltf_reaction_evidence', ())),
                )
            qualified[key] = QualifiedLevels(
                datetime.fromisoformat(row['known_at']), row['stop_loss'], tuple(row['targets']),
                row['stop_policy'], row['target_policy'], qualification,
            )
    data, hashes = {}, {}
    for symbol in symbols:
        data[symbol] = {}
        for tf in (args.ltf, args.htf):
            path = args.data_root / symbol / f'{tf}.csv'
            rows = read_klines_csv(path)
            if not rows or any(r.exchange != 'BYBIT' or r.symbol != symbol or r.interval != str(tf) for r in rows):
                raise ValueError(f'missing/incorrect CSV series identity: {path}')
            data[symbol][tf] = [r.to_strategy_candle(tf * 60000) for r in rows]
            hashes[f'{symbol}/{tf}.csv'] = sha256(path.read_bytes()).hexdigest()
    end = min(series[args.ltf][-1].close_time for series in data.values())
    if any(end >= series[args.htf][-1].close_time + timedelta(minutes=args.htf)
           for series in data.values()):
        raise ValueError('stale HTF history: a required completed interval is missing')
    execution = {}
    for symbol in symbols:
        cs = [c for c in data[symbol][args.ltf] if c.close_time <= end]
        if len(cs) < args.bars:
            raise ValueError(f'insufficient execution bars: {symbol}')
        execution[symbol] = cs[-args.bars:]
        start = cs[max(0, len(cs) - args.bars - args.warmup_bars)].open_time
        data[symbol] = {tf: [c for c in series if c.open_time >= start and c.close_time <= end]
                        for tf, series in data[symbol].items()}
    portfolio = VirtualPortfolio(mode=args.mode, equity=args.initial_capital)
    updates, states, snapshot_counts = [], {}, Counter()
    for i in range(args.bars):
        bars = {symbol: execution[symbol][i] for symbol in sorted(symbols)}
        as_of = next(iter(bars.values())).close_time
        signals = []
        for symbol in sorted(symbols):
            snapshot = evaluate_snapshot(data[symbol], symbol=symbol, as_of=as_of,
                                         htf_minutes=args.htf, ltf_minutes=args.ltf,
                                         mode=args.mode, qualified_levels=qualified,
                                         auto_level_policy=auto_policy)
            snapshot_counts[symbol] += 1
            signals.extend(snapshot.signals)
            for signal in snapshot.signals:
                row = asdict(signal)
                row['direction'] = signal.direction.name
                signature = {k: v for k, v in row.items() if k != 'event_time'}
                canonical = json.dumps(signature, sort_keys=True, default=encode)
                if states.get(signal.signal_id) != canonical:
                    updates.append(row)
                    states[signal.signal_id] = canonical
        portfolio.step(bars, signals)
    args.report_root.mkdir(parents=True, exist_ok=True)
    latest = [json.loads(value) for value in states.values()]
    project_root = Path(__file__).resolve().parent.parent
    implementation_files = [*sorted((project_root / 'src').rglob('*.py')),
                            Path(__file__).resolve(), project_root / 'config/source_rules.json',
                            project_root / 'pyproject.toml']
    code_hashes = {path.relative_to(project_root).as_posix(): sha256(path.read_bytes()).hexdigest()
                   for path in implementation_files}
    payload = {
        'strategy_version': STRATEGY_VERSION, 'mode': args.mode,
        'analysis_mode': 'SOURCE_CONSERVATIVE', 'trade_entry_allowed': False,
        'symbols': sorted(symbols), 'htf_minutes': args.htf, 'ltf_minutes': args.ltf,
        'bars_per_symbol': args.bars, 'warmup_bars': args.warmup_bars,
        'input_hashes': hashes, 'policy': asdict(portfolio.policy),
        'starting_balance': portfolio.starting_balance,
        'balance': portfolio.balance, 'unrealized_pnl': portfolio.unrealized_pnl,
        'fees_paid': portfolio.fees_paid, 'slippage_cost': portfolio.slippage_cost,
        'input_code_hashes': code_hashes,
        'qualified_level_inputs': {key: asdict(value) for key, value in qualified.items()},
        'automatic_level_policy': asdict(auto_policy) if auto_policy is not None else None,
        'level_selection_policy': ('AUTO_RESEARCH_PROXY_PENDING_SOURCE_QUALIFICATION' if auto_policy is not None
                                   else 'EXPLICIT_QUALIFIED_LEVELS_WITH_SOURCE_CONTEXT'),
        'latest_signal_status_counts': dict(Counter(row['status'] for row in latest)),
        'automatic_level_blocking_counts': dict(Counter(reason for row in latest
                                                        for reason in row['level_blocking_reasons'])),
        'signal_statistics_scope': 'LATEST_STATE_PER_UNIQUE_SIGNAL',
        'snapshots_per_symbol': dict(snapshot_counts), 'signal_updates': updates,
        'unique_signal_count': len(states),
        'decision_count': len(portfolio.journal),
        'virtual_entry_count': sum(d.action == 'VIRTUAL_ENTRY' for d in portfolio.journal),
        'final_equity': portfolio.equity, 'open_virtual_positions': sorted(portfolio.positions),
        'pending_virtual_setups': len(portfolio.pending),
        'limitations': [('AUTO_LEVELS_ARE_RESEARCH_PROXIES_NOT_SOURCE_QUALIFIED_AND_CANNOT_CANONICALLY_ENTER'
                         if auto_policy is not None
                         else 'EXPLICIT_LEVELS_REQUIRE_AUDITABLE_SOURCE_CONTEXT'),
                        'SOURCE_CONTEXT_IS_CURRENTLY_CALLER_ASSERTED_WHERE_DETECTORS_ARE_NOT_IMPLEMENTED',
                        'SOURCE_COMPLETE_POI_LIQUIDITY_ORDER_FLOW_DETECTORS_NOT_YET_IMPLEMENTED',
                        'SCORE_AND_MIDPOINT_ENTRY_ARE_BACKTEST_PARAMETERS',
                        'CLOSED_HTF_OBSERVATION_CAN_DELAY_NEXT_OPEN_SFP',
                        'FUNDING_AND_LIQUIDATION_NOT_MODELLED', 'NO_LIVE_FEED_OR_EXECUTION_ADAPTER'],
    }
    summary = json.dumps(payload, indent=2, sort_keys=True, default=encode) + '\n'
    journal = ''.join(json.dumps(asdict(d), sort_keys=True, default=encode) + '\n' for d in portfolio.journal)
    (args.report_root / 'summary.json').write_text(summary, encoding='utf-8')
    (args.report_root / 'decisions.jsonl').write_text(journal, encoding='utf-8')
    digest = sha256((summary + journal).encode('utf-8')).hexdigest()
    (args.report_root / 'fingerprint.sha256').write_text(digest + '\n', encoding='utf-8')
    print(f'{args.mode}: {len(symbols)} symbols, {args.bars} bars each; {len(states)} unique setups; '
          f'{payload["virtual_entry_count"]} virtual entries; trade_entry_allowed=false; fingerprint={digest}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())