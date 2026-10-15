# Current batch — v4.1 cached-evidence causal failure audit review

State: `MACHINE_STRATEGY_V4_1_FAILURE_AUDIT_REVIEW_PENDING`.

Frozen predecessor: `MACHINE_STRATEGY_V4_1_DEVELOPMENT_FINANCIAL_STOP`. Its result namespace and code/data/results remain immutable. External result manifest SHA256 `d0a05dcd49545ae963a89840aa09388419b5213f963ba0bd266686e622812d74`.

Authored audit artifacts now exist in `docs/machine_strategy_v4_1_failure_audit_v1/`:
- `AUDIT_PROTOCOL.md`
- `INPUT_INVENTORY.json`
- `CAUSAL_EVIDENCE_REGISTRY.json`
- `UNRESOLVED_EVIDENCE.json`
- `FAILURE_AUDIT_REPORT.md`
- `REDESIGN_HYPOTHESES.json`

Current supported diagnosis before independent acceptance:
- 54 candidates; 46 all-nine no-fill; 8 all-nine filled; 7 all-nine CLOSED; 1 filled unresolved.
- 396 retired + 18 expired scenario states imply 44 all-nine retired candidates + 2 all-nine expired candidates.
- 7 CLOSED = 2W/5L, WR 28.5714%, PF_R 0.462899, gross -0.850574R / -132.71 modeled USDT, net -2.433195R / -613.690876 modeled USDT.
- Costs materially worsen an already-negative gross aggregate.
- Candidate stream is dominated by STB38; RANGE10, SFP5, BREAKER1, OB0. BTC LONG9 candidates/0CLOSED.
- SHORT is poor in the tiny CLOSED sample but cannot be removed post-result; positive H4/SFP/LONG tiny slices cannot be selected.
- One all-nine filled ETH LONG RANGE H1 case remains unresolved `WAIT_INTRABAR_ORDER`; no exit is imputed.

Next action is independent review/freeze only, following `agent_control/V4_1_FAILURE_AUDIT_REVIEW_WORK_ORDER.md`. No historical engine calls, financial replay, changed trade simulation, robustness/OOS, tuning or strategy design until audit PASS.

Safety: `trade_entry_allowed=false`; no PAPER/LIVE/private exchange API/orders/platform; production NONE.
