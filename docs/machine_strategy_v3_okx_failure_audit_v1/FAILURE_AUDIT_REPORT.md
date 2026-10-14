# MACHINE_STRATEGY_v3 OKX — causal failure audit

This audit explains the frozen failed qualification result; it does not change v3, create new trades, choose parameters or qualify a production strategy. The known 20 all-nine-CLOSED cases still have WR 50% and negative gross/net edge. All 99 candidates and nine states remain in the parent freeze.

## Admission scarcity

| Saved origin outcome | BTC | ETH | Total |
|---|---:|---:|---:|
| Unique raw formations | 5960 | 5987 | 11947 |
| Directional physical buckets | 4731 | 4838 | 9569 |
| Terminal non-smooth approach rejection | 5234 | 5277 | 10511 |
| Expired pending | 560 | 555 | 1115 |
| Catalog candidates | 50 | 49 | 99 |

The raw-origin partition reconciles exactly:11,823 terminal diagnostics + 99 emitted candidates + 8 EOF pending + 11 conflicts + 6 priority-losing siblings = 11,947. Non-smooth rejection affects 88.0% of raw formations and is the sole outcome in 8,270 physical buckets. It is a unique terminal disposition, not a retry count. Family raw→catalog: SFP 9,169 → 51, OB 530 → 0, STB 530 → 29, RANGE 1,512 → 10, BREAKER 206 → 9. Formation rates are descriptive because multiple families can share a physical bucket.

Protected gate order is M15 CONF after reaction → opposing BOS structural rejection → same-BOS nested SFP/OB POI → POI consumption/reservation → H1/H4/D1 context → entry/stop/nearest FTA economics → physical reservation. The early non-smooth veto masks later context outcomes; it does not prove that the rejected origins otherwise satisfy context or would be profitable. Confirmation and direction filters constrain different evidence; redundancy is a hypothesis, not an established cause.

There are 116 price-plan proposals in 110 physical groups. Ninety-nine groups emitted; 11 conflicted (ten reused POI, one physical ID); six siblings lost fixed priority. Even accepting all conflicting groups would produce at most 110 candidates. Reservations are a minor contributor to overall scarcity.

WAIT origin-bound POI 33,197 and refinement BOS 28,623 are hourly retry events. At most 17 evaluations per origin provide conservative unique-origin bounds, not exact stage conversions. The JSON gives per-product bounds. Exact WAIT overlap, unique intermediate transition rates, context snapshots of rejected origins and their confirmation timing are unavailable from these saved logs. No strategy replay was performed to invent those missing records. Discovery-time reaction_at=null does not mean no later reaction. Native raw counts include warmup/exclusions and source_validated=false; their gap cannot be attributed to source-policy normalization.

Selected formation→decision median is 4h; non-smooth terminal median is 7h, with quartiles 5/10h. Expiry terminal decisions occur 17h after formation because pending expiry is 16h and the protected comparison is strict. These timing facts motivate investigation but do not prove that confirmation arrived after a usable move on rejected origins.

## No-fill mechanics

All 70 no-fill cases have the same status under all nine scenarios. Forty-two expired after four M15 bars with no entry touch (21 LONG/21 SHORT; BTC 22/ETH 20). Twenty-eight invalidated at target-side OPEN (zero stop-side), with 18 at the first eligible OPEN and 10 later (3 at 15 min, 4 at 30 min, 3 at 45 min).

Every target-open cancellation was preceded by a completed M15 CLOSE beyond target; 18 already had the decision-time completed mark beyond the selected FTA. Twelve cancelling opens exactly equal the prior close, and others differ only by a small price increment in the saved series. Thus the stored GAP_INVALIDATED label names an OPEN rule, not necessarily a discontinuous price jump. Forty-two expiries had median first-open entry distance88.78 bp and closest-wick miss58.38 bp. These are retrospective geometric facts, not P&L or proof that a longer lifetime would work.

No-fill active-order envelopes stop at cancellation OPEN and exclude its later wicks. The separately labeled full-expiry-window market envelope may include post-cancellation prices; one case (nine states) later touches entry there, which is not an attainable fill under the retained rules. Eleven expired cases see a target-side wick without entry touch. No hypothetical fills, winners, losses or optimal expiry were calculated. Reservations/siblings precede catalog selection and cannot explain no-fill of already selected cases.

