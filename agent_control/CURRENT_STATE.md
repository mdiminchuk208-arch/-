# Current State

Branch: `machine-v3-research`.
Failure audit: completed and frozen in `docs/machine_strategy_failure_audit_v1/`.
Audit commit: `8ca75ed35876d8f5d4d363e9e8808d7bd4417e87`.
Audit manifest SHA-256: `9dd7cd7a26ac503c350501a8967c7fed450888aed349542f5592162e993d1201`.

ECC project trust/config verification is complete. Actual project config is `/workspace/-/.codex/config.toml`; the initially assumed `/workspace/.codex` path is absent. All four named roles and 348 ECC skills are available. Three analysis roles ran via cloud collaboration with the configured model/instructions; strategy_designer did not run. Hooks remain untrusted.

Frozen workflow head before v3 research:
`ba65e91c2b1675f48e80ac785bb3adf89d17bb0b`

Development results:
- v2: 223 CLOSED, WR 52.9148%, PF 0.68294, expectancy -0.21520R, Net -47.9898R, MaxDD 78.9546R.
- v2.1: 83 CLOSED, WR 45.7831%, PF 0.83755, expectancy -0.13665R, Net -11.3418R, MaxDD 29.0633R.
- v2.2: 39 CLOSED, WR 33.3333%, PF 0.89625, expectancy -0.14008R, Net -5.4633R, MaxDD 23.6498R.

Important diagnostic from frozen v2 breakdown:
- LONG: 118 CLOSED, PF ~1.4625, expectancy ~+0.2294R, Net ~+27.073R.
- SHORT: 105 CLOSED, PF ~0.1913, expectancy ~-0.7149R, Net ~-75.063R.

This asymmetry is diagnostic only and must not be converted directly into a production rule without causal analysis and a new pre-outcome specification.

Frozen failure audit conclusions:
- Modeled fees/slippage exceed aggregate gross in v2/v2.1/v2.2; net remains -47.9898R/-11.3418R/-5.4633R. SHORT is already gross-negative in every version, including across v2 years and symbols.
- Nearest-FTA sub-1R geometry, fill selection and tiny stop denominators contribute to the observed failure. No unique causal signal-versus-exit decomposition is identifiable from saved realized outcomes alone.
- No direction-sign or saved accounting mismatch; timing bounds overstate same-bar wick-fill/stop precision (6/4/4 records), and unresolved cases are all LONG (5/2/1). The frozen engine and outcomes are preserved.
- v2.1/v2.2 are dependent nested development cohorts; extreme-case diagnostics and subgroup comparisons select no new parameter or exclusion.

QA: 963 tests PASS, static/type/compile checks PASS, 10 generated files byte-identical under independent audit replay, all 14 frozen machine namespaces and original/baseline/source/dataset invariance PASS. Independent review: 498 groups checked, zero mismatches, final PASS. No new historical financial backtest. All actual-history causality proof references are inherited hash-verified receipts; local projection determinism is not a new future-mutation proof.

Next gate: a separate pre-outcome MACHINE_STRATEGY_v3 design investigation is justified after this diagnostic freeze. No v3 strategy has been designed or implemented, no filters fitted to P&L, and SHORT remains enabled in the frozen research definitions. Independent OOS and exchange-realism evidence remain prerequisites for a production claim.

Execution caveats:
- historical exact tick epochs not proven;
- modeled normalized-R costs;
- funding unavailable/excluded;
- no independent forward/OOS validation;
- no paper session.

Production candidate: NONE.
PAPER_TRADING_READY=false.
REAL_TRADING_READY=false.
trade_entry_allowed=false.
