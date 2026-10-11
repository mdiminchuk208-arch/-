# Machine v2 pre_outcome QA

PASS: 930 inherited/new tests; 8 deterministic output files byte-identical. Frozen parent/data/engine/cohort IDs verified. Synthetic/open-gap/limit/dual-hit/EOF/funding and cost identities pass; original source/baseline/audit and all predecessors unchanged. Completed candles/known_at/prefix/future mutation/LIVE rejection regression pass. Full new-file lint, inherited fatal lint, compile and mypy pass. trade_entry_allowed=false.

Actual historical prefix QA: BTCUSDT 210 and ETHUSDT 216 cases at the fixed 2024-07-01 cutoff are byte-identical to full-history cases. A 10x mutated future suffix preserves every prefix case; prefix SHADOW and full BACKTEST/SHADOW outputs match. Actual QA script/log/receipt retained.
