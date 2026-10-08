# Controlled exit research addendum

Canonical baseline is unchanged: commit
`3a9632606f79b4454509a60674eeac3877f77bbf`, TP fractions 40/30/30, existing SL,
and the existing per-unit cost-adjusted breakeven immediately after TP1.
All 57 source/config hashes remain protected. This addendum is registered before
running any alternative exit policy. Some canonical external outcomes have already
been inspected; those periods are not represented as wholly blinded exit research.

## Fixed experiments

Allocation comparisons keep immediate cost-adjusted BE after TP1:
A = 40/30/30, B = 30/30/40, C = 25/25/50, D = 25/35/40.
Separate timing comparisons keep A allocation:

- BE_TP1: existing immediate BE and pessimistic same-bar handling.
- BE_LATER_CLOSE: original SL until a later complete LTF candle closes on the
  favourable side of the unchanged cost-adjusted BE price. The new stop becomes
  active on the next bar; an earlier crossing is never filled retroactively.
- ORIGINAL_SL_UNTIL_TP2: original SL through TP1; cost-adjusted BE after TP2,
  with the same pessimistic same-bar stop priority.
- STRUCTURAL_AFTER_TP1: original SL until TP1, then ratchet to the latest newly
  confirmed adverse-side LTF structural swing formed after TP1. Confirmation is
  computed by the unchanged SOURCE_CONSERVATIVE analyzer from the last 576
  already-closed LTF bars. Only a level not already swept/broken by the observation
  close and on the protective side of the current close can be used. Ratchets are
  applied at that close for the next bar, never to the bar that confirmed them.
  This is a declared experimental exit normalization, not a source-approved rule.

No entry, Score, structure, OB, POI, freshness, target prices, risk, leverage,
fee or slippage rule changes. Full portfolio experiments reuse the exact frozen
observed signals; changed exit cash/occupancy may affect later risk admissions.
Those feedback differences are recorded, not attributed to changed entry rules.
Paired single-entry replays additionally reuse each actual canonical fill's
entry equity, quote, quantity and risk, isolating exit effects from admission
feedback. They are counterfactual research, not newly found strategy signals.
All variants have the same observed endpoint; open positions are censored.

## Development and untouched reserve

The original 2026 Bybit history remains DEVELOPMENT. Previously inspected new
canonical periods retain their REFERENCE / VALIDATION / retrospective HOLDOUT
labels, with the partial exit unblinding limitation stated above.

An extra exit-only reserve is fixed before its strategy outcomes are inspected:
BTCUSDT Binance mirror, 60m/5m, calendar 2019 Q4
[2019-10-01T00:00:00Z, 2020-01-01T00:00:00Z), 90 preceding days of reference,
minimum 576 LTF warmup, all continuous coverage segments retained. BTC is the
first symbol in the original priority, not a choice by profit. This period was
never part of the primary common-basket study, which starts in 2020. It is an
unseen retrospective reserve, not prospective OOS, and remains a distinct
single-symbol cohort with unverified Binance market type. It cannot be pooled
with a seven-symbol basket to manufacture sample size.

No variant is selected from any performance table. A candidate change would need
a separate sufficient untouched sample; baseline remains frozen throughout.

## Measurements and counterfactuals

Per independent cohort/mapping/period/segment report trades, win rate, average
win/loss, expectancy, PF, mean/median R, NAV drawdown, losing streak, TP1/2/3 hit
rates, BE stops after TP1, fees/slippage and net PnL. Allocation fractions always
refer to the original entry quantity and sum to one. Every partial exit allocates
the original entry fee proportionally and pays its own exit fee/slippage.

For actual baseline post-TP1 BE exits, examine at most 30 subsequent calendar
days, clipped to the original contiguous observation boundary. Report separately
unconditional later target price touches and targets reached before the original
SL under pessimistic stop-first OHLC handling. Same-bar ambiguous cases and
right-censoring remain explicit. A later price touch alone is not a counterfactual
profit, and no signal or market candle is invented.

Do not pool independent capitals or overlapping walk windows. TP1/BE inference
requires at least 100 comparable closed OOS trades and 30 post-TP1 events;
these are minimum research gates, not proof that a strategy change is justified.
Below them the recommendation is insufficient evidence to change exits.
Use expectancy p*AvgWin - (1-p)*AvgLoss and the descriptive break-even win-rate
AvgLoss/(AvgWin+AvgLoss) only where the denominators and observed samples exist.
All entry rules remain fixed, trade_entry_allowed=false, LIVE/private execution
disabled. Regression checks compare A bit-for-bit with canonical trades,
decisions and equity, and verify future-prefix and BACKTEST/SHADOW invariance.
