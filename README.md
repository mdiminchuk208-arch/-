# Crypto Bot / Strategy Engine — current source validation

The full native Bybit replay completed **40 series / 993,575 candles**:
**19,448 physical READY → 16,351 FILLED → 16,333 CLOSED**;
18 OPEN and 118 pending cases remain censored.
The chronological first50 contains **12 WIN / 38 LOSS / 0 BE**:
WinRate 24.00%, PF 0.314118,
Expectancy -11.882466 USDT, Avg R -0.507798, Net PnL -594.123317 USDT.

[Full source report and all50 trades](SOURCE_ALIGNED_BYBIT_50_TRADE_REPORT.md),
[first50 CSV](data/reports/source_permitted_analysis_2026_10_10/first50.csv),
[all physical union cases CSV.gz](data/reports/source_permitted_analysis_2026_10_10/all_physical_union_cases.csv.gz),
[all38 cohort metrics](data/reports/source_permitted_analysis_2026_10_10/cohort_metrics.csv).
These are independent source trade cases with fixed reference1170 USDT / planned risk23.4,
source FTA/Range exits and declared OHLC fees/slippage. 2026 is DEVELOPMENT; funding is unmodeled.
The canonical TP40/30/30, SL and cost-adjusted TP1 breakeven remain frozen.
Only BACKTEST/SHADOW; **trade_entry_allowed=false**; LIVE/private exchange API/orders are prohibited.

All54 SW5/SW9/SW11/SW12/SW22 PDF pages and the ZIP/DOCX sources are retained.
[Source rules and all15 registered paths](SOURCE_PERMITTED_PROTOCOL.md),
[source reconstruction](SOURCE_PERMITTED_RECONSTRUCTION.md),
[causal physical dedup](PHYSICAL_SOURCE_UNION_PROTOCOL.md),
[native SFP lifecycle](SFP_SOURCE_LIFECYCLE_CORRECTION.md),
[bounded execution with exact real parity](BOUNDED_SOURCE_EXECUTION_PROTOCOL.md).
Source modules: `source_permitted.py`, `source_permitted_cases.py`, `source_physical.py`, `source_sfp_lifecycle.py`.

QA:548 tests PASS, compileall PASS, mypy46files PASS, Ruff zero new findings against d466;
full native/source/identity proof, all76,524 cohort case instances, first50 chronological uniqueness,
prefix/future mutation, input SHA/gaps, old artifacts and both exact resumes PASS.
[QA receipts](data/reports/source_permitted_qa_2026_10_10).
The complete detector corpus is sealed separately from complete physical execution;
the interrupted provisional memory aggregation and failed extra-CLOSE verifier log are preserved.
The verifier correction introduced no source, selection, quote, stop, target or PnL change.

```bash
python scripts/run_source_permitted_bybit.py --output data/reports/source_permitted_bybit_2026_10_10 --resume-existing --workers 4
python scripts/run_source_permitted_physical_union.py --source data/reports/source_permitted_bybit_2026_10_10 --output data/reports/source_permitted_physical_bybit_2026_10_10 --resume-existing
```

---

## Preserved earlier README through d46646f

# Crypto Bot / Strategy Engine

Package version: **0.4.20**. Offline Strategy Engine policy: **0.4.21-causal-limit.3**.
The directory/archive name retains `phase1_4_18` for compatibility.

The current project analyzes market structure, structural/range SFPs, causal
HTF→LTF BOS links and source-qualified OTE geometry. It also provides offline
BACKTEST/SHADOW observation and virtual position management.

`trade_entry_allowed=false`. LIVE and PAPER modes are rejected by the replay
interface. No private exchange client, real order adapter or production-site
integration is added.

## Architecture

- `data/`: public Bybit history, CSV storage and coverage/data QA.
- `strategy/market_analysis.py`, `structure.py`, `sfp.py`: causal closed-candle
  market structure, liquidity episodes and SFP formation/invalidation.
- `strategy/range_engine.py`: range creation, midpoint validation, consumed
  boundaries, retirement and range SFPs. Automatic clarity proves ordered swing
  boundaries, midpoint reaction and clean structure; explicit audit overrides remain.
- `strategy/mtf_sfp.py`, `global_opportunity.py`: strictly post-SFP BOS linking,
  invalidation precedence, provenance and opportunity deduplication.
