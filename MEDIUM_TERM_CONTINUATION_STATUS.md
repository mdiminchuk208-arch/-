# Medium-term + Anti-Scalp — completed state

Active objective is completed: medium-term H1/H4 source setups, H4/D1 context
and mandatory causal pre-entry Anti-Scalp. The stopped V2/70WR search remains
cancelled. Do not rerun or select V2 candidates. Work is on
medium-term-source-research; main baseline dab8d254aaf4babc07659e3d03d14b269445767b
and all 16,851 main blobs remain unchanged. No automatic main merge.

Model checkpoints: c754eb0 causal source engine before P&L; 0b6bd4e equivalent
lazy compiler; 7ef3605 actual H1 setup ownership correction before corrected
P&L; 78bf462 verified complete primary READY preparation before corrected P&L.
Complete executions and delivery QA: e05bc2c1def8b6b8f252e3747446f83cbf4a4cbd.
The final report artifact commit is the latest descendant of this checkpoint.
Read MEDIUM_TERM_BYBIT_REPORT.md (A–M), MEDIUM_TERM_RESEARCH_PROTOCOL.md,
MEDIUM_TERM_COMPILATION_PROTOCOL.md, MEDIUM_TERM_ROLE_CORRECTION_PROTOCOL.md,
and MEDIUM_TERM_SOURCE_RECONSTRUCTION.md. Do not tune thresholds from results.

## Completed primary history

BTC/ETH pinned Bybit mirror; 2022 is causal warmup. Entries cover
2023-01-01..2025-12-05 23:30 UTC, about 2.93 years. Normalized H1/H4 and complete
UTC D1 use real complete M15 aggregates; native comparison/provenance limits
remain recorded. No fabricated M5, interpolation or exchange mixing.

Final root: data/reports/medium_term_2026_10_10/role_corrected_v2/bybit_2023_2025.
Enabled independent: 6,760 READY → 2,352 FILLED → 2,352 CLOSED, zero OPEN;
818 WIN/1,534 LOSS; WR 34.7789%, PF 0.7764113; Net -7,152.2197671 USDT.
Enabled shared: 880 FILLED/CLOSED, zero OPEN; 338 WIN/542 LOSS; WR 38.4091%,
PF 0.7422048; expectancy -1.2283031 USDT; Avg R -0.1299293;
Gross -231.8389481 - Fees 636.8008335 - Slippage 212.2669352
= Net -1,080.9067168 USDT. NAV 89.0932832 from 1,170; max drawdown 93.2981%;
longest loss streak 11; daily-NAV Sharpe -1.7345148, Sortino -2.4250984.
These are development backtests, not OOS confirmation or LIVE authorization.

Shared holding mean/median 25.0048/9.5h, p25 2.5h, p75 25.3125h,
p90 59.275h, min 0.25h, max 577.75h. Independent mean/median 164.1327/9.25h,
max 10,314.25h; rare cases longer than a year remain. Holding is an OHLC upper
bound, used only for outcome reporting. Funding/liquidation are not modeled;
independent sums are not account NAV. No timer or retrospective duration gate.

Cost gate OFF retains mandatory medium setup/context and canonical risk.
OFF: 6,796 READY → 2,351 independent FILLED/CLOSED; shared 880 FILLED/CLOSED,
shared Net -1,083.5258484 USDT. Cost gate reduced READY by 36, left shared
trade count unchanged, and changed independent count by +1 through causal
path selection. Never interpret it as deleting trades after outcomes.

Anti-Scalp: 10,716 logged path/reason decisions; 4,743 physical ideas with a
rejection; 3,817 unique rejected ideas never reached READY. Exclusive final
reasons: NO_HTF_CONTEXT 3,680; TARGET_TOO_CLOSE 67; POOR_EDGE_COST_RATIO 70.
Logged path counts: 9,659 / 366 / 691 respectively. Shared admission rejections
are zero. Common HTF/source guards remain active in both arms.
Old pre-entry overlay rejects 6,381 of 7,675 old <1h cases, without using future
holding in the gate. Filtered old source-valid losses are not relabeled false
positives. Full holding bins/costs/IDs are in the report and statistics JSON.

