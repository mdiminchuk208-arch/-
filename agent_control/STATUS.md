# Agent Status

State: FAILURE_AUDIT_FROZEN_V3_DESIGN_GATE_OPEN

Branch: `machine-v3-research`. Failure audit task completed; no v3 rule or financial rerun created.

Audit commit: recorded in the subsequent control-state commit after the diagnostic freeze.

Audit: `docs/machine_strategy_failure_audit_v1/`.
Freeze manifest SHA-256: `9dd7cd7a26ac503c350501a8967c7fed450888aed349542f5592162e993d1201`.

Verified cloud ECC runtime:
- launcher `/workspace/ecc-setup/codex-ecc`, Codex `0.159.0-alpha.3`, CODEX_HOME `/workspace/ecc-setup/codex-home`;
- `ecc@ecc` v2.2.3 installed/enabled, 348 unique enabled skills, no skill read errors;
- native config/value/write trusted `/workspace` and the actual Git root `/workspace/-`, without a global trust bypass;
- native config/read confirms active project layer `/workspace/-/.codex`, disabledReason=null, multi_agent=true and all four named roles; `/workspace/.codex` does not exist in this checkout;
- research skill YAML frontmatter repaired so native skills/list recognizes it; instruction body unchanged;
- ECC hooks remain untrusted; no hook activation.

Actual independent agents: strategy_explorer, execution_auditor, backtest_reviewer through cloud collaboration, using the configured gpt-6-sol/high role instructions. Native CLI role availability was verified separately; these were not native CLI agent_type launches. strategy_designer was available and not launched.

Principal findings:
1. v2 SHORT has negative gross before costs across each year and both symbols. 2024/RANGE concentrate losses, but losses extend beyond them. No SHORT exclusion follows.
2. Modeled costs exceed aggregate gross edge in all three versions. Many CLOSED v2 plans target a nearest FTA below 1R (LONG 89/118; SHORT 78/105), and fill selection changes the observed geometry distribution.
3. Tiny structural stop denominators inflate both gains/losses and modeled costs in R. v2.2 is sensitive to single extreme observations; its nested subsets do not prove an optimal threshold.
4. No saved direction-sign/accounting error in 345 CLOSED version records. Wick-fill/same-bar-stop timing bounds overstate precision in 6/4/4 records; unknown intrabar elapsed time is retained. Frozen execution remains unchanged.
5. All unresolved intrabar cases are LONG (5/2/1), limiting resolved-only direction comparisons. Calendar/symbol/branch/context slices overlap and are not independent experiments.

QA: PASS. 963 tests; Ruff (full checks on new code, inherited fatal checks), compile, mypy, Original verified resume; 10 generated artifacts byte-identical under fresh diagnostic replay; all 14 frozen machine namespaces and original/source/baseline/dataset invariance verified. All 1372 pre-entry case-version rows passed outcome isolation, recursive known_at/end_swing_at and saved execution chronology checks; filled/closed partitions and counts/statuses match. Independent reviewer recomputed 498 groups without mismatches and returned PASS. Actual historical midpoint/future-mutation proof is inherited unchanged, not freshly rerun. The local saved-case projection check claims determinism only.

Unresolved: unique causal attribution of signal versus fill/exit policy; historical ticks/spread/funding; executable sizing/portfolio/margin; intrabar outcomes/timing; meaningful frozen D1 regime labels; untouched OOS/forward evidence.

Evidence justifies investigating a separate MACHINE_STRATEGY_v3 pre-outcome design now that this audit is frozen. It does not select rules/parameters or establish profitability. Any later implementation/evaluation needs its own frozen specification and independent validation protocol. Production candidate: NONE. PAPER_TRADING_READY=false; REAL_TRADING_READY=false; trade_entry_allowed=false. No PAPER/LIVE/private exchange API use.
