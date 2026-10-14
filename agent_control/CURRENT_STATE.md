# Current State

Branch: `machine-v3-research`. Strategy first; platform/site work remains paused. Production candidate: NONE. OOS not registered; PAPER=false; LIVE=false; `trade_entry_allowed=false`.

## Frozen references

- Baseline: `ba65e91c2b1675f48e80ac785bb3adf89d17bb0b`; original/v2/v2.1/v2.2 and source fidelity artifacts unchanged.
- OKX Stage A: `5a63716e0a042d8b1778581ae0d513d6314fb188`, manifest `e8733326e85b6082a33f11ec001066d33bc345bcded6acda26b54cd56ddeb9f0`. Reuse all 210,240 completed native M15 bars, derived H1/H4/D1 and 4,380 signed funding rows; no recollection.
- Compatibility policy: `23f275cae85d1cab4d91cc07351ffdef2560d75d`, frozen before implementation/outcomes.
- Implementation checkpoint: `0f741938df2c1e1e15a4faaf0990b5b49ce2b8a4`.
- Compatibility READY: `e57b15091bda7e994133e586d7ab851d32011c5d`, manifest `5faeb02bd244777aa416d57f50f9809d9e59abe1eb2ec2fc8c062de721619fd1`. Protected strategy and policy bytes unchanged; independent causality/final review PASS, 54 targeted tests and static/replay PASS.

## First one-shot development result

Decision: **MACHINE_STRATEGY_V3_QUALIFICATION_STOP**. Full frozen catalog: BTC 50 + ETH 49 = 99 unique candidates, all retained with nine scenarios. Twenty CLOSED under every scenario; 70 no fill; nine eligibility disagreements. Twenty-one fill under at least one scenario; no filled-unknown exit. Disagreements force STOP. Even all 99 candidates closing cannot reach CLOSED>=200.

The known CLOSED subset is diagnostic, not the full unresolved catalog's WR/PF. Base: 10 WIN / 10 LOSS, WR 50%, PF_R 0.278459, expectancy -0.309356R, net -6.187114R / -3420.497559USDT. Doubled costs: 9 WIN / 11 LOSS, WR 45%, PF_R 0.162663, net -9.243979R / -5196.618486USDT. Base gross cash is already negative before fees/slippage/funding. All four coin/direction R sums are negative, with 4–8 CLOSED cases each. Tiny positive H4/BREAKER/cash-only slices are not selected; SHORT remains enabled in research.

Output namespace: `docs/machine_strategy_v3_okx_financial_validation_v1/`. Audit/reports/CSV/archived logs: `docs/machine_strategy_v3_okx_financial_audit_v1/`.

Externally pinned financial run checkpoint: `2d7770680867f93948d4d26b91633cbb8cdbc9136bd54a988436a687accc6dd0`.
Financial audit freeze: `129bde6fe60600449c6740d5cca4e093a20549f1a678390931836d081b50f4c2`.

Accounting QA (99 cases / 366 scenario-column checks), completed-segment resume without trade reevaluation, lossless gzip restoration and independent statistics/red-team/final review PASS. External financial `--resume-existing` verification PASS, including after the campaign-control transition. Actual raw large audits remain in workspace; exact gzip artifacts and hashes are published. Fresh checkout: run `scripts/pack_okx_v3_catalog_audits_v1.py --restore`, then the externally pinned verifier in NEXT_TASK.

## Current gate

MACHINE_STRATEGY_V4_IMPLEMENTATION_READINESS_OPEN. Design publication `f88bff4a79a1e5c1aa64c0f16204a1f8b546fa1f` is MACHINE_STRATEGY_V4_DESIGN_PASS. Independently reviewed design frozen with external manifest `b9452dea092c0d186d2ac164c044f2fad0d865becf9904791caebbf7b477273b` at docs/machine_strategy_v4_design_v1/DESIGN_FREEZE_MANIFEST.json; positive verified reuse PASS. Implementation has not started; financial/OOS/PAPER/LIVE qualification remains absent.

Twenty-eight synthetic reference design tests, eight QA commands, byte-identical hash-only verification replay and three serial independent specialist roles PASS. Source/policy ambiguities are retained, not optimized by outcomes; immutable inherited input pins36. Actual identities, initial STOP resolutions and limitations are preserved in the v4 namespace.

The separately named v4 implementation-readiness gate is now open; execute NEXT_TASK.md and V4_IMPLEMENTATION_READINESS_WORK_ORDER.md. It must prove actual historical adapter/runner completeness, production prefix/future-mutation/replay and exact funding binding before complete implementation freeze. No historical v4 financial result may be generated or viewed in that gate. Financial validation requires its own later authorization.

ECC ecc@ecc 2.2.3 enabled; hooks inactive. trade_entry_allowed=false; no OOS execution, PAPER/LIVE/private API/orders/platform work. v3 and every earlier frozen result remain unchanged.

## Causal failure audit completed

MACHINE_STRATEGY_V3_OKX_FAILURE_AUDIT_COMPLETE. Namespace: docs/machine_strategy_v3_okx_failure_audit_v1/. External manifest SHA:9b0353dbfeabfa2768f4a1f62af820c128f98c48faad09544acee4c0547867a3; positive --resume-existing PASS. No new v3 trade/financial evaluation.

Verified mechanisms:11947 unique raw formations/9569 physical buckets;10511 terminal non-smooth vetoes before context;42 no-entry-touch one-hour expiries;28 target-OPEN cancellations (18 already beyond FTA at completed decision CLOSE);9 disagreements from unrepresentable synthetic zones. Known20-CLOSED payoff remains negative; partial closure diagnostic only. Fixed reference U and all99cases preserved.

Exact per-origin WAIT transitions remain unavailable from saved aggregate logs; bounds/evidence gaps are explicit. Distinct context fields:18 admission context origins versus20 selected H1 impulses. Eight new synthetic boundary tests, sixQA commands and byte-identical diagnostic replay PASS. Strategy explorer, execution auditor, backtest reviewer and fresh final independent reviewer all completed serially; no designer ran before freeze.

Conditional hypotheses justify opening MACHINE_STRATEGY_v4 design-only after this audit publication. No numeric parameter or profitable subgroup has been selected; no new financial/OOS/PAPER/LIVE/private API/orders permission. trade_entry_allowed=false.

## v4 diagnosis-to-design transition

The H00-H05 contracts have now been adopted as separately versioned pre-outcome machine choices and independently accepted; earlier audit/opening paragraphs describe historical milestones. Their economic effect remains untested. Source full/partial exit and OB/TF/approach alternatives remain explicitly unresolved as source authority.
