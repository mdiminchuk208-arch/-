# MACHINE_STRATEGY_v4.1 — causal failure audit v1

Status: **AUTHORED / INDEPENDENT REVIEW PENDING**. Cached frozen evidence only; no historical replay, changed trade simulation, tuning, OOS or new strategy implementation was performed.

## Executive finding

The v4.1 financial STOP is not explained by one isolated bug or by exchange costs alone. The strongest frozen evidence supports a three-part failure:

1. **Execution availability is extremely low.** 54 emitted candidates produce only 8 cases with any/all-nine fill evidence; 46 candidates never fill. Of the 46 no-fill candidates, 44 are all-nine `UNFILLED_RETIRED` and only 2 are all-nine `UNFILLED_EXPIRED`. This points first to the interaction of selected entry geometry with the pending-lifecycle/structure/context retirement rules, not merely a too-short fixed expiry.
2. **The tiny realized sample has negative gross edge before costs.** Seven all-nine CLOSED cases produce 2 WIN / 5 LOSS, WR 28.57%, gross -0.8505737502R / -132.71 modeled USDT. Fees/slippage enlarge the loss to -2.4331948693R / -613.690875537 USDT, but they do not create the negative sign.
3. **The sample is too small and compositionally sparse to justify subgroup rules.** Only 7 CLOSED versus required 200; BTC LONG has 9 candidates and zero CLOSED; OB has zero candidates; H4 has one CLOSED winner; SFP has two CLOSED. Positive tiny slices are diagnostics, not usable strategy rules.

No independent reviewer found a separate critical integrity or causality defect in the frozen v4.1 implementation/result chain. Therefore the evidence supports a strategy/admission/execution-availability diagnosis, while preserving explicit execution-model limitations.

## Frozen funnel

- Candidates: **54** (BTC 25, ETH 29).
- All-nine no-fill: **46** (85.19%).
- Any/all-nine fill evidence: **8** (14.81%).
- All-nine CLOSED: **7** (12.96%).
- Filled unresolved: **1** (1.85%), an ETH LONG RANGE H1 case with all nine states `WAIT_INTRABAR_ORDER`.
- Scenario states: 486 = 396 `UNFILLED_RETIRED` + 18 `UNFILLED_EXPIRED` + 63 `CLOSED` + 9 `WAIT_INTRABAR_ORDER`.
- Since the 46 no-fill cases retain all nine scenarios and there are zero mixed terminal-status cases, the state counts imply **44 all-nine retired cases and 2 all-nine expired cases**.

### Interpretation

The old v3 failure had many orders that simply failed to touch during a fixed one-hour lifetime. v4.1 removed that fixed one-hour order expiry and tied the lifetime to structural validity up to the inherited 16-hour parent ceiling. Yet v4.1 still fills only 8/54 candidates, with retirement overwhelming expiry. Therefore the next diagnosis should focus on **why the frozen lifecycle invalidates/consumes/stales the candidate before entry**, and on whether the intended entry geometry is reachable while the setup remains valid.

This does **not** authorize extending lifetime again or ignoring structural retirement. A retirement-reason census must be derived from cached evidence first.

## Realized edge

Base all-nine CLOSED population:
- CLOSED 7
- WIN 2 / LOSS 5
- WR 28.5714%
- PF_R 0.462899
- expectancy -0.347599R
- gross -0.850574R / -132.71 modeled USDT
- net -2.433195R / -613.690876 modeled USDT
- max DD 3.772211R
- max loss streak 3
- Wilson 95% lower 0.082219

Doubled fee/slippage, same event paths:
- PF_R 0.301548
- expectancy -0.574634R
- net -4.022435R / -1095.340404 modeled USDT
- max DD 5.047838R

Costs:
- base fees 361.237146 USDT
- base slippage 120.412382 USDT
- signed funding +0.668652463 USDT

### Interpretation

Costs are material and punitive, but **the gross aggregate is already negative**. A future version cannot be justified by fee/slippage adjustment alone. The admission model must improve the probability that the nearest structural target is reached before the structural stop/body invalidation, while still keeping costs modeled conservatively.

The frozen H05 planned payoff rule (`N2_s >= K_s`) is a feasibility test on distances/costs. It is not a probability forecast. v4.1 demonstrates that a favorable planned target/stop ratio does not by itself create predictive edge.

## Directional evidence

- LONG: 22 candidates overall, only 1 qualifying CLOSED winner plus 1 filled unresolved RANGE case. BTC LONG: 9 candidates, 0 CLOSED. ETH LONG: 13 candidates, 11 no-fill, 1 CLOSED WIN, 1 unresolved.
- SHORT: 32 candidates overall, 6 CLOSED; 1 WIN / 5 LOSS, WR 16.67%, gross -1.655610R, net -3.191220R. BTC SHORT 1/3 wins; ETH SHORT 0/3.

