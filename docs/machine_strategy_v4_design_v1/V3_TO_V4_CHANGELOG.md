# MACHINE_STRATEGY_v3 -> v4 change log

All changes below are pre-outcome v4 design choices. No v4 historical financial result has been generated or viewed.

| Area | v3 | v4 | Cause | Classification |
|---|---|---|---|---|
| Approach/smoothness | Any opposite M15 BOS between reaction and selected CONF terminally rejected before context | Introduces CLEAN/CORRECTIVE/INVALID. Corrective paths may reach HTF context while structural boundary remains intact and final same-direction CONF exists | H01: 10,511/11,947 raw formations died at early non-smooth gate | PROJECT_POLICY |
| FTA lifecycle | OPEN-side target invalidation could be first explicit retirement | Latest completed M15 close reaching/passing nearest FTA retires before order; never fall back to farther FTA | H02: many target-open cancellations already completed by prior close | PROJECT_POLICY |
| Active order lifetime | Fixed 1 hour | Event-driven while formation/context/POI/FTA remain valid, with inherited 16h parent pending ceiling as maximum | H03: 42 orders expired after four M15 bars without touch; 1h was machine convention | PROJECT_POLICY |
| Structural vs executable zone | Structural zone directly required executable grid representation | Structural zone stored unchanged; technical execution envelope expands exactly one active grid unit per side for representability; all stress scenarios remain adverse | H04: zero-width/narrow zones caused synthetic eligibility disagreement | TECHNICAL_NORMALIZATION |
| Pre-entry economics | Nearest target move merely had to exceed modeled round-trip cost | Nearest FTA must deliver >= +1R net at doubled fee+slippage relative to full modeled stop risk | H05: sampled winners were much smaller than losses and gross edge negative | PROJECT_POLICY risk-parity |
| Telemetry | Aggregate WAIT/rejection counters insufficient for per-origin transition diagnosis | Immutable formation/physical IDs plus gate first-eval/pass/wait/terminal causal events; outcome-blind observer only | H00 evidence gap | OBSERVER_ONLY |
| Directions | LONG/SHORT both active | unchanged | No causal evidence supports direction deletion | INHERITED |
| Setup families | SFP/OB/BREAKER/STB/RANGE | unchanged | No family deletion by exposed P&L | INHERITED |
| Target selection | nearest valid structural FTA, no farther fallback | unchanged | Preserve source/structure intent | INHERITED |
| Stops | structural family stop; SFP ATR14 buffer | unchanged | Avoid outcome-based stop tuning | INHERITED |
| Costs | 6bp fee +2bp slippage/leg model; actual funding only in OKX compatibility binding | unchanged; doubled-cost also used for admission payoff safety | Existing frozen model | INHERITED PROJECT_POLICY |
| Qualification | WR>=70% and frozen sample/PF/net/DD/cohort/robustness thresholds | unchanged | User/frozen project target | INHERITED PROJECT_POLICY |

## Explicit non-changes

- no SHORT ban;
- no coin-specific rule;
- no profitable-subgroup filter;
- no time-of-day/month/quarter filter;
- no farther-FTA substitution;
- no fixed-percentage TP replacement;
- no parameter sweep over expiry, entry offsets, ATR length, R:R or smoothness counts;
- no relaxation of qualification criteria.
