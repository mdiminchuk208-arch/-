# Historical instrument metadata recovery v2 — Stage A STOP

Gate A FAIL. `STOP_REASON=NO_VERIFIED_HISTORICAL_INSTRUMENT_METADATA`. `metadata_verified_periods=0`.
`SECOND_FINANCIAL_BACKTEST_RAN=FALSE`. `trade_entry_allowed=false`.

Scope: BTCUSDT / ETHUSDT, Bybit mainnet linear USDT perpetual, 2023-01-01 00:00 UTC through
2025-12-05 23:30 UTC inclusive. The interval map is half-open `[1672531200,1764977401)`;
full metadata is UNKNOWN for both symbols. Individual source observations are retained separately.

## Recovered primary public evidence

Official Bybit docs full Git clone: 3678 reachable commits,
HEAD `59e3d457dea6b419a14987c19a3aabf4ffb38238`. Official instrument document history: 96 non-merge changes;
full filter diffs and V5 changelog retained. Five full immutable document versions: pre-2023,
end-2023, end-2024, requested end, current. Official pybit clone: 713
commits, HEAD `70fef73cb6e55305c77a2e585706f3706a7d1d1a`; no filter/effective-date snapshot found in SDK history.
SDK code/tests were not executed.

Documentation examples include ETHUSDT linear tick 0.05 / qty step 0.01 / min qty 0.01 in December 2022,
BTCUSDT linear tick 0.50 / qty step 0.001 / min qty 0.001 in the 2023 version, then BTC tick 0.10.
Commit `208e13bc0447b0d520593b6872d025264d0a93ae` (2024-02-06) changes the BTC sample tick 0.50→0.10.
That is a documentation edit date, not the exchange parameter effective date.
Saved requests include testnet hosts; examples/server time/launchTime do not prove mainnet historical applicability.
No value is backdated from a current API or candle digits.

The public announcement frontend is reachable. Its ordinary public search endpoint/schema was read from
saved frontend JS; no credentials, cookies, market-API aliases or proxy bypass were used.
Six parameter queries retrieve 154 unique indexed hits. All 145 tick-size hits
were retrieved across 3 pages. Five minimum-order-quantity and four trading-parameter hits were also retained;
quantity-step, minimum-order-size, and order-quantity-perpetual queries return zero hits.
All 72 selected historical derivative parameter notices were fetched and their complete
literal content inspected. Selection is retrieval triage, not a strategy filter; no lower date bound.
Two exact symbol matches provide partial tick-change evidence:

| Symbol | Tick change stated | Title date | Body date stated | Official primary reference |
| --- | --- | --- | --- | --- |
| ETHUSDT | 0.05 → 0.01 | 2023-01-06 | 2023-01-17 08:00:00 UTC | [Changes To Tick Size for ETHUSDT & ETH-PERP Perpetual Contracts (Jan 6, 2023)](https://announcements.bybit.com/en/article/changes-to-tick-size-for-ethusdt-eth-perp-perpetual-contracts-2023-01-06--bltb4b6d3ffa3c5206c/) |
| BTCUSDT | 0.5 → 0.1 | 2023-02-08 | 2023-02-10 08:00:00 UTC | [Changes to Tick Size for USDT & USDC Perpetual Contracts (2023-02-08)](https://announcements.bybit.com/en/article/changes-to-tick-size-for-usdt-usdc-perpetual-contracts-2023-02-08--blt80c14139bdd327bc/) |

The current titles and bodies disagree on dates. Both versions are retained explicitly; no silent date resolver.
A 2024 notice contains NEIROETHUSDT, which is not ETHUSDT and is excluded as an exact-symbol match.
The date on a current mutable announcement page does not prove when its present body was historically known.
No original publication snapshot/version history or confirmation of actual implementation was recovered.
These notices support announced partial changes, not complete VERIFIED instrument intervals.

The linked official 2024-12-27 price-limit announcement is retained in full. It concerns priceLimitRatioX/Y
and trading price limits, not historical tick/qty/minimum/precision interval coverage.
Public instruments GETs for both symbols and the public announcements index return upstream CloudFront
HTTP 403 (geographic restriction). The announcement website/search are separately reachable.
The public web.archive.org CDX attempt is blocked at proxy CONNECT (403 / curl exit 56).
Access restrictions were not bypassed.

## Why Gate A fails

Required tuple: tick_size, price_precision, qty_step, quantity_precision, minimum_qty, contract_type,
linear_perpetual identity, base_asset, quote_asset, effective_from/effective_to. No recovered source proves
this entire tuple on a non-trivial historical interval, together with applicable historical known time.
Tick changes alone do not supply qty step/minimum/precision applicability. Present values cannot fill gaps.
A complete search of this current index cannot prove that deleted/unindexed changes never occurred;
absence of another change notice is not unchanged-period proof.

Repo field/path search, historical manifests, immutable project copies, client/models and synthetic fixtures
supply no authoritative historical instrument snapshot. Searches project paths/hashes only, never monetary
outcomes or legacy SOURCE truth. Negative findings are scoped to these saved/reachable sources; this is not
proof that suitable metadata does not exist elsewhere.

The next required input is authoritative production snapshots or a complete effective-dated parameter record
proving all required fields and known/applicable periods. A partial interval is acceptable when fully proven;
no minimum arbitrary duration, no current-value interpolation, no assumption of unchanged filters.

## Preserved evidence state and STOP boundary

Stage B/C/D/E/F/G/H were not run after Gate A failed. No annotation unit map, Evidence v3 freeze,
second financial preregistration or financial result is created. Annotation units: NOT_RUN, not a measured zero.
The four counts below are inherited unchanged from the frozen v2 funnel, not a new completion run:
RAW 176365; QUALITATIVE_REQUIRED 131099; remaining UNKNOWN partition 45266;
EVIDENCE_COMPLETE 0 / SOURCE_DECISION_READY (SOURCE ALLOW) 0. All 176365 retain critical metadata UNKNOWN.
Necessary objective primitives passing is not complete SOURCE validity. Blocker breakdown remains in
STAGE_A_STOP_STATUS.json with explicit inherited provenance. Old880 is not re-evaluated; prior frozen
102 inactive / 3 qualitative-required / 775 unknown remain preserved, without outcome diagnostics.

Strategy v1/v1.1, U1–U6, N11, active branches, M15/H1/H4/D1, FIRST_TEST_ONLY, stop/FTA/WAIT semantics,
v2 adapter, first result, baseline and audit are unchanged. This recovery namespace is not Evidence v3.
No financial history run, P&L computation, execution, LIVE/private API or production integration.
