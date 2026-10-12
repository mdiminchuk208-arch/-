# Execution auditor — v3 pre-outcome gate

Actual agent `/root/execution_auditor`, cloud collaboration, configured gpt-6-sol/high instructions. Independently reviewed execution/risk architecture and synthetic contracts; no historical v3 execution, private API or frozen edits.

Recommended exact price mechanics: verified causal tick epoch, passive entry rounding, immutable structural boundary rounded outward exactly once, nearest raw FTA rounded inward without skipping to a farther target. No epsilon/current filter/candle-decimal precision may substitute for historical proof. Current frozen metadata verifies zero historical intervals; missing epoch must WAIT.

Recommended cash-stop unit K=d(F-S)+(fee+slip)*(F+S). Non-gap modeled stop net equals-1 by construction, but gap risk, raw stop distance, tick count, cost share and implied notional remain visible. Units differ from v2 price-risk R. Positive modeled nearest-target net is feasibility only, not demonstrated expectancy or leverage safety. Source SFP ATR buffer must be fixed at pattern-end, not drift with decision-time bars.

Independent review identified and drove closures: aligned opposite HTF trends cannot fall through to a transition POI; mixed/transition HTF combinations have a distinct explicit context name; first wick contact needs interval/knowledge timestamps; holding-time bounds are not observation-time differences; expiry requires contiguous active M15 coverage; nearest coincident FTA IDs are retained; all required raw-risk field names match spec/code; metadata reasons are standardized; directional timestamp buckets have explicit collision priority; supplied inventory requires a complete causal adapter.

Grid representability is separate from execution proof. Resting limit and target touch imply full fills only under a declared model; stop-wick price is the modeled trigger plus slippage debit. OHLC/tick alone cannot prove queue, spread, latency, partial fills or within-bar gap fills. Any wick entry plus stop/target touch is unresolved; no continuous-path ordering assumption. Missing/changed metadata and data gaps produce WAIT/censoring without invented P&L.

Synthetic QA uses both directions, grid reflection with integral reflection origin, analytic price-dependent cost comparisons, and price+tick scaling. Historical adapter, exchange-realism, funding and portfolio evidence remain unresolved. Final reviewer receipt covers final code/artifact hashes before freeze. `trade_entry_allowed=false`.

Final independent closure: PASS for nonfinancial scope. Fractional proof timestamps such as100.9 atdecision100 are rejected by exact JSON integer checks. Malformed available epochs WAIT; future-known appended metadata leaves past selection unchanged. All36synthetic tests pass. No historical financial execution.
