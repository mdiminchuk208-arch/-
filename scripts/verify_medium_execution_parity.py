"""Replay complete shared histories in SHADOW and compare BACKTEST artifacts."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from crypto_bot.strategy.source_medium_term import MediumTermPortfolio
from crypto_bot.strategy.source_pdf_native import evidence_json
from crypto_bot.strategy.virtual_portfolio import SimulationPolicy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_medium_term_research import (
    ROOT,
    deserialize_signal,
    indexed,
    load_data,
    read_rows,
    write_json,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cohort', choices=('bybit_2023_2025', 'native_bybit_2026'), required=True)
    args = parser.parse_args()
    root = ROOT / 'role_corrected_v2' / args.cohort
    lock = json.loads((root / 'run_lock.json').read_text())
    policy, symbols = lock['policy'], lock['symbols']
    results = {}
    clocks = {s: load_data(args.cohort, s, policy)[0][policy['execution_clock']] for s in symbols}
    for arm in ('enabled', 'disabled_cost_gate'):
        base = root / 'simulation' / arm
        coverage = json.loads((base / 'coverage.json').read_text())
        start, end = (datetime.fromisoformat(coverage[k]) for k in ('shared_start', 'shared_end'))
        signals, cancellations, exits = [], [], []
        for s in symbols:
            folder = root / 'detection' / s / arm
            signals.extend(deserialize_signal(r) for r in read_rows(folder / 'signals.jsonl.gz'))
            cancellations.extend(read_rows(folder / 'cancellations.jsonl.gz'))
            exits.extend(read_rows(folder / 'exit_events.jsonl.gz'))
        signals.sort(key=lambda s: (s.known_at, policy['entry_tie_precedence'].index(s.setup_type), -s.htf, s.symbol, s.signal_id))
        ss, cc, ee = indexed(signals), indexed(cancellations), indexed(exits)
        p = MediumTermPortfolio(equity=policy['case_reference_equity'], mode='SHADOW',
                                anti_scalp_enabled=arm == 'enabled',
                                policy=SimulationPolicy(risk_fraction=policy['risk_fraction'],
                                                        fee_fraction=policy['fee_rate'],
                                                        slippage_fraction=policy['slippage_fraction']))
        per_time = {s: {c.close_time: c for c in cs if c.open_time >= start and c.close_time <= end}
                    for s, cs in clocks.items()}
        if ss[start]:
            p.source_step({s: next(c for c in cs if c.close_time == start) for s, cs in clocks.items()},
                          ss[start], cc[start], ee[start])
        for now in sorted(next(iter(per_time.values()))):
            p.source_step({s: rows[now] for s, rows in per_time.items()}, ss[now], cc[now], ee[now])
        for t in p.trades.values():
            t['source_setup'] = p.source_signals[t['signal_id']].setup_type
        observed = {'shared_trades': list(p.trades.values()), 'shared_journal': [asdict(d) for d in p.journal],
                    'shared_equity_curve': p.equity_curve,
                    'admission_anti_scalp_rejections': p.anti_scalp_admission_rejections}
        for name, rows in observed.items():
            saved = read_rows(base / (name+'.jsonl.gz'))
            if evidence_json(rows) != evidence_json(saved):
                raise ValueError('BACKTEST/SHADOW mismatch '+args.cohort+'/'+arm+'/'+name)
        results[arm] = {'status': 'PASS', 'FILLED': len(p.trades),
                        'journal_decisions_compared': len(p.journal),
                        'NAV_rows_compared': len(p.equity_curve), 'trade_entry_allowed': False}
        print('FULL_SHARED_BACKTEST_SHADOW_PARITY', args.cohort, arm, results[arm], flush=True)
    write_json(ROOT / 'qa' / ('full_execution_parity_'+args.cohort+'.json'), results)


if __name__ == '__main__':
    main()
