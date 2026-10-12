# Current State

Branch: `machine-v3-research`.

Latest completed gate: MACHINE_STRATEGY_v3 Historical Market-Metadata Recovery Freeze.
Completed decision: `V3_MARKET_METADATA_FROZEN_FINANCIAL_STOP`.
Metadata freeze commit: `7e89543ef9b443ac65b64f125c919e885dccf37b`.
Namespace: `docs/machine_strategy_v3_market_metadata_recovery/`.
Manifest SHA-256: `74c7d32b4e832d01d0d8f1fd6bb56ac7e218730bcb5613f4986a24b339c70e80`.

Historical metadata recovery is exhausted for the present evidence set without a defensible executable epoch. BTCUSDT and ETHUSDT remain 0% VERIFIED for both 2022 warmup and the exact 2023-01-01 through 2025-12-05T23:30Z development interval. No historical v3 financial outcomes have been generated or viewed. Do not repeat broad archival search as a substitute for evidence and do not infer old grids from current API values, candle decimals, later notices or search silence.

Frozen v3 design/implementation remain intact:
- v3 design freeze: `62590f1e09e2fa7516038ba1b3d813b0411d93ab`
- v3 implementation freeze: `43e57ee5c7867dd9421961629746555c8a2e9556`
- implementation manifest SHA-256: `d5eb8bd912a0b290679b30969dfa5e8015c4212c07b3263f42c9ca4a34d3a018`
- adapter SHA-256: `ed4091e385d4b7ed61bbf6680c56806b618bdf74d63a37b73c37d681a8874150`
- runner SHA-256: `d1ac5407902ec22cac1e66a943cc610bcc1023b7c72290e55c09c73a1cffb0b8`

The active task is now the prospective-only readiness gate in `agent_control/NEXT_TASK.md`.

Goal of the active gate: establish a clean forward path without weakening historical STOP. Capture BTC/ETH Bybit tick/price-grid metadata prospectively with immutable causally known receipts; fill and verify the exact 365-day M15 warmup gaps from independently verifiable public data if possible; enforce an integrity-only raw-access embargo; harden historical-outcome authorization controls; and determine whether an exact append-only 365-day OOS registration can be created.

Current illustrative prospective warmup from the frozen readiness artifacts is `[2025-10-13T00:00:00Z,2026-10-13T00:00:00Z)`, but it is NOT a registration. Previously recorded missing local intervals include a December-2025-to-January-2026 gap and a September/October-2026 tail for each symbol. Public Bybit gap acquisition previously returned HTTP 403. The new gate must independently resolve or preserve those gaps; no interpolation or post-hoc date shift.

Control-plane limitation to fix in the active gate: the metadata recovery scope required a fixture workaround for two active tests coupled to an old NEXT_TASK header, while the direct current-phase suite had one failure and one error. Active non-frozen test/control code should be made phase-stable without editing frozen namespaces or weakening the fail-closed historical-outcome guard. Missing/invalid/forged authorization must continue to block before financial history is evaluated.

Required prospective validation invariants remain:
- BTCUSDT + ETHUSDT Bybit USDT linear perpetual;
- completed native M15 with deterministic UTC H1/H4/D1 derivation;
- 365-day pre-start warmup;
- 365-day locked OOS evaluation if/when separately registered;
- no pre-start orders/carried positions;
- no interim signals/positions/trade labels/P&L/equity observation;
- pre-end raw access limited to logged integrity/continuity/metadata checks isolated from strategy state;
- exact registration timestamps/hashes fixed before first allowed observation;
- any material implementation change after registration invalidates that OOS for the changed version.

Expanded project config has 15 specialist roles and `max_threads=10`. The active gate should use the smallest competent team led by OOS/metadata/data/no-lookahead specialists with a fresh final independent reviewer. Report actual agents only.

Protected freezes:
- baseline: `ba65e91c2b1675f48e80ac785bb3adf89d17bb0b`
- failure audit: `8ca75ed35876d8f5d4d363e9e8808d7bd4417e87`
- v3 design: `62590f1e09e2fa7516038ba1b3d813b0411d93ab`
- v3 implementation: `43e57ee5c7867dd9421961629746555c8a2e9556`
- v3 metadata recovery: `7e89543ef9b443ac65b64f125c919e885dccf37b`

Historical financial backtest remains ready=false and authorized=false.
OOS remains `STOP_NO_PRISTINE_OOS` until a future gate proves and freezes otherwise.
Production candidate: NONE.
PAPER_TRADING_READY=false.
REAL_TRADING_READY=false.
trade_entry_allowed=false.
