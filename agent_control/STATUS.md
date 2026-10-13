# Agent Status

State: MACHINE_STRATEGY_V3_QUALIFICATION_STOP / CAMPAIGN_BLOCKED_AT_STAGE_A
Branch: `machine-v3-research`.

User priority is explicit: the project lead owns the strategy loop end-to-end. Do not require routine user steering. The next user-facing milestone is strategy qualification sufficient to reopen platform reconnection planning.

## Strategy truth
`MACHINE_STRATEGY_v3` is coded/frozen but not yet qualified. The project must determine whether v3 can meet the hard launch target and, if not, autonomously freeze its failure evidence and move to a new explicit version.

## Hard user target
A promoted strategy version must achieve:
- Win Rate >= 70% on the applicable qualification sample;
- positive net expectancy after realistic fees/slippage/funding;
- positive net P&L;
- the preregistered Profit Factor/drawdown/loss-streak and robustness requirements;
- no critical leakage/lookahead;
- survival of OOS/forward validation and Paper qualification.

The 70% target is not waived for a strong in-sample result. It remains required on OOS/forward and Paper qualification samples.

## Selected venue
OKX is the active strategy/data/trading target unless a later evidence-based reselection gate explicitly changes it.
Primary products:
- BTC-USDT-SWAP
- ETH-USDT-SWAP

Backtesting uses the repository's deterministic Python runner with official/public OKX data and retained OKX evidence.

## Active campaign
`agent_control/CURRENT_BATCH.md` now defines the autonomous serial strategy campaign:
1. finish v3 readiness;
2. one-shot historical validation;
3. robustness/failure audit;
4. if failed, freeze evidence and create a new explicit strategy version;
5. repeat until a robust candidate qualifies or a genuine user-required blocker appears;
6. pristine OOS/forward validation;
7. Paper qualification (minimum 200 CLOSED + 30 calendar days plus metrics);
8. only then reopen platform reconnection planning.

No routine user confirmation is required between these steps.

## Allowance policy
SERIAL-FIRST: normally one specialist at a time; hard ceiling two threads, second only for independent review. Medium reasoning for routine engineering/data work; High reserved for critical statistical/red-team/final review. Checkpoint/push after each stage/version and resume rather than repeat if allowance ends.

Platform/site/integration implementation is paused until the strategy reaches the platform-reconnection milestone.

Historical financial v3 backtest remains unauthorized until readiness prerequisites are frozen, after which the campaign may open the one-shot validation gate without asking the user for routine approval.
OOS registration: none yet.
Production candidate: NONE.
PAPER_TRADING_READY=false.
REAL_TRADING_READY=false.
trade_entry_allowed=false.

## Stage A checkpoint — OKX Qualification v1

Pre-outcome readiness in progress under docs/machine_strategy_v3_okx_qualification_v1/. STAGE_A_PREREGISTRATION.json pins the two complete UTC development years 2024-10-13→2026-10-13, 365-day warmup from 2023-10-14, WR>=70% and other fixed qualification thresholds before any financial outcome. Eleven new public-data integrity tests pass; new collector uses exact Decimal, confirm=1, exclusive historical pagination, continuity rejection, append-only raw receipts and resumable checkpoints. It imports no strategy/outcome runner. Frozen runner is Bybit-bound with fixed modeled fees/slippage and funding=null; no silent OKX substitution or financial authorization. Ordinary OKX API SWAP fee and historical epochs still unresolved. Official historical funding archive lead is being checked with one scoped cost specialist.

Next autonomous action: acquire/verify continuous native OKX M15, recover official funding archive and historical tick/lot treatment; independently audit Stage A, then freeze PASS or exact blockers before financial access. PAPER/LIVE=false; trade_entry_allowed=false.

## Frozen Stage A — qualification STOP

Decision: MACHINE_STRATEGY_V3_QUALIFICATION_STOP, Stage A only. Freeze commit: `5a63716e0a042d8b1778581ae0d513d6314fb188`. Namespace: `docs/machine_strategy_v3_okx_qualification_v1/`. Manifest SHA-256: `e8733326e85b6082a33f11ec001066d33bc345bcded6acda26b54cd56ddeb9f0`. Preregistration commit aa10ed0d65e97ab7f3b58a06ed8d3151f7f72371; prereg SHA-256 74d161d04dc5634859b1e6e1b8fa07d60281c86fde7b4a02d0bced15f3c93988.

Completed and preserved: native official OKX BTC/ETH M15 acquisition, 105,120 candles/product (210,240 total), no gaps/duplicates/interpolation, 365-day warmup plus two full UTC development years; deterministic H1/H4/D1 derivation. Forty-eight official monthly funding ZIPs plus recent API yield 2,190 signed actual settlements/product; all 4,380 scoped rows match raw sources and 60 archive/API overlaps per contract match. 702 native pages and 774 total response receipts verified. New nonfinancial input bridge labels OKX and modeled close availability honestly.

QA PASS for new data/evidence infrastructure: 24 targeted tests, Ruff/format, mypy/compile, byte-identical readiness/native/derived replay, protected hashes and parent freeze resume. Inherited full suite not rerun/claimed PASS. Independent marker FINAL_STAGE_A_STOP_REVIEW_PASS. Actual serial specialists: /root/okx_stage_a_cost_funding (cost/funding, official archive recovery); /root/okx_stage_a_tick_audit (filter/compatibility audit); /root/okx_stage_a_final_review (independent QA/replay/STOP seal). Root sole implementation writer; no strategy_designer, parameter search or concurrent collectors.

Hard evidence barriers: no complete verified historical OKX tick/lot/filter epochs; bounded announcement API probes HTTP403 Cloudflare1010, not evaded. Current metadata, candle decimals/GCD or arbitrary coarse grid are not historical proof or guaranteed conservative substitute. Ordinary account-applicable API SWAP fee remains UNKNOWN: FAQ example and Spot frontend cannot establish it. The old financial runner is Bybit-bound/ex-funding; venue/funding outcome binding is deferred technical work while source barriers remain unresolved, not a financial result.

WR>=70% and all additional preregistered numeric criteria remain immutable for the eventual validation. No new v3 financial outcome was run/read; v3 is neither qualified nor financially failed. Do not open a strategy-redesign gate to hide a readiness barrier. Stage B remains unauthorized, OOS not registered, PAPER/LIVE=false, trade_entry_allowed=false.

Resume: `python scripts/verify_okx_stage_a_v1.py --resume-existing --expected-manifest-sha256 e8733326e85b6082a33f11ec001066d33bc345bcded6acda26b54cd56ddeb9f0`. Reuse completed candles/funding and frozen inputs; never recollect/rebuild this sealed namespace. Next readiness repair needs defensible historical filter coverage and applicable fee evidence, or a separately versioned genuinely conservative compatibility policy accepted independently before outcomes. New sources/repairs belong in a new namespace; no fake verified epochs, no cheaper fee assumptions or repeated blocked-route evasion. The autonomous campaign stays active but is blocked at this evidence barrier, not waiting for routine parameter approval.
