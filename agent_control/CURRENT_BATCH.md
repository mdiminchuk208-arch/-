# Current Batch — Exchange Audit Stage 1A

Execute only this batch, then stop and report/checkpoint results. Do not continue automatically into later venues.

## Task
Perform Stage 1 low-cost hard-gate triage from `agent_control/EXCHANGE_AUDIT_RUNBOOK.md` for exactly:
1. **OKX**
2. **Binance Futures**

Use one `venue_researcher` sequentially. Do not run both venues in parallel. Medium reasoning. Narrow context only.

For each venue create/update:
- `docs/exchange_selection_audit_v1/checkpoints/okx.json`
- `docs/exchange_selection_audit_v1/checkpoints/binance_futures.json`

Each checkpoint must contain official/current evidence sufficient for the seven Stage-1 triage criteria, retrieval timestamps, source URLs, public endpoint status where probed, hashes/receipts where feasible, and explicit PASS/FAIL/UNKNOWN with reason.

Do not calculate final scores, do not launch cross-venue specialist audits, do not run red-team/final review, and do not research the next venue in this cloud run.

After both checkpoints are durable, update `agent_control/STATUS.md` with Stage 1A completion and stop. If allowance pressure or an environment blocker appears after OKX, checkpoint OKX and stop rather than repeating or pushing onward.

All v3/PAPER/LIVE invariants remain unchanged.
