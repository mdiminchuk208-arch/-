# Strategy V2 high precision — registered research protocol

Registered on branch `strategy-v2-70wr-research`, before V2 feature/outcome mining.
Baseline: `dab8d254aaf4babc07659e3d03d14b269445767b`. No baseline file is
modified. No automatic merge into main. BACKTEST/SHADOW/RESEARCH only;
`trade_entry_allowed=false`; no private API, real orders or withdrawals.

## Scope and contamination

Use the complete verified physical union: 16,333 CLOSED cases and separately
retain 18 censored OPEN cases. Each opportunity keeps its original representative,
entry, cancellation, SL, source exit, fixed $23.4 planned risk, fees and slippage.
V2 selects cases, never substitutes another family's later or more profitable
quote. This is an independent-case study, not a shared-capital portfolio.

The 2026 Bybit dataset and its aggregate outcomes have already been inspected.
TEST is a chronological, V2-specific held-out **development test**, not untouched
market OOS or prospective validation. This follows RESEARCH_PROTOCOL.md. Report
the numerical target gate separately from this provenance limitation; the final
TARGET_70_CONFIRMED claim requires both admissible OOS provenance and numerical
gates. No new data acquisition or relabelling of inspected history is permitted.

## Features and partitions

Freeze features at original READY, earlier than the fill interval. Derive them
from the original qualified signal, native bars with CLOSE <= READY and evidence
with known_at <= READY. Use the original ledger only for identity/labels. Real
fill delay, holding, realized fees/slippage, exit, MAE, entry candle extrema and
Range deviation observed at fill are diagnostic/label columns, forbidden inputs.
Expected entry/slippage and quantity are deterministic original policy estimates.
Expected target fees and slippage use the entire predeclared target allocation;
gross target R and friction R share the fixed planned risk denominator. Preserve
also price-distance R using the unadjusted SL distance; never confuse these units.
Unknown features stay missing, not inferred from outcomes.

Order all CLOSED opportunities by READY, then physical ID. Boundaries are the
READY timestamps at floor(.60*N) and floor(.80*N); keep timestamp ties together.
Partition all rows, with no random split or symbol/date selection. Purge TRAIN
labels whose exit >= first VALIDATION READY and VALIDATION labels whose exit >=
first TEST READY. They remain in the full feature table and descriptive ledger.
TEST labels are sequestered; training/selection scripts read only TRAIN/VALIDATION.
Time of day/session/month/symbol/direction/mapping are robustness diagnostics,
not search inputs. OPEN cases remain censored and cannot manufacture CLOSED count.

Confluence uses only independent families on the **same existing physical ID**
and known by original READY. Different OB stop/quote paths count as one family.
Later confirmations never enter an earlier feature. Separately examine recent
same-direction native HTF Range deviation context (within 4 HTF bars), labelled
market context rather than an additional physical family. Reconstruct its known
time, not a future-mutated POI snapshot. Macro HTF flow is retrieved separately
from flow history, ignoring invalidations that occur after READY; SFP reaction
flow must not be called macro HTF alignment.

## Fixed deterministic search space

Scopes: all union, CORE A (Breaker conservative), CORE B (Range aggressive),
CORE C (SFP BOS), A+B, A+B+C, >=2 independent physical families, Breaker with
recent Range context, Breaker+SFP, and Breaker+Range family confluence.
CORE membership is a qualified path known by READY, even when another original
path represents the opportunity. Report representative-path cohorts separately.

Include baseline/each scope alone. Exhaustively cross these preregistered grids,
including an unfiltered option on each axis:
friction_R <= [.30,.20,.15,.10,.075,.05]; net_target_R >= [.5,.75,1,1.5,2,2.5,3];
gross_target_R >= [1,1.5,2,2.5,3]. Extend each cost rule by at most ONE of:
macro-flow alignment; fresh first-test; >=2 or >=3 swept pools; POI age <=4 or <=8
entry-zone bars; structure age <=4 or <=8 entry-zone bars; allowed P/D; OTE;
BOS displacement >=1 native ATR; sweep >=.1 native ATR; no adverse liquidity;
recent Range context. Also examine target ceiling [.5,.75,1,1.5,2] as a single
extension. Maximum five predicates per deterministic rule. Missing required
features fail the predicate. No symbols, months, dates or IDs in rules.

