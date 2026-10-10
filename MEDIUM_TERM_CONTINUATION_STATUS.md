# Medium-term + Anti-Scalp continuation

Active user objective: medium-term H1/H4 source setups, H4/D1 context and
mandatory causal pre-entry Anti-Scalp. The stopped V2/70WR search is cancelled.
Do not rerun or select V2 candidates. Main baseline dab8d25 remains unchanged;
work is on medium-term-source-research. All 16,851 main blobs are preserved.

Code checkpoints: c754eb0 causal source engine before P&L, 0b6bd4e equivalent
lazy compiler, 7ef3605 actual H1 setup ownership correction before corrected
P&L. Completed native results + full mode parity + 573 passing tests: eba82ce.
Read MEDIUM_TERM_RESEARCH_PROTOCOL.md, MEDIUM_TERM_COMPILATION_PROTOCOL.md,
MEDIUM_TERM_ROLE_CORRECTION_PROTOCOL.md and MEDIUM_TERM_SOURCE_RECONSTRUCTION.md.

Completed native ten-coin / 40-series / 993,575-bar source detection is in
causal_final/native_bybit_2026. Final corrected executions and annotated READY
are in role_corrected_v2/native_bybit_2026. Do not recompute completed detection.
replay_medium_role_correction.py verifies archived code at 0b6bd4e, current
history hashes and every original artifact, then verifies corrected manifests.
Its --resume-existing reused all native scopes successfully. Preserve all
older/incomplete roots, including validated, role_corrected and causal_final.

Native enabled: 6,721 READY → 2,281 FILLED → 2,270 CLOSED, 11 OPEN independent
cases. Shared: 399 FILLED, 396 CLOSED, 3 OPEN; 153 WIN/243 LOSS; PF 0.8338009;
closed Net -664.2150117 USDT. Shared final NAV 527.0810836 from 1,170;
equity P&L -642.9189164 includes OPEN mark/partial cashflows. These are native
development results, not the requested final 2.93-year primary assessment.

At this checkpoint the primary compiled BTC/ETH detection is RUNNING (parent
101319, workers 101320/101321 in this session). Preserve it; do not launch a
duplicate. Original module code is already loaded in the running processes.
Log: qa/compiled_primary_run.log; output: compiled_primary/bybit_2023_2025.
No assumption that jobs survive a new environment/session. A log is not a
complete reusable segment: require COMPLETE manifest plus exact fingerprints
and artifact membership/checksums. If a process was lost, preserve incomplete
files and investigate; do not fabricate a resume or replace expected hashes.

When primary detection/execution seals, register verified READY reuse with:

```bash
/workspace/crypto-bot-venv/bin/python scripts/replay_medium_role_correction.py --cohort bybit_2023_2025 --prepare-only --resume-existing
```

Commit its frozen preparation before corrected P&L, then run the same command
without --prepare-only. Run verify_medium_artifacts.py for both cohorts and
verify_medium_execution_parity.py --cohort bybit_2023_2025. Native full
BACKTEST/SHADOW parity already passed both arms (1.267M decisions compared).
Generate final_qa_receipt.json only after all primary checks complete, then
run report_medium_term.py with MPLCONFIGDIR=/workspace/.cache/matplotlib.
The full A–M report, ledgers, breakdowns and chart are not yet generated.

Safety: trade_entry_allowed=false; BACKTEST/SHADOW only; no LIVE, private
exchange API, orders or withdrawals. Fees/slip remain 0.0006/0.0002 each leg;
edge_cost_ratio >=3 is the frozen engineering policy. TP40/30/30, structural
levels, canonical SL/risk and cost-adjusted BE remain. Future holding/outcomes
are never gate inputs. Native and primary price provenance remain separate.

Cloud setup draft revision 3 is saved, not published; details and repeatable
installer are in CLOUD_ENVIRONMENT_SETUP.md. Full inherited lint has 555
unchanged findings and zero new findings; do not claim a clean full-tree lint.
