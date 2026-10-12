# Metadata recovery QA

Evidence/implementation QA: PASS under the explicitly declared phase fixtures.
Financial readiness: **V3_MARKET_METADATA_FROZEN_FINANCIAL_STOP**.

| Check | Executed result |
|---|---|
| Complete suite with declared historical phase fixtures | 1,062 tests PASS, no skips/failures; full_unittest.log. |
| Direct unmodified current-phase inherited suite | 1,059 tests, one failure and one error retained in full_unittest_current_phase.log. Both are immutable readiness tests coupled to the old NEXT_TASK header. This run did not pass. |
| New metadata tests | 28 PASS: exact ratios/context independence, intervals/coverage, proof-schema limits, receipts, public capture failures/header exclusion, actual frozen bars and current-phase guards. |
| Deterministic replay | 11 machine-readable outputs match byte-for-byte; lead research source/search inventory also rebuilds from retained receipts. |
| Evidence integrity | 117 response-body hashes and selected-source links verified; no cookies/authorization headers retained. Raw body bytes unchanged by header filtering. |
| Time/identity/coverage | Explicit UTC and subsecond-aware chronology; issuer claims distinguished from independent known-at; exact BTC/ETH perpetual identity; separate warmup/development durations; zero verified coverage. |
| Grid/contradictions | Exact integer ratios of Decimal strings, no float tolerance, source rounding or boundary inference; five conditional off-grid bars and stale example/fixture context checks retained. |
| Outcome isolation | Metadata-only builder/import/read scope, no outcome column reads or strategy engine invocation; collector/public endpoint scope separately reviewed. No historical v3 outcome generated/viewed. |
| Frozen invariance | V3 design, implementation and failure-audit namespace hashes/membership PASS; original/source/baseline/v2/v2.1/v2.2 untouched. |
| Static/build | Strict Ruff/new-file format, inherited fatal-rule scan, mypy with untyped body checks on new modules, compile PASS. |
| Statement coverage | 83.42% across new builder/collector, including actual metadata-only replay and deterministic capture fixtures; not evidence of historical tick truth. |

The phase runner patches **only** reads of agent_control/NEXT_TASK.md during the
two frozen readiness test modules, returning exact task bytes from implementation
freeze 43e57ee. Every assertion still runs; all other tests use the actual task.
No repository/frozen file or guard function is patched. The final reviewer accepted
this as reproduction of historical unit-test input, not a claim that the raw
current-phase suite passed. Initial raw failure evidence is preserved separately.

New actual-current-phase tests confirm unauthenticated public/kernel/accounting
calls block before historical input/exits. A forged missing auth file produces
FileNotFoundError in the frozen guard outside its old phase; it still blocks before
history and is recorded as an error-handling limitation, not authorization. A
fake grant cannot promote the pinned implementation STOP manifest. A later
financial-auth gate must address authorization/error handling append-only within
its own scope; this evidence task did not modify the frozen runner.

QA_RECEIPT.json pins code, logs, counts and replay outputs. Final independent
review is separately required before sealing. QA PASS cannot promote any epoch
without substantive complete causal production-filter/application/continuity proof.