Rank on TRAIN only: numerical profitability gate first, then WR, expectancy,
PF, sample size and deterministic ID. Minimum TRAIN 600 CLOSED for shortlist;
retain top 20 per scope plus scope/cost controls. Validation evaluates only this
sealed shortlist. Keep all search attempts, including zero samples and failures.
Report sample-size fragility and multiple-search selection bias.

Three fixed, interpretable confluence scores have exactly seven components:
Breaker conservative membership; strong Range context (physical Range family OR
recent Range deviation); macro HTF alignment; >=2 swept pools; fresh first-test;
net target R >=1; friction R <=.15. Weights: equal [1,1,1,1,1,1,1], source-hint
[2,2,2,1,1,2,2], cost-first [1,1,1,1,1,3,3]. Evaluate all integer thresholds.
No source claim is made for these experimental weights. Validation chooses score
profile and nested A/A+/TOP thresholds with minimum 400/300/200 validation cases.
If no threshold reaches a floor, retain the unfiltered score and label failure.

## Interpretable meta-filter and selection

If deterministic validation does not reach the joint goal, fit TRAIN-only:
logistic regression, C=1, no class weighting, max_iter=2000, deterministic seed 70;
and decision trees depth 1/2/3, min_samples_leaf 100/200, seed 70. Logistic uses
the seven score inputs with raw pool count/net target R/friction R; TRAIN-only
median imputation and standardization. Trees additionally may use sweep/ATR,
SL/ATR, gross target R, POI/structure age, displacement/ATR, P/D, OTE and first
test. A depth-3 tree has at most seven internal conditions. No black box.
Validation selects thresholds [.30,.40,.50,.55,.60,.65,.70,.75,.80,.85,.90,.95].
Coefficients/tree nodes, fitted preprocessing and all attempted thresholds remain.

Final primary is chosen using VALIDATION only, requiring TRAIN>=600 and
VALIDATION>=200, preferring the joint numerical gates, then positive expectancy,
WR, expectancy, PF, count and ID. Freeze best deterministic, best meta (if fit),
and the three score tiers (<=5 distinct final candidates) before opening TEST.
Report insufficient candidates honestly; do not relax floors after seeing TEST.
No refit on validation. Freeze code hashes, fitted models, predicates, split hashes
and TEST predictions without labels in a Git commit before TEST evaluation.
One final TEST execution only; exact hashed resume may verify completed artifacts
but cannot select another candidate. Do not choose an OOS winner post hoc.

## Metrics, robustness, QA and verdict

Every final candidate: CLOSED/WIN/LOSS/BE, WR, Wilson 95% CI, PF, expectancy, R,
net/gross PnL, actual fees/slippage, realized case-sum drawdown in exit chronology,
average wins/losses, payoff, holding and trades/month. Undefined denominator ->
null. Drawdown is not NAV drawdown. Keep all LONG/SHORT/symbol/mapping/HTF-LTF/
family/month rows, including empty and loss groups; leave-one-group-out diagnostics
must not revise rules. Report TRAIN three chronological subperiods and validation
two subperiods. Stress fixed selected cases at 1.5x and 2x friction, explicitly
without rerouting their frozen fills/quotes/exits. No portfolio claim.

Numerical target gates: TEST>=200 CLOSED, WR>=.70, PF>=1.5, expectancy>0,
AvgR>0, net>0. Robustness/provenance limitations can prevent confirmation even
if point estimates pass. No claim of LIVE readiness.

QA: all 40 exact dataset hashes and original report manifests; physical uniqueness;
timestamp-tie splits and purged labels; recursive known-time audit; independent
expected-cost math; feature equality after deleting future bars/signals/flow and
Range events, including mutations of their future prices/invalidations; label
mutation has zero effect on feature values/predictions; training access receipts;
one-time TEST opening after committed freeze; all tests, compileall, mypy and
Ruff delta against dab8d25. No prior file is overwritten. Save the full user task.

Final report ends with exactly TARGET_70_CONFIRMED or TARGET_70_NOT_CONFIRMED.
