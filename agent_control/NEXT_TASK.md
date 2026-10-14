# Next Task — MACHINE_STRATEGY_v4 Pre-outcome Design v1

State: DESIGN_GATE_OPEN. Continue from the completed failure audit; do not repeat diagnosis or any v3 run.

## Pinned predecessor

- Causal audit publication: `54419daa29e7e68d6f692daee9cf2132203393ef`.
- Failure audit manifest: `9b0353dbfeabfa2768f4a1f62af820c128f98c48faad09544acee4c0547867a3`.
- Financial audit manifest: `129bde6fe60600449c6740d5cca4e093a20549f1a678390931836d081b50f4c2`.
- v3 decision remains MACHINE_STRATEGY_V3_QUALIFICATION_STOP.

Verify existing failure audit with:

```bash
/workspace/crypto-bot-venv/bin/python scripts/build_okx_v3_failure_audit_v1.py --resume-existing --expected-manifest-sha256 9b0353dbfeabfa2768f4a1f62af820c128f98c48faad09544acee4c0547867a3
```

On fresh checkout first restore exact raw audits using `scripts/pack_okx_v3_catalog_audits_v1.py --restore`; neither restoration nor verification evaluates trades.

## Execute

Read and execute `docs/machine_strategy_v4_design_v1/DESIGN_GATE_PROTOCOL.md` completely, using pinned `DESIGN_INPUTS.json`. Produce all required design artifacts, one pre-outcome specification, explicit source/policy/technical choices, synthetic QA, independent review and external design freeze. Update STATUS/CURRENT_STATE, commit/push to machine-v3-research. Open implementation readiness only after design PASS; STOP honestly if a material external blocker prevents identification.

Use serial strategy_designer, execution_auditor, backtest_reviewer and final_independent_reviewer roles. Root is sole writer, hard ceiling root plus one specialist. The failure audit is already independently frozen, so strategy_designer is now permitted for this separate version.

Do not select rules/parameters by the exposed historical P&L. Preserve source alternatives, LONG/SHORT symmetry and all qualification thresholds including WR>=70%. No v3 edits/rerun; no v4 historical strategy/financial run, OOS execution, PAPER/LIVE, private API/orders or platform work. trade_entry_allowed=false. ECC hooks inactive.
