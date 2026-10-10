# Bounded memory execution — registered before final outcomes

The full40 detector finished all 993575 native Bybit bars with verified complete
per-symbol manifests. Its subsequent all-symbol in-memory candidate aggregation
was killed by the environment at the 32 GiB limit, before any provisional or final
case outcomes were published. The original log, code lock and all segments remain.
The base COMPLETE manifest seals the **detector corpus only**, explicitly recording
the interrupted provisional aggregation. It does not certify completed provisional
execution. The primary source cases are executed in the separate physical root.

No detector rerun, new entry filter, exit, risk parameter or outcome selection is
introduced. SFP qualification and physical aliases use the same published pure
functions. Their namespaces include symbol: processing each symbol's causal
subsequence gives exactly its subsequence in the global READY ordering. The small
claim records are then merged by the original global ordering before family
filtering. Existing native detector ordering within segment files is retained.

The original `select_union` function runs on each symbol for all19 cohort scopes.
All selected IDs and duplicate evidence are merged and sealed before any replay.
The unchanged `replay_case`, fixed risk, all native prices, both cancellation modes,
all source exits, fees, slippage and censoring rules execute one symbol at a time.
Symbol case/decision shards are retained; the unchanged fill sort, first50 CLOSED,
statistics, breakdowns and fixed old9 control replay are assembled one cohort at
a time. This avoids holding every symbol's deeply nested evidence simultaneously.

Independent full/prefix/future-mutation, exact selection, native formation, costs,
body lifecycle and exact resume checks still apply. Original completed frozen
research and canonical strategy remain unchanged. Only BACKTEST/SHADOW;
`trade_entry_allowed=false`; no LIVE/private API or order placement.
