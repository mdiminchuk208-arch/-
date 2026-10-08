# Phase 1.2 changelog — 0.2.1 (rechecked)

## Source / API facts used

The Bybit V5 public API documents:

- `GET /v5/market/kline`
- category `linear` for USDT perpetuals
- uppercase symbol such as `BTCUSDT`
- intervals including `1`, `3`, `5`, `15`, `30`, `60`, `120`, `240`, etc.
- `start` and `end` in milliseconds
- maximum `limit=1000`
- returned Kline list sorted in reverse by start time
- current, unfinished candle close is only the latest traded price

The instrument endpoint documents `launchTime`, `deliveryTime`, status, tick size and lot-size fields.

## Engineering normalizations

These are project decisions rather than exchange trading rules:

1. Normalize downloaded candles to ascending chronological order.
2. Exclude unfinished candles by default before strategy analysis.
3. Paginate historical Klines backward from the requested end time because Bybit returns latest-first data.
4. Never silently fill a missing candle; Data QA reports it.
5. Use exchange/server response time for closed-candle and coverage logic when available.
6. Reject weekly/monthly fixed-boundary QA until their exchange session boundaries are explicitly validated.
7. Flag candle timestamps that are not aligned to the expected fixed interval boundary.


## Recheck fixes in 0.2.1

1. Historical pagination now advances using raw returned rows even when the newest row is still unfinished; this prevents `limit=1` from prematurely terminating a download.
2. The CLI uses `/v5/market/time` for the request end timestamp instead of trusting the local PC clock.
3. Instrument metadata now includes and validates `contractType`; the CLI only accepts `Trading` USDT `LinearPerpetual` instruments.
4. Added parsing for `maxMktOrderQty`, `minNotionalValue`, `fundingInterval` and maximum leverage. `maxOrderQty` is no longer implicitly treated as the market-order maximum.
5. Malformed OHLC rows fail as a stable `BybitAPIError` instead of leaking a raw dataclass `ValueError`.
6. Added explicit precision warning: float-normalized market data is acceptable for this early structure/QA phase, but not for future exact order sizing/rounding.

7. Bybit now parses `marketRegion`; symbols marked with a TradFi market region are not accepted by the crypto-perpetual eligibility helper.
