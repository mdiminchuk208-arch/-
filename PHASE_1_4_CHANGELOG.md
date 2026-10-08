# Phase 1.4 — v0.4.0

## Added
- Multi-timeframe SFP -> LTF BOS causal linker.
- Source-aligned gate: completed SFP first, then lower timeframe, then expected-direction BOS; only after BOS may an entry be searched for.
- Explicit separation between `entry_search_allowed` and `trade_entry_allowed`.
- `trade_entry_allowed` remains `False` in Phase 1.4.
- Configurable HTF:LTF pairs. `60:5` and `240:15` are convenience defaults only and are labeled `BACKTEST_PARAMETER`.
- Optional `max_wait_ltf_bars`; the source has no expiry rule, so default `0` means no invented expiry within the available dataset.
- New Bybit multi-timeframe fetch CLI for `5/15/60/240` native candles.
- New MTF CSV/JSON reports.

## Source boundary
The Base Trading Tools material states that after SFP completes, the trader may move to a lower timeframe, wait for a structure break, and only then search for an entry. It also says SFP is valid on any timeframe while H1+ is preferred for searching.

The source does **not** specify:
- exact HTF->LTF mapping;
- maximum wait after SFP;
- exact entry zone after LTF BOS.

Those gaps are not silently filled in v0.4.0.
