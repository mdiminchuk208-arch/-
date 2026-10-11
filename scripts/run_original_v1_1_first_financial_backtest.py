"""One preregistered original-v1.1 coverage/accounting run; immutable resume.

No MediumTermEngine or historical source labels are imported for admission.
The real-history source annotation catalog is empty. All active-branch probes
must WAIT; an unexpected ALLOW is an integrity error, never a fabricated fill.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
from collections import Counter, defaultdict
from datetime import UTC, datetime
from hashlib import sha256

from original_strategy_executable_profile_v1 import ACTIVE
from original_v1_1_evidence_adapter import (
    BASELINE_BRANCH_MAP,
    VERSION,
    all_proposals,
    baseline_probe,
    enumerate_series,
    evidence_case,
    inspect_proposal,
)
from original_v1_1_financial_accounting import EQUITY, FEE, RISK, SLIPPAGE, metrics
from original_v1_1_financial_data import (
    BASE,
    END,
    OUT,
    PRE,
    ROOT,
    START,
    STRATEGY_COMMIT,
    STRATEGY_MANIFEST,
    STRATEGY_SHA,
    TFS,
    Bar,
    checksum,
    compact,
    iso,
    load_market,
    read_rows,
    save,
    write_csv,
    write_rows,
)
from verify_original_strategy_spec_v1_1 import resume as strategy_resume

PROTOCOL = ROOT / 'ORIGINAL_V1_1_FINANCIAL_BACKTEST_PROTOCOL.md'
PREREG = ROOT / 'original_v1_1_financial_backtest_preregistration.json'
REPORT = ROOT / 'ORIGINAL_V1_1_FIRST_FINANCIAL_BACKTEST_REPORT.md'
SOURCE_REQUEST = ROOT / 'data/source_materials/original_v1_1_financial_backtest_2026_10_11/user_request.txt'
CODE = ['scripts/original_v1_1_financial_data.py', 'scripts/original_v1_1_evidence_adapter.py',
        'scripts/original_v1_1_financial_accounting.py', 'scripts/run_original_v1_1_first_financial_backtest.py',
        'tests/test_original_v1_1_first_financial_backtest.py']
RESULT = OUT / 'result'
SEAL = OUT / 'result_manifest.json'
VIEWS = ('INDEPENDENT_SOURCE_CASES', 'SHARED_PORTFOLIO')
CANDIDATE_FIELDS = ['candidate_id', 'symbol', 'branch', 'direction', 'setup_tf', 'decision_at',
                    'status', 'SOURCE_STRATEGY_DECISION', 'evidence_complete', 'source_pass',
                    'missing_evidence', 'parallel_blockers', 'trade_entry_allowed']
TRADE_FIELDS = ['candidate_id', 'symbol', 'branch', 'direction', 'setup_tf', 'status', 'entry_at',
                'exit_at', 'entry', 'initial_stop', 'exit', 'quantity', 'initial_risk', 'gross_pnl',
                'fees', 'slippage', 'net_pnl', 'result_R', 'trade_entry_allowed']


def relative(path):
    return str(path.relative_to(ROOT))


def prepare():
    if PREREG.exists() or SEAL.exists():
        raise ValueError('Existing preregistration/result cannot be rewritten')
    strategy_resume()
    assert checksum(STRATEGY_MANIFEST) == STRATEGY_SHA
    _, dataset = load_market()
    save(PRE / 'dataset_manifest.json', dataset)
    catalog = {'version': VERSION, 'historical_source_validated_records': [],
        'instrument_metadata_records_known_in_historical_interval': [],
        'reason': 'No explicitly source_validated historical annotation bundle exists in frozen source inputs. '
                  'Baseline engine role/classification fields and old751 labels are not authoritative SOURCE evidence.',
        'synthetic_examples_excluded': True, 'baseline_engine_labels_excluded': True}
    save(PRE / 'historical_evidence_catalog.json', catalog)
    comparison_paths = [BASE / 'simulation/enabled' / name for name in
                       ('shared_trades.jsonl.gz', 'shared_summary.json', 'shared_equity_curve.jsonl.gz')]
    comparison_paths += [BASE / 'detection' / s / 'enabled/signals.jsonl.gz' for s in ('BTCUSDT', 'ETHUSDT')]
    config = {'stage': 'FIRST_FINANCIAL_BACKTEST_PRE_OUTCOME', 'strategy_commit': STRATEGY_COMMIT,
        'freeze_manifest': relative(STRATEGY_MANIFEST), 'freeze_sha256': STRATEGY_SHA,
        'strategy_artifacts': json.loads(STRATEGY_MANIFEST.read_text())['artifacts'],
        'dataset_manifest': relative(PRE / 'dataset_manifest.json'), 'exact_period': dataset['exact_trading_interval'],
        'symbols': ['BTCUSDT', 'ETHUSDT'], 'TF_universe': list(TFS), 'evidence_adapter_version': VERSION,
        'evidence_input': relative(PRE / 'historical_evidence_catalog.json'),
        'source_admission': 'Only frozen profile evaluate; no baseline engine/owner/cost/tree gates',
        'entry_stop_exit': 'Unmodified U1–U6/N11; full contextual FTA or Range80+20 same exit zone; fixed stop',
        'WAIT': 'Unknown/absent causal evidence is WAIT, never SOURCE_REJECT or absence of setup',
        'raw_enumeration': 'Preregistered necessary OHLC proposal convention, not exhaustive discretionary setup detection: '
            'last confirmed strict3-bar swings, wick reclaim, prior raid/full-range engulf, provisional zone body-cross, '
            'provisional last-swing bracket deviation/reclaim. No qualitative thresholds; proposals never set source_validated.',
        'fill_semantics': 'Frozen LIMIT plan requires physical selection then strictly later observed quote; '
            'no artificial quotes from OHLC. No orders are possible without complete source annotations.',
        'intrabar': 'WAIT_INTRABAR_ORDER; no SL-first/TP-first, no synthetic subbars/path; censored not closed',
        'cost_normalization': {'entry_fee_fraction': str(FEE), 'exit_fee_fraction': str(FEE),
            'entry_slippage_fraction': str(SLIPPAGE), 'exit_slippage_fraction': str(SLIPPAGE),
            'model': 'Reference-price notional cost debits. Preserve frozen source LIMIT price. '
                     'Assumptions inherited from baseline-C rates; not measured actual historical execution.',
            'funding': 'Unavailable/excluded, no assumed funding zero or funding-inclusive Net claim',
            'identity': 'Gross reference-price P&L minus Fees minus Slippage equals Net'},
        'accounting_views': {'INDEPENDENT_SOURCE_CASES': {'initial_equity': str(EQUITY), 'risk_fraction': str(RISK),
            'sizing': 'Each case fixed23.4 USDT gross initial-stop risk, no source/portfolio gates',
            'DD': 'Chronological closed-case reference cash ledger, not investable shared capital'},
            'SHARED_PORTFOLIO': {'initial_equity': str(EQUITY), 'risk_fraction': str(RISK),
            'sizing': '2% of causally known equity at actual observable fill; no project total-risk/margin/overlay gates',
            'capital_exhaustion': 'Accounting censor only, never a SOURCE reject',
            'DD': 'Known chronological marked equity; no future price/capital'}},
        'coverage_integrity': 'Empty historical evidence catalog locks zero complete cases. '
            'Unexpected ALLOW is a failed integrity check, not permission to create synthetic historical evidence.',
        'EOF': 'No forced liquidation; unfilled pending separately, OPEN/ambiguous cases censored; CLOSED-only outcome ratios',
        'metrics': ['RAW', 'EVIDENCE_COMPLETE', 'SOURCE_PASS', 'WAIT', 'REJECT', 'ALLOW', 'ORDERS', 'FILLED',
            'CLOSED', 'OPEN_CENSORED', 'WIN', 'LOSS', 'WR', 'Gross', 'Fees', 'Slippage', 'Net', 'PF', 'Expectancy',
            'AvgR', 'medianR', 'AvgWin', 'AvgLoss', 'payoff', 'breakevenWR', 'DD', 'loss_streak', 'holding',
            'direction', 'symbol', 'branch', 'TF', 'year', 'month', 'WAIT_reasons'],
        'empty_sample': 'Counts/P&L/exposure DD zero; WR/PF/expectancy/R/holding ratios null, not zero-performance claims',
        'comparison': 'After primary result only: frozen baseline-C880 cohort re-evaluated by same evidence schema at '
            'legacy READY event with predetermined branch map. Inactive styles source/profile-reject; others WAIT if unannotated. '
            'Do not conflate a rejected exact old style with absence of a later confirmed setup. Aggregate differences not causal attribution.',
        'baseline_branch_projection': BASELINE_BRANCH_MAP,
        'comparison_inputs': {relative(p): checksum(p) for p in comparison_paths},
        'trade_entry_allowed': False, 'LIVE_private_API': 'FORBIDDEN', 'project_overlays': False,
        'preoutcome_dependencies': {relative(p): checksum(p) for p in
            [PROTOCOL, SOURCE_REQUEST] + [ROOT / name for name in CODE]
            + sorted(p for p in PRE.rglob('*') if p.is_file())},
        'all_previous_tests_required': 661, 'result_mutations_after_outcome': 'FORBIDDEN',
        'next_action': 'Commit PRE-OUTCOME first. Then one --run; after result use --resume-existing only.'}
    save(PREREG, config)
    print('PREREGISTRATION_CREATED; market hashes/evidence locked; no real financial result calculated')


def verify_preregistration():
    config = json.loads(PREREG.read_text())
    assert checksum(STRATEGY_MANIFEST) == config['freeze_sha256'] == STRATEGY_SHA
    strategy_resume()
    for section in ('preoutcome_dependencies', 'comparison_inputs', 'strategy_artifacts'):
        for name, digest in config[section].items():
            assert checksum(ROOT / name) == digest, ('Preregistered dependency changed', name)
    # A genuine commit containing exactly these protocol/preregistration bytes is
    # mandatory. Merely preparing uncommitted JSON cannot unlock the first run.
    commit = subprocess.check_output(['git', 'log', '-1', '--format=%H', '--', relative(PREREG)], cwd=ROOT, text=True).strip()
    assert commit, 'PRE-OUTCOME commit required'
    for p in [PREREG, PROTOCOL] + [ROOT / name for name in CODE]:
        assert subprocess.check_output(['git', 'show', f'{commit}:{relative(p)}'], cwd=ROOT) == p.read_bytes()
    subprocess.check_call(['git', 'merge-base', '--is-ancestor', STRATEGY_COMMIT, commit], cwd=ROOT)
    catalog = json.loads((PRE / 'historical_evidence_catalog.json').read_text())
    assert not catalog['historical_source_validated_records']
    assert not catalog['instrument_metadata_records_known_in_historical_interval']
    return config, commit


def baseline_comparison():
    # Deliberately invoked only after the primary monetary metrics are written.
    trades = read_rows(BASE / 'simulation/enabled/shared_trades.jsonl.gz')
    signals = {r['signal_id']: r for s in ('BTCUSDT', 'ETHUSDT') for r in
               read_rows(BASE / 'detection' / s / 'enabled/signals.jsonl.gz')}
    probes = [baseline_probe(signals[t['signal_id']]) for t in trades]
    assert len(probes) == 880
    summary = json.loads((BASE / 'simulation/enabled/shared_summary.json').read_text())
    gross = sum(t['gross_pnl'] + t['slippage_total'] for t in trades)
    fees = sum(t['fees_total'] for t in trades)
    slip = sum(t['slippage_total'] for t in trades)
    net = sum(t['net_pnl'] for t in trades)
    assert abs(gross - fees - slip - net) < 1e-7
    positives = [t['net_pnl'] for t in trades if t['net_pnl'] > 0]
    negatives = [-t['net_pnl'] for t in trades if t['net_pnl'] < 0]
    holding = sorted(t['duration_seconds'] for t in trades)
    r_values = [t['result_R'] for t in trades]
    old = {'READY_signals': len(signals), 'admitted_entries': len(trades),
        'closed': len(trades), 'WIN': len(positives), 'LOSS': len(negatives),
        'win_rate_percent': 100 * len(positives) / len(trades), 'gross_pnl': gross,
        'fees': fees, 'slippage': slip, 'net_pnl': net, 'profit_factor': sum(positives) / sum(negatives),
        'expectancy': net / len(trades), 'average_R': sum(r_values) / len(r_values),
        'average_holding_seconds': sum(holding) / len(holding),
        'median_holding_seconds': (holding[439] + holding[440]) / 2,
        'max_drawdown_fraction': summary['max_drawdown_fraction'],
        'gross_definition': 'Old gross_pnl already includes slippage; added it back once for cost-before Gross'}
    result = {'baseline_C': old, 'baseline880_v1_1_decisions': dict(Counter(p['v1_1_decision'] for p in probes)),
        'baseline880_v1_1_reasons': dict(Counter(p['v1_1_reason'] for p in probes)),
        'new_v1_1_filled_not_in_baseline': 0, 'exact_matched_source_filled_cases': 0,
        'no_matched_causal_effect_estimate': True,
        'gates_not_applied': ['universal_H1_H4_owner', 'mandatory_D1_H4_context_objects', 'old_NO_HTF_CONTEXT',
            'H4_D1_only_FTA', 'old_adverse751_446', 'fitted_68pct_tree', 'AntiScalp_ratio3',
            'canonical40_30_30', 'TP1_BE', 'cost_BE', 'project_totalrisk_daily_correlation_leverage'],
        'comparison_limit': 'Primary result is no evidence-complete trades, not a test of setup profitability. '
            'Inactive legacy styles rejected at that exact event; no claim a new confirmed setup could not form later.'}
    write_csv(RESULT / 'baseline880_source_decisions.csv', probes, list(probes[0]))
    save(RESULT / 'baseline_C_comparison.json', result)
    return result


def compute_result(data):
    candidates, raw = [], []
    for p in all_proposals(data):
        raw.append(p)
        row = inspect_proposal(p)
        if row['SOURCE_STRATEGY_DECISION'] == 'ALLOW':
            raise ValueError('Unexpected source ALLOW with frozen empty real annotation catalog')
        candidates.append(row)
    decisions = Counter(r['SOURCE_STRATEGY_DECISION'] for r in candidates)
    funnel = {'RAW_CANDIDATES': len(raw), 'EVIDENCE_COMPLETE': sum(r['evidence_complete'] for r in candidates),
        'SOURCE_PASS': sum(r['source_pass'] for r in candidates), 'SOURCE_WAIT': decisions['WAIT'],
        'SOURCE_REJECT': decisions['REJECT'], 'SOURCE_ALLOW': decisions['ALLOW'], 'ORDERS': 0, 'FILLED': 0,
        'CLOSED': 0, 'OPEN_CENSORED': 0, 'PENDING_UNFILLED': 0,
        'accounting_state': 'ZERO_EXPOSURE_SOURCE_EVIDENCE_BLOCKED', 'trade_entry_allowed': False}
    assert len(raw) == decisions['WAIT'] + decisions['REJECT'] + decisions['ALLOW']
    wait = Counter(r['status'] for r in candidates if r['SOURCE_STRATEGY_DECISION'] == 'WAIT')
    parallel = Counter(code for r in candidates for code in r['parallel_blockers'])
    required = ('WAIT_NO_AVAILABLE_LOWER_TF', 'WAIT_UNRESOLVED_LIQUIDITY_CONTEXT',
                'WAIT_UNRESOLVED_STOP_GEOMETRY', 'WAIT_BRANCH_CONFLICT', 'WAIT_INTRABAR_ORDER', 'MISSING_QUALITATIVE_EVIDENCE')
    for code in required:
        wait.setdefault(code, 0)
        parallel.setdefault(code, 0)
    curve = [{'timestamp': iso(t), 'equity': float(EQUITY)} for t in (START, END)]
    views = {v: metrics([], curve, v) for v in VIEWS}
    return raw, candidates, funnel, {'exclusive_primary_reasons': dict(wait),
        'overlapping_evidence_blockers': dict(parallel),
        'note': 'Frozen evaluate checks missing tick metadata before qualitative predicates/lower refinement. '
                'Parallel blockers explain hidden gaps; do not add overlapping counts to exclusive WAIT.'}, views, curve


def report_text(funnel, waits, views, comparison, pre_commit):
    primary = views['SHARED_PORTFOLIO']
    old = comparison['baseline_C']
    lines = ['# ORIGINAL v1.1 first financial backtest', '',
        ('Первый frozen result: **ZERO_EXPOSURE_SOURCE_EVIDENCE_BLOCKED**. Это не доказательство нулевого edge: '
        'нет ни одного evidence-complete case. Missing annotation не означает отсутствие setup.'), '',
        f'PRE-OUTCOME commit: `{pre_commit}`. Strategy: `{STRATEGY_COMMIT}`.',
        f'Strategy freeze SHA256: `{STRATEGY_SHA}`.',
        (f'Exact trading interval UTC: {iso(START)} — {iso(END)}. BTCUSDT/ETHUSDT; M15/H1/H4/D1. '
        'Warm-up2022 сохранён отдельно, trading interval не расширен.'), '',
        '## Funnel', '', '| Stage | Count |', '| --- | ---: |']
    lines += [f'| {k} | {v} |' for k, v in funnel.items() if type(v) is int]
    lines += ['', ('RAW count — preregistered OHLC proposals, не число доказанных source setups. '
        'Enumeration не является исчерпывающим detector discretionary patterns; реальные сетапы могли существовать '
        'без annotation или вне этой RAW convention. Максимум реальных source-valid trades не доказан.'), '',
        '## Financial accounting', '', '| Metric | Independent cases | Shared portfolio |', '| --- | ---: | ---: |']
    for k in ('closed', 'WIN', 'LOSS', 'win_rate_percent', 'gross_pnl', 'fees', 'slippage', 'net_pnl',
              'profit_factor', 'expectancy', 'average_R', 'median_R', 'average_win', 'average_loss_magnitude',
              'payoff_ratio', 'breakeven_WR_percent', 'max_drawdown', 'max_loss_streak',
              'average_holding_seconds', 'median_holding_seconds'):
        values = [views[v][k] for v in VIEWS]
        lines.append(f'| {k} | {values[0] if values[0] is not None else "N/A"} | {values[1] if values[1] is not None else "N/A"} |')
    lines += ['', ('PnL/costs и DD равны0 из-за отсутствия экспозиции; WR/PF/R/expectancy/holding N/A из-за пустого '
        'denominator. Капитал1170 USDT; sizing2% accounting normalization, не source rule. '
        'Fees6bps/leg, slippage2bps/leg — заранее объявленные modeled notional debits; ни одна execution leg '
        'не возникла. Funding отсутствует в данных и исключён: это не утверждение funding=0. '
        'Shared chronology/sizing и реальный fill/exit path не были exercised; synthetic unit QA не заменяет их '
        'историческую проверку. Нет investor-ready portfolio или прибыльности стратегии.'), '',
        '## Evidence coverage / WAIT', '',
        ('Нет historical source_validated qualitative annotations и причинной исторической tick metadata. '
        'Первый frozen blocker — WAIT_UNRESOLVED_INSTRUMENT_METADATA. SOURCE predicates после него '
        'NOT_EVALUATED; они не помечены FAIL. Статусы WAIT/REJECT раздельные.'), '',
        'Exclusive primary reasons: `' + compact(waits['exclusive_primary_reasons']) + '`.', '',
        'Overlapping evidence blockers: `' + compact(waits['overlapping_evidence_blockers']) + '`.', '',
        ('Дефициты: meaningful liquidity/smooth approach/whole impulse/range clarity/structural endpoints/'
        'branch confirmation, source POI/stop/FTA/identity. M15 OB/SFP требует strictly-lowerTF, '
        'которого нет в замороженном universe. Не активировали M1/M5 и не изобрели numeric classifiers.'), '',
        '## Baseline C comparison', '', '| Metric | Baseline C | v1.1 shared |', '| --- | ---: | ---: |']
    for k in ('closed', 'win_rate_percent', 'gross_pnl', 'fees', 'slippage', 'net_pnl', 'profit_factor',
              'expectancy', 'average_R', 'max_drawdown_fraction', 'average_holding_seconds', 'median_holding_seconds'):
        lines.append(f'| {k} | {old[k]} | {primary[k] if primary[k] is not None else "N/A"} |')
    lines += ['', f'Baseline READY signals: {old["READY_signals"]}; admitted entries: {old["admitted_entries"]}.', '',
        'Old880 source re-evaluation: `' + compact(comparison['baseline880_v1_1_decisions']) + '`.',
        'Reasons: `' + compact(comparison['baseline880_v1_1_reasons']) + '`.', '',
        ('Новые FILLED, отсутствующие в baseline:0. Matched new fills:0. Inactive direct/aggressive/component '
        'styles отвергнуты именно как old entry branch в executable profile; остальные missing-evidence случаи WAIT. '
        'Это не утверждение, что source запрещает эти inactive alternatives или последующий confirmed setup.'), '',
        ('Baseline Gross восстановлен до costs как old gross_pnl+slippage, чтобы не вычесть slippage дважды. '
        'Состав cohort, admission, exits, accounting и evidence availability различаются. '
        'Без matched fills нельзя приписать различия одному удалённому gate или оценить effect size.'), '',
        'Gates не применялись: `' + compact(comparison['gates_not_applied']) + '`.', '',
        '## Artifacts and QA', '',
        (f'Artifacts: `{relative(RESULT)}`; preregistration: `{relative(PREREG)}`; '
        f'dataset manifest: `{relative(PRE / "dataset_manifest.json")}`. '
        'QA receipts лежат рядом с result и входят в result manifest.'), '',
        ('Funnel/metrics/branch-TF-symbol-direction-year-month breakdowns; all candidates/WAIT/REJECT/ALLOW; '
        'per-candidate source/evidence trace; all-trades CSV и cost ledger с заголовками (пустые); '
        'baseline880 per-case decisions. No optimisation/no new thresholds/no strategy mutations.'), '',
        ('Source v1.1 и более ранние frozen namespaces не менялись. `trade_entry_allowed=false`. '
        'LIVE/private API запрещены. После первого frozen result STOP.')]
    return '\n'.join(lines) + '\n'


def run():
    if RESULT.exists() or SEAL.exists():
        raise ValueError('First result already exists; only --resume-existing permitted')
    _config, pre_commit = verify_preregistration()
    data, dataset = load_market()
    assert dataset == json.loads((PRE / 'dataset_manifest.json').read_text())
    RESULT.mkdir()
    raw, candidates, funnel, waits, views, curve = compute_result(data)
    write_rows(RESULT / 'all_raw_proposals.jsonl.gz', raw)
    write_rows(RESULT / 'all_evidence_and_rule_traces.jsonl.gz', candidates)
    write_csv(RESULT / 'all_candidates.csv', candidates, CANDIDATE_FIELDS)
    for decision, name in [('WAIT', 'all_WAIT'), ('REJECT', 'all_REJECT'), ('ALLOW', 'all_ALLOW')]:
        write_csv(RESULT / f'{name}.csv', [r for r in candidates if r['SOURCE_STRATEGY_DECISION'] == decision], CANDIDATE_FIELDS)
    write_rows(RESULT / 'per_trade_rule_trace.jsonl.gz', [])
    write_csv(RESULT / 'all_trades.csv', [], TRADE_FIELDS)
    write_csv(RESULT / 'intrabar_ambiguous_cases.csv', [], ['candidate_id', 'status', 'known_at', 'trade_entry_allowed'])
    for view in VIEWS:
        write_csv(RESULT / f'cost_ledger_{view}.csv', [], ['candidate_id', 'leg', 'timestamp', 'gross', 'fee', 'slippage', 'net'])
        save(RESULT / f'equity_{view}.json', curve)
    save(RESULT / 'funnel.json', funnel)
    save(RESULT / 'WAIT_breakdown.json', waits)
    save(RESULT / 'metrics.json', views)
    # Primary outcome now recorded. Only now inspect baseline's old financial fields.
    comparison = baseline_comparison()
    groups = defaultdict(list)
    for axis, values in [('symbol', ('BTCUSDT', 'ETHUSDT')), ('direction', ('LONG', 'SHORT')),
                         ('branch', ACTIVE), ('tf', [str(tf) for tf in TFS]),
                         ('year', ['2023', '2024', '2025']),
                         ('month', [f'{year}-{month:02d}' for year in (2023, 2024, 2025) for month in range(1, 13)])]:
        for value in values:
            groups[(axis, value)] = []
    for row in candidates:
        dt = datetime.fromtimestamp(row['decision_at'], UTC)
        for axis, value in [('symbol', row['symbol']), ('direction', row['direction']), ('branch', row['branch']),
                            ('tf', str(row['setup_tf'])), ('year', str(dt.year)), ('month', dt.strftime('%Y-%m'))]:
            groups[(axis, value)].append(row)
    breakdown = []
    for (axis, value), rows in sorted(groups.items()):
        breakdown.append({'axis': axis, 'value': value, 'raw': len(rows),
            'WAIT': sum(r['SOURCE_STRATEGY_DECISION'] == 'WAIT' for r in rows),
            'REJECT': sum(r['SOURCE_STRATEGY_DECISION'] == 'REJECT' for r in rows),
            'ALLOW': 0, 'FILLED': 0, 'CLOSED': 0, 'WIN': 0, 'LOSS': 0,
            'WR': None, 'Gross': 0, 'Fees': 0, 'Slippage': 0, 'Net': 0, 'PF': None, 'AvgR': None})
    write_csv(RESULT / 'breakdowns.csv', breakdown, list(breakdown[0]))
    REPORT.write_text(report_text(funnel, waits, views, comparison, pre_commit), encoding='utf-8')
    save(RESULT / 'run_receipt.json', {'status': 'FIRST_RESULT_COMPUTED_NO_MUTATIONS',
        'PRE_OUTCOME_commit': pre_commit, 'strategy_commit': STRATEGY_COMMIT,
        'preregistration_sha256': checksum(PREREG), 'financial_result_started_after_preoutcome_commit': True,
        'new_evidence_labels_created': False, 'real_execution_paths_exercised': False,
        'trade_entry_allowed': False, 'stop': 'QA/seal this first result; no second strategy/accounting variant'})
    print('FIRST_RESULT', compact(funnel))


def resume():
    _config, _ = verify_preregistration()
    if not SEAL.exists():
        raise ValueError('Result not sealed; preserve incomplete artifacts')
    manifest = json.loads(SEAL.read_text())
    actual = {relative(p): checksum(p) for p in RESULT.rglob('*') if p.is_file()}
    actual[relative(REPORT)] = checksum(REPORT)
    assert actual == manifest['artifacts'], 'Result checksum/membership mismatch'
    assert manifest['preregistration_sha256'] == checksum(PREREG)
    data, dataset = load_market()
    assert dataset == json.loads((PRE / 'dataset_manifest.json').read_text())
    raw, candidates, funnel, waits, views, _ = compute_result(data)
    assert funnel == json.loads((RESULT / 'funnel.json').read_text())
    assert waits == json.loads((RESULT / 'WAIT_breakdown.json').read_text())
    assert views == json.loads((RESULT / 'metrics.json').read_text())
    assert raw == read_rows(RESULT / 'all_raw_proposals.jsonl.gz')
    assert candidates == read_rows(RESULT / 'all_evidence_and_rule_traces.jsonl.gz')
    print('VERIFIED_RESUME_FIRST_RESULT', funnel['RAW_CANDIDATES'], 'proposals; unchanged result/profile/data; no second variant')


def rows_digest(rows):
    digest = sha256()
    for row in rows:
        digest.update((compact(row) + '\n').encode())
    return digest.hexdigest()


def qa():
    """Read-only financial/causal validation; only its additive receipt is written.

    Prefix/future mutations and SHADOW are replays of these exact frozen decisions,
    never second financial variants or new annotations.
    """
    if SEAL.exists() or (RESULT / 'QA_receipt.json').exists():
        raise ValueError('Existing result QA/freeze cannot be rewritten')
    config, pre_commit = verify_preregistration()
    data, dataset = load_market()
    assert dataset == json.loads((PRE / 'dataset_manifest.json').read_text())
    preflight = json.loads((PRE / 'preflight_QA_receipt.json').read_text())
    assert preflight['status'] == 'PASS'
    for check in preflight['checks']:
        assert check['exit_code'] == 0
        assert checksum(ROOT / check['log']) == check['sha256']
    test_log = (PRE / 'qa/full_unittest.log').read_text()
    test_count = int(re.search(r'Ran (\d+) tests?', test_log).group(1))
    assert test_count >= config['all_previous_tests_required'] + 22
    assert re.search(r'^OK$', test_log, re.MULTILINE)
    raw = read_rows(RESULT / 'all_raw_proposals.jsonl.gz')
    traces = read_rows(RESULT / 'all_evidence_and_rule_traces.jsonl.gz')
    funnel = json.loads((RESULT / 'funnel.json').read_text())
    assert len(raw) == len(traces) == funnel['RAW_CANDIDATES']
    assert len({r['candidate_id'] for r in raw}) == len(raw), 'Duplicate RAW IDs'
    assert raw == sorted(raw, key=lambda r: (r['decision_at'], r['symbol'], r['setup_tf']))
    by_series = defaultdict(list)
    for proposal, trace in zip(raw, traces, strict=True):
        bar = proposal['bar']
        assert START <= bar['open_time'] < bar['completed_at'] == bar['known_at'] == proposal['decision_at'] <= END
        assert bar['completed_at'] - bar['open_time'] == proposal['setup_tf'] * 60
        assert not proposal['source_validated'] and proposal['raw_only']
        assert not proposal['trade_entry_allowed'] and not trace['trade_entry_allowed']
        anchor = proposal['anchor']
        if isinstance(anchor, int):
            assert anchor <= bar['open_time']
        elif isinstance(anchor, list):
            assert all(t <= bar['open_time'] for t in anchor)
        else:
            assert int(anchor.rsplit('/', 1)[1]) <= proposal['decision_at']
        assert evidence_case(proposal, {})['facts'] == {}
        assert trace == inspect_proposal(proposal, mode='SHADOW'), 'Historical BACKTEST/SHADOW mismatch'
        by_series[(proposal['symbol'], proposal['setup_tf'])].append(proposal)
    cutoffs = [int(datetime(year, 7, 1, tzinfo=UTC).timestamp()) for year in (2023, 2024, 2025)]
    prefix_checks, future_checks = [], []
    for symbol, frames in data.items():
        for tf, bars in frames.items():
            actual = by_series[(symbol, tf)]
            for cutoff in cutoffs:
                prefix_bars = [b for b in bars if b.end <= cutoff]
                expected = [r for r in actual if r['decision_at'] <= cutoff]
                prefix = list(enumerate_series(symbol, tf, prefix_bars))
                assert prefix == expected, ('Prefix changed', symbol, tf, cutoff)
                prefix_checks.append({'symbol': symbol, 'tf': tf, 'cutoff': iso(cutoff),
                    'raw_count': len(prefix), 'sha256': rows_digest(prefix)})
            cutoff = cutoffs[1]
            mutated = [b if b.end <= cutoff else Bar(b.start, b.end, b.open * 2, b.high * 2, b.low * 2, b.close * 2)
                       for b in bars]
            mutated_prefix = [r for r in enumerate_series(symbol, tf, mutated) if r['decision_at'] <= cutoff]
            expected = [r for r in actual if r['decision_at'] <= cutoff]
            assert mutated_prefix == expected, ('Future mutation changed past', symbol, tf)
            future_checks.append({'symbol': symbol, 'tf': tf, 'cutoff': iso(cutoff),
                'future_bars_mutated': sum(b.end > cutoff for b in bars), 'prefix_sha256': rows_digest(expected)})
    decision_counts = Counter(r['SOURCE_STRATEGY_DECISION'] for r in traces)
    for decision in ('WAIT', 'REJECT', 'ALLOW'):
        assert decision_counts[decision] == funnel['SOURCE_' + decision]
    for name, expected in [('all_candidates', traces)] + [(f'all_{d}', [r for r in traces if r['SOURCE_STRATEGY_DECISION'] == d])
                                                        for d in ('WAIT', 'REJECT', 'ALLOW')]:
        with (RESULT / f'{name}.csv').open(newline='') as stream:
            rows = csv.DictReader(stream)
            count = 0
            for row, trace in zip(rows, expected, strict=True):
                assert row['candidate_id'] == trace['candidate_id']
                assert row['SOURCE_STRATEGY_DECISION'] == trace['SOURCE_STRATEGY_DECISION']
                assert row['status'] == trace['status'] and row['trade_entry_allowed'] == 'False'
                count += 1
            assert count == len(expected)
    assert funnel['SOURCE_ALLOW'] == funnel['ORDERS'] == funnel['FILLED'] == funnel['CLOSED'] == funnel['OPEN_CENSORED'] == 0
    for view, value in json.loads((RESULT / 'metrics.json').read_text()).items():
        curve = json.loads((RESULT / f'equity_{view}.json').read_text())
        assert value == metrics([], curve, view)
        assert value['gross_pnl'] - value['fees'] - value['slippage'] == value['net_pnl'] == 0
        assert all(point['equity'] == float(EQUITY) for point in curve)
    for file in ('all_trades.csv', 'intrabar_ambiguous_cases.csv', *(f'cost_ledger_{v}.csv' for v in VIEWS)):
        with (RESULT / file).open(newline='') as stream:
            assert not list(csv.DictReader(stream)), ('Fabricated execution', file)
    assert read_rows(RESULT / 'per_trade_rule_trace.jsonl.gz') == []
    with (RESULT / 'breakdowns.csv').open(newline='') as stream:
        totals = Counter()
        for row in csv.DictReader(stream):
            totals[row['axis']] += int(row['raw'])
        assert all(count == len(raw) for count in totals.values()) and len(totals) == 6
    with (RESULT / 'baseline880_source_decisions.csv').open(newline='') as stream:
        old = list(csv.DictReader(stream))
        assert len(old) == 880 and len({row['signal_id'] for row in old}) == 880
        assert all(row['trade_entry_allowed'] == 'False' for row in old)
    save(RESULT / 'QA_receipt.json', {'status': 'PASS', 'PRE_OUTCOME_commit': pre_commit,
        'all_previous_and_new_tests': test_count, 'preflight_receipt_sha256': checksum(PRE / 'preflight_QA_receipt.json'),
        'freeze_and_dataset_verification': 'PASS', 'known_at_and_completed_all_proposals': len(raw),
        'BACKTEST_SHADOW_equal_all_proposals': len(raw), 'unique_chronological_RAW_ids': 'PASS',
        'prefix_consistency': prefix_checks, 'future_mutation': future_checks,
        'financial_identity_both_views': 'PASS_ZERO_EXPOSURE_PLUS_SYNTHETIC_COST_TESTS',
        'flat_accounting_and_no_fabricated_fills': 'PASS', 'export_counts_and_grouping': 'PASS',
        'qualitative_annotation_coverage': 'EMPTY_NOT_INFERRED',
        'historical_fills_and_shared_sizing_exercised': False,
        'no_LIVE_private_API': True, 'trade_entry_allowed': False,
        'resume': 'Run --seal then read-only --resume-existing; keep its receipt outside the sealed namespace'})
    print('FIRST_RESULT_QA_PASS', len(raw), 'causal proposals;', test_count, 'tests; 24 real prefixes / 8 future mutations')


def seal():
    if SEAL.exists():
        raise ValueError('Result freeze already exists; never rewrite')
    _, pre_commit = verify_preregistration()
    qa = json.loads((RESULT / 'QA_receipt.json').read_text())
    assert qa['status'] == 'PASS'
    artifacts = {relative(p): checksum(p) for p in RESULT.rglob('*') if p.is_file()}
    artifacts[relative(REPORT)] = checksum(REPORT)
    save(SEAL, {'status': 'FIRST_RESULT_FROZEN', 'registered_at_UTC': datetime.now(UTC).isoformat(),
        'PRE_OUTCOME_commit': pre_commit, 'strategy_commit': STRATEGY_COMMIT,
        'preregistration_sha256': checksum(PREREG), 'strategy_manifest_sha256': STRATEGY_SHA,
        'artifacts': artifacts, 'QA': qa, 'trade_entry_allowed': False,
        'source_profitability_identifiable': False, 'NEXT': 'STOP. Do not optimise or run a second variant.'})
    print('FIRST_RESULT_FROZEN_SHA256', checksum(SEAL))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    for name in ('prepare', 'run', 'qa', 'seal', 'resume-existing'):
        group.add_argument('--' + name, action='store_true')
    args = parser.parse_args()
    if args.prepare:
        prepare()
    elif args.run:
        run()
    elif args.qa:
        qa()
    elif args.seal:
        seal()
    else:
        resume()


if __name__ == '__main__':
    main()
