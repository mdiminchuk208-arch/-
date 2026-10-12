# Current State

Branch: `machine-v3-research`.

Latest completed gate: MACHINE_STRATEGY_v3 Prospective Data/Metadata Capture + OOS Registration Readiness Freeze.
Decision: `V3_PROSPECTIVE_READINESS_FROZEN_STOP`.
Prospective freeze commit: `fdf5b95e34c724ab73e8f3e64d36aed562ad965b`.
Namespace: `docs/machine_strategy_v3_prospective_readiness/`.
Manifest SHA-256: `b96797ec01575303b6d4c0170f0683554386f53569ef41ad38ed3f91cf7fe45d`.
Independent seal: `FINAL_REVIEW_PASS_FOR_PROSPECTIVE_STOP`.
No OOS registration exists; allowed=false/created=false; actual start/end=null.

Metadata: STOP. Official current instruments-info and native M15 gap queries for
BTCUSDT/ETHUSDT returned HTTP403 country-block responses. Fourteen immutable public
receipts retained; dated notices do not prove current applied filters/continuity.
No tick epoch opened, no daemon activated, no geographic restriction bypass.

Warmup: STOP. Frozen integrity snapshot `2026-10-12T18:10:50Z`, completed cutoff
18:00Z; illustrative window `[2025-10-13T00:00Z,2026-10-13T00:00Z)` is not a
registration. Per symbol: 35,016 completed M15 expected, 28,221 present, 6,795
missing closed bars; another 24 unfinished/future at that snapshot. Counts do not
claim a live current feed. Exact missing completed intervals:

- BTC: `[2025-12-05T23:30Z,2026-01-25T11:30Z)` and `[2026-09-22T11:15Z,2026-10-12T18:00Z)`.
- ETH: `[2025-12-05T23:30Z,2026-01-25T12:30Z)` and `[2026-09-22T12:15Z,2026-10-12T18:00Z)`.

No public/native overlap exists to corroborate OHLCV; attribution/authenticity is
incomplete. No interpolation, aliases, price edits or H1/H4/D1 production occurred.
Final-code standalone workers independently reproduce counts/gaps in logged
integrity-only processes; previous attempts are retained with their code snapshots.

Control-plane mandatory QA: FAIL. The actual unmodified current-phase full suite
ran 1,096 tests: 2 failures + 1 error, zero skips, 1,093 passed. Immutable root
tests assert old task phases. No old NEXT_TASK injection, guard patch, exclusion,
skip or weakened assertion was used. New infrastructure tests: 34 PASS, coverage
80.29%; ten output replays, hashes/chronology, native prefix/future mutation,
exact overlap, public route/truncation, auth/freeze negatives, Ruff/format, mypy
and compile PASS. All frozen parents/strategy/adapter/runner/test bytes unchanged.
New denial facade is phase-independent and rejects all financial artifacts before
reads; it does not replace or repair direct frozen-runner authorization. Audit
hooks deny unexpected reads/imports/sockets/subprocess but OS isolation is absent.
A reviewer incidentally saw legacy QA stdout text without analysis; no v3/OOS
candidate outcome was observed. Raw logs are retained and safe summaries emit
only test IDs/counts.

Six required functions were performed by five actual cloud agents:
`/root/oos_forward_validator` (also no_lookahead_auditor; shared identity),
`/root/prospective_tick_metadata_researcher`,
`/root/prospective_historical_data_engineer`,
`/root/prospective_market_microstructure_auditor`,
`/root/prospective_final_independent_reviewer` (independent final seal).
Root alone authored implementation; no strategy designer ran. Role findings and
exact scopes are pinned in INDEPENDENT_REVIEW.md/reviews. ECC trusted project
config/multi_agent/348 skills verified; hooks inactive, cloud collaboration used
configured role models/instructions. No native ECC role launch claimed.

Exact remaining blockers (details in OOS_REGISTRATION_READINESS.json):

- `OFFICIAL_CURRENT_INSTRUMENT_CAPTURE_HTTP_403`
- `WARMUP_CLOSED_NATIVE_M15_GAPS_BOTH_SYMBOLS`
- `WARMUP_PUBLIC_MIRROR_AUTHENTICITY_UNVERIFIED`
- `LITERAL_COMPLETED_WARMUP_BEFORE_STRICT_NEXT_START_CONTRADICTION`
- `FROZEN_ACTIVE_TEST_HEADERS_CONFLICT_WITH_CURRENT_TASK`
- `NO_OS_LEVEL_STRATEGY_STATE_ISOLATION`
- `FROZEN_RUNNER_DIRECT_AUTH_DESIGN_REQUIRES_NEW_VERSION`

The strict next-UTC-D1 formula and fixed 365-day warmup/evaluation remain intact.
A conditional preregistered tail is a possible independently reviewed operational
clarification, not adopted here. Pinned old tests cannot be revised under this gate;
an explicitly authorized append-only active test/control version is required.
Do not shift dates, relax proof or fabricate a registration to force READY.

Protected references:

- baseline `ba65e91c2b1675f48e80ac785bb3adf89d17bb0b`
- failure audit `8ca75ed35876d8f5d4d363e9e8808d7bd4417e87`
- v3 design `62590f1e09e2fa7516038ba1b3d813b0411d93ab`
- implementation `43e57ee5c7867dd9421961629746555c8a2e9556`
- implementation manifest `d5eb8bd912a0b290679b30969dfa5e8015c4212c07b3263f42c9ca4a34d3a018`
- adapter SHA-256 `ed4091e385d4b7ed61bbf6680c56806b618bdf74d63a37b73c37d681a8874150`
- runner SHA-256 `d1ac5407902ec22cac1e66a943cc610bcc1023b7c72290e55c09c73a1cffb0b8`
- metadata recovery `7e89543ef9b443ac65b64f125c919e885dccf37b`
- metadata manifest `74c7d32b4e832d01d0d8f1fd6bb56ac7e218730bcb5613f4986a24b339c70e80`

NEXT_TASK.md retains the completed STOP gate. Verify its immutable package only:

```sh
/workspace/crypto-bot-venv/bin/python scripts/build_machine_strategy_v3_prospective_readiness.py --resume-existing --expected-manifest-sha256 b96797ec01575303b6d4c0170f0683554386f53569ef41ad38ed3f91cf7fe45d
```

Further collection/governance/hardening requires a separate append-only gate;
do not overwrite this freeze. Historical financial evaluation is unauthorized,
with historical verified tick coverage still 0% for warmup/development.
OOS remains `STOP_NO_PRISTINE_OOS`; no registered pristine data/window exists.
Production candidate: NONE.
PAPER_TRADING_READY=false.
REAL_TRADING_READY=false.
trade_entry_allowed=false.
