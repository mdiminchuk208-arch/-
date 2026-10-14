# Failure-audit QA

Status: PASS. Eight synthetic evidence-boundary/partition tests executed. Exact commands, statuses and logs are in QA_RECEIPT.json. Ruff/format, mypy and compilation cover new diagnostic source/test only. Frozen financial --resume-existing externally pinned verification confirms unchanged inputs; the old historical strategy runner and whole repository suite were not invoked.

Diagnostic reader replay produced identical bytes for all seven generated evidence JSON files. Tests cover exact OPEN exit/cancellation versus later wicks, future-after-exit/future-after-decision mutations, uncertain wick extrema, LONG/SHORT price symmetry, unique-origin partition and exclusion of partial disagreement closures. No trade execution, cash outcome simulation, numeric parameter search or historical strategy replay occurs.

Missing per-origin WAIT history is null exact counts with conservative bounds. Completed-only diagnostic ATR and retrospective OHLC envelopes remain outside admission. Stored P&L comes from the immutable parent ledger; no OOS/PAPER/LIVE/private API/orders are authorized. trade_entry_allowed=false.
