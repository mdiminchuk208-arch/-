# Stage A QA

PASS. 769 regression tests, zero failures/skips; new Stage A safety/provenance checks included.
Ruff on all new scripts/tests, compileall src/scripts/tests, mypy src: PASS.
Frozen v1/v1.1/v2 and first-result artifact hashes, exact dataset hashes, baseline/Source Audit archive invariance: PASS.
Completed-candle/known_at, prefix/future mutation, canonical IDs, source registry consistency, BACKTEST/SHADOW:
covered by unchanged frozen artifacts and full tests; no new historical SOURCE labels or events were generated.
Effective period coverage and UNKNOWN→no frozen metadata admission: PASS. Exact-symbol notice identification: PASS.
All four report outputs replay byte-identically offline. Source files/literal hashes validated.
No monetary outcomes read into metadata proof; inherited result/baseline verified by hashes only.
Financial identity/intrabar fills/second result acceptance: NOT_APPLICABLE, because Gate A STOP.
SECOND_FINANCIAL_BACKTEST_RAN=FALSE. trade_entry_allowed=false. No LIVE/private API or production integration.
