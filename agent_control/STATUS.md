# Agent Status

State: EXCHANGE_SELECTION_AUDIT_V1_TASK_OPEN
Branch: `machine-v3-research`.

Latest completed gate: MACHINE_STRATEGY_v3 Prospective Data/Metadata Capture + OOS Registration Readiness Freeze.
Completed decision: `V3_PROSPECTIVE_READINESS_FROZEN_STOP`.
Prospective freeze commit: `fdf5b95e34c724ab73e8f3e64d36aed562ad965b`.
Namespace: `docs/machine_strategy_v3_prospective_readiness/`.
Manifest SHA-256: `b96797ec01575303b6d4c0170f0683554386f53569ef41ad38ed3f91cf7fe45d`.

The previously opened Bybit-only Prospective Capture Activation + Control Plane v2 task was not executed and is superseded before implementation by `EXCHANGE_SELECTION_AUDIT_v1` at the user's explicit direction.

Project directive: `agent_control/LAUNCH_DIRECTIVE.md` is active. Primary objective is the earliest safe evidence-backed Crypto Bot launch. Frozen `MACHINE_STRATEGY_v3` rules must not be redesigned/tuned during the launch path. Routine sequencing, technical architecture choices, gate creation, and reviewer selection are delegated to the project lead; escalate only user-required external/account/capital/credential/live-authorization choices.

Orchestration catalog contains 22 configured specialist roles, but the authoritative allowance-saving policy is now strict: normal work uses 2–3 active agents, hard concurrency ceiling is 4, and no more than 2 `venue_researcher` workers may run concurrently. Venue/source work must be split into small checkpointed batches with narrow context. Routine venue collectors use medium reasoning where configured; high reasoning is reserved for key synthesis/audit/red-team/final-review tasks. This replaces the earlier 8/16-thread policies after observed disproportionate Work/Codex allowance consumption.

The user stopped the latest cloud run after excessive allowance consumption. Repository HEAD had not advanced beyond the control-policy commit at the stop check, so no incomplete cloud-produced audit result is being treated as evidence. Resume from the existing preregistered exchange audit, not from assumptions about unfinished cloud work.

Rationale for the current gate: Bybit public market-data/instrument endpoints are blocked with HTTP403 in the current research environment, historical tick provenance remains unresolved, and the user requires a wider venue search that explicitly prioritizes lower bot/API fees as well as data/API quality. Starting a 365-day Bybit-only prospective clock before selecting the best venue would create avoidable lock-in.

The open gate audits at minimum OKX, Binance Futures, Hyperliquid, Gate, Bitget, Bybit, KuCoin Futures, BloFin, MEXC, Kraken derivatives/futures, Coinbase International where applicable, and Deribit where applicable.

The audit must freeze two separate rankings:
- Research / Validation Venue
- Future Execution Venue

Primary comparison dimensions: API-specific maker/taker fees and normalized round-trip cost, funding-data capability, public historical data/tick metadata provenance, public endpoint accessibility, liquidity/spread/depth/slippage, bot order/margin/SL-TP functionality, API permissions/safety, rate limits and operational reliability.

No strategy financial outcome may be run/read. No prospective OOS clock may start until exchange selection is frozen and a later capture-registration gate explicitly opens it.

Required core functions remain available, but use them in staged batches rather than all at once: cost_funding_auditor, historical_data_engineer, market_microstructure_auditor, execution_auditor, tick_metadata_researcher, statistics_robustness_analyst, overfit_red_team, final_independent_reviewer. Additional configured launch roles may be used only when relevant: venue_researcher, api_reliability_auditor, exchange_security_auditor, exchange_adapter_architect, platform_backend_architect, devops_observability_engineer, risk_controls_auditor.

Protected freezes remain immutable:
- baseline `ba65e91c2b1675f48e80ac785bb3adf89d17bb0b`
- failure audit `8ca75ed35876d8f5d4d363e9e8808d7bd4417e87`
- v3 design `62590f1e09e2fa7516038ba1b3d813b0411d93ab`
- v3 implementation `43e57ee5c7867dd9421961629746555c8a2e9556`
- v3 metadata recovery `7e89543ef9b443ac65b64f125c919e885dccf37b`
- v3 prospective readiness `fdf5b95e34c724ab73e8f3e64d36aed562ad965b`

Historical financial backtest ready=false and authorized=false.
OOS registration: none.
Production candidate: NONE.
PAPER_TRADING_READY=false.
REAL_TRADING_READY=false.
trade_entry_allowed=false.

Exchange audit scoring/probe protocol preregistered before venue collection: `docs/exchange_selection_audit_v1/SCORING_PREREGISTRATION.json`, SHA-256 `ab7add22e1ab5efd543499729c431e03fda1fd6f213063c94bbbf6614e9ce699`. Fixed weights/missing-data penalties/hard gates/sensitivity; no cloud-produced venue evidence has yet been frozen after the interrupted run.
