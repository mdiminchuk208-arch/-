"""Two independent causal runs on public CSV history; offline comparisons only."""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, replace
from datetime import timedelta
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

from crypto_bot.analysis_report import write_event_csv, write_structure_transition_csv, write_trend_state_csv
from crypto_bot.data.qa import audit_klines
from crypto_bot.data.storage import read_klines_csv
from crypto_bot.global_report import write_global_opportunities_csv
from crypto_bot.mtf_report import write_mtf_candidates_csv, write_mtf_opportunities_csv, write_mtf_summary_json
from crypto_bot.range_report import write_ranges_csv, write_range_sfp_events_csv
from crypto_bot.strategy.global_opportunity import cluster_cross_pair_opportunities
from crypto_bot.strategy.market_analysis import analyze_market, StructureAnalysisMode, TrendState
from crypto_bot.strategy.mtf_sfp import link_sfp_formations_to_ltf_bos, MtfSfpStatus
from crypto_bot.strategy.range_engine import RangeDetectionParams, augment_market_report_with_range_sfps
from crypto_bot.strategy.recovery_ablation import (
    plain, stable_key, bos_records, range_records, sfp_records, mtf_records,
    comparison, market_fingerprint,
)
from crypto_bot.strategy.structure_stability import compare_bos_suffix


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plain(data), ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def load_legacy(root):
    if root is None:
        return None
    path = root / 'src/crypto_bot/strategy/market_analysis.py'
    spec = importlib.util.spec_from_file_location('phase1411_legacy_market', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    # Dependencies used by legacy analyzer must be byte-identical, preventing a false baseline.
    for name in ('common/models.py', 'strategy/structure.py', 'strategy/sfp.py'):
        current = Path(__file__).resolve().parents[1] / 'src/crypto_bot' / name
        assert current.read_text(encoding='utf-8') == (root / 'src/crypto_bot' / name).read_text(encoding='utf-8'), name
    return module


def summarize_diff(path, source, technical):
    result = comparison(source, technical)
    write_json(path, result)
    return {key: value for key, value in result.items() if key != 'rows'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--symbols', nargs='+', default=['BTCUSDT', 'ETHUSDT'])
    parser.add_argument('--data-root', type=Path, default=Path('data/history/bybit'))
    parser.add_argument('--report-root', type=Path, default=Path('data/reports/phase1_4_14/final_240d'))
    parser.add_argument('--legacy-root', type=Path)
    parser.add_argument('--evaluation-days', type=int, default=240)
    parser.add_argument('--tolerances', nargs='+', type=float, default=[.04, .06, .08, .10, .12])
    parser.add_argument('--wait-minutes', nargs='+', type=int, default=[60, 120, 240])
    parser.add_argument('--cluster-minutes', nargs='+', type=int, default=[0, 15, 60])
    args = parser.parse_args()
    if args.evaluation_days <= 0 or any(w <= 0 for w in args.wait_minutes) or any(w < 0 for w in args.cluster_minutes):
        parser.error('invalid evaluation/wait/cluster parameter')
    for t in args.tolerances:
        RangeDetectionParams(t)
    legacy = load_legacy(args.legacy_root)
    modes = list(StructureAnalysisMode)
    overall_ok = True
    for symbol in args.symbols:
        print(f'{symbol}: loading and validating input', flush=True)
        candles = {}
        manifest = {'symbol': symbol, 'version': '0.4.14', 'evaluation_days': args.evaluation_days,
                    'tolerances': args.tolerances, 'wait_minutes': args.wait_minutes,
                    'cluster_minutes': args.cluster_minutes, 'inputs': {}, 'code_hashes': {}}
        root = Path(__file__).resolve().parents[1]
        tracked = list(sorted((root/'src').rglob('*.py')))
        tracked.extend((Path(__file__).resolve(), root/'config/source_rules.json', root/'pyproject.toml'))
        for p in tracked:
            if p.exists():
                manifest['code_hashes'][str(p.relative_to(root))] = hashlib.sha256(p.read_bytes()).hexdigest()
        for tf in (5, 15, 60, 240):
            path = args.data_root / symbol / f'{tf}.csv'
            rows = read_klines_csv(path)
            qa = audit_klines(rows, tf*60000)
            if not rows or not qa.is_healthy:
                raise ValueError(f'unhealthy data: {path}: {qa}')
            if any(r.symbol != symbol or r.interval != str(tf) or r.exchange != 'BYBIT' for r in rows):
                raise ValueError(f'incorrect series identity: {path}')
            candles[tf] = [r.to_strategy_candle(tf*60000) for r in rows]
            span = (candles[tf][-1].close_time - candles[tf][0].open_time).total_seconds()/86400
            minimum_span = args.evaluation_days - tf / 1440
            if span < minimum_span:
                raise ValueError(
                    f'input span must cover the requested {args.evaluation_days}d evaluation window '
                    f'(including closed-candle boundary rounding): {path}'
                )
            manifest['inputs'][tf] = {'path': str(path.resolve()), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'rows': len(rows), 'start': candles[tf][0].open_time, 'end': candles[tf][-1].close_time,
                'span_days': span, 'qa': asdict(qa)}
        out = args.report_root / symbol
        common_end = min(cs[-1].close_time for cs in candles.values())
        manifest['shared_symbol_evaluation_end'] = common_end
        manifest['shared_symbol_evaluation_start'] = common_end - timedelta(days=args.evaluation_days)
        write_json(out/'manifest.json', manifest)
        reports = {}
        summary = {'symbol': symbol, 'structure': {}, 'pairs': {}, 'global': {},
                   'legacy_checked': legacy is not None, 'checks_passed': True,
                   'interpretation': 'Ancestry is causal and conservative; independent mode differences are counterfactual audit only. No source rule or profitability threshold is inferred. Trade entries remain zero.'}
        for tf, cs in candles.items():
            reports[tf] = {}
            legacy_fp = None
            if legacy is not None:
                print(f'{symbol} {tf}: legacy baseline', flush=True)
                old = legacy.analyze_market(cs, timeframe_minutes=tf)
                legacy_fp = market_fingerprint(old)
                del old
            for mode in modes:
                print(f'{symbol} {tf}: {mode.value}', flush=True)
                report = analyze_market(cs, timeframe_minutes=tf, analysis_mode=mode)
                reports[tf][mode] = report
                dest = out/str(tf)/mode.value
                dest.mkdir(parents=True, exist_ok=True)
                write_event_csv(replace(report, events=tuple(e for e in report.events if 'STRUCTURE' in e.kind.value or 'CONF_CONFIRMED' in e.kind.value)), dest/'structure_events.csv')
                write_structure_transition_csv(report, dest/'transitions.csv')
                write_trend_state_csv(report, dest/'states.csv')
                suffix_start = cs[-1].close_time - timedelta(days=60)
                suffix = [c for c in cs if c.open_time >= suffix_start]
                short = analyze_market(suffix, timeframe_minutes=tf, analysis_mode=mode)
                stability = compare_bos_suffix(report, short, compare_start=suffix[0].open_time+timedelta(days=7))
                info = {'states': report.state_candle_counts(), 'longest_broken': report.longest_state_run(TrendState.BROKEN),
                        'transitions': dict(Counter(t.resolution_mode for t in report.structure_transition_diagnostics)),
                        'suffix_stability': asdict(stability), 'market_fingerprint': market_fingerprint(report)}
                if mode == StructureAnalysisMode.TECHNICAL_RECOVERY and legacy_fp is not None:
                    info['matches_legacy'] = info['market_fingerprint'] == legacy_fp
                    overall_ok &= info['matches_legacy']
                    summary['checks_passed'] &= info['matches_legacy']
                if mode == StructureAnalysisMode.SOURCE_CONSERVATIVE:
                    assert not any(e.recovery_transition_ids for e in report.events)
                    assert 'SAME_DIRECTION_POST_BOS_RECOVERY' not in info['transitions']
                write_json(dest/'summary.json', info)
            source, tech = (reports[tf][m] for m in modes)
            # The independent liquidity/SFP layer must not change with structure mode.
            for kinds in ({'SWING_HIGH_CONFIRMED','SWING_LOW_CONFIRMED'}, {'BEARISH_SFP_FORMATION_CONFIRMED','BULLISH_SFP_FORMATION_CONFIRMED'}):
                def semantic_event(e):
                    return stable_key(
                        e.kind, e.event_time, e.candle_index, e.price, e.level_id,
                        e.level_price, e.episode_id, e.member_level_ids,
                        e.sfp_pattern_extreme_price, e.liquidity_origin, e.range_id,
                    )
                assert [semantic_event(e) for e in source.events if e.kind.value in kinds] == [
                    semantic_event(e) for e in tech.events if e.kind.value in kinds
                ]
            summary['structure'][tf] = summarize_diff(out/str(tf)/'bos_ablation.json', bos_records(source), bos_records(tech))
            summary['structure'][tf]['structural_sfp'] = summarize_diff(
                out/str(tf)/'structural_sfp_ablation.json',
                sfp_records(source, range_only=False),
                sfp_records(tech, range_only=False),
            )
        all_pairs = {}
        for htf, ltf in ((60,5),(240,15)):
            pair = f'{htf}_to_{ltf}'
            pair_end = min(candles[htf][-1].close_time, candles[ltf][-1].close_time)
            start = pair_end-timedelta(days=args.evaluation_days)
            for tolerance in args.tolerances:
                label = f'{pair}/tolerance_{tolerance:g}'
                print(f'{symbol} {label}: ranges and MTF', flush=True)
                base_path = out / label
                range_reports, merged_reports = {}, {}
                pair_summary = {'evaluation_start': start, 'evaluation_end': pair_end, 'stages': {}, 'waits': {}}
                for mode in modes:
                    merged, ranges = augment_market_report_with_range_sfps(candles[htf], reports[htf][mode], params=RangeDetectionParams(tolerance))
                    range_reports[mode], merged_reports[mode] = ranges, merged
                    write_ranges_csv(ranges, base_path/mode.value/'ranges.csv')
                    write_range_sfp_events_csv(ranges, base_path/mode.value/'range_sfp.csv')
                a,b = (range_reports[m] for m in modes)
                for stage, ra, rb in (
                    ('range_candidates_loaded',range_records(a),range_records(b)),
                    ('validated_ranges_loaded',range_records(a,validated=True),range_records(b,validated=True)),
                    ('range_sfp_loaded',sfp_records(merged_reports[modes[0]],a),sfp_records(merged_reports[modes[1]],b)),
                    ('range_candidates_evaluation',range_records(a,start=start,end=pair_end),range_records(b,start=start,end=pair_end)),
                    ('validated_ranges_evaluation',range_records(a,validated=True,start=start,end=pair_end),range_records(b,validated=True,start=start,end=pair_end)),
                    ('range_sfp_evaluation',sfp_records(merged_reports[modes[0]],a,start=start,end=pair_end),sfp_records(merged_reports[modes[1]],b,start=start,end=pair_end)),
                ):
                    pair_summary['stages'][stage] = summarize_diff(base_path/f'{stage}.json',ra,rb)
                for wait in args.wait_minutes:
                    records = {}
                    for mode in modes:
                        mtf = link_sfp_formations_to_ltf_bos(merged_reports[mode],reports[ltf][mode],
                            htf_minutes=htf,ltf_minutes=ltf,max_wait_minutes=wait,candidate_not_before=start,
                            ltf_observation_start=candles[ltf][0].open_time,ltf_observation_end=pair_end)
                        assert all(not c.trade_entry_allowed for c in mtf.candidates)
                        assert all(not o.trade_entry_allowed for o in mtf.opportunities)
                        assert all(not c.entry_search_allowed for c in mtf.candidates if c.htf_recovery_transition_ids or c.ltf_recovery_transition_ids)
                        dest=base_path/mode.value/f'wait_{wait}'
                        write_mtf_candidates_csv(mtf,dest/'contexts.csv')
                        write_mtf_opportunities_csv(mtf,dest/'opportunities.csv')
                        write_mtf_summary_json(mtf,dest/'summary.json')
                        records[mode]=mtf_records(mtf,range_reports[mode])
                        all_pairs.setdefault((tolerance,wait,mode),[]).append((pair,mtf))
                    contexts_a,opps_a=records[modes[0]];contexts_b,opps_b=records[modes[1]]
                    confirmed_a={k:v for k,v in contexts_a.items() if v['status']==MtfSfpStatus.LTF_BOS_CONFIRMED.value}
                    confirmed_b={k:v for k,v in contexts_b.items() if v['status']==MtfSfpStatus.LTF_BOS_CONFIRMED.value}
                    pair_summary['waits'][wait] = {
                        'all_context_outcomes':summarize_diff(base_path/f'wait_{wait}_contexts.json',contexts_a,contexts_b),
                        'sfp_to_bos':summarize_diff(base_path/f'wait_{wait}_confirmed.json',confirmed_a,confirmed_b),
                        'opportunities':summarize_diff(base_path/f'wait_{wait}_opportunities.json',opps_a,opps_b),
                    }
                    # Additional identical UTC slice for cross-pair/cross-symbol comparison.
                    shared_start=common_end-timedelta(days=args.evaluation_days)
                    shared_records={}
                    for mode in modes:
                        h=replace(merged_reports[mode],events=tuple(e for e in merged_reports[mode].events if e.event_time<=common_end))
                        l=replace(reports[ltf][mode],events=tuple(e for e in reports[ltf][mode].events if e.event_time<=common_end))
                        shared=link_sfp_formations_to_ltf_bos(h,l,htf_minutes=htf,ltf_minutes=ltf,max_wait_minutes=wait,
                            candidate_not_before=shared_start,ltf_observation_start=candles[ltf][0].open_time,ltf_observation_end=common_end)
                        shared_records[mode]=mtf_records(shared,range_reports[mode])
                    pair_summary['waits'][wait]['shared_utc_opportunities']=summarize_diff(base_path/f'wait_{wait}_shared_utc_opportunities.json',shared_records[modes[0]][1],shared_records[modes[1]][1])
                summary['pairs'][label]=pair_summary
        for tolerance in args.tolerances:
            for wait in args.wait_minutes:
                for window in args.cluster_minutes:
                    global_records={}
                    for mode in modes:
                        pair_reports=all_pairs[(tolerance,wait,mode)]
                        opps=cluster_cross_pair_opportunities(symbol,pair_reports,cluster_window_minutes=window)
                        assert all(not o.trade_entry_allowed for o in opps)
                        # Replace ordinal local IDs by semantic local-BOS keys for comparison.
                        refs={f'{p}#{o.opportunity_id}':stable_key(p,o.expected_direction,o.ltf_bos_event_time,o.ltf_bos_level_price)
                              for p,r in pair_reports for o in r.opportunities}
                        global_records[mode] = {}
                        for o in opps:
                            members = tuple(sorted(refs[r] for r in o.local_opportunity_ids))
                            global_key = stable_key(o.expected_direction, o.cluster_start_time, o.cluster_end_time, members)
                            global_records[mode][global_key] = plain({
                                'analysis_mode': mode.value,
                                'time':o.cluster_start_time,'members':list(members),
                                'recovery_context_refs':o.recovery_context_refs,'trade_entry_allowed':o.trade_entry_allowed,
                                'entry_search_allowed':o.entry_search_allowed})
                        write_global_opportunities_csv(opps,out/'global'/f'{tolerance:g}_{wait}_{window}'/mode.value/'opportunities.csv')
                    label=f'{tolerance:g}_{wait}_{window}'
                    summary['global'][label]=summarize_diff(out/'global'/f'{label}.json',global_records[modes[0]],global_records[modes[1]])
        write_json(out/'summary.json',summary)
        print(f'{symbol}: complete, checks_passed={summary["checks_passed"]}',flush=True)
    return 0 if overall_ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