### Interpretation

The observed SHORT closed sample is poor and is the main contributor to realized losses, but n=6 is far too small to justify a post-result SHORT ban. Conversely the lone LONG winner cannot establish positive LONG edge. Directional logic must stay symmetric unless a future pre-outcome design supplies a structural reason for different treatment.

## Family evidence

Candidate composition:
- STB: 38 = 35 no-fill + 3 CLOSED.
- RANGE: 10 = 8 no-fill + 1 CLOSED + 1 unresolved.
- SFP: 5 = 3 no-fill + 2 CLOSED.
- BREAKER: 1 = 1 CLOSED.
- OB: 0 candidates.

Qualified CLOSED diagnostics:
- STB: 3 CLOSED, 1W/2L, net -0.662108R.
- RANGE: 1 CLOSED loss, net -0.993845R.
- SFP: 2 CLOSED, 1W/1L, net +0.222703R.
- BREAKER: 1 CLOSED loss, net -0.999946R.

### Interpretation

The five-family strategy collapses into a heavily STB-weighted candidate stream, while OB is unreachable in this fixed window and BREAKER is nearly absent. This is a **coverage/composition problem**, but the tiny family samples do not justify selecting SFP or deleting STB/RANGE/BREAKER. A future pre-outcome design should require outcome-blind formation/gate telemetry that explains why families fail to become executable candidates.

## Timeframe evidence

- H1/60: 35 candidates, 6 CLOSED, 1W/5L, net -3.772211R.
- H4/240: 19 candidates, 1 CLOSED winner, net +1.339016R.

The single H4 winner is not sufficient evidence to switch the strategy to H4-only. It is an overlapping tiny positive slice explicitly flagged by the frozen overfit review.

## Intrabar uncertainty

One ETH LONG RANGE H1 case is filled under all nine scenarios but unresolved under all nine because entry and terminal events share an M15 interval whose order cannot be established from the frozen OHLC data. This creates 9 filled-unknown scenario states and independently blocks qualification.

However, it affects only one candidate. It cannot explain the broad 46-case no-fill funnel or the 5 losses among 7 CLOSED. The correct treatment remains UNKNOWN, not a guessed winner or loser.

## Model limitations

The audit preserves the already frozen limitations:
- historical tick/lot epochs are modeled compatibility stress, not verified historical metadata epochs;
- ordinary account-applicable OKX historical fees are unverified;
- actual queue/fill/slippage/API publication latency are unverified;
- signed funding rates are sealed, while settlement-close mark proxy and adverse timing are modeled;
- development history is exposed, not pristine OOS.

These limitations can change real-world magnitude, but they do not authorize erasing the observed negative modeled gross result.

## Causal ranking

1. **Pre-fill retirement / reachability mismatch — highest priority.** 44/54 candidates are retired in all nine scenarios before fill. Exact retirement-reason distribution must be extracted from cached evidence before new design.
2. **Admission lacks demonstrated directional hit probability — high priority.** The 7 CLOSED cases are gross-negative; structural payoff feasibility alone is insufficient.
3. **Family/candidate composition collapse — high priority.** STB dominates, OB absent, BREAKER scarce; the intended diversified setup tree is not producing diversified executable opportunities.
4. **SHORT closed-sample weakness — medium diagnostic priority.** Strongly negative observed sample, but too small for direction removal.
5. **Modeled costs — important amplifier, not root sign cause.** Costs substantially worsen already-negative gross edge.
6. **Intrabar ambiguity — local qualification blocker, not global cause.** One case only.
7. **Sample scarcity — fundamental qualification failure.** Seven CLOSED cannot establish a 70% WR claim or robust subgroup estimates.

## Audit conclusion

The evidence **does justify a future separately scoped design gate**, but only after an independent review of this cached-evidence audit. The justified design problem is not “tune v4.1 until WR is 70%.” It is:

- explain and reduce structurally unjustified pre-fill retirement without using future outcomes;
- make entry reachability and selected-POI lifetime internally coherent;
- improve pre-entry predictive structure rather than only planned RR;
- restore measurable family opportunity coverage with outcome-blind telemetry;
- preserve conservative cost/funding/execution handling and all-nine stress;
- keep LONG/SHORT unless a new pre-outcome structural contract says otherwise.

No v4.2 rule is frozen by this report. Independent audit review/freeze is still required before strategy design resumes.
