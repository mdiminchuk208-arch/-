# MACHINE_STRATEGY_v4 — pre-outcome specification

Status: DESIGN_DRAFT_COMPLETE_REVIEW_PENDING. No v4 historical financial outcome has been generated or viewed. This document defines one deterministic candidate architecture derived from the frozen v3 failure mechanisms. It does not claim profitability.

## Design objective

Preserve the source-aligned SMC/structure architecture while correcting mechanisms demonstrated by the frozen v3 audit:

1. mechanically overbroad early approach rejection prevented context from being evaluated on most formations;
2. orders were sometimes created when the last completed price had already completed the nearest FTA idea;
3. fixed one-hour resting-order expiry was a project convention rather than structural invalidation;
4. structural zones and executable price lattices were conflated;
5. nearest-FTA economics permitted very small planned rewards relative to a full stop loss.

The design remains LONG/SHORT symmetric. No direction, coin, setup family or time slice is removed because of historical P&L.

## V4_STATE_AND_APPROACH

Higher-timeframe state definitions remain inherited from v3 unless explicitly overridden below: completed D1/H4/H1/M15 only, deterministic equal-cutoff advancement, no incomplete bars, H4 RANGE priority, aligned H4/D1 trend, mixed/transition-origin POI logic, mirrored LONG/SHORT handling.

### Approach override

V3 terminally rejected a formation when any opposite M15 BOS existed between reaction and selected confirmation. V4 replaces that terminal pre-context veto with an explicit three-state approach contract:

- `APPROACH_CLEAN`: reaction -> selected same-direction M15 CONF with no intervening opposite CONF/BOS.
- `APPROACH_CORRECTIVE`: one or more opposite M15 BOS/CONF events may occur after reaction, but the formation structural boundary remains intact and the final selected M15 CONF returns to the candidate direction before decision.
- `APPROACH_INVALID`: completed price closes through the immutable formation structural invalidation boundary, the formation/source is retired/consumed, required causal evidence is missing/gapped, or no same-direction M15 CONF exists before retirement.

`APPROACH_CORRECTIVE` is not automatically tradable. It proceeds to the same HTF context, POI, FTA and economics gates as `APPROACH_CLEAN`. Context is therefore observed before the design rejects an otherwise structurally alive corrective path.

Classification: PROJECT_POLICY motivated by H01. It is not promoted to SOURCE_RULE.

## V4_SETUP_FAMILIES

Retain all five v3 families symmetrically:

- SFP
- OB
- BREAKER
- STB
- RANGE

Raw formation geometry, causal reaction requirements, origin-bound refinement objects, structural invalidation anchors and source provenance remain inherited from v3 unless a rule below explicitly changes execution/lifecycle treatment.

No family is removed or promoted based on v3 profitability.

## V4_DECISION_AND_FTA_LIFECYCLE

At every candidate decision:

1. use only completed bars known by decision;
2. build the same complete contextual nearest-FTA inventory used by v3;
3. select the nearest signed-forward FTA by raw structural distance, preserving canonical tie handling;
4. compare the latest completed M15 close available at decision with the selected FTA.

For LONG, if completed close >= selected FTA price, the trade idea is `FTA_ALREADY_COMPLETED` and no resting order may be created. For SHORT, if completed close <= selected FTA price, same result. Equality is completed, not still pending.

Do not choose a farther FTA after this rejection. A later independent formation/confirmation may create a new idea.

While an order is resting, any completed close beyond/equal the selected target retires the order before the next bar can fill it. OPEN-based gap cancellation remains an execution safeguard, but it is no longer the first lifecycle check when completed evidence had already invalidated the idea.

Classification: PROJECT_POLICY motivated by H02.

## V4_ENTRY_AND_ORDER_LIFETIME

Entry remains `RESTING_LIMIT_ONLY` at the inherited source-permitted/proximal structural price after technical quantization.

V4 removes the arbitrary fixed 3600-second active-order expiry. The order remains active only while all of the following remain causally true:

- formation/source is not retired or consumed;
- structural invalidation boundary has not been closed through;
- selected HTF context remains admissible for the direction;
- refinement/POI remains valid and unconsumed;
- nearest selected FTA remains ahead of current completed price;
- no metadata/data-integrity STOP occurs;
- the parent pending idea has not reached the inherited 16-hour pending-lifecycle ceiling.

Thus lifetime is structural/event-driven, with the existing 16-hour parent pending ceiling retained only as a maximum safety bound. No alternative duration is searched against outcomes.

A fill requires price contact while the order is valid. No open-price improvement is assumed; modeled fill remains the limit price.

Classification: PROJECT_POLICY motivated by H03.

## V4_STRUCTURAL_VS_EXECUTABLE_ZONE

Structural geometry and executable representation are separate objects.

### Structural zone

The setup/source defines an immutable raw structural zone/boundary exactly as in the family contract.

### Executable zone

For each active compatibility price grid `t`, define a technical execution envelope equal to the structural zone expanded by exactly one grid unit on each side solely for representability:

`exec_low = structural_low - t`
`exec_high = structural_high + t`

