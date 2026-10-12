# Historical market-metadata recovery

Primary decision: **V3_MARKET_METADATA_FROZEN_FINANCIAL_STOP**.

Both BTCUSDT and ETHUSDT remain UNVERIFIED for the entire exact scope:
2022-01-01T00:00:00Z <= time < 2025-12-05T23:30:00Z. Verified warmup and
development coverage are separately **0%** for each symbol. No shorter fully
proven executable interval was found. Partial leads do not authorize dropping
periods or running a financial backtest.

## Recovered evidence and limits

117 public response receipts and 14 selected source leads are retained with raw
byte hashes, URLs, chronology and explicit proof limits. Search covered official
notices and indexes, official documentation Git history, Internet Archive/Arquivo
API and announcement variants, Common Crawl, CCXT fixtures and third-party
instrument metadata. Failed/empty/bounded searches are not absence or unchanged-
continuity proof. The reproducible query inventory records access limits.

The official ETH/BTC Open Graph publication fields explicitly contain UTC `Z`:
ETH 2023-01-06T07:03:06.000Z and BTC 2023-02-07T11:02:47.000Z. This closes the
timezone ambiguity of those issuer date fields, not independent pre-effective
availability. ETH's immutable archive capture is 2023-02-05, after its advertised
2023-01-17T08:00Z change. BTC's notice lacks a contemporaneous independent capture.
Title, advertised publication/effective time, archive time and retrieval stay
separate. None supplies complete actual application and interval continuity.

Immutable CCXT Bybit fixtures in October/November 2023 contain exact
LinearPerpetual/USDT instrument identities and `priceFilter.tickSize` values
BTCUSDT 0.10 and ETHUSDT 0.01. They corroborate a later setting but provide no
explicit exchange-response capture timestamp or guarantee of interval continuity.
Git author/committer times are not substituted for exchange capture/effective time.
Official documentation examples can remain stale: a late-2023 document still
contains BTC 0.50 with an early-2023 embedded example timestamp. Treating revision
dates as active production settings creates a false cross-source conflict.

Tardis documents historical `priceIncrement` changes as best-effort/incomplete;
instrument access returned HTTP 401. Its public exchange catalog lists symbol
availability, not a complete filter history. An archived official production API
URL returned HTTP 200 with `retCode=10001`, `Illegal category` and an empty list;
HTTP success therefore supplies no instrument tick. Current Bybit queries returned
HTTP 403. Archive misses/errors and documentation examples are not promoted.

## Price-grid consistency

Exact integer-ratio checks of immutable raw OHLC detect conditional conflicts
with the naive notice-based old-grid-until-advertised-time assumption:

- BTC: one bar at 2023-02-10T07:45Z, one cell outside the 0.5 grid.
- ETH: four bars at 2023-01-17T07:00Z through 07:45Z, six cells outside 0.05.

Those values are identical in raw mirror aliases; normalization did not create
them. They cannot prove an earlier actual tick change, justify shifting the
advertised boundary or authorize rounding historical prices. Post-notice alignment
also cannot create an epoch. PRICE_GRID_COMPATIBILITY.json and
CROSS_SOURCE_CONTRADICTIONS.json retain exact rows, assumptions and source context.
No VERIFIED epoch exists against which historical exchange compatibility can pass.

## Prospective alternative

A separately registered public-only collector can archive instruments-info raw
responses, request/response/server timestamps, exact symbol/contract/filter fields
and independently timestamped hashes alongside official change/application proof.
It must preserve uncertain intervals between captures; repeated equal snapshots
alone do not prove no intrainterval change. Current public access is not ready.
This is an assessment, not an activated collector, OOS registration or validation-
protocol change. No signal, position, PAPER/LIVE or private API is authorized.

## Verification and disposition

Source hashes, chronological separation, exact coverage and deterministic rebuild
are checked; 11 generated artifacts replay byte-for-byte. QA_REPORT.md documents
1,062 tests passing under their declared phase fixtures, 28 new metadata
tests, and the retained direct-current-phase inherited failures. Frozen strategy,
adapter, runner and all predecessors remain unchanged. Final independent review
must affirm this evidence-freeze STOP before sealing. Required six role functions
were performed by four actual cloud agents, including procedural and final
independent reviewers; shared audit roles and the failed
native ECC model-auth attempt are disclosed in INDEPENDENT_REVIEW.md.

The financial authorization gate may **not** open. Even a later affirmative
metadata gate would need separate explicit financial authorization. Current OOS
STOP and `trade_entry_allowed=false` remain unchanged. No historical v3 financial
outcomes were generated or viewed in this gate.
