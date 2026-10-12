# Current State

Branch: `machine-v3-research`.

Latest completed gate: MACHINE_STRATEGY_v3 Historical Market-Metadata Recovery Freeze.
Completed-gate decision: `V3_MARKET_METADATA_FROZEN_FINANCIAL_STOP`.
Metadata freeze commit: `7e89543ef9b443ac65b64f125c919e885dccf37b`.
Namespace: `docs/machine_strategy_v3_market_metadata_recovery/`.
Manifest SHA-256: `74c7d32b4e832d01d0d8f1fd6bb56ac7e218730bcb5613f4986a24b339c70e80`.

Historical provenance recovery retained 117 public response receipts and 14
selected leads. Official ETH/BTC notice publication fields explicitly state UTC,
but independent pre-effective availability/application and complete continuity
remain unproven. Later CCXT fixtures are explicit tick-filter leads, not production
capture timestamps or interval proof. Official examples can be stale. Five raw
OHLC bars conditionally disagree with naive notice-based old-grid windows; neither
an earlier actual change boundary nor corrected candle prices were inferred.

Both BTCUSDT and ETHUSDT have 0% VERIFIED executable tick coverage for each period:

- warmup `[2022-01-01T00:00:00Z,2023-01-01T00:00:00Z)`: 0 / 31,536,000 seconds;
- development `[2023-01-01T00:00:00Z,2025-12-05T23:30:00Z)`: 0 / 92,446,200 seconds.

Minimal unresolved interval per symbol is `[1640995200,1764977400)`, equivalent
to the whole `[2022-01-01T00:00:00Z,2025-12-05T23:30:00Z)`. No shorter fully proven
executable interval exists in recovered evidence. Local source continuity/hash
checks do not establish exchange authenticity. Required blockers remain
`NO_VERIFIED_HISTORICAL_TICK_EPOCHS` and `HISTORICAL_EXCHANGE_PRICE_GRID_UNVERIFIED`.

QA/review passed for this evidence freeze with explicit scope: 28 new metadata
tests; 1,062 full tests under declared historical phase fixtures; 83.42% new-code
coverage; 11 byte-identical replay outputs; evidence integrity, UTC/identity,
exact-decimal grid, static outcome isolation, frozen invariance, Ruff/format, mypy
and compile. The direct current-phase suite did NOT pass (1,059 tests, one failure
and one error), due to two immutable tests reading the prior readiness task header.
Those modules alone receive exact old task bytes in the recorded fixture runner;
assertions/guards/frozen files are unchanged, other tests use the actual task.
Raw failing logs remain pinned. The frozen guard's missing forged-auth-file error
blocks before history and is an explicit limitation for later append-only auth
work. This is not a claim that the unmodified current-phase full suite passed.

Actual agents: `/root/tick_metadata_researcher` (82 evidence responses, chronology),
`/root/historical_data_engineer` (data plus microstructure/no-lookahead/execution
audit functions), `/root/backtest_reviewer_final` (procedural independent checks),
and `/root/metadata_final_independent_reviewer` (fresh final independent seal
review). Four identities performed all six required role functions; shared audit
functions are not three independent reviewers. Final review marker is
`FINAL_REVIEW_PASS_FOR_FINANCIAL_STOP`. Root authored implementation and 35 bounded
public captures. Findings and role scopes are pinned in INDEPENDENT_REVIEW.md and
reviews/. No strategy designer was used. ECC config/348 skills/multi_agent were
verified and hooks stayed inactive; native model delegation failed HTTP 401 before
role creation, so only actual cloud agents count as launches.

The full frozen causal v3 adapter/guarded runner, five families and both directions
remain intact. Historical v3 financial outcomes were neither run nor viewed.
Protected references remain unchanged:

- baseline: `ba65e91c2b1675f48e80ac785bb3adf89d17bb0b`
- failure audit: `8ca75ed35876d8f5d4d363e9e8808d7bd4417e87`
- v3 design: `62590f1e09e2fa7516038ba1b3d813b0411d93ab`
- implementation freeze: `43e57ee5c7867dd9421961629746555c8a2e9556`
- implementation manifest: `d5eb8bd912a0b290679b30969dfa5e8015c4212c07b3263f42c9ca4a34d3a018`
- adapter SHA-256: `ed4091e385d4b7ed61bbf6680c56806b618bdf74d63a37b73c37d681a8874150`
- runner SHA-256: `d1ac5407902ec22cac1e66a943cc610bcc1023b7c72290e55c09c73a1cffb0b8`

NEXT_TASK.md retains the completed metadata gate. Resume is verification only:

```sh
/workspace/crypto-bot-venv/bin/python scripts/build_machine_strategy_v3_market_metadata_recovery.py --resume-existing --expected-manifest-sha256 74c7d32b4e832d01d0d8f1fd6bb56ac7e218730bcb5613f4986a24b339c70e80
```

Do not rebuild/overwrite this namespace. Further provenance recovery must be
append-only under a separately opened gate. A first financial authorization gate
may NOT be opened from this STOP; first financial backtest ready=false and
authorized=false. Prospective public metadata collection was assessed, not
activated, and the validation protocol was not changed.

OOS remains `STOP_NO_PRISTINE_OOS`: inventoried history is development-exposed,
old2026TEST is not pristine, and no prospective OOS registration was created.
Production candidate: NONE.
PAPER_TRADING_READY=false.
REAL_TRADING_READY=false.
trade_entry_allowed=false.
