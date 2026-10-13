# Crypto Bot — Launch-First Project Directive

This directive is authoritative for future work unless explicitly superseded by the user.

## Primary objective
Move Crypto Bot to the earliest **safe, evidence-backed working launch**. Do not restart the project, do not redesign `MACHINE_STRATEGY_v3`, and do not open speculative strategy-improvement work while launch blockers remain.

The user delegates routine project sequencing, technical architecture choices, gate creation, reviewer selection, and repository control-layer updates to the project lead. Escalate to the user only for choices that inherently require the user: credentials/secrets, account/legal jurisdiction, real capital, irreversible external actions, or explicit authorization to enable LIVE trading.

## Immutable strategy rule
Treat the frozen v3 strategy rules as immutable through the launch path. Venue-specific adaptation may change only exchange/data/execution parameters and adapters under an explicit pre-outcome compatibility freeze. Never tune strategy rules because a venue/backtest result looks better or worse.

## Usage-efficiency policy
The configured specialist catalog may remain broad, but simultaneous agent use must be economical:

- normal gate target: **4–6 active agents**;
- hard concurrency ceiling: **8 threads**;
- never launch agents merely because capacity exists;
- batch independent venue/source research, then stop those workers before synthesis/review;
- routine venue/source collection should use **medium reasoning** where configured;
- **high reasoning** is reserved for key synthesis, statistical/robustness analysis, security/execution audits, red-team review, and final independent review;
- avoid repeatedly loading large frozen strategy namespaces into venue/data workers unless strictly required;
- reuse pinned evidence, receipts, hashes, summaries and prior artifacts rather than recollecting/re-reading them without cause;
- if a smaller competent team can close a gate, prefer it even if a larger team might be marginally faster;
- preserving Work/Codex allowance is part of launch efficiency: speed means useful progress per allowance, not maximum parallelism.

## Current gate
`EXCHANGE_SELECTION_AUDIT_v1` remains the active gate and must finish before any new 365-day prospective capture clock is started.

### Acceleration policy for the exchange audit
Parallelize independent research selectively while keeping synthesis/review independent:

- use `venue_researcher` workers for grouped or individual venues where this materially improves evidence collection;
- do not run all venue workers simultaneously by default; keep the normal total active team within 4–6 and never exceed 8;
- use `cost_funding_auditor`, `historical_data_engineer`, `market_microstructure_auditor`, `execution_auditor`, `tick_metadata_researcher`, `api_reliability_auditor`, and `exchange_security_auditor` for cross-venue verification as needed;
- use `statistics_robustness_analyst` for deterministic scoring/sensitivity;
- use `exchange_adapter_architect` and `platform_backend_architect` only to assess migration/architecture cost after objective venue evidence is collected;
- use `overfit_red_team` and `final_independent_reviewer` as independent challenge/seal;
- one implementation/writer path at a time; reviewers remain read-only.

## Fixed launch sequence after exchange selection
Unless a hard blocker requires a narrower repair gate, proceed in this order:

1. **Freeze venue selection**: primary research/validation venue, primary execution venue, secondary execution venue, benchmark venue.
2. **Unified Exchange Layer**: create venue-neutral market-data/metadata/account/order/position interfaces; preserve website and strategy core.
3. **Venue-specific v3 compatibility freeze**: bind current v3 to selected product semantics, fees, funding, tick/lot rules and execution model without strategy redesign.
4. **Verified data + metadata path**: obtain/collect defensible historical/prospective evidence; start pristine prospective capture only after registration prerequisites are met.
5. **Financial validation/backtest gate** only when evidence and authorization allow it.
6. **Pristine OOS** under the frozen preregistration/embargo protocol.
7. **Paper Trading** only after strategy qualification; minimum 200 CLOSED virtual trades + 30 calendar days and required metrics.
8. **LIVE readiness review** with risk/security/operational checks.
9. **LIVE activation** only with explicit user authorization; start conservatively and preserve kill switches.

## Parallel product work
Website/backend work may advance in parallel when it does not contaminate strategy validation. Keep Dashboard, Scanner, Portfolio, Journal, Stats, Backtest UI, Settings, Telegram alerts, Audit Log, Safe Mode, STOP AUTO TRADING and CLOSE ALL exchange-agnostic behind the unified exchange layer.

## Safety invariants
- Historical financial v3 execution stays unauthorized until an explicit gate authorizes it.
- PAPER remains OFF until qualification.
- LIVE remains OFF until qualification + explicit user authorization.
- `trade_entry_allowed=false` remains invariant until that point.
- Never request or expose private keys/API secrets in repository artifacts.
- API permissions should remain Read + Trade without Withdraw where the venue model supports API keys.
- Do not bypass geo/API restrictions with VPN/proxy/spoofing in research evidence.

## Reporting
At every completed gate, record exact PASS/STOP, freeze/manifest hashes, actual agents used, blockers, and the next narrowest gate. Prefer forward progress toward launch over reopening settled work.
