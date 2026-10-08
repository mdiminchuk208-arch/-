# BACKTEST → SHADOW contracts

## Scope

This implementation extends the existing core rather than replacing detection
rules. `evaluate_snapshot` calls SOURCE_CONSERVATIVE structure analysis, default
fail-closed Range Engine and existing MTF linking. It uses only closed candles
with `close_time <= as_of`; future OHLC cannot affect the snapshot.

Snapshots are immutable. Signals identify symbol, HTF/LTF, direction, SFP/BOS/
observation timestamps, geometry availability, entry zone, optional entry
reference, stop/targets, evidence score, reasons, strategy version and analysis
mode. JSON exports use LONG/SHORT. IDs derive from stable market identity, not
sequential report IDs. Decisions use observation time, not backdated geometry time.

Missing, duplicate, out-of-order, overlapping, unfinished, nonpositive-price or
wrong-duration bars fail closed in replay. Each supplied timeframe must be
contiguous. Empty histories produce no signal.

## Qualification and signal states

- WAITING_FOR_ENTRY_GEOMETRY;
- WAITING_FOR_SOURCE_LEVELS;
- REJECTED_ENTRY_GEOMETRY (invalid broken-extreme→anchor impulse);
- SOURCE_CONTEXT_BLOCKED;
- INVALIDATED (all contributing HTF SFP contexts invalidated);
- READY_FOR_VIRTUAL_ENTRY.

READY requires OTE geometry and SL plus three strictly ordered directional targets.
By default, qualification is an explicit caller assertion: the engine validates
geometry and availability time. Opt-in `--auto-levels` instead detects a conservative
experimental subset of OB/HTF-gap evidence; it does not establish source certification.
See AUTO_LEVELS.md. Future references cannot unlock current decisions. Rejection
and invalidation are terminal in the virtual ledger. Consumed IDs cannot be reused.

`QualifiedLevels` accepts known_at, stop_loss, targets, stop_policy and target_policy.
The CLI's `--qualified-levels FILE.json` reads an object keyed by emitted signal ID,
with those five fields. Targets are exactly three prices; known_at is an ISO
timestamp with a UTC offset. These inputs are retained in the output manifest.
No levels are invented by default.

Automatic selection and caller assertions cannot be mixed in one run. Automatic
signals export `level_policy`, structured `level_evidence`, and
`level_blocking_reasons`; the manifest preserves both threshold parameters and
latest status/blocking counts per unique signal. Withdrawal of a formerly ready
setup clears its pending virtual entry at the observation close. Existing open
positions keep their original signal levels and continue to be managed.

## Explicit BACKTEST parameters

The source defines an OTE zone, not a unique optimal price. New `optimal_entry`
is the midpoint, labelled MIDPOINT_OF_OTE_BACKTEST_PARAMETER; the core geometry's
original single-price field stays unset. Virtual fills follow a distinct next-open
policy: a subsequent bar must open inside the zone, with directional slippage.
The midpoint is a reference, not a claim of optimal trading performance.

Score measures evidence completeness: SFP 35, causal BOS 30, ready structure/OTE
20, qualified levels 15. This experimental 0–100 score is not a profitability
estimate or validated source scoring rule.

Virtual defaults: per-trade risk 2%, aggregate cap 6%, daily net realized loss
limit 4%, Isolated x3, per-side fee 0.06%, per-side slippage 0.02%, re-entry score
>=75. The 4% daily value is the preserved configurable simulation default.
The source-aligned 0.25–2% helper in risk.py is unchanged; the virtual
policy independently implements the user's 2–5% range.

## Virtual management and causal ordering

`VirtualPortfolio.step` receives a synchronized batch of closed execution bars
for every open-position symbol. Incoming signals are observed at that batch's
close and queued for a subsequent candle; the signal candle cannot fill them.
All next-open admissions occur before any same-batch close PnL is booked.
Symbol ordering is deterministic when portfolio risk is scarce.