The raw intended entry is never moved for performance reasons. It is directionally quantized as in v3 and is valid only if the resulting price lies inside the executable envelope. The raw structural zone remains stored separately and is still used for source/structure reasoning.

A one-grid technical envelope is classified TECHNICAL_NORMALIZATION, not SOURCE_RULE. It is evaluated across every preregistered compatibility grid; no favorable grid may be selected. If eligibility/state differs materially across scenarios, adverse/unresolved treatment from the compatibility policy remains mandatory.

Lot/minimum-size assumptions remain compatibility-model inputs, not backdated OKX facts.

Classification: TECHNICAL_NORMALIZATION motivated by H04.

## V4_STOP_AND_TARGET

Protective stop construction remains structural and mirrored:

- immutable family boundary;
- SFP retains causal pattern-end ATR14 outward buffer;
- final executable stop is the first active-grid price strictly outside the boundary;
- no stop tightening based on observed historical outcomes.

Target remains the nearest valid FTA. V4 does not replace targets with fixed percentages and does not skip to a farther FTA to improve R:R.

## V4_PREENTRY_PAYOFF_GATE

V3 permitted any target move strictly greater than modeled round-trip costs. That allowed economically tiny plans where a full loss was much larger than the planned win.

V4 introduces one pre-outcome, symmetric risk-parity gate:

- compute fixed cash stop unit `K` under the actual modeled entry/stop using the same risk normalization;
- compute net cash profit at the nearest FTA under **doubled total fee+slippage costs**, excluding unknown future funding direction from the admission feature;
- require that doubled-cost net target profit is at least `1.0 * K`.

Equivalent condition: planned nearest-FTA `net_target_R_doubled_cost >= +1.0R`.

Rationale: a planned full structural winner must cover at least one complete modeled stop-risk unit under the mandatory adverse cost envelope. `1R` is risk-unit parity, not a threshold selected from the 20 exposed v3 CLOSED outcomes.

Funding is still accounted in realized validation P&L using the sealed signed historical funding series, but future funding sign is not used as an admission feature.

If the nearest FTA fails the gate, reject as `REJECT_INSUFFICIENT_STRUCTURAL_PAYOFF`. Never choose a farther target to pass.

Classification: PROJECT_POLICY motivated by H05.

## V4_EXECUTION_AND_AMBIGUITY

Preserve conservative compatibility execution principles:

- evaluate every candidate under all preregistered price/lot scenarios;
- no scenario cherry-picking;
- adverse/worst valid financial result governs qualification;
- material eligibility/fill/closure disagreement remains unresolved/STOP according to the compatibility policy;
- no imputed winners or discarded adverse cases;
- same-bar order ambiguity remains conservative WAIT/UNKNOWN where ordering cannot be proven from OHLC;
- actual signed historical funding is included after fill while exposure is open;
- base and doubled cost columns are both mandatory.

## V4_REENTRY

No automatic retry of the same physical formation/POI after expiry, invalidation, loss or target completion. A new trade requires a new independent causal formation/confirmation identity. This remains inherited from v3.

## V4_TELEMETRY_OBSERVER

Every raw origin receives immutable identifiers:

- `formation_id`
- `physical_bucket_id`
- `source_family`
- `direction`
- `formation_known_at`

Every gate emits one causal event record with:

- gate name;
- first evaluated at;
- first pass at if any;
- repeated WAIT count;
- latest WAIT reason;
- terminal disposition/time;
- context snapshot IDs;
- approach state;
- selected refinement object IDs;
- selected FTA ID/price;
- raw/quantized entry-stop-target geometry;
- payoff-gate diagnostics;
- no outcome/PnL fields.

Telemetry cannot modify admission and is not available to strategy rules. Its purpose is to make future scarcity diagnoses identifiable without reconstructing retry counters.

Classification: OBSERVER_ONLY motivated by H00.

## V4_COST_MODEL

Historical validation inherits the same explicit modeled base costs unless a later pre-outcome cost-policy version supersedes them:

- fee per leg: 0.0006;
- slippage per leg: 0.0002;
- actual signed OKX funding settlements while open;
- mandatory doubled total fee+slippage sensitivity.

These are model assumptions, not claims of exact historical account fees.

## V4_QUALIFICATION

Carry forward unchanged:

- Win Rate >= 70%;
- CLOSED >= 200;
- base Profit Factor >= 1.20;
- net expectancy R > 0;
- net P&L > 0;
- doubled-cost PF >= 1.00;
- doubled-cost net P&L > 0;
- case-ledger max drawdown <= 20R;
- max consecutive net losses <= 10;
- each BTC/ETH x LONG/SHORT cohort >= 30 CLOSED and net positive;
- Wilson 95% WR lower bound >= 0.60;
- largest calendar-quarter profit share <= 0.50;
- largest coin profit share <= 0.80;
- zero filled unknown exits;
- no critical causality/integrity failure.

No threshold may be relaxed after outcomes.

## Outcome isolation

The v3 development period is exposed development data. V4 design may use only the frozen causal failure mechanisms and diagnostics already published; it must not compare alternative v4 parameters by financial outcome. No v4 financial run is authorized until design freeze + implementation freeze + independent readiness review.

PAPER=false. LIVE=false. `trade_entry_allowed=false`.
