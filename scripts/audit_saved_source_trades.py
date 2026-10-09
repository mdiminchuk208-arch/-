"""Inventory real-history closed trade artifacts without certifying missing sources.

Keep overlapping windows, independent accounts and experimental exits separate.
Execution reasons explain recorded PnL; missing methodology evidence cannot
establish whether the underlying discretionary strategy would have lost.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime
import gzip
from hashlib import sha256
import json
from pathlib import Path


def rows(path):
    with (gzip.open(path, 'rt') if path.suffix == '.gz' else path.open()) as reader:
        for line in reader:
            if line.strip():
                yield json.loads(line)


def classify(trade, signal):
    # These classifications use only the retained conservative-TF description.
    # They never certify original-material compliance from caller assertions.
    if trade['ltf'] > 15:
        return ('FALSE_POSITIVE_IMPLEMENTATION',
                'OUTSIDE_RETAINED_CONSERVATIVE_LTF_1_TO_15_MINUTES',
                'SOURCE_CONSERVATIVE_ENTRY_CLAIM_ONLY')
    return ('UNCERTAIN_SOURCE', 'ORIGINAL_MATERIALS_AND_CAUSAL_CONTEXT_NOT_PROVEN',
            'ORIGINAL_METHODOLOGY_COMPLIANCE')


def source_folder(repo, folder, summary):
    if isinstance(summary.get('source'), str):
        return repo / summary['source']
    relative = folder.relative_to(repo).parts
    if 'execution_sensitivity' in relative:
        i = relative.index('execution_sensitivity')
        return repo / 'data/reports/robustness_research/canonical' / relative[i + 1] / folder.name
    return folder


def audit(repo, output):
    repo = repo.resolve()
    output = output.resolve()
    if output.exists():
        raise ValueError('Use a fresh audit output directory')
    evidence = []
    excluded = []
    requests = defaultdict(list)
    for path in sorted((repo / 'data/reports').rglob('trades.jsonl*')):
        relative = path.relative_to(repo).as_posix()
        if 'constructed' in path.parts:
            excluded.append(relative)
            continue
        # Runtime reconstructions live outside data/reports and are not studies.
        closed = [row for row in rows(path) if row.get('status') == 'CLOSED']
        if not closed:
            continue
        summary_path = path.parent / 'summary.json'
        summary = json.loads(summary_path.read_text()) if summary_path.exists() else {}
        source = source_folder(repo, path.parent, summary)
        blob_hash = sha256(path.read_bytes()).hexdigest()
        for index, trade in enumerate(closed):
            record = dict(artifact=relative, artifact_sha256=blob_hash,
                          closed_record_index=index, trade=trade,
                          source_folder=source.relative_to(repo).as_posix(),
                          cohort=summary.get('cohort', 'BYBIT_2026_DEVELOPMENT'),
                          variant=summary.get('variant', summary.get('scenario', 'SAVED_BASELINE')),
                          window=summary.get('window'),
                          primary_development=(
                              'historical_blocker_investigation/stage3/' in relative))
            evidence.append(record)
            requests[source].append(record)
    for folder, records in requests.items():
        candidates = [folder / 'signals.jsonl', folder / 'signals.jsonl.gz']
        path = next((p for p in candidates if p.exists()), None)
        if path is None:
            continue
        wanted = defaultdict(list)
        for record in records:
            wanted[record['trade']['signal_id']].append(record)
        for signal in rows(path):
            for record in wanted.get(signal['signal_id'], ()):
                cutoff = datetime.fromisoformat(record['trade']['entry_interval_start'])
                known = datetime.fromisoformat(signal['event_time'])
                previous = record.get('signal')
                if known <= cutoff and (previous is None or known > datetime.fromisoformat(previous['event_time'])):
                    record['signal'] = signal
        for record in records:
            record['signal_artifact'] = path.relative_to(repo).as_posix()
    counts = Counter()
    groups = defaultdict(Counter)
    primary = []
    output.mkdir(parents=True)
    with (output / 'closed_trade_source_audit.jsonl').open('w') as writer:
        for record in evidence:
            trade = record['trade']
            signal = record.pop('signal', {})
            category, reason, scope = classify(trade, signal)
            outcome = 'WIN' if trade['net_pnl'] > 1e-9 else 'LOSS' if trade['net_pnl'] < -1e-9 else 'BE'
            fills = trade['fills']
            assert abs(sum(fill['net_pnl'] for fill in fills) - trade['net_pnl']) < 1e-7
            assert abs(trade['gross_pnl'] - trade['fees_total'] - trade['net_pnl']) < 1e-7
            context = {name: 'UNKNOWN / INSUFFICIENT EVIDENCE' for name in (
                'htf_trend', 'active_order_flow', 'liquidity_against_setup',
                'conf_new_structure', 'source_poi_type', 'source_poi_freshness',
                'ob_first_repeated_test', 'premium_discount', 'source_fta',
                'source_stop_validity', 'setup_specific_source_exit')}
            context.update(sfp_time=signal.get('sfp_time', 'UNKNOWN'),
                           bos_time=signal.get('bos_time', 'UNKNOWN'),
                           entry_zone=trade.get('entry_zone'),
                           entry=trade['actual_entry_after_slippage'],
                           stop=trade['stop'], targets=trade['targets'],
                           software_level_policy=signal.get('level_policy', 'UNKNOWN'),
                           software_level_evidence=signal.get('level_evidence', []),
                           source_attestation=signal.get('source_qualification_evidence', []))
            record.update(classification=category, classification_reason=reason,
                          classification_scope=scope, original_materials_reverified=False,
                          outcome=outcome, context=context,
                          actual_exit_reasons=[f['reason'] for f in fills],
                          realized_gross_pnl=trade['gross_pnl'], fees=trade['fees_total'],
                          slippage_cost=trade.get('slippage_total'), net_pnl=trade['net_pnl'],
                          causal_loss_explanation=(
                              'Recorded adverse-price stop exits and fees produced the recorded loss; '
                              'this does not prove methodology-valid entry or causal source-rule failure.'
                              if outcome == 'LOSS' else 'Recorded fills reconcile gross PnL and fees.'),
                          trade_entry_allowed=False)
            writer.write(json.dumps(record, sort_keys=True) + '\n')
            counts[category] += 1
            groups[f"{record['cohort']}:{record['variant']}:{trade['htf']}/{trade['ltf']}"][category] += 1
            if record['primary_development']:
                primary.append({key: record[key] for key in (
                    'artifact', 'trade', 'classification', 'classification_reason',
                    'classification_scope', 'outcome', 'net_pnl', 'context')})
    receipt = dict(closed_artifact_instances=len(evidence), files_with_closed=len({r['artifact'] for r in evidence}),
                   classifications=dict(counts), groups={k: dict(v) for k, v in groups.items()},
                   primary_development=primary, excluded_constructed_artifacts=excluded,
                   counts_are_not_independent_trades=True,
                   windows_and_capitals_not_pooled=True,
                   source_valid_wins_proven=0, source_valid_losses_proven=0,
                   false_negative_count=None,
                   false_negative_status='UNDETERMINED_WITHOUT_ORIGINALS_AND_SOURCE_COMPLETE_DETECTORS',
                   trade_entry_allowed=False)
    (output / 'source_trade_audit_receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print('Audited real-history closed artifact instances:', len(evidence))
    print('Primary development classifications:', dict(Counter(r['classification'] for r in primary)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    audit(Path(__file__).resolve().parents[1], args.output)
