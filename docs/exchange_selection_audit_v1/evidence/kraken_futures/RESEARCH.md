# Kraken Futures public venue evidence

`PF_XBTUSD` and `PF_ETHUSD` are tradeable USD-quoted `flexible_futures` perpetual products in the current instrument response. `PI_XBTUSD`/`PI_ETHUSD` are separate inverse contracts and must not be merged (`instruments`). The PF products support multi-collateral margin; isolated/cross leverage preferences are documented (`docs_leverage`). Settlement and account collateral are account dependent, so no USDT-linear equivalence is claimed.

Actual native 15-minute trade candles were retrieved for both products on 2024-10-13 and again near current time (`m15_*_old`, `m15_*_now`). Both mark-price old sentinels also succeeded (`chart_mark_*_old`). This proves a bounded two-year sentinel, not full continuity or historical tick epochs. The official historical-data guide identifies the Futures charts/history endpoints (`docs_general_history`). Current OI is in public tickers; historical OI and public archived books are unverified (`ticker_*`).

The public Kraken fee page says Futures Tier 1 maker **0.02%**, taker **0.05%**; higher tiers and region/account conditions are separate (`fees_page`). No API-specific exception was found. The deprecated Futures fee schedule endpoint warns that actual charged fees require authenticated Spot GetTradeVolume (`docs_fee_schedule`). No private endpoint was used.

Historical funding returned 8,919 ascending hourly entries per product, from 2025-10-06 to 2026-10-13 (`funding_v3_*`, `docs_openapi`). Funding is kept separate from trade fees; formula/sign and surcharge are not claimed without a current product-specific source.

`FACTS.json` retains three books per symbol with quantities multiplied by the current PF `contractSize=1`; instruments identify BTC/ETH base and USD quote (`instruments`, `docs_orderbook_new`). The API docs describe orderbook values as prices and sizes but do not explicitly name the PF size currency, so the base-unit interpretation should be reviewed before a hard liquidity score. Send-order docs confirm reduce-only, stop/take-profit and client IDs; the Derivatives guide confirms separate General API and Withdrawal API permissions (`docs_send_order`, `docs_futures_intro_new`). All source URLs, UTC times, statuses and hashes are in `SOURCE_INDEX.json`.

Official document excerpts:

- `fees_page`: `Tier 1 < $5M $0+ N/A 0.02% 0.05% 0.4% 0.8%` under Futures Maker and Taker columns; the same section says: `For Canada, US, and New Zealand customers, futures are not available or do not apply to cross-platform tier qualification.`
- `docs_futures_intro_new`: `General API: No Access / Read Only / Full Access (excludes withdrawals)` and `Withdrawal API: No Access / Full Access (controls withdrawal permissions)`.
- `docs_leverage`: `Sets a contract’s margin mode, either “isolated” or “cross” margin. When specifying a max leverage, the contract’s margin mode will be isolated.`
- `docs_send_order`: `Set as true if you wish the order to only reduce an existing position. Any order which increases an existing position will be rejected. Default false.` It also documents `stp`, `take_profit`, `trailing_stop` and globally unique `cliOrdId`.
- `docs_futures_limits`: `Public endpoints do not have a cost and therefore do not count against any rate limiting budget. For /derivatives endpoints, clients can spend up to 500 every 10 seconds.`
- `docs_openapi`: `The contract size of the Futures.` for `contractSize`, and `A structure containing lists with bid and ask prices and sizes.` for order books. Neither excerpt explicitly states PF book size denomination; this is why the conversion remains marked contingent.
