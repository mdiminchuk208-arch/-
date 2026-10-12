# Prospective data, metadata and registration readiness

Primary decision: **V3_PROSPECTIVE_READINESS_FROZEN_STOP**.
Historical financial STOP is unchanged. No OOS registration, collector daemon,
candidate signal/position or historical v3 financial outcome was created/viewed.
`trade_entry_allowed=false`; PAPER/LIVE and private exchange API remain disabled.

## Evidence and warmup

Fourteen bounded public response receipts (eight metadata/notice, six warmup/
source-discovery) retain raw bytes, hashes, request/retrieval times and allowlisted
headers. Official BTCUSDT/ETHUSDT instruments-info and native M15 gap requests
returned HTTP 403, with a CloudFront country-block response. No route/proxy or
alternative API host was used to evade that restriction. Accessible announcements
provide dated notice evidence, not current production filters or continuous epochs.
An independent official public bulk archive lists BTC files only through 2024.
Bounded mirror discovery did not find independently verified native M15 gap data;
this is not proof that such data does not exist.

The illustrative warmup remains `[2025-10-13T00:00Z,2026-10-13T00:00Z)`; this is
not a registration or a shifted evaluation window. Snapshot 2026-10-12T18:10:50Z
uses completed cutoff 18:00Z: 35,016 completed bars expected per symbol,
28,221 present and **6,795 missing**. Twenty-four final bars were unfinished/future
at that snapshot. Distinguish unfinished bars from missing closed history.

BTC missing closed spans: `[2025-12-05T23:30Z,2026-01-25T11:30Z)` and
`[2026-09-22T11:15Z,2026-10-12T18:00Z)`.
ETH: `[2025-12-05T23:30Z,2026-01-25T12:30Z)` and
`[2026-09-22T12:15Z,2026-10-12T18:00Z)`.
Public/native files have zero overlap: zero conflicts gives no independent
corroboration. Row identity/closure/valid OHLCV and pinned hashes are verified;
public-mirror attribution is not complete exchange-authenticity proof. No aliases,
interpolation, source rounding, source selection from behavior or H1/H4/D1
production occurred. New standalone workers independently reproduce both prefix
counts/gaps and exact overlap assessment; reviewed records bind final worker hash.
Early worker records and their corresponding code snapshots remain explicit
pre-change evidence rather than current-code QA.

## Infrastructure and hardening

New append-only public capture tooling allows only exact public market metadata/
M15 and official notice routes. It disables redirects, bounds requests/responses,
filters sensitive headers and preserves failure/truncation receipts. Future use
requires a separately reviewed acquisition/registration gate; no daemon was started.

Validated instrument metadata would require official successful linear response,
exact unique LinearPerpetual/USDT quote+settle/Trading identity and positive exact
string priceFilter.tickSize. Response completion is knowledge time. Server Date,
issuer publication and effective/application timestamps are separate. Even equal
snapshots leave inter-capture intervals UNVERIFIED. No epoch was opened.

The standalone integrity worker reads only exact pinned raw M15 paths, rejects a
cutoff beyond actually completed M15 time, imports no candidate engine/state, and
records input/code hashes and counts in exclusive-create access logs. Dynamic
probes deny new imports, unallowlisted file reads, socket and subprocess access.
CPython audit hooks are an operational boundary, **not OS filesystem isolation**
against native code; full OOS state isolation remains unresolved. Valid future
numeric rows/values cannot change completed-prefix assessment. Unparseable source
timestamps cannot be classified as future and fail the whole-file integrity check;
no silent row deletion. Whole-file hash changes always invalidate pinned input.

The new financial-denial facade rejects every caller artifact before any artifact
or history read and is phase-header independent. It does not patch or replace the
frozen runner. The frozen direct runner still has its self-declared authorization/
missing-file design limitation. A separate new control/runner version is required;
do not claim this facade alone hardens arbitrary direct imports.

## Exact registration and objective blockers

The frozen formula remains first UTC D1 open strictly after MAX(implementation
freeze committer time, separate registration committer time), with 365 UTC days
warmup and 365 UTC days locked OOS. Actual start/end/registration remain null.
Requiring all warmup bars completed before a commit that selects a strictly later
start creates a timing contradiction: the last warmup bar only closes at the
start, while a later commit moves the required start to another midnight. A
conditional preregistered tail could be an independently reviewed non-outcome
operational clarification; it has not been adopted or silently substituted here.

Mandatory unmodified current-phase full-suite PASS also conflicts with immutable
hash-pinned root tests that assert old active task headers. This gate preserves
their bytes and runs all assertions with the actual NEXT_TASK: no old task bytes,
monkeypatches, skips, exclusions or expected-failure conversions. Full-suite failure
is a control-plane STOP, not a disguised PASS. Resolution requires explicit
append-only governance/version authorization, preserving every previous freeze.

Additional blockers: current metadata HTTP 403; missing closed warmup bars;
public-mirror authenticity; OS state isolation; frozen direct authorization design.
Historical financial execution remains unauthorized regardless of prospective QA.

## Review and QA

Five actual cloud specialist identities performed all six required functions,
with OOS/no-lookahead sharing one identity. A fresh final reviewer did not collect
or author implementation. Details are in INDEPENDENT_REVIEW.md and reviews/.
ECC project config, multi_agent and 348 enabled skills were verified; ECC
verification-loop guided QA, hooks stayed inactive. Native role launch through
ECC was not claimed; configured role models/instructions guided cloud collaboration.

QA_REPORT.md/QA_RECEIPT.json separate passing new infrastructure checks from the
failing full current-phase suite. Ten generated outputs replay byte-for-byte;
four parent namespaces and pinned strategy/adapter/runner/test bytes are unchanged.
A reviewer incidentally saw legacy test stdout while tailing the full QA log;
those values were not analyzed and are not v3/OOS candidate observations. Subsequent
summary extraction emits only test IDs/counts. Raw full logs remain retained.
