# Next Task — MACHINE_STRATEGY_v3 OKX Failure Audit v1

Continue from the frozen first OKX development result. Do not rebuild Stage A, compatibility implementation or rerun the historical strategy.

## Frozen references
- Policy preregistration: `23f275cae85d1cab4d91cc07351ffdef2560d75d`.
- Compatibility READY: `e57b15091bda7e994133e586d7ab851d32011c5d`, manifest `5faeb02bd244777aa416d57f50f9809d9e59abe1eb2ec2fc8c062de721619fd1`.
- First financial run checkpoint: `2d7770680867f93948d4d26b91633cbb8cdbc9136bd54a988436a687accc6dd0`.
- Financial audit freeze: `129bde6fe60600449c6740d5cca4e093a20549f1a678390931836d081b50f4c2` in `docs/machine_strategy_v3_okx_financial_audit_v1/freeze_manifest.json`.
- Decision: `MACHINE_STRATEGY_V3_QUALIFICATION_STOP`.

On fresh checkout restore exact raw audits with `python scripts/pack_okx_v3_catalog_audits_v1.py --restore`, then verify `python scripts/verify_okx_v3_financial_audit_v1.py --resume-existing --expected-manifest-sha256 129bde6fe60600449c6740d5cca4e093a20549f1a678390931836d081b50f4c2`. Neither command evaluates trades.

## Evidence already complete
All 99 reference candidates and nine scenario states are preserved: 20 all-nine CLOSED, 70 no fill, nine eligibility disagreements. The incomplete CLOSED subset has negative gross/net R and cash; all four coin/direction R groups are negative and small. The whole 99-candidate catalog cannot satisfy CLOSED>=200. Accounting, matched resume, lossless restoration, independent statistics/red-team/final STOP review are complete. Do not repeat them unless new evidence exposes a defect.

## Current scope
Complete and freeze a causal failure audit using existing outputs and decision-time geometry only:
1. Trace admission scarcity through raw formations, pending, confirmation/context/refinement, sibling/reservation and fill stages. Distinguish repeated retry counters from unique candidates.
2. Trace the nine eligibility disagreements to exact grids, selected entry/stop/FTA, zone and economic rejection reasons. Preserve the partially CLOSED disagreement as diagnostic only; do not impute winners or erase cases.
3. Diagnose gross-edge, cost, funding, construction and no-fill failures across LONG/SHORT, BTC/ETH, branch/TF/time/context, risk denominator and holding intervals. Small positive H4/BREAKER or cash-only slices are not a strategy rule.
4. Verify symmetry and source/policy provenance before attributing losses to a market direction. Do not disable SHORT on historical performance.
5. Identify causal hypotheses and specific evidence gaps, without selecting thresholds or parameters against P&L.
6. Independently review and freeze the diagnosis before any `strategy_designer` creates a separately named, pre-outcome version.

Use serial read-only `strategy_explorer`, `execution_auditor`, and `backtest_reviewer` roles as needed, plus independent final review. Root is the only writer. Create `docs/machine_strategy_v3_okx_failure_audit_v1/`, reports/QA/freeze manifest, update STATUS/CURRENT_STATE, commit/push in `machine-v3-research`.

No new financial backtest, no optimization, no existing-rule edits. No OOS/PAPER/LIVE/private exchange API/orders or platform work. `trade_entry_allowed=false`.
