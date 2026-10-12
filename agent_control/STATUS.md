# Agent Status

State: V3_DESIGN_FROZEN_FIRST_FINANCIAL_STOP

Branch: `machine-v3-research`.

Failure audit is frozen and immutable.
- Audit commit: `8ca75ed35876d8f5d4d363e9e8808d7bd4417e87`
- Published audit head: `d143bb9d8aee44e0a40cef653fec07e7d1df7243`
- Audit namespace: `docs/machine_strategy_failure_audit_v1/`
- Audit QA: PASS (963 tests + independent review)

The `agent_control/NEXT_TASK.md` design gate is completed and frozen. No v3 financial backtest was run.

V3 design namespace: `docs/machine_strategy_v3_design/`.
V3 design freeze commit: recorded in the subsequent control-state commit after freeze.
Spec SHA-256: `c3876fa2239268f251454304d66a5828f6928e379c27398d4ded3b9c99786ed8`.
Manifest SHA-256: `f612b806292844e5d17bee783c9e04879e4a3d32530570a900a467e4ca2e5cc0`.

Required design principles:
- do not disable SHORT merely because v2 SHORT lost money;
- do not mine profitable subgroups;
- redesign direction/context symmetrically;
- address structurally tiny risk denominators and cost/R instability;
- address entry/nearest-FTA economics without moving targets to manufacture R:R;
- preserve causal timestamps and explicit intrabar uncertainty;
- preregister dataset exposure and genuinely untouched OOS before the first v3 outcome;
- freeze every v3 rule before viewing aggregate v3 P&L.

Actual roles used: strategy_explorer, execution_auditor, strategy_designer, backtest_reviewer through cloud collaboration with configured gpt-6-sol/high instructions. Native ECC config/read separately verified all four roles, multi_agent=true and 348 enabled skills; project layer `/workspace/-/.codex` effective. ECC verification-loop applied; hooks not activated. Final independent reviewer and execution auditor returned PASS for the nonfinancial contract scope.

Architecture: symmetric completed H1/H4/D1 trend/range/mixed-transition/uncertain state, M15 refinement, all five setup families retained; fixed structural boundaries plus verified tick rounding; nearest-FTA strictly positive modeled net feasibility; MODELED_CASH_STOP_R with raw risk/cost/notional diagnostics; conservative OHLC ambiguity WAIT, occurrence intervals, immutable pattern-end SFP ATR, contiguous M15 coverage and physical/POI reservation. These are pre-outcome machine hypotheses, not SOURCE_RULE promotions, calibrated optima or execution/profitability proof.

Implementation state: NONFINANCIAL_CONTRACT_CORE. Historical raw-family/state/target-inventory adapter and full case runner are not implemented in this gate. Grid source authenticity/completeness remains a required adapter precondition. OHLC touch fills and stop prices are declared theoretical assumptions, not queue/spread/partial-fill proof.

QA: 999 full tests PASS (36 new synthetic methods); 90.11% new contract-core coverage; Ruff/format, mypy, compile and Original resume PASS.12 generated outputs byte-identical under fresh replay. Exact integer timestamp guards close fractional proof-time truncation; valid future metadata append/mutation preserves prefix. Static admission scan finds no realized outcome column reads. Frozen Original/source/baseline/v2.x/audit invariance PASS. New manifest directly pins 92 inventory data files, 13 cited primary source documents, source/exposure evidence and frozen primitives. Verified v3 `--resume-existing`: PASS.

Exposure: 92 physical records = 74 canonical native/public histories + 6 overlapping raw source representations + 12 derived D1. Native 40 contains 993,575 candles. All are exposed development; old2026TEST is explicitly not untouched OOS. Source representations can differ in OHLCV and content hashes; they are not new independent history.

First v3 financial backtest ready: false.
STOP reasons: HISTORICAL_EVENT_ADAPTER_NOT_IMPLEMENTED; NO_VERIFIED_HISTORICAL_TICK_EPOCHS.
Independent OOS gate: STOP_NO_PRISTINE_OOS.

Exact future OOS plan: BTC/ETH Bybit USDT linear perpetual, completed M15 plus UTC H1/H4/D1; first UTC D1 OPEN strictly after the later complete-implementation pre-outcome freeze and append-only OOS registration commit timestamps. Current partial-core design freeze alone cannot start this clock. Lock365 UTC days and365 days prior contiguous warmup, with no pre-start orders/carried positions. Resolve/register start/end before first observation. No interim candidate signals/positions/P&L; raw access only logged integrity checks by a role/script without strategy state. Missing preregistration, embargo, metadata or data continuity => STOP, no post-outcome date shift. No pristine data or ready warmup is currently established.

Next prerequisites: implement and independently freeze the full causal historical adapter without P&L, establish archived tick-epoch provenance/coverage, and register genuinely untouched evaluation. Do not treat this design QA as financial authorization or qualification. Funding, actual fills/spread, sizing/margin and independent validation remain unresolved.

V3 financial result: UNKNOWN_NOT_RUN. No new financial result is authorized in this completed phase.
Production candidate: NONE.
PAPER_TRADING_READY=false.
REAL_TRADING_READY=false.
trade_entry_allowed=false.