DECISION_GEOMETRY records 99 plans, distances from the available completed mark, fixed frozen SFP ATR and a separately classified diagnostic completed-TF SMA14 TR. Diagnostic ATR uses only completed bars before decision; first postdecision OPEN is explicitly retrospective. These added indicators are neither SOURCE_RULE nor strategy inputs.

## Known CLOSED edge and construction

Only 20 all-nine-CLOSED cases enter financial decomposition. The additional BTC LONG RANGE H4 disagreement with three valid closures remains separately diagnostic (+3.469 R in the adverse valid base scenario); it is not counted as a winner or removed.

Base gross = -3.114007 R, fees = 2.291637 R, slippage = 0.763879 R, signed funding = -0.017591 R, net = -6.187114 R. Net WIN average +0.238775 R versus absolute LOSS average 0.857487 R. The implied 78.22% break-even rate at this observed payoff is a descriptive arithmetic identity, not a new target or fitted threshold. WR 50% alone misses the asymmetric payoff problem; costs worsen alreadynegative sampled gross edge.

Exits:10 STRUCTURAL_FTA, 5 FIXED_INITIAL_STOP, 5 SFP_PATTERN_BODY_INVALIDATION. Reference target/stop distance median 0.4426; planned net-at-target median 0.3066 R (ex funding). Fixed reference U remains unchanged across quantities/grids/cost columns. Case U varies by coin/geometry; ETH SHORT cash +30.07 USDT can coexist with net R -0.3908, so no favorable accounting unit is selected. Body invalidation, large structural/ATR stop and near FTA are observed construction mechanisms; the audit does not infer profits from tighter stops, later exits or farther targets.

CLOSED_EDGE_DECOMPOSITION retains per-case fee/slippage/funding/net, stop/target/U/holding intervals, all coin/direction/branch/TF/context/year/month partitions and OHLC excursion lower/upper bounds. Exact ordered intrabar MFE/MAE is unobserved. Lower bounds use full exposure bars and modeled fill/exit endpoints; upper bounds admit overlapping boundary bars. Bars at/after an exact OPEN exit are excluded. Extrema are retrospective price distances D, not admission features or new financial exits.

Doubled column net = -9.243979 R. Its own chosen worst scenario differs in one case, so aggregate gross/funding differ slightly; the R denominator stays the same for each case across both columns. This change is not solely a fixed-execution fee subtraction. All four coin/direction netR sums are negative with only 4–8 cases. H4 (3), BREAKER (1) and cash-only positive slices are tiny overlapping diagnostics, not production filters. Twenty cases have 18 distinct admission `context.origin_id` values and 20 distinct selected H1 `selected_impulse.id` values. These are separate fields and definitions; admission-context overlap, BTC/ETH correlation and time partitions limit independence.

## Nine eligibility disagreements

All 48 ineligible states have REJECT_ROUNDED_ENTRY_OUTSIDE_ZONE. Eight cases have a zero-width RANGE boundary and one a narrow ETH SFP zone. At every rejected synthetic tick there is no representable price inside that frozen zone: this is not a wrong floor/ceil choice within an otherwise usable zone. Seven cases reject P05/P20, two reject P20 only; all three lot/minimum variants have identical eligibility within each price grid. No denominator, quantity or funding defect caused these rejections.

ELIGIBILITY_DISAGREEMENTS preserves all nine rows per case, raw E/SL/FTA, derived grid geometry, zone/grid feasibility and recorded status/reason. These are synthetic reference-family fragilities, not source-verified historical exchange rejects. Current 2026 metadata cannot be backdated, and a favorable partial closure cannot resolve unknown coarser eligibility.

## What the evidence supports

REDESIGN_HYPOTHESES ranks causal investigation by mechanism prevalence/construction, not profitable slices: explicit structural-approach semantics; completed-mark/FTA validity; structural entry lifetime/reachability; executable boundary versus zone contract; pre-entry economic payoff/anti-scalp consistency. Observer-only per-origin gate telemetry is a prerequisite. Every hypothesis states what remains unproved, overfit risks and preregistration requirements. None is an adopted rule or selected numeric parameter.

Actionable design hypotheses exist for a separately named MACHINE_STRATEGY_v4 after this diagnosis is independently frozen. The new design must preserve the qualification targets, both directions, source/policy separation and all-case handling. No old v3 financial rerun, in-place tuning, threshold relaxation, profitable subgroup selection, OOS/PAPER/LIVE/private API or platform action is authorized. `trade_entry_allowed=false`.