- `strategy/trade_plan.py`, `order_block.py`: OTE and qualified reference
  geometry. Full source certification of automatic OB/POI selection remains blocked.
- `strategy/auto_levels.py`: opt-in experimental closed-candle OB/HTF-gap
  selection with one stop, three opposing POIs, freshness checks and evidence.
- `strategy/replay.py`: immutable as-of snapshots and explained signals.
- `strategy/virtual_portfolio.py`: simulated resting-limit OPEN/touch entries, risk guards,
  TP1/TP2/TP3 (40/30/30) and fee/slippage-adjusted breakeven.
- `scripts/run_strategy_replay.py`: reproducible offline CSV replay, input
  hashes, JSON signal updates, JSONL decisions and output fingerprint.
- `strategy/historical_replay.py`: knowledge-gated index of causal structural
  facts, checked against independent prefix snapshots, including causal Range SFP.
- `scripts/run_historical_portfolio.py`: one $1170 portfolio over a large common
  history period, compounding, trade journal, equity curve, funnel and statistics.

See [STRATEGY_REPLAY.md](STRATEGY_REPLAY.md) for contracts and limitations, and
[AUTO_LEVELS.md](AUTO_LEVELS.md) for automatic-level policies. See
[STRATEGY_ENGINE_WORK_REPORT.md](STRATEGY_ENGINE_WORK_REPORT.md) for measured
baseline, corrections and verification evidence.
The current automatic-level change and its measured evidence are recorded in
[AUTO_LEVELS_WORK_REPORT.md](AUTO_LEVELS_WORK_REPORT.md).
Current blocker investigation and preserved before/after evidence:
[HISTORICAL_BLOCKER_INVESTIGATION.md](HISTORICAL_BLOCKER_INVESTIGATION.md).
Completed real-history pipeline evidence: **40 READY, 7 virtual entries, 7 closed**
across six independently replayed timeframe mappings, with actual LONG/SHORT,
complete rejection funnels and accounting checks. See
[HISTORICAL_PIPELINE_FINAL_REPORT.md](HISTORICAL_PIPELINE_FINAL_REPORT.md) for
the measured results, source-policy qualifications and blocked public-data download.
Earlier historical research remains in [HISTORICAL_PORTFOLIO_REPORT.md](HISTORICAL_PORTFOLIO_REPORT.md).

## Tests

Run from this project directory; no third-party runtime dependencies are needed:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
python -B -m compileall -q src scripts tests
```

## Offline replay

```bash
PYTHONPATH=src python scripts/run_strategy_replay.py \
  --symbols BTCUSDT ETHUSDT --bars 48 --warmup-bars 576 \
  --report-root data/reports/strategy_replay
