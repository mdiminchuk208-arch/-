# Registered execution assumptions

UNPROVEN_PRICE_ROUNDING_ASSUMPTION: no historical tick rounding; continuous theoretical prices used. Outward/inward epsilon is 1e-8 relative, not inferred historical tick. This research mode is authorized in the current user request and cannot support exchange-executable/live claims.

UNPROVEN_WITHIN_BAR_CONTINUITY_ASSUMPTION: ordered stop-only limit crossings assume a continuous price path between observed extrema. Ambiguous profit/order chronology stays WAIT_INTRABAR_ORDER. No M1/M5 added.

NOT_REQUIRED_FOR_THIS_ACCOUNTING_VIEW: qty_step, minimum_qty, quantity_precision, exchange lot sizing, display price_precision, base/quote currency labels for dimensionless R. Linear price payoff is an explicit theoretical model; historical contract/filter periods remain unverified. No account-sized Net, liquidation, leverage, spread, market impact or actual funding claim.
