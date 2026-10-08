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

