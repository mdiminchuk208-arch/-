# Venue researcher contract

Read full NEXT_TASK.md, LAUNCH_DIRECTIVE.md and frozen scoring preregistration.
Assigned two venues due cloud concurrency cap; keep independent venue directories.
Root alone writes implementation/scoring. No ranks/strategy/state/outcome reads.

Write only `evidence/<slug>/`: raw captures/receipts, SOURCE_INDEX.json, FACTS.json,
RESEARCH.md. Use helper `scripts/exchange_selection_public_capture.py` when ready,
or a temporary stdlib helper with same preserved proxy/CA/TLS and no cookies/auth.
Official host only, public GET or Hyperliquid public info POST. No private queries,
geo-block evasion, account session, fabricated success or remembered fee claim.
Retain headers allowlist only, UTC request start/completion, latency, raw SHA/status.

FACTS.json fields: venue; products {BTC,ETH} with exact symbols, margin/settle/model
and identity source IDs; fees {maker_rate,taker_rate,api_specific,base_tier,source_ids,
literal_quote,discounts_separate,unresolved}, where rates are decimal fractions
(not percent), null if current API applicability is unproven; funding {intervals,
formula,sign,history_endpoint,history_depth,surcharge,source_ids}; data {native_m15,
oldest_actual_m15_sample_utc,pagination,closure,archive,trades,book_history,mark_index,
oi_history,source_ids}; metadata {current_filters,change_history,historical_epochs,
causal_prospective,source_ids}; execution {rest_ws,isolated_margin,leverage,reduce_only,
sl_tp,client_order_id,queries,key_permissions_no_withdraw,ip_allowlist,status_feed,
rate_limits,demo,signing,custody,source_ids}; limitations; hard_research/exec blockers.
Every claim needs an ID+literal quote or parsed API field; missing fields are null.

For BOTH BTC/ETH, probe instrument filters, native M15 now and old sentinel around
2024-10-13T00:00Z (two-year path), public book (two separated samples, no long sleep),
funding history/OI where possible. If geo-blocked do not evade/retry alternate hosts.
HTTP200 is not product or history proof. Account-restricted public evidence can be
UNKNOWN. Missing archive/epoch continuity stays unknown. Book rows must normalize
exact documented contract units into base quantity, with source IDs/time; do not
infer undocumented contract multipliers. Root computes costs/slippage later.

If helper available, `capture(url,dest,method='GET',payload=None,source_kind='...')`
returns receipt with raw path. Each response is bounded, no cookies/auth retained,
no redirects automatically followed; redirects to official docs may be requested
separately after verifying host, no API geo-evasion. Stop failed endpoints honestly.
