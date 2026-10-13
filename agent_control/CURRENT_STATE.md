# Current State

Branch: `machine-v3-research`.

## User priority
Strategy first. Platform/site/unified-exchange-layer work is paused until the strategy has a defensible validation result.

## MACHINE_STRATEGY_v3 status
`MACHINE_STRATEGY_v3` design and implementation are frozen and reproducible enough to inspect/test, but the strategy is NOT yet qualified as a trading candidate.

Known facts:
- frozen v3 design exists;
- frozen v3 implementation/runner exists;
- prior implementation/readiness QA passed substantial deterministic tests;
- no accepted historical v3 financial qualification result exists yet;
- historical tick/filter provenance and executable historical data compatibility have been unresolved blockers;
- current metadata must not be silently backdated;
- no OOS clock has started;
- PAPER/LIVE are still off.

Therefore: v3 is **coded/frozen, not finished as a validated strategy**.

## Why rules stay frozen during the next test
The next step is not to randomly improve v3 before testing. That would create post-hoc tuning/overfit risk. First run a preregistered fair validation of the frozen version. If it fails, preserve the failure evidence and then design a new explicit strategy version (v3.1/v4) before another financial evaluation.

## Active gate
`MACHINE_STRATEGY_v3 Qualification v1`.

Current Stage A1 is pre-outcome readiness:
- pin exact frozen strategy inputs/hashes;
- establish BTC/ETH validation data path, preferably Bitget public USDT perpetual data;
- verify continuous M15/timestamp/completed-bar semantics;
- resolve historical tick/lot/filter treatment without backdating current metadata;
- freeze fees/slippage/funding assumptions;
- freeze qualification metrics/pass-fail rules;
- verify no-lookahead/deterministic replay readiness;
- STOP before reading new financial outcomes.

If Stage A1 PASSes, the next gate is the one-shot historical financial validation of frozen v3. If v3 fails that validation/robustness gate, the next work becomes strategy redesign, not platform work.

## Venue scope
The original project live/execution set remains:
- Bybit
- Bitget
- BloFin
- MEXC

A broader exchange audit was performed and is retained as research evidence, but its additional venues are not automatically part of the user's live plan. Bitget may be used as the public research/validation source because its retained evidence is more accessible; that does not force Bitget to be the only live exchange.

## Preserved exchange-selection research
`EXCHANGE_SELECTION_AUDIT_v1` remains frozen as conditional nonfinancial research:
- freeze commit `ff20ac4bee75d605c0a7f4234fe74bb89a337fbf`
- manifest SHA-256 `06556298d9f8041c493af5225740425cdfc51807566a322e2dd86f944b9c24d5`
- final marker `FINAL_REVIEW_PASS_FOR_EXCHANGE_SELECTION`

## Safety state
Production candidate: NONE.
Historical financial v3 backtest ready=false and authorized=false until Stage A readiness PASS.
OOS registration: none.
PAPER_TRADING_READY=false.
REAL_TRADING_READY=false.
trade_entry_allowed=false.

Protected freezes remain immutable unless a later explicit strategy-version gate supersedes them.
