# Current State

Branch: `machine-v3-research`.
Prior full-attempt artifact preserved: **EXCHANGE_SELECTION_AUDIT_v1**. Active task is the newer OKX-only Stage 1A batch; the prior result is not used to bypass that checkpoint/STOP.
Decision: `EXCHANGE_SELECTION_AUDIT_FROZEN_PASS` — conditional nonfinancial architecture selection only.
Freeze commit: `ff20ac4bee75d605c0a7f4234fe74bb89a337fbf`.
Namespace: `docs/exchange_selection_audit_v1/`.
Manifest SHA-256: `06556298d9f8041c493af5225740425cdfc51807566a322e2dd86f944b9c24d5`.

Frozen roles:
- PRIMARY_RESEARCH_VALIDATION_VENUE=bitget (82, tied with OKX; preregistered lexicographic tie-break).
- PRIMARY_EXECUTION_VENUE=blofin (69, highest eligible).
- SECONDARY_EXECUTION_VENUE=kraken_futures (29, tied with KuCoin; lexicographic tie-break).
- REFERENCE_BENCHMARK_VENUE=okx (82).

Bitget/BloFin primaries survive both cost-weight ±5 shifts and all 76 snapshot removals. Secondary changes Kraken→KuCoin in 1/76 when the thin ETH CI book is omitted; this observation remains retained. Bitget/Kraken book-size units are unproven and cost/liquidity scores are zero. KuCoin's required visible-depth grid is incomplete. Higher raw execution scorers Deribit/Hyperliquid remain hard-excluded for isolated-control/signer-scope uncertainty. Fee unknowns/promotions are not treated as base API rates.

QA: 30 targeted tests PASS; math/synthesis coverage 84.7943%; Ruff/format, mypy and compile PASS; 18 JSON outputs byte-identical replay; 503 raw receipts and 606 predecessor artifact hashes verified. Final independent marker is retained. The inherited full suite was not rerun or claimed PASS; phase-dependent header-test conflict remains preserved.

An additive independently reviewed timestamp follow-up is at `docs/exchange_selection_audit_v1_followup/`: four Kraken CI normalized time_utc fields are receipt completion, not exchange server/event time. Raw ISO serverTime remains retained. Scratch substitution changes no sample count, scores or roles, so conditional architecture PASS remains valid. Those fields are prohibited as causal/financial event times. New unified contracts must separate exchange server time, any actual event time, receipt clocks and known_at. Original audit bytes/manifest remain unchanged.

The predecessor prospective gate remains `V3_PROSPECTIVE_READINESS_FROZEN_STOP`: historical verified tick epochs still absent at all venues, full historical continuity not proved, warmup/authenticity/control-isolation/authorization blockers preserved. Current filters must never be backdated. Actual account/jurisdiction, fee tier, one-way protective behavior, retry semantics and collateral compatibility are unverified. Architecture selection does not clear these gates.

Active batch: `agent_control/CURRENT_BATCH.md` — OKX only, one medium-reasoning venue_researcher using retained receipts, checkpoint at `docs/exchange_selection_checkpoints_v1/okx.json`, commit/push and STOP. No new ranking, cross-venue review or other venue research in this batch. The earlier Unified Exchange Layer proposal is preserved in `docs/control_plane_proposals/unified_exchange_layer_v1_NOT_OPEN.md` but is NOT open. NEXT_TASK retains full exchange-audit requirements; EXCHANGE_AUDIT_RUNBOOK and CURRENT_BATCH constrain the next execution.

Current allowance policy from remote `4435687`: serial-first, one active specialist, hard two-thread ceiling with second only for independent verification, one venue collector, medium routine reasoning. Existing frozen evidence is reused. The latest remote scope supersedes earlier 4/16-thread and automatic-next-gate controls.

Production candidate: NONE.
Historical financial v3 backtest ready=false and authorized=false.
OOS registration: none.
PAPER_TRADING_READY=false.
REAL_TRADING_READY=false.
trade_entry_allowed=false.

Protected freezes remain immutable:
- baseline `ba65e91c2b1675f48e80ac785bb3adf89d17bb0b`
- failure audit `8ca75ed35876d8f5d4d363e9e8808d7bd4417e87`
- v3 design `62590f1e09e2fa7516038ba1b3d813b0411d93ab`
- v3 implementation `43e57ee5c7867dd9421961629746555c8a2e9556`
- v3 metadata recovery `7e89543ef9b443ac65b64f125c919e885dccf37b`
- v3 prospective readiness `fdf5b95e34c724ab73e8f3e64d36aed562ad965b`, manifest `b96797ec01575303b6d4c0170f0683554386f53569ef41ad38ed3f91cf7fe45d`
- adapter SHA-256 `ed4091e385d4b7ed61bbf6680c56806b618bdf74d63a37b73c37d681a8874150`
- runner SHA-256 `d1ac5407902ec22cac1e66a943cc610bcc1023b7c72290e55c09c73a1cffb0b8`
