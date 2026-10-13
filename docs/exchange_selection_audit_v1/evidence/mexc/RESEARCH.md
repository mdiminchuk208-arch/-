# MEXC public venue evidence

BTC_USDT and ETH_USDT are USDT-settled perpetuals with `apiAllowed=true`, current exact price units 0.1 and 0.01, and contract sizes 0.0001 BTC and 0.01 ETH respectively (`instrument_btc`, `instrument_eth`). The API docs say depth quantity is contracts (`docs_api`), so `FACTS.json` multiplies book quantity by these exact contract sizes.

Current and January/May 2026 native Min15 probes returned actual candles. Both 2024-10-13 probes and both 2025-10-13 probes returned empty arrays (`m15_*_old`, `m15_*_2025`); the two-year research history gate is unverified. The docs specify start/end seconds and a 2000-row request maximum (`docs_api`).

Current public instrument fields show makerFeeRate=0 and takerFeeRate=0.0002. These are **not** entered as ordinary bot API fees: the docs provide a private account-specific tiered fee endpoint, and the fee webpage contains selected-pair promotions and MX discounts (`docs_api`, `fees_page`). Actual ordinary API account/tier applicability is unresolved without private account evidence. No private endpoint was called.

Current funding has an 8-hour cycle; the last reported history page reaches April 2025, not a proven complete archive (`funding_current_*`, `funding_*_last`). REST and WebSocket, isolated leverage, one-way reduce-only, stop/take-profit fields and order queries are documented (`docs_api`). Withdrawal-permission separation and IP allowlisting remain unverified. All source URLs, UTC times, statuses and hashes are in `SOURCE_INDEX.json`.

Official API-document excerpts (`docs_api`):

- `positionOpenType int position open type,1：isolated，2：cross，3：both`
- `note: [411.8, 10, 1] 411.8 is the price，10 is the volume of contracts for this price,1 is the order quantity`
- `The maximum data in a single request is 2000 pieces.`
- `Gets the user's current trading fee rate` followed by `GET api/v1/private/account/tiered_fee_rate` and `Required permissions: Trade reading permission`.
- `reduceOnly boolean false Default false,For one-way positions, if you need to only reduce positions, pass in true, and two-way positions will not accept this parameter.`
- `openType, 1: isolated position, 2: full position` in the leverage-control endpoint description.

The current public instrument receipts, rather than the stale sample values in the API documentation, supply exact live tick, contract and `apiAllowed` fields.
