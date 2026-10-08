# Frozen strategy robustness research protocol

Registered before inspecting performance on any newly recovered historical data.
Canonical strategy commit: `3a9632606f79b4454509a60674eeac3877f77bbf`.
Policy: `0.4.21-causal-limit.3`; BACKTEST/SHADOW only; trade_entry_allowed=false.
The baseline lock records exact code/config SHA256 and default policy parameters.
No strategy source file may change during this research stage. Experimental variants
must be isolated, labelled and excluded from canonical results.

## Data and temporal contamination

The previously inspected Bybit January–September 2026 history is DEVELOPMENT,
including every subdivision of it. It cannot be relabelled untouched OOS.
Public exchange archives and GitHub mirrors may supply a separate dataset, with
original URL, repository commit, exchange/instrument provenance and hashes.
Spot and derivatives data, different exchanges and disconnected coverage remain
separate cohorts. No gap interpolation, synthetic OHLC or price splicing is allowed.

For an external continuous cohort, before viewing its strategy outcomes, freeze
chronological splits from coverage only: first 60% reference, next 20% validation,
last 20% retrospective external holdout, rounded to UTC calendar days. This is
unseen data under already frozen rules, not a claim of prospective performance:
historical periods preceding 2026 development must be labelled retrospective.
New observations after freeze would be required for prospective OOS evidence.
The primary external study excludes calendar 2026 entirely: its latest permitted
execution close is 2026-01-01T00:00:00Z. This prevents the 2026 development market
dates being treated as untouched merely because the exchange is different.
Symbols are selected by this fixed priority, never by profit: BTCUSDT, ETHUSDT,
SOLUSDT, XRPUSDT, BNBUSDT, DOGEUSDT, ADAUSDT, LINKUSDT, AVAXUSDT, LTCUSDT.
Data availability determines cohorts; missing assets remain explicitly missing.
TFs 5m, 15m, 60m, 240m must use complete aligned real lower-timeframe aggregates
or separately verified original bars. 1D is not a strategy input.

## Fixed windows and metrics

Canonical mappings: 15/5, 60/5, 60/15, 240/5, 240/15, 240/60. Each independent
portfolio starts with $1170; PnL cannot be added into a fictitious shared capital.
Minimum warmup remains 576 LTF bars. Walk-forward uses 90 calendar days of
reference and the following 90 days of evaluation, advancing 90 days; the last
partial window is retained and labelled. No fitting occurs in reference periods.
All windows, including loss periods and zero-trade windows, are retained.
At period end positions are marked to market, not force-closed; open trades and
unfinished setups remain right-censored. Report realized and equity PnL separately.

Report setups/READY/fills/closed trades, LONG/SHORT, symbol/mapping, costs, R,
win/loss/BE, TP1/2/3/SL, PF, expectancy, drawdown and duration, losing streak,
exposure, holding time and trades/month. Regime and volatility labels are causal:
trailing 30-day price return (>10% bull, <-10% bear, else sideways), trailing
30-day daily-return standard deviation (<2% low, 2–4% medium, >4% high).
Insufficient preceding observations get UNKNOWN; no full-sample quantiles or
future labels. These are research labels, not new trading filters.

## Sensitivity, not selection

One-at-a-time variants fixed before outcomes: aggression .55/.60/.65; engulf
ratio 1.0/1.05; POI freshness inclusive wick / exclusive wick / body overlap;
OTE shallow .700/.705/.710 and deep .785/.790/.795; risk 2%/2.1%/2.5% within
existing admissible bounds; near-edge vs interior midpoint limit; reentry Score
75/80; two/three/four opposing POI availability (qualification-only if the fixed
three-TP contract prevents a compatible execution experiment). Cost scenarios
base, 1.5x, 2x fees and slippage. No best value is selected and baseline is unchanged.
Structural sensitivity evaluates the fixed primary 60/5 mapping on validation
data only; cost/risk and entry-frequency analyses cover all six mappings.
The same complete frozen symbol cohort is retained across comparable variants.

## Inference and verdict

At least 100 closed trades per mapping is required for an affirmative edge verdict;
seven fills across independent development mappings are insufficient. Sharpe,
Sortino and Calmar are withheld below 90 daily observations or 30 closed trades;
zero denominators are undefined, never infinity. Monte Carlo requires at least
50 closed trades in one comparable mapping/cohort; never pool six portfolios to
reach the threshold. If eligible, use 2000 seeded bootstrap/shuffled sequences,
report DD/streak distributions and the observed-sample limitation, not market guarantees.

Verdicts: INSUFFICIENT SAMPLE; NO ROBUST EDGE; PROMISING — REQUIRES MORE VALIDATION;
ROBUST ENOUGH FOR EXTENDED SHADOW TESTING. An affirmative robustness verdict needs
positive untouched holdout expectancy/PF, surviving 1.5x and 2x friction, sufficient
sample and consistent results across at least three temporal windows and regimes.
No LIVE readiness verdict is permitted. Poor outcomes are reported unchanged.
