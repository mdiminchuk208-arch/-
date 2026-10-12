# MACHINE_STRATEGY_v3 implementation readiness

Decision: **V3_IMPLEMENTATION_FROZEN_FINANCIAL_STOP**.

The causal historical adapter and later execution infrastructure are implemented
against the existing frozen design. This is an implementation/evidence freeze,
not a new strategy version or a financial evaluation. No historical v3 execution
outcome was generated or viewed. `trade_entry_allowed=false`; PAPER/LIVE and
private API use remain disabled.

## Implementation and data

`scripts/machine_strategy_v3_historical_adapter.py` loads the pinned BTCUSDT and
ETHUSDT Bybit M15 public mirror, releases completed bars/events causally, derives
complete UTC H1/H4/D1 groups, and implements SFP, OB, Breaker, STB and Range.
It records causal state, POI/FTA/liquidity inventories, formation/confirmation
times, immutable ATR/structural boundaries, order identities, first-test evidence,
reservation and explicit WAIT/REJECT diagnostics. It imports no outcome runner.
`scripts/machine_strategy_v3_guarded_runner.py` provides the frozen order lifecycle,
gap/intrabar/EOF handling and later cash-stop accounting. Readiness tests exercise
only internally registered synthetic event fixtures. Every historical public,
kernel and accounting entry requires a separately authorized phase and committed
READY freeze; arbitrary fixture bytes and forged capabilities are rejected.

Each canonical series contains 137,758 M15 bars from 2022-01-01T00:00Z through
2025-12-05T23:30Z exclusive, including 102,718 development bars from 2023-01-01.
No duplicate or missing M15 bar occurs inside that declared interval. Derived
counts per symbol are 34,439 H1, 8,609 H4 and 1,434 D1. Incomplete last groups
are recorded and excluded; the unavailable final half-hour is not fabricated.
Independent stored H1/H4 and raw aliases are not used to repair/fill this path.
Local content/identity/continuity is verified against frozen source hashes.
This does not assert independent exchange authenticity or historical tick-grid
validity beyond the retained public source provenance.

The exact rule conformance and non-outcome operational clarifications are in
HISTORICAL_ADAPTER_SPEC.json and the four role reviews. No threshold sweep,
historical subgroup selection, direction removal or rule redesign was performed.

## Remaining blockers

`NO_VERIFIED_HISTORICAL_TICK_EPOCHS` and
`HISTORICAL_EXCHANGE_PRICE_GRID_UNVERIFIED` affect **both BTCUSDT and ETHUSDT**
for the entire development interval
**2023-01-01T00:00Z <= time < 2025-12-05T23:30Z** and the preceding 2022 warmup.
Executable verified tick coverage is zero. Dated notices were found and hashed,
including a contemporary ETH archive, but do not establish all epoch boundaries,
pre-effective publication knowledge and unchanged continuity. Unknown intervals
remain UNVERIFIED; current API settings and observed decimals are not backfilled.
See TICK_EPOCHS.json, TICK_EPOCH_EVIDENCE.md and immutable evidence receipts.

OOS remains **STOP_NO_PRISTINE_OOS**. All 92 inventoried series are exposed
development. A 365-day warmup for an illustrative earliest post-freeze UTC day
has explicit local gaps; unauthenticated Bybit gap-acquisition probes returned
HTTP 403 for both symbols. OOS_READINESS.json retains the exact intervals,
procedure and receipts. No OOS signal, position or outcome was generated. Exact
future start/end require a separate append-only registration after the complete
implementation freeze; warmup and metadata prerequisites are not ready yet.

## Verification and use

QA_REPORT.md, QA_RECEIPT.json, CAUSALITY_QA.json, OUTCOME_GUARD_QA.json and qa/
contain executed checks. Historical prefix/full-future/future-OHLC mutation compares
only pre-entry states through the first seven development days, using the entire
declared future index as the adversarial extension. Empty historical tick evidence
prevents any executable order; all-family positive paths are checked on mirrored
synthetic fixtures. This limitation is explicit and is not a positive historical
execution validation claim. Frozen source, baseline, audit and design hashes are
unchanged. Independent review is recorded in INDEPENDENT_REVIEW.md and reviews/.

The manifest pins code, tests, reports, receipts, logs and protected parent inputs.
`--resume-existing` requires its externally pinned SHA-256 and checks membership
and every recorded byte; it does not rerun or overwrite research.
The first financial run is **not authorized or ready**. Later evidence must be
append-only and independently frozen before any such separately authorized run.
