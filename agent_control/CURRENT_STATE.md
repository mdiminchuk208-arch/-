# Current State

Branch: `machine-v3-research`.

## User priority
Strategy first. Platform/site/integration work is paused until the strategy has a defensible validation result.

## MACHINE_STRATEGY_v3 status
`MACHINE_STRATEGY_v3` design and implementation are frozen, but the strategy is NOT yet qualified as a trading candidate.

Known facts:
- frozen v3 design exists;
- frozen v3 implementation/runner exists;
- prior implementation/readiness QA passed substantial deterministic tests;
- no accepted historical v3 financial qualification result exists yet;
- no OOS clock has started;
- PAPER/LIVE are still off.

Therefore: v3 is coded/frozen, not finished as a validated strategy.

## Selected venue for strategy and future trading path
The project has already selected **OKX** from the exchange-analysis direction that compared OKX / Kraken / Deribit / Hyperliquid.

Use OKX as the primary venue for:
- strategy market data;
- historical validation inputs;
- metadata/cost/funding assumptions where evidence is defensible;
- the future trading integration target unless a later explicit evidence-based reselection gate changes it.

Primary products:
- BTC-USDT-SWAP
- ETH-USDT-SWAP

Backtesting is executed by the project's own deterministic Python runner in the repository, not by an exchange website. Primary market inputs come from official/public OKX data and retained OKX evidence.

Existing OKX evidence establishes current public reachability, exact product identity, current instrument metadata, native 15m point reachability, books and funding-history access. It does NOT yet establish complete historical continuity, historical tick/filter epochs or exact ordinary API SWAP fee applicability. Those are the active qualification-readiness items.

## Why rules stay frozen during the next test
The next step is not to change v3 before seeing a fair result. First run a preregistered validation of the frozen version. If it fails, preserve the failure evidence and then design a new explicit strategy version (v3.1/v4) before another financial evaluation.

## Active gate
`MACHINE_STRATEGY_v3 Qualification v1`.

Current Stage A1 is pre-outcome readiness:
- pin exact frozen strategy inputs/hashes;
- establish continuous OKX BTC/ETH native M15 data path and completed-bar/timestamp semantics;
- resolve historical tick/lot/filter treatment without backdating current metadata;
- freeze OKX fees/slippage/funding assumptions;
- freeze qualification metrics/pass-fail rules;
- verify no-lookahead/deterministic replay readiness;
- STOP before reading new financial outcomes.

If Stage A1 PASSes, the next gate is the one-shot historical financial validation of frozen v3 on OKX. If v3 fails that validation/robustness gate, the next work becomes strategy redesign, not platform work.

## Safety state
Production candidate: NONE.
Historical financial v3 backtest ready=false and authorized=false until Stage A readiness PASS.
OOS registration: none.
PAPER_TRADING_READY=false.
REAL_TRADING_READY=false.
trade_entry_allowed=false.

Protected freezes remain immutable unless a later explicit strategy-version gate supersedes them.