The historical CLI defaults to one $1170 portfolio for all ten symbols. Entry
fees reduce balance immediately; equity equals balance plus gross open-position
P&L at the currently observable mark. Before admissions, all symbols are marked
at the synchronized candle open. Quantity budgets the modeled SL loss including
entry/exit costs at 2% of current equity; it is not reset to the starting capital.
Admission reserves entry fee/slippage before checking margin and the 6% risk cap.
Each exit books gross P&L less exit fee to balance; its economic net result also
allocates the already-paid entry fee once. `balance_change` is the ledger delta;
`net_pnl` on exit is the partial trade result. Summing exit net results reconciles
the completed trade, while summing all balance changes reconciles portfolio cash.

Reports retain marks, margin, daily realized P&L, fees, slippage, equity peak and
bar-close drawdown. MFE/MAE are explicitly full-bar envelopes: exit-bar extremes
may have occurred after an intrabar fill. Open positions are marked at the last
close, not forcibly liquidated. Funding, liquidation and historical exchange lot
filters remain unmodelled; quantities are fractional linear coin units.

An extreme gap can exceed nominal risk and exhaust capital. This is recorded as
an adverse gap and explicit BANKRUPT state; losses are not silently clamped.
Daily loss is measured from realized balance changes, with the day's reference
equity fixed at UTC rollover. A later profit does not reset the daily latch.

`historical_replay.indexed_signal_updates` accelerates large offline research.
It exposes append-only structure facts only at the close of their indexed candle,
including SFP events whose display timestamp is the open. Future invalidations,
context arrivals, transition resolution, OB consumption and POI freshness each
wait for their observation time. Only completed transitions and confirmed price
references reach shared signal construction. UNREVIEWED Range emits no usable
Range SFP, so indexing cannot enable Range entries or accept manual review inputs.
The event queue cannot rewind when an old touch is discovered during later
geometry resolution. State-change journaling omits repeated unchanged WAITING
messages; the portfolio and fills follow the same rules in both offline modes.

TP1 closes 40% of original quantity and moves the remaining stop to breakeven
including fees and slippage. TP2/TP3 close 30% each. The old stop wins same-bar
SL/TP ambiguity. If TP1 and the new BE stop are reachable in one OHLC bar, BE wins
over TP2/TP3. Before admission, TP1 must have positive net reward after modeled
entry/exit costs. This prevents a BE stop beyond TP1 being filled outside the
candle's range; it imposes no arbitrary minimum RR.
Gap stops use the adverse opening price. Daily limit blocks new
entries but existing positions continue to be managed. The daily latch persists
after later profits until UTC rollover.

Repeated IDs do not create repeated trades. A new signal may re-enter only after
the old position completes and with score >=75. Admission checks modeled total
stop risk and available isolated margin.

## Before integration

1. Source review/certification of automatic OB/POI selection is still needed.
   Original PDFs are absent from the uploaded archive. The opt-in experiment uses
   explicitly normalized HTF gap seeds and three distinct opposing targets; it
   does not remove the existing source-conformance gate. Without explicit levels
   or all automatic evidence, observations produce no simulated trades.
2. A current-market public-feed adapter is not connected. SHADOW here is the tested
   closed-candle observer and virtual-management contract, including offline parity,
   rather than a deployed market-watching service.
3. Closed-HTF snapshots defer next-open SFP knowledge until the HTF candle closes.
   A lower-latency open-observation adapter needs separate causality tests.
4. Independent snapshots recompute prefixes. The historical index is tested
   against prefix snapshots and supports long offline periods. It does not serve
   a current-market feed. Warmup can affect left-edge context and is recorded.
5. Funding, liquidation, exchange fills, contract minimums and price/quantity
   rounding are not modeled. Modeled stop risk does not guarantee a limit on gap
   losses. Results do not establish profitability.
6. Range clarity remains manually reviewed. The structural cross-asset audit does
   not close all Range normalization gates.

LIVE is rejected. Trade-entry permission stays false for snapshots, signals and
the virtual portfolio. This work adds no private API, real order adapter or
production-site integration.
