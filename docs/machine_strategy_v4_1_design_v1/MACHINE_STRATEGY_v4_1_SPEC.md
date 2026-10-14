# MACHINE_STRATEGY_v4.1 — Selected-POI contract amendment

Status: PRE_OUTCOME_DESIGN_REVIEW_CANDIDATE. This is a narrow amendment to the independently frozen MACHINE_STRATEGY_v4 design after the independently accepted v4 implementation STOP. No historical v4/v4.1 trade outcome, catalog-count comparison, WR, PF or P&L is authorized or used here.

## Inheritance boundary

MACHINE_STRATEGY_v4.1 inherits the complete frozen v4 design except the selected-entry-POI first-test/consumption contract and the explicit Decimal arithmetic scope declared here. It does not change LONG/SHORT symmetry, the five setup families, HTF state/context rules, M4 approach selector, structural anchors, nearest-FTA logic, H04 executable envelope, H05 doubled-cost 1R planned-payoff gate, nine compatibility scenarios, 57600-second parent deadline, fixed-U reporting, funding policy, exits, qualification thresholds or safety controls.

## Common selected-POI identity model

Every candidate carries distinct immutable identities:

- `formation_id`: source formation identity;
- `source_parent_id`: parent structural object from which the setup derives;
- `selected_poi_id`: the exact intended entry object;
- `selected_poi_kind`: `REFINED_M15_POI`, `STB_BODY`, `BREAKER_BODY`, or `RANGE_BOUNDARY`;
- `selected_poi_native_tf`: the timeframe on which first physical contact is evaluated;
- `origin_conf_id` and `origin_conf_known_at`: completed confirmation that causally creates or validates the selected entry object;
- `reaction_required_at`: completed required formation/reaction event, when applicable;
- `eligibility_at`: first instant at which subsequent native physical contact may consume the selected entry object;
- `emission_decision_at`: later H1 decision at which a resting order may be reserved.

`eligibility_at` is never backdated to a wick or OPEN that was not knowable then. It is the maximum of all completed prerequisites specific to that family. Contacts belonging to those mandatory prerequisites are not consumption events. Once eligibility has started, the first later eligible native physical contact owns/consumes the selected POI even if no order has yet been emitted.

This is PROJECT_POLICY required to make the machine contract causal and non-self-cancelling; it is not promoted to SOURCE_RULE.

## SFP and OB

The selected POI remains the frozen refined M15 OB/FVG already selected by v4. Its existing zone identity is preserved.

- Native first-test TF: M15.
- `origin_conf_id`: the zone's own origin BOS/CONF identity already carried by the refined POI.
- `eligibility_at = max(zone_born_at, origin_conf_known_at, required_parent_reaction_known_at)`.
- Contacts before `eligibility_at` do not consume this selected POI.
- The first M15 bar whose OPEN is at/after `eligibility_at` and whose OHLC intersects the selected POI is the first eligible contact; the contact becomes known at that M15 bar CLOSE.
- If that contact was completed before `emission_decision_at`, the candidate is rejected as pre-emission consumed.
- If the order was already active at the bar OPEN, current-bar execution is evaluated before contact consumption becomes known at CLOSE; an unfilled order is retired prospectively after CLOSE.

No extra reset is introduced merely because another same-direction M15 confirmation exists later.

## STB

The selected STB entry object is the immutable manipulation candle body used by the frozen v4 raw-entry rule. It is NOT the full manipulation parent zone.

Create generated handle:

`selected_poi_id = H("M4_1_STB_BODY", formation_id, body_low, body_high)`.

- `source_parent_id` remains the full manipulation formation identity.
- Full-parent contact/legacy parent consumption does not by itself consume `STB_BODY`.
- Full-parent structural invalidation remains governed only by the inherited structural-anchor rule.
- Native first-test TF is the setup native H1/H4 TF because the selected body is a native formation body.
- `origin_conf_id` is the selected causal M15 confirmation used by the setup.
- `eligibility_at = max(formation_known_at, origin_conf_known_at)`.
- The formation/manipulation bar itself is a required source event and is exempt from selected-body consumption.
- The first later native setup-TF bar opening at/after `eligibility_at` whose OHLC intersects the body consumes the selected body, subject to the same current-bar active-order ordering described above.

This separates selected-entry ownership from parent-source retirement and removes the inherited ambiguity identified by `B_STB_BODY_SOURCE`.

