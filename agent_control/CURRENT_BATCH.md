# Current Batch — Exchange Audit Stage 1A-OKX

Execute only this batch, then stop and report/checkpoint the result. Do not continue automatically into Binance or any other venue.

## Task
Perform Stage 1 low-cost hard-gate triage from `agent_control/EXCHANGE_AUDIT_RUNBOOK.md` for exactly one venue:
- **OKX**

Use exactly one `venue_researcher`. No parallel subagents. Medium reasoning. Narrow context only: the exchange-audit preregistration, runbook, venue worker contract, and current batch. Do not load frozen strategy/history artifacts unless a specific triage criterion strictly requires them.

Create/update exactly this durable checkpoint:
- `docs/exchange_selection_audit_v1/checkpoints/okx.json`

The checkpoint must contain official/current evidence for the seven Stage-1 triage criteria, retrieval timestamps, source URLs, public endpoint status where probed, hashes/receipts where feasible, and explicit PASS/FAIL/UNKNOWN with reason.

Do not calculate final scores. Do not launch cross-venue specialist audits. Do not run red-team/final review. Do not research Binance or another venue in this cloud run.

After the OKX checkpoint is committed and pushed, update `agent_control/STATUS.md` to `EXCHANGE_SELECTION_AUDIT_V1_STAGE_1A_OKX_COMPLETE` and STOP. If an environment/access blocker prevents completion, persist the evidence gathered, record the blocker in the checkpoint/status, push, and STOP rather than retrying broadly.

All frozen v3/PAPER/LIVE invariants remain unchanged; `trade_entry_allowed=false`.
