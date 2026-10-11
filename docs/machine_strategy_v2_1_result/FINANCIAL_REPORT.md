# Frozen machine financial result

{
  "cases": 373,
  "orders": 373,
  "filled": 85,
  "CLOSED": 83,
  "open_censored": 0,
  "order_censored": 0,
  "intrabar_unresolved": 2,
  "WIN": 38,
  "LOSS": 45,
  "FLAT": 0,
  "WR_percent": 45.78313253012048,
  "Gross_R": 27.61045018010263,
  "Fees_R": 29.21419925919829,
  "Slippage_R": 9.738066419732764,
  "Funding_R": null,
  "Net_R_ex_funding": -11.341815498828415,
  "PF_net": 0.8375520967969219,
  "Expectancy_R": -0.1366483795039568,
  "AvgR": -0.1366483795039568,
  "MedianR": -0.6316756641047537,
  "AvgWin_R": 1.538851462890601,
  "AvgLoss_R": -1.5515149130815833,
  "payoff_ratio": 0.991838009364776,
  "breakeven_WR_percent": 50.20488590429668,
  "MaxDD_R": 29.063266435212768,
  "MaxDD_percent_closed_case_curve": 26.38837114598526,
  "max_loss_streak": 5,
  "average_hold_hours": 9.704819277108435,
  "median_hold_hours": 3.5,
  "equity_curve_convention": "100 initial R units; one unit price risk per independent case; sorted observable exit time then case ID. Diagnostic closed-case curve, no shared margin/portfolio claim.",
  "net_definition": "Closed independent cases only; funding unavailable/excluded. All amounts are normalized risk units, not exchange account currency.",
  "status_counts": {
    "UNFILLED_EXPIRED": 177,
    "CLOSED": 83,
    "GAP_INVALIDATED_BEFORE_FILL": 111,
    "WAIT_INTRABAR_ORDER": 2
  },
  "known_entry_fees_all_filled_R": 15.575922408927978,
  "cost_multiplier": "1",
  "trade_entry_allowed": false,
  "raw_candidates": 18020,
  "allowed_setups": 373
}

See ALL_CASE_EXECUTIONS/ALL_TRADES/CLOSED_TRADES and BREAKDOWNS for every case, WIN/LOSS and complete groups. Normalized risk units, funding excluded, theoretical unrounded execution; not exact Original or historical exchange-account PnL. Unresolved intrabar exclusions may bias resolved results. No strategy changes after outcomes.