```

Add `--mode SHADOW` for the same read-only observation and virtual management
policy. The CLI consumes packaged history; it does not connect a current-market
feed. Without caller-qualified stop and three targets, entry stays blocked by default.

Add `--auto-levels` to opt into experimental automatic level selection. Its
manifest records `--min-ob-body-fraction` (default 0.6) and
`--min-engulf-body-ratio` (default 1.0), causal POI/OB evidence and blocking reasons.
Three-candle HTF gaps are experimental POI seeds, not source-certified POIs.
Fewer than three fresh opposing seeds blocks virtual entry. This option cannot
be combined with `--qualified-levels`. No targets are filled in from RR multiples.

## Historical virtual portfolio

```powershell
$env:PYTHONPATH = "src"
py scripts/run_historical_portfolio.py --days 180 --workers 4 --mode BACKTEST --report-root data/reports/my_portfolio_180
py scripts/run_historical_portfolio.py --days max --workers 4 --mode SHADOW --report-root data/reports/my_portfolio_shadow
```

The historical CLI uses all ten preserved symbols by default and the existing
experimental auto-level policy (body 0.6, engulf 1.0). Capital defaults to $1170,
risk 2%, Isolated x3. It performs no network requests. `--days max` uses the full
common available period after warmup; unavailable 365-day coverage fails rather
than substituting data. `--start` and `--end` accept timezone-aware timestamps
for a fixed-start prefix comparison. `--workers` affects speed, not results.

Reports include input and code SHA-256, signals.jsonl, decisions.jsonl,
trades.jsonl, equity_curve.jsonl, summary.json and fingerprint.sha256. No trades
means return/fees zero and win rate, PF, expectancy and R are undefined (`null`).
No positions are forced closed to improve an ending result.

## Preserved policies

Structure uses SOURCE_CONSERVATIVE; recovery remains diagnostic. Production
cross-pair clustering uses exact timestamps. Core source geometry and its risk
skeleton remain distinct from explicit replay experiment parameters.

The virtual portfolio follows the requested 2–5% per-trade risk, at most 6%
aggregate modeled stop risk, configurable daily loss limit, Isolated leverage
up to x5 (default x3), and re-entry score at least 75 after trade completion.
The daily limit stays latched until the next UTC risk day; existing positions
continue to be managed.
Balance pays entry fees immediately. Equity includes open-position P&L; new
admissions use synchronized opening marks and costs already paid, before any
current-bar close outcome. Negative capital after an extreme gap is explicitly
marked BANKRUPT and new admissions remain blocked.

Historical PHASE documents describe earlier stages. Their claims are not a
substitute for current logs and reports under `data/reports/work_audit/`.
## Preserved initial READY root-cause audit

Historical zero-READY diagnosis: see `READY_AUDIT_REPORT.md` and
`data/reports/ready_root_cause/verified_audit/near_ready_charts.html`.
That historical audit used the earlier engine with 353 passing tests, including
nine diagnostic tests. Its original 344-test release and frozen evidence remain
preserved. Subsequent implementation fixes and current results are recorded in
the blocker investigation; current full suite has 409 passing tests.

`RUN_READY_AUDIT.cmd` runs tests and a fresh read-only audit on Windows. It
refuses to overwrite an existing output directory. Source CSV history and the
frozen `historical_portfolio_audit/backtest_max` report are required. No network,
manual review approval or exchange execution is performed.

## Primary PDF source trade cases (2026-10-09)

The actual SW5, SW9, SW11, SW12 and SW22 PDFs are retained with complete text,
page counts and hashes under `data/source_materials/primary_pdf_2026_10_09`.
All 54 pages and diagrams were read. See `SOURCE_PDF_PROTOCOL.md` for primary
SOURCE_RULE citations and choices registered before outcomes. The isolated
`source_pdf_native` policy supersedes the missing-PDF source experiment for this study;
the frozen canonical strategy and all prior scripts/artifacts remain retained.
`SOURCE_PDF_NATIVE_PROTOCOL.md` records the causal native 5m observation timing
correction registered after the first PDF replay and before its own outcomes.

The full native Bybit dataset is 40 series / 993575 candles. Independent
SOURCE_TRADE_CASE_VALIDATION cases use fixed reference risk and chronological
deduplication; separate portfolio and ANY_TF diagnostics are not primary cases.
Only BACKTEST/SHADOW with `trade_entry_allowed=false` is permitted.

```bash
python scripts/run_source_pdf_native_bybit.py --output data/reports/source_pdf_native_bybit_2026_10_09 --resume-existing --workers 4
python scripts/verify_primary_pdfs.py
python scripts/verify_source_pdf_native_evidence.py --input data/reports/source_pdf_native_bybit_2026_10_09 --output /tmp/source_pdf_evidence.json
python scripts/audit_source_pdf_native_execution.py --input data/reports/source_pdf_native_bybit_2026_10_09 --output /tmp/source_pdf_execution.json
python scripts/report_source_pdf_native_bybit.py --input data/reports/source_pdf_native_bybit_2026_10_09 --output /tmp/source_pdf_report.md
python scripts/verify_source_pdf_preservation.py
```

`--resume-existing` verifies exact source/config/code/input/artifact hashes and
does not replay a COMPLETE result. Changed policy or incomplete/corrupt outputs
fail closed and require a fresh retained output root. Historical versions need
their original source context, never replacement expected hashes. Final results,
all trades and comparison with fc61f35/74a6f8d are in
`SOURCE_ALIGNED_BYBIT_50_TRADE_REPORT.md`; current QA is under
`data/reports/source_pdf_native_qa_2026_10_09`. The completed primary-PDF replay
produces **9 unique READY / 0 FILLED / 0 CLOSED**; all nine limits were independently
traced through their real 5m active intervals to cancellation. This already inspected 2026 dataset is
DEVELOPMENT; the registered machine maximum is not an exhaustive discretionary
source maximum or an edge/LIVE-readiness verdict.