## BREAKER

The selected BREAKER entry object is the immutable body of the broken contextual parent OB under a new generated breaker identity.

Create generated handle:

`selected_poi_id = H("M4_1_BREAKER_BODY", parent_ob_id, breaker_formation_known_at, direction)`.

- `source_parent_id = parent_ob_id`.
- The completed native opposite body-break that creates the breaker is `reaction_required_at` and is exempt from consuming the new breaker body.
- `origin_conf_id` is the selected same-direction M15 confirmation used after breaker creation.
- Native first-test TF is the setup native H1/H4 TF on which the breaker formation was created.
- `eligibility_at = max(breaker_formation_known_at, origin_conf_known_at)`.
- First subsequent eligible native body contact consumes the breaker body.
- Contacts to the parent OB before breaker creation cannot consume a breaker object that did not yet exist.
- Parent structural retirement remains separate and cannot silently replace selected-body consumption.

This resolves `B_GENERATED_POI_ORIGIN` without fabricating a source rule.

## RANGE

The selected RANGE entry object is the frozen zero-width native range boundary for the candidate direction.

Create generated handle:

`selected_poi_id = H("M4_1_RANGE_BOUNDARY", range_id, direction, boundary_price)`.

The required deviation/reclaim and later boundary reaction are formation prerequisites. Therefore the required boundary-reaction contact that completes the RANGE setup is explicitly exempt from selected-POI consumption.

- `source_parent_id = range_id`.
- `reaction_required_at` is the completed native boundary-reaction CLOSE required by the frozen RANGE setup.
- `origin_conf_id` is the selected same-direction M15 confirmation used after the required reaction.
- Native first-test TF is the source range native H1/H4 TF.
- `eligibility_at = max(reaction_required_at, origin_conf_known_at)`.
- The first later native bar with OPEN at/after `eligibility_at` that touches the boundary consumes the selected POI.
- The mandatory boundary reaction itself never self-cancels the setup.
- Source range permanent retirement on native CLOSE at/outside its range boundary remains inherited and separate.

This resolves `B_RANGE_REACTION` while keeping later consumed entries non-reusable.

## Context requirement and timing

A selected POI may become eligible only if the candidate's required completed context evidence is known by `eligibility_at`. If required context is not yet complete/admissible, the object remains `WAIT_CONTEXT_FOR_POI_ELIGIBILITY`; contact during that WAIT does not establish an eligible first test. When context becomes admissible later, eligibility begins prospectively; it is never backdated.

At a native bar:

1. use only state completed before bar OPEN for already-known retirement/context/deadline checks;
2. if an order is already active, evaluate OPEN/wick execution under the frozen event-order rules;
3. publish native contact at bar CLOSE;
4. a newly published first eligible contact consumes the POI for subsequent OPENs;
5. same-time higher-TF states are advanced only when their bars are completed and never used retroactively for an earlier OPEN.

No completed CLOSE may retroactively cancel an earlier valid OPEN/fill.

## Pre-emission and pending ownership

Before reservation/emission, reject if an eligible first contact was already completed after `eligibility_at`. Reservation gives the candidate exclusive ownership but is not itself consumption. During pending life, if first eligible contact occurs and the modeled order fills on that same bar under frozen execution semantics, the fill owns the contact. If it does not fill, the POI becomes consumed at that bar CLOSE and the order retires before the next OPEN. No retry of the same physical/POI identity is allowed.

## Arithmetic amendment

Design/eligibility/geometry arithmetic and all selected-POI boundary construction use Decimal precision 50, ROUND_HALF_EVEN. Financial ledger accumulation and realized cash/R accounting use Decimal precision 80, ROUND_HALF_EVEN. Prices, quantities, timestamps, IDs and fixed-U values cross the boundary only through canonical serialized Decimal strings; the ledger consumes those frozen values and must not recompute design geometry with precision 80. Exact comparisons use Decimal equality/ordering without epsilon.

## Qualification and safety

All v4 qualification thresholds remain unchanged, including WR>=70%, CLOSED>=200, PF/base and doubled-cost gates, positive net expectancy/P&L, DD/loss-streak/cohort/Wilson/concentration/integrity requirements. No historical outcome access is authorized by this amendment. PAPER=false, LIVE=false, `trade_entry_allowed=false`.
