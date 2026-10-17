# PURE SOURCE Stage20 — closed-parent and annotation-availability binding

Base: Stage19 merge `3a4cf35d400efc352432a8cdc64d473fa50b4116` (PR22). Stage18 defines qualitative claims; Stage19 audited the original sources. Stage20 binds those claims to actual closed data and their first accepted replay observation. Every addition is TECHNICAL_NORMALIZATION. No new SOURCE rule, qualitative threshold, branch preference or trading admission is introduced.

## Contract

`SourceClaimJournal` has one explicit exchange/symbol and a monotonic caller-supplied replay clock. `observe_frame` advances that clock when no annotation arrives. Ingestion verifies the timeframe duration, closed prefix, exact `newly_closed` suffix, append-only previously seen candle history, complete contiguous observation window, real subject IDs and recursive causal parent membership. Parent lifecycle is evaluated at the claim's declared known time; later events cannot rewrite that historical context. Previously seen parent identity metadata and lifecycle prefixes cannot change.

A candle subject ID includes market, timeframe, UTC timestamps and OHLC. It references an observed candle without inventing a formed market object. Supplied canonical object geometry remains the responsibility of its upstream producer. This module binds object content and ancestry, not the truth of every upstream detection.

A provenance artifact is immutable UTF8 JSON bytes. The claim references its full SHA256. The exact schema repeats the bounded claim fields and context hash, plus a nonblank annotator reference. Duplicate keys, extra fields, wrong content/context, future evidence and unknown subjects are rejected before journal mutation. The artifact bytes remain in the receipt.

Availability is `max(declared known_at, first accepted replay frame decision_at)`. Repeated delivery preserves the first receipt. Delivery at a later frame cannot create an earlier fact. A lookup requires the exact semantic, scope, timeframe, window and subject set. Missing evidence stays UNKNOWN without a fabricated evidence ID. Conflicting PASS/FAIL annotations stay UNKNOWN and retain both claim identities; neither author nor latest annotation wins. Agreeing annotations retain the first fact identity while accumulating provenance.

## Trust and integration limits

The clock is the supplied replay clock, not an authenticated wall clock. The caller must supply the current authoritative frame and preserve the journal rather than reset it to backdate delivery. Stage20 is in-memory; it does not supply durable cross-process arrival authentication. `observe_frame` makes clock progression possible even without claim arrivals.

Content hashes prove artifact integrity and binding, not author identity, annotation truth, real historical availability or blindness. The annotation methods remain Stage18 human/curated transports. No generated market annotation is declared SOURCE-valid here.

`BoundClaimAssessment.evidence` is a legacy compatibility projection. That old shape omits semantic/scope/window metadata. Callers must retain the complete assessment, journal receipt and claim, and enforce the intended consumer binding. Existing Stage4/6 and production providers are unchanged in this stage; extracting a generic legacy evidence object does not establish end-to-end migration. No claim PASS automatically establishes object validity or trade eligibility.

## QA and preserved boundaries

Targeted tests cover closed-window/content binding, future and late delivery, missing ancestry, gaps, unfinished bars, scope and market mismatch, conflict/no winner, idempotence, changed past candles, backward clocks, future lifecycle mutation, prefix/full repeat, future OHLC mutation, future/hidden `newly_closed`, clock advance without annotations and same-ID parent revisions. Fixtures are synthetic QA, never historical SOURCE annotations or financial cases.

Independent causality review found the `newly_closed` and same-ID parent mutation paths; both were hardened before final QA. Execution-semantics review required the explicit clock, content-authentication and lossy-projection limits above. Frozen Stage1–19 artifacts remain byte-identical.

The remaining safe task is a typed consumer adapter retaining the full binding, followed by independent object-family migrations. Missing market annotations and unspecified execution geometry remain unresolved. Baseline remains NOT_IDENTIFIABLE. Trade entry, financial backtest, PAPER, LIVE and private API permissions remain false.

## Files

- `src/crypto_bot/strategy/source_claim_binding_v1.py`
- `tests/test_source_claim_binding_v1.py`
- `config/pure_source_claim_binding_v1.json` (declaration, not mutable runtime permission controls)
- `docs/pure_source_stage20_qa_v1/` (QA receipts, synthetic binding trace and freeze manifest)
