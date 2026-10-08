# Phase 1.4.1 recheck notes

- Source recheck confirms: after completed SFP, move to a lower timeframe, wait for structure break, then search for an entry.
- Source recheck confirms: SFP can form on any timeframe, with H1+ preferred for searching.
- H1/H4 are fetched as native Bybit candles, not reconstructed from M1 in this phase.
- Bybit official V5 kline docs still list 5/15/60/240 intervals, reverse-sorted rows and max 1000 rows per request.
- LTF BOS must occur strictly after the completed HTF SFP event time; a BOS at the exact confirmation timestamp is not treated as post-SFP.
- Bearish SFP expects a bearish LTF break (`BULLISH_STRUCTURE_BROKEN_BOS`).
- Bullish SFP expects a bullish LTF break (`BEARISH_STRUCTURE_BROKEN_BOS`).
- Exact pair mapping remains a BACKTEST_PARAMETER.
- No source-invented expiry is used by default.
- New in 0.4.1: right-censoring and explicit observation bounds prevent truncated data from being mislabeled as a failed/expired setup.
- New in 0.4.1: loaded warm-up history is separated from the scored evaluation window to reduce start-boundary structure bias.
- New in 0.4.1: shared BOS links are reported separately from unique BOS events; neither is a trade count.
- A matched LTF BOS unlocks entry-search only. It is not a market order and not yet an entry candidate with SL/TP/RR.
