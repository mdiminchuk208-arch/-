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
- `origin_conf_id` and `origin_conf_known_at`: immutable completed confirmation latched for selected-entry lifecycle; `proposal_selected_conf_id` separately records the latest inherited M4 CONF used by an H1 proposal;
- `reaction_required_at`: completed required formation/reaction event, when applicable;
- `eligibility_at`: first instant at which subsequent native physical contact may consume the selected entry object;
- `emission_decision_at`: later H1 decision at which a resting order may be reserved.

`eligibility_at` is never backdated to a wick or OPEN that was not knowable then. It is the first admissible completed M15 inventory cutoff at/after the maximum prerequisite lower bound, including the completed context and current M4 gate. Contacts belonging to those mandatory prerequisites are not consumption events. Once eligibility has started, the first later eligible native physical contact owns/consumes the selected POI even if no order has yet been emitted.

This is PROJECT_POLICY required to make the machine contract causal and non-self-cancelling; it is not promoted to SOURCE_RULE.

The selected physical-object inventory runs on completed-prefix evidence at every M15 cutoff, starting when the family object is known, independently of whether other gates yet permit an H1 trade proposal. It emits no new trade signal. For generated STB/BREAKER/RANGE objects, the first cutoff at which all family prerequisites, the inherited current M4 confirmation gate and completed candidate context are admissible latches that gate's origin CONF and eligibility_at. Until that first cutoff there is WAIT; afterward neither a later proposal CONF nor a later viable H1 proposal can rebase the physical POI. SFP/OB keep their own refined-zone BOS/CONF identity. Actual native contacts still require matching native context snapshotted at native OPEN. A native bar already OPEN before a midbar M15 eligibility start remains ineligible.

Example: native H1 generated body, CONF A known09:00, eligibility09:00, contact09:00–10:00 completed10:00, CONF B known11:00, first viable H1 proposal12:00. The object remains consumed from10:00; choosing B as current proposal evidence cannot erase A's earlier eligible clock.

For every family the displayed `eligibility_lower_bound` is only a prerequisite bound. The actual `eligibility_at` is the FIRST admissible completed M15 inventory cutoff at/after that bound, including required completed context and current inherited M4 confirmation gate. Late context therefore cannot yield a backdated formula. Inventory `eligibility_at` is nullable before latch; generated `origin_conf_id`/`origin_conf_known_at` are nullable before latch; `proposal_selected_conf_id` and `emission_decision_at` are nullable before H1 proposal.

## SFP and OB

The selected POI remains the frozen refined M15 OB/FVG already selected by v4. Its existing zone identity is preserved.

- Native first-test TF: M15.
- `origin_conf_id`: the zone's own origin BOS/CONF identity already carried by the refined POI.
- `eligibility_lower_bound = max(zone_born_at, origin_conf_known_at, required_parent_reaction_known_at)`.
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
- `origin_conf_id` is the M15 confirmation latched by the first admissible completed-prefix inventory cutoff; latest proposal confirmation is recorded separately.
- `eligibility_lower_bound = max(formation_known_at, origin_conf_known_at)`.
- The formation/manipulation bar itself is a required source event and is exempt from selected-body consumption.
- The first later native setup-TF bar opening at/after `eligibility_at` whose OHLC intersects the body consumes the selected body, subject to the same current-bar active-order ordering described above.

This separates selected-entry ownership from parent-source retirement and removes the inherited ambiguity identified by `B_STB_BODY_SOURCE`.

## BREAKER

The selected BREAKER entry object is the immutable body of the broken contextual parent OB under a new generated breaker identity.

Create generated handle:

`selected_poi_id = H("M4_1_BREAKER_BODY", parent_ob_id, breaker_formation_known_at, direction)`.

