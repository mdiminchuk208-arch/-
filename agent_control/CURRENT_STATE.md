# Current State

Branch: `machine-v3-research`.

Latest completed gate: MACHINE_STRATEGY_v3 Prospective Data/Metadata Capture + OOS Registration Readiness Freeze.
Decision: `V3_PROSPECTIVE_READINESS_FROZEN_STOP`.
Freeze commit: `fdf5b95e34c724ab73e8f3e64d36aed562ad965b`.
Namespace: `docs/machine_strategy_v3_prospective_readiness/`.
Manifest SHA-256: `b96797ec01575303b6d4c0170f0683554386f53569ef41ad38ed3f91cf7fe45d`.
Independent seal: `FINAL_REVIEW_PASS_FOR_PROSPECTIVE_STOP`.

The prospective-readiness gate established that the frozen v3 strategy/implementation remain outcome-clean, but OOS registration is not ready. In the current cloud environment, official Bybit instruments-info and native M15 requests returned HTTP403. No proxy/VPN/geolocation bypass was used. The illustrative 365-day warmup snapshot had 6,795 missing completed M15 bars per symbol and no independent overlap that could authenticate the public-mirror history. The unmodified then-current full suite also exposed three frozen phase-dependent test failures/errors, and true OS-level strategy-state isolation plus a new outer authorization design were still absent.

Exact completed-gate blockers:
- `OFFICIAL_CURRENT_INSTRUMENT_CAPTURE_HTTP_403`
- `WARMUP_CLOSED_NATIVE_M15_GAPS_BOTH_SYMBOLS`
- `WARMUP_PUBLIC_MIRROR_AUTHENTICITY_UNVERIFIED`
- `LITERAL_COMPLETED_WARMUP_BEFORE_STRICT_NEXT_START_CONTRADICTION`
- `FROZEN_ACTIVE_TEST_HEADERS_CONFLICT_WITH_CURRENT_TASK`
- `NO_OS_LEVEL_STRATEGY_STATE_ISOLATION`
- `FROZEN_RUNNER_DIRECT_AUTH_DESIGN_REQUIRES_NEW_VERSION`

Historical market-metadata recovery remains STOP with 0% verified executable tick coverage over 2022 warmup and 2023-2025 development. Historical v3 financial evaluation is still ready=false and authorized=false. No OOS registration exists. PAPER/LIVE remain off.

## Open gate

`agent_control/NEXT_TASK.md` now opens: **MACHINE_STRATEGY_v3 Prospective Capture Activation + Control Plane v2 Freeze**.

This gate is intentionally engineering-focused. It must attempt to start a lawful, non-evasive prospective collector from a normal project CI environment (for example an ordinary GitHub-hosted runner) for official public BTCUSDT/ETHUSDT Bybit instrument metadata and completed M15 bars. If successful it creates a separate append-only capture surface, verifies raw bytes/hashes/identity, enables bounded recurring collection and freezes the first defensible prospective capture time `T0`. `T0` is not OOS registration and does not verify earlier history.

In parallel it must create append-only active-test governance so current tests check stable semantic capabilities rather than old task prose; retain all legacy frozen bytes; add an outer fail-closed Authorization Gateway v2 without touching the frozen adapter/runner; and implement the strongest available OS/process isolation for integrity-only tooling. Any unavailable guarantee remains an explicit STOP rather than being simulated.

No strategy rules may change. No signals, setups, orders, positions, outcomes or financial metrics may be generated/viewed in the open gate. `trade_entry_allowed=false` remains invariant.

Required specialist functions: historical_data_engineer, tick_metadata_researcher, oos_forward_validator, no_lookahead_auditor, market_microstructure_auditor, backtest_engineer, final_independent_reviewer. Record only actual launched identities/functions.

Protected references remain immutable:
- baseline `ba65e91c2b1675f48e80ac785bb3adf89d17bb0b`
- failure audit `8ca75ed35876d8f5d4d363e9e8808d7bd4417e87`
- v3 design `62590f1e09e2fa7516038ba1b3d813b0411d93ab`
- v3 implementation `43e57ee5c7867dd9421961629746555c8a2e9556`
- v3 metadata recovery `7e89543ef9b443ac65b64f125c919e885dccf37b`
- v3 prospective readiness `fdf5b95e34c724ab73e8f3e64d36aed562ad965b`
- adapter SHA-256 `ed4091e385d4b7ed61bbf6680c56806b618bdf74d63a37b73c37d681a8874150`
- runner SHA-256 `d1ac5407902ec22cac1e66a943cc610bcc1023b7c72290e55c09c73a1cffb0b8`

Production candidate: NONE.
PAPER_TRADING_READY=false.
REAL_TRADING_READY=false.
trade_entry_allowed=false.
