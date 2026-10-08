# Phase 1.4.2 v0.4.2 changelog

## Goal
Close the two blockers found in the first real BTC/ETH MTF run before Entry Engine work:
1. SFP invalidation / experimental BOS wait-window handling.
2. Duplicate context links that share one LTF BOS.

## Source-derived behavior
- A completed SFP still requires moving to a lower timeframe and waiting for BOS before entry search.
- A formed SFP becomes irrelevant if a later candle body closes below the SFP minimum (bullish/long case) or above the SFP maximum (bearish/short case). Source: `[SW.BAND]12. Индикаторы.pdf`, p.13.

## Explicit technical normalizations
- The machine represents the SFP invalidation min/max with the completed sweep candle low/high. This value is known at SFP formation time and does not use future H/L/C of the confirmation candle.
- If invalidation and LTF BOS share the exact same timestamp, invalidation wins conservatively.
- Multiple valid HTF SFP contexts linked to the same expected-direction LTF BOS become one `ENTRY_SEARCH_CANDIDATE` opportunity. All contributing context IDs are retained.
- The most recent SFP context is a display representative only; it does not receive extra score.

## Backtest parameter
- `max_wait_ltf_bars` remains a BACKTEST_PARAMETER. The source does not specify an expiry window.
- CLI now supports `--wait-windows` to compare several finite windows in one run.

## New outputs
For each symbol / HTF:LTF / wait-window:
- `mtf_sfp_candidates.csv`
- `mtf_opportunities.csv`
- `candidate_quality_audit.csv`
- `summary.json`

The audit output contains SFP time/level/extreme, invalidation time, LTF BOS time, elapsed bars, deadline and opportunity ID for manual review.

## Safety boundary
`ENTRY_SEARCH_CANDIDATE` is not an order and not a trade entry. `trade_entry_allowed` remains `False` in Phase 1.4.2.