- `source_parent_id = parent_ob_id`.
- The completed native opposite body-break that creates the breaker is `reaction_required_at` and is exempt from consuming the new breaker body.
- `origin_conf_id` is the same-direction M15 confirmation latched at the first eligible cutoff after breaker creation, independently of later viable proposal.
- Native first-test TF is the setup native H1/H4 TF on which the breaker formation was created.
- `eligibility_lower_bound = max(breaker_formation_known_at, origin_conf_known_at)`.
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
- `origin_conf_id` is the same-direction M15 confirmation latched at the first eligible cutoff after the required reaction, independently of later viable proposal.
- Native first-test TF is the source range native H1/H4 TF.
- `eligibility_lower_bound = max(reaction_required_at, origin_conf_known_at)`.
- The first later native bar with OPEN at/after `eligibility_at` that touches the boundary consumes the selected POI.
- The mandatory boundary reaction itself never self-cancels the setup.
- Source range permanent retirement on native CLOSE at/outside its range boundary remains inherited and separate.

This resolves `B_RANGE_REACTION` while keeping later consumed entries non-reusable.

## Context requirement and timing

A selected POI may become eligible only if the candidate's required completed context evidence is known by `eligibility_at`. If required context is not yet complete/admissible, the object remains `WAIT_CONTEXT_FOR_POI_ELIGIBILITY`; contact during that WAIT does not establish an eligible first test. When context becomes admissible later, eligibility begins prospectively; it is never backdated.

Execution and contact publication have separate clocks. Execution/rechecks remain on every M15 OPEN and observed M15 bar, including after an H1 emission within an already-running native H1/H4 bar. The order need not have existed at that native bar OPEN. Native first-test contact remains unknown until that native bar CLOSE.

1. Before each M15 OPEN, apply all previously completed evidence with known_at<=OPEN and the half-open deadline; native CLOSE at exactly that OPEN is already known.
2. Execute an order emitted at an earlier/equal cutoff on the following M15 bar using inherited OPEN/wick rules; never use a future native CLOSE to suppress that execution.
3. At a completed cutoff advance D1,H4,H1,M15 in that order, then publish first eligible selected-POI contacts whose native bars completed.
4. If the registered owner filled on any M15 bar during that eligible native interval, that fill owns the published contact, even if the exposure already exited. If unfilled, consume and retire pending before the next M15 OPEN. A current native CLOSE cannot retroactively cancel any earlier valid M15 fill.
5. Only after completed contacts/context/deadlines have been applied may an H1 emission reserve a POI. Thus contact known_at==emission_decision_at is preconsumed, not available for new reservation. Equal-cutoff evidence is usable at the next M15 OPEN, never an earlier one.

Example: H4 [08:00,12:00), eligibility 08:00, H1 emission 09:00, modeled M15 fill at 09:15 remains valid; contact publication at 12:00 cannot cancel it. Another proposal at 10:00 is blocked by the existing exclusive reservation.

Eligibility is latched once for each selected physical POI; later confirmations/context reacquisition cannot reset it, erase consumed_at or remove reservation. Before first eligibility, contacts are exempt only as specified by the family. After eligibility, native contacts require matching native-TF context at that native OPEN, inherited from the first-eligible-test convention; candidate context changes still retire PENDING on M15 completed evidence. Consumed/reserved/retired state is permanent for that identity.

No completed CLOSE may retroactively cancel an earlier valid OPEN/fill.

## Pre-emission and pending ownership

Before reservation/emission, reject if an eligible first contact was already completed after `eligibility_at`. Reservation gives the candidate exclusive ownership but is not itself consumption. During pending life, if first eligible contact occurs and the modeled order fills on that same bar under frozen execution semantics, the fill owns the contact. If it does not fill, the POI becomes consumed at that bar CLOSE and the order retires before the next OPEN. No retry of the same physical/POI identity is allowed.

## Arithmetic amendment

Design/eligibility/geometry arithmetic and all selected-POI boundary construction use Decimal precision 50, ROUND_HALF_EVEN. Financial ledger accumulation and realized cash/R accounting use Decimal precision 80, ROUND_HALF_EVEN. Prices, quantities, timestamps, IDs and fixed-U values cross the boundary only through canonical serialized Decimal strings; the ledger consumes those frozen values and must not recompute design geometry with precision 80. Exact comparisons use Decimal equality/ordering without epsilon.

## Qualification and safety

All v4 qualification thresholds remain unchanged, including WR>=70%, CLOSED>=200, PF/base and doubled-cost gates, positive net expectancy/P&L, DD/loss-streak/cohort/Wilson/concentration/integrity requirements. No historical outcome access is authorized by this amendment. PAPER=false, LIVE=false, `trade_entry_allowed=false`.
