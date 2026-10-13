# Current State

Branch: `machine-v3-research`.

Latest completed gate: MACHINE_STRATEGY_v3 Prospective Data/Metadata Capture + OOS Registration Readiness Freeze.
Decision: `V3_PROSPECTIVE_READINESS_FROZEN_STOP`.
Freeze commit: `fdf5b95e34c724ab73e8f3e64d36aed562ad965b`.
Namespace: `docs/machine_strategy_v3_prospective_readiness/`.
Manifest SHA-256: `b96797ec01575303b6d4c0170f0683554386f53569ef41ad38ed3f91cf7fe45d`.

The completed prospective gate established several Bybit-specific and control-plane blockers, including HTTP403 on official public instruments/M15 capture from the current cloud environment, unresolved 365-day warmup gaps/authenticity, phase-dependent active tests, and incomplete isolation/authorization architecture. Historical verified tick coverage remains 0%; historical v3 financial evaluation remains unauthorized.

A Bybit-only prospective capture/control-v2 gate was briefly opened but was not executed. It is now superseded before implementation because the user explicitly requested a broader exchange search, including venues outside the original four, with special attention to lower API trading commissions.

## Open gate

`agent_control/NEXT_TASK.md` now opens **EXCHANGE_SELECTION_AUDIT_v1 Freeze**.

The candidate universe includes at minimum OKX, Binance Futures, Hyperliquid, Gate, Bitget, Bybit, KuCoin Futures, BloFin, MEXC, Kraken derivatives/futures, Coinbase International where applicable, and Deribit where applicable. Additional credible venues may be added with evidence.

The audit preregisters two distinct decisions rather than forcing one exchange to win everything:
1. `PRIMARY_RESEARCH_VALIDATION_VENUE`
2. `PRIMARY_EXECUTION_VENUE`
plus secondary execution and benchmark venues.

The frozen primary Execution ranking weights all-in execution cost at 35%, liquidity/spread/slippage at 25%, API/order controls at 15%, funding at 10%, operational/safety fit at 10%, and public data quality at 5%.

The frozen primary Research/Validation ranking weights historical data depth/continuity at 25%, tick/instrument provenance at 20%, public API accessibility/reliability at 20%, funding/OI/trades/orderbook history at 15%, reproducibility/docs at 10%, and execution-cost realism at 10%.

The audit must use ordinary/base-tier **API-specific** fee schedules as the primary fee comparison, distinguish web/app promotions from bot API fees, normalize maker/taker round-trip costs, and test public endpoints without private credentials, VPN/proxy/geolocation evasion. It must also measure BTC/ETH spread/depth/slippage from public books and verify exact bot requirements such as isolated margin, reduce-only, conditional SL/TP, permission granularity and rate limits.

No strategy parameters may change. No financial strategy outcome, OOS signal, position or P&L may be generated/viewed in this gate. The 365-day prospective clock must not start until venue selection is frozen and a later capture-registration gate explicitly authorizes it.

Required specialist functions: cost_funding_auditor, historical_data_engineer, market_microstructure_auditor, execution_auditor, tick_metadata_researcher, statistics_robustness_analyst, overfit_red_team and final_independent_reviewer.

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

Exchange audit in progress: scoring/missing-data rules committed before evidence at `055bcc2`; bounded public-only GitHub-hosted probe infrastructure added. No strategy/OOS/order execution.