## Completed native comparison

Ten coins / 40 series / 993,575 bars; development comparison, not OOS.
Original complete detector: causal_final/native_bybit_2026. Final annotated
READY and corrected executions: role_corrected_v2/native_bybit_2026.
Enabled: 6,721 READY → 2,281 independent FILLED → 2,270 CLOSED, 11 OPEN.
Shared: 399 FILLED, 396 CLOSED, 3 OPEN; 153 WIN/243 LOSS; PF 0.8338009;
closed Net -664.2150117 USDT. NAV 527.0810836 from 1,170; its P&L includes
OPEN marks/partial cashflows. Never force an EOF close or merge case budgets.

## Reuse and artifacts

Both cohorts and both arms are COMPLETE; no research process is pending.
Do not recompute completed detection or regenerate the sealed final report.
Use /workspace/crypto-bot-venv/bin/python with these verification-only resumes:

```bash
/workspace/crypto-bot-venv/bin/python scripts/replay_medium_role_correction.py --cohort bybit_2023_2025 --resume-existing
/workspace/crypto-bot-venv/bin/python scripts/replay_medium_role_correction.py --cohort native_bybit_2026 --resume-existing
/workspace/crypto-bot-venv/bin/python scripts/verify_medium_artifacts.py
```

The replay wrapper validates original code at 0b6bd4e, current history hashes,
every original manifest/artifact, current correction dependencies and complete
execution membership/checksums. Do not replace expected hashes or invoke the
current original runner against an archived lock to bypass a mismatch.

All files are under data/reports/medium_term_2026_10_10. analysis contains eight
full FILLED ledgers (OPEN retained), two first50 chronological CLOSED ledgers,
nine holding/calendar/side/coin/setup/TF CSV breakdowns, statistics JSON,
standalone SVG/PNG and a COMPLETE checksum manifest. UTC audit timestamps are
preserved; human CSV timestamps include Asia/Yekaterinburg (+05). Year/month/day
groups use UTC entry_interval_start. Full source proofs, journal, fills, NAV,
admission blocks, lifecycle and structural exit events remain available.
Preserve every older/incomplete/control root, including validated,
role_corrected, causal_final, compiled_primary and native_completed exports.
Initial fontcache-warning log/figures and failed QA probes are also preserved.

## QA and environment

Full unittest: 573 PASS, zero failed/skipped; targeted medium: 17 PASS;
compile PASS; mypy all 53 source files PASS. Changed-file lint PASS; full lint
has 555 exactly inherited findings, zero new. Prefix/future-mutation/compiler
parity, all 16,851 baseline blobs, 3,569,825 known timestamps, cost identities,
all complete manifests and both full BACKTEST/SHADOW paired histories PASS.
Final CSV roles/costs/ratios/timezones/first50 and renderer byte determinism PASS.
Receipts: qa/final_qa_receipt.json and qa/export_delivery_receipt.json.

Safety remains trade_entry_allowed=false; only BACKTEST/SHADOW. No LIVE,
private exchange API, real orders or withdrawals. Fees/slip stay 0.0006/0.0002
per leg; edge_cost_ratio >=3 is engineering policy frozen before outcomes.
TP40/30/30, structural levels, canonical risk and cost-adjusted BE remain.
Future holding/results never enter pre-entry gates. Native/primary provenance
stays separate; complete history is used, not the best first50 subset.

Cloud setup draft revision 4 is saved and read back, not published. Its scripts
and PIP_CACHE_DIR, MPLCONFIGDIR, XDG_CACHE_HOME requirements are verified;
repository membership, network and secret requirements are preserved. Review
and save the draft in environment settings, then publish for future launches.
See CLOUD_ENVIRONMENT_SETUP.md. No running-job survival or fresh-task restoration
is assumed. Do not automatically restart cancelled or expensive research.
