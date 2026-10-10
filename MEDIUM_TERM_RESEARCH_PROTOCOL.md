# Medium-term source research — registered before new outcomes

Parent checkpoint: e917313; preserved main baseline: dab8d254aaf4babc07659e3d03d14b269445767b.
The interrupted V2 objective is cancelled, not resumed. The new user request and
its Anti-Scalp addition authorize a separate medium-term implementation.

## Audit conclusion

The 16,333 CLOSED cases were independent reference-account simulations across
ten coins, 40 series and 15 source entry paths. They were not a shared canonical
portfolio. 8,720 cases used M15/M5; 4,361 H1/M5; 2,086 H4/M5; 728 H1/M15;
389 H4/M15 and 49 H4/H1. The median interval-bound holding time was 65 minutes;
7,675 lasted under one hour. Source case exits were full first FTA (range 80/20),
not canonical TP40/30/30 with cost-adjusted BE. No max-holding, timed exit,
minimum holding or forced end-of-history closure was present.

Relevant preserved code: source_permitted._direct permits independent local
non-OB ideas; _emit quotes/stops from local POIs and targets the mapping's first
FTA; _conservative accepts micro BOS/new POI; evaluate registers six mappings.
SourceTradeCasePortfolio intentionally removes shared occupancy and notional
budget. Canonical VirtualPortfolio already has TP40/30/30, BE and risk guards.
Old gross quote P&L +11,576.961931511372, fees 91,180.15562066888, slippage
30,393.385669964762, net -109,996.57935912227. Holding time is an outcome,
not a causal filter. These independent-account sums are not investable NAV.

## Sources, roles and declared interpretation

Primary SW5/9/11/12/22 PDFs and saved Cryptology materials remain the source
rules. Reuse their native causal detectors without changing frozen code.
D1/H4 provide actual confirmed structure/range and major liquidity. H4/H1
own setups. M15 may refine an already known H1 setup; H1 may refine H4.
No M5/M15 POI can originate a separate idea. SFP countertrend delivery remains
permitted with an actual main-TF raid/reclaim and causal refinement.
Direction alignment is required for direct trend entries; no universal trend
gate is invented for source countertrend SFP or range delivery.

Stops keep source geometry but must also cover the main setup invalidator;
micro refinement cannot shrink away the main idea's structural stop. ATR14
applies only to the registered SFP ATR path, never generic synthetic TP.
Targets are three distinct already-known structural prices: nearest fresh
opposing H4/D1 typed POI/FTA first, then next fresh macro POIs or unswept
external liquidity. A nearer valid FTA is never skipped. Range boundaries
join the list when source-valid. Insufficient real targets means WAIT.
TP40/30/30 and canonical cost-adjusted BE are the user's project exit policy,
explicitly distinguished from PDF source case full-FTA exits.

One physical main opportunity has one immutable causal selected entry path.
Quote/stop/family aliases do not create independent ideas. A repeated OB needs
a genuinely new main reaction/structural confirmation; D/S remain fresh.
Lifecycle: DISCOVERED, QUALIFIED, READY, ENTERED, CLOSED/INVALIDATED/EXPIRED.
No time cooldown/TTL/forced closure/minimum holding. Structural changes supply
the cooldown. Pending cancellations and entered structural exits use main-TF
body evidence, not generic micro BOS. End-of-data is OPEN/CENSORED, not CLOSED.
Revision before any new P&L evaluation: SFP P/D snapshots use the actual macro
dealing range, not the pattern candle envelope. Refinement-POI body invalidation
and absence of valid current macro context withdraw pending entries only;
entered positions retain main-thesis exit watches. Initial detector jobs were
interrupted before simulation and their logs/locks remain archived in the parent
report root. Corrected runs use the `validated` subdirectory and a new lock.
Prefix QA then found a new engine error: RANGE terminal-map membership was
checked without comparing the terminal observation timestamp. READY evidence
was identical under prefix/future mutation, but one range exit was early.
Correct it to terminal_known_at <= current_close and preserve failed snapshots.
Final causal runs use `causal_final`; no thresholds or source entry rules change.
Independent detection may use up to three workers on the four-CPU instance.
An already consumed first structural target withdraws pending quotes at its
observable execution close (EXPIRED); it does not close an entered position or
retroactively undo an ambiguous same-bar entry. Holding is never a gate.

## Anti-Scalp addition (frozen before new backtest)

Fee rate 0.0006 per leg, slippage 0.0002 per leg, matching existing baseline.
For unit quantity and sign s: gross=s*(target-entry), entry fill=entry*(1+s*slip),
exit fill=target*(1-s*slip). Costs=fee*(entry fill+exit fill)+slip*(entry+target).
edge_cost_ratio=gross/cost. Check the nearest real structural target before
READY; recheck the actual fill reference before admission. Require ratio >=3.
This engineering risk buffer limits estimated costs to one third of potential
gross movement; it is not a literal PDF rule or a profitability guarantee.
Reject status REJECTED_SCALP_RISK with NO_HTF_CONTEXT first, TARGET_TOO_CLOSE
for missing/not-yet-known/at-cost targets, POOR_EDGE_COST_RATIO for ratios below
three. No actual future duration, realized P&L, MFE/MAE or outcome enters gates.

## Registered data and comparisons

Primary: existing pinned Bybit mirror BTC/ETH real M15, H1, H4 data from
mestoness/btc-eth-candles-history@9ca04178df06ce649f00779a49e11094fe5b1c70.
Requested entries 2023-01-01..2026-01-01; actual coverage ends 2025-12-05
23:30 UTC (2.93 years). 2022 supplies causal warmup only. H1/H4 normalized
complete M15 aggregates have saved native comparison differences; retain that
provenance limitation. D1 consists only of complete UTC days of real bars.
No interpolation, partial aggregate, fabricated M5 or exchange mixing.
Secondary matched development cohort: original ten native Bybit coins/40
series/993,575 bars, D1 complete aggregates added. These data were already
inspected: no OOS/holdout claim. Do not select periods/coins by new outcomes.

Run paired medium candidates with Anti-Scalp enabled/disabled over identical
causal signals. The disabled arm is research-only, not the strategy default.
Run canonical shared equity 1,170, 2% risk, 6% aggregate risk, 4% daily loss,
3x isolated margin; distinguish occupancy effects from horizon/filter effects.
Independent-case control uses identical canonical TP/BE/risk caps per case,
not the old unlimited-case notional assumption. Preserve all OPEN cases.

## Required evidence and QA

Hash-lock source code, policy, history and artifacts. --resume-existing must
verify every dependency and output before reusing a completed segment.
Report holding bounds and bins, gross-reference minus fees minus slippage =
net, turnover, setup/TF/coin/side/year/month, daily-NAV Sharpe/Sortino subject
to existing sample gates, drawdown and loss streak. Compare old short cases
by applying only their saved pre-entry evidence; use future holding solely
for descriptive grouping after the decision, never candidate selection.
Full old tests, targeted tests, compile, lint with inherited baseline separate,
mypy, BACKTEST/SHADOW parity, prefix/future-mutation and timestamp proofs.
Always trade_entry_allowed=false; no LIVE/private API/orders/withdrawals.
No outcome-driven threshold revisions, fixed-percent TPs or count target.
