# Current State

Branch: `machine-v3-research`.
Latest completed gate: MACHINE_STRATEGY_v3 pre-outcome design freeze.
Current open gate: MACHINE_STRATEGY_v3 implementation readiness freeze.

V3 namespace: `docs/machine_strategy_v3_design/`.
V3 freeze commit: `62590f1e09e2fa7516038ba1b3d813b0411d93ab`.
V3 spec SHA-256: `c3876fa2239268f251454304d66a5828f6928e379c27398d4ded3b9c99786ed8`.
V3 manifest SHA-256: `f612b806292844e5d17bee783c9e04879e4a3d32530570a900a467e4ca2e5cc0`.
Published v3 design head before readiness work: `acd9a906b288ce7405c2957ae1825c617a2543e5`.

All four project roles contributed to the v3 design through cloud collaboration. ECC verification-loop applied; hooks remain untrusted. V3 design QA: 999 tests PASS, 90.11% new-core coverage, deterministic replay/resume PASS, static/type/compile PASS, independent reviews PASS. Frozen predecessors preserved. No v3 financial outcomes have been run or viewed.

V3 is a separate machine architecture with symmetric causal states and all five families, verified-grid WAIT, structural stops, nearest-target modeled feasibility, cost-inclusive cash-stop units and explicit OHLC/timestamp uncertainty. No historical P&L tuning, direction/family deletion or portfolio overlay is permitted.

The completed v3 scope is still only a NONFINANCIAL_CONTRACT_CORE. The newly opened readiness task must implement and freeze the full historical event adapter and later-runner infrastructure exactly against the frozen spec, prove development data-grid authenticity/continuity, and establish verified historical price tick epochs. Strategy redesign is not authorized.

Current first-v3-financial-backtest blockers:
- `HISTORICAL_EVENT_ADAPTER_NOT_IMPLEMENTED`
- `NO_VERIFIED_HISTORICAL_TICK_EPOCHS`

First v3 financial backtest ready=false until both blockers are objectively removed and the complete implementation is frozen. The readiness task itself must NOT run or reveal historical v3 P&L, PF, WR, expectancy, drawdown, MFE/MAE, equity, or case-level financial outcomes.

Independent OOS remains `STOP_NO_PRISTINE_OOS`. All inventoried local/native/public/source/derived histories are development-exposed; old2026TEST is not pristine. The readiness task may verify acquisition/warmup/metadata continuity for a later prospective OOS registration but may not generate candidate signals or outcomes for that future evaluation. Exact OOS start/end require a separate append-only registration after complete implementation freeze.

Failure audit remains frozen in `docs/machine_strategy_failure_audit_v1/` at commit `8ca75ed35876d8f5d4d363e9e8808d7bd4417e87`, manifest SHA-256 `9dd7cd7a26ac503c350501a8967c7fed450888aed349542f5592162e993d1201`.

Frozen workflow head before v3 research: `ba65e91c2b1675f48e80ac785bb3adf89d17bb0b`.

Historical v2 development diagnostics remain reference-only:
- v2: 223 CLOSED, WR 52.9148%, PF 0.68294, expectancy -0.21520R, Net -47.9898R, MaxDD 78.9546R.
- v2.1: 83 CLOSED, WR 45.7831%, PF 0.83755, expectancy -0.13665R, Net -11.3418R, MaxDD 29.0633R.
- v2.2: 39 CLOSED, WR 33.3333%, PF 0.89625, expectancy -0.14008R, Net -5.4633R, MaxDD 23.6498R.

Failure-audit findings remain diagnostic only: v2 SHORT was gross-negative; modeled costs exceeded aggregate gross; nearest-FTA sub-1R geometry and tiny stop denominators were material; no sign/accounting defect was found. These findings cannot be used to mine a profitable subgroup or alter frozen v3 rules during readiness implementation.

ECC project trust/config verification is complete. Actual project config is `/workspace/-/.codex/config.toml`; all four named roles and 348 ECC skills are available. Hooks remain untrusted.

Production candidate: NONE.
PAPER_TRADING_READY=false.
REAL_TRADING_READY=false.
trade_entry_allowed=false.
