# ORIGINAL v1.1 FIRST FINANCIAL BACKTEST — PRE-OUTCOME

Authorization is the complete request preserved in
`data/source_materials/original_v1_1_financial_backtest_2026_10_11/user_request.txt`.
This is one new stage after frozen commit
`43e9d7addcd427650ff856dd1fa99f78ee5c06f7`; strategy manifest SHA256 is
`dca962ff1f829887d0787a6329112e77f4ce714023bee85f666ed37843f2ecbb`.
U1–U6/N11, all strategy artifacts, v1, source audit and baseline stay immutable.
No outcome may change this protocol, adapter, metrics or accounting assumptions.

Before any real-history financial result, commit this protocol, the executable
preregistration, producer/test scripts, market/evidence hashes and preflight QA in
a separate PRE-OUTCOME commit. The runner verifies these committed bytes before
unlocking `--run`. Tests use synthetic arithmetic fixtures; they do not calculate
the current profile's real-history profitability before the PRE-OUTCOME commit.

## Dataset and exact interval

Same verified baseline-C Bybit BTCUSDT/ETHUSDT files, no additional symbol/history
or timeframe. Trading interval UTC: 2023-01-01 00:00:00 through 2025-12-05 23:30:00.
2022-01-01 warm-up is the existing baseline warm-up, not scored trading exposure.
Native M15/H1/H4 CSV.gz bytes must match archived baseline audits. D1 contains only
complete real UTC days derived from M15; both OHLC and canonical content SHA256
must match baseline-C D1. Partial last day is excluded. Scoring requires native
OPEN >= trading start and native CLOSE <= trading end. Availability differs by TF:
M15 ends23:30, H1 ends23:00, H4 ends20:00 and last completed D1 ends00:00 on Dec5.
No interpolation, incomplete bars, M1/M5, public/private API fetch or extension.
Exact native/derived hashes and 271,770 scored bars are in dataset_manifest.json.

## RAW proposals and evidence adapter

Adapter `RAW_GEOMETRY_WITH_EXTERNAL_EVIDENCE_v1` is an explicit candidate
enumeration normalization, not SOURCE_RULE or a unique original pattern detector.
It reads only causal completed bars. Last confirmed strict three-bar swings are
RAW reference points only, confirmed at right-neighbour CLOSE before another raid.
Necessary geometric proposals: wick raid/reclaim for SFP; old raid/full-range
engulf for OB/STB; first later body-cross of a provisional engulf zone for Breaker;
deviation/reclaim of a provisional last-swing bracket for both conservative Range
descriptions. No percentage, ATR, tolerance, range-clarity or smoothness threshold
is added. Last-swing bracket/zone selection does not prove externality, meaningful
liquidity, whole impulse, actual source endpoints or complete formation/confirmation.
RAW IDs denote proposals, not proven canonical physical ideas.

This RAW convention is not exhaustive discretionary setup detection. Its count
does not equal the number of real source-valid setups and cannot prove a historical
maximum. All admitted ideas still require the frozen source profile and explicit
causal evidence. No new machine boolean becomes source_validated merely because
a primitive was observed.

The frozen historical annotation catalog is empty: no authoritative causal
source_validated historical annotations for meaningful liquidity, EQ tilt, smooth
approach, whole impulse, range clarity, structural endpoints or branch confirmation
are present. No dated historical public instrument-tick metadata bundle exists.
Synthetic v1.1 examples, MediumTermEngine labels/role fields, old751/446 and fitted
tree outputs are excluded. Do not backdate current exchange metadata or infer a
legal tick from displayed OHLC decimal precision.

Absence of annotations is WAIT, not absence of setup. The exact frozen checker is
called for every primary proposal. Missing instrument metadata is the earliest
frozen WAIT; later predicates are NOT_EVALUATED, not FAIL. Independently report
overlapping missing-qualitative/stop/liquidity/lower-TF blockers. Never sum these
overlapping diagnostic counts as if they were exclusive reasons. M15 confirmed
OB/SFP lacks a strictly lower TF in this profile; do not silently enable M1/M5.

This registered empty catalog analytically permits no evidence-complete historical
ALLOW. Unexpected ALLOW is an integrity error. Preserve zero admissions rather
than manufacturing annotations, fills or financial cases to exercise accounting.
The first result may therefore be ZERO_EXPOSURE_SOURCE_EVIDENCE_BLOCKED. Its zero
PnL is not proof that strategy expectancy/WR/edge is zero. Real fill/exit/portfolio
paths remain historically unexercised in that state.

## Admission, entry and position management

Only frozen `ORIGINAL_STRATEGY_EXECUTABLE_PROFILE_v1`. Active SFP, confirmed OB,
Breaker, STB/BTS half entry and conservative reclaim/return/retest Range branches.
Source entry/SL/FTA must be determined before source ALLOW. Physical-idea selection
is mandatory before lifecycle activation; duplicates are confluence, conflicts
WAIT_BRANCH_CONFLICT. FIRST_TEST_ONLY: used source POI/formation cannot be relabelled
as new evidence. New formation/confirmation/new POI/full validation is required.

Non-Range exits100% at the nearest known opposing causal contextual FTA; no H4/D1
owner restriction. Range80% plus remaining20% in the same frozen source exit zone;
optional breakout remainder disabled. SL fixed: OB extreme/minimum tick, Breaker
raid/impulse/minimum tick, SFP SMA14 TR from pattern extreme, STB raid, Range deviation.
Nonunique stop -> WAIT_UNRESOLVED_STOP_GEOMETRY. SFP manual invalidation is separate
completed pattern-TF body close beyond extreme. No TP1→BE or stop movement.

Frozen source LIMIT plan is not FILLED. Activation requires physical selection and
strictly later causal price evidence accepted by its unchanged lifecycle contract.
No invented quote/one-minute subbar or future OHLC. Unknown mutually exclusive
intrabar order -> WAIT_INTRABAR_ORDER, censored, never SL-first/TP-first or optimistic/
pessimistic path. EOF does not liquidate positions; pending unfilled is separate
from FILLED OPEN/censored. With the registered empty evidence catalog no orders or
execution paths can exist; report this limitation rather than pretend a historical
portfolio/fill model was validated.

## Accounting views and costs

Both views are registered; neither is selected based on performance.

- INDEPENDENT_SOURCE_CASES: reference1170 USDT per case, fixed2% initial gross-stop
  risk23.4 USDT. Quantity=23.4/abs(entry−fixed stop). Independent gross setup cases,
  no portfolio gates; DD is a chronological closed-case reference cash ledger.
- SHARED_PORTFOLIO: initial1170 USDT,2% of causally known equity at observable fill;
  shared chronology/known marked equity. No project leverage, margin, totalrisk6%,
  daily, correlation or anti-scalp admission restrictions. If capital cannot size
  a position, report accounting censor, never SOURCE_REJECT. With no ALLOW this
  view is the flat zero-exposure account, not proof of an exercised portfolio engine.

These sizing conventions are ACCOUNTING_NORMALIZATION_PRE_BACKTEST, not SOURCE_RULE.
Costs inherit baseline-C rates: entry fee0.0006 and exit fee0.0006; entry slippage
0.0002 and exit slippage0.0002. Apply modeled notional debits at reference prices,
keeping source LIMIT quotes intact. These are assumptions, not actual measured
historical fills, maker/taker tiers or execution expenses. Funding series is absent
and excluded, not asserted zero; Net is not funding-inclusive. No liquidation model.
Gross uses reference entry/exit P&L before costs; Gross−Fees−Slippage=Net. Costs
must not alter original admission, source risk anchors, source targets or lifecycle.

Closed-trade outcome ratios use CLOSED only; open/censored cases never become
WIN/LOSS. WIN Net>0, LOSS Net<0, exact zero separately. WR=WIN/CLOSED; PF=sum positive
Net/sum absolute negative Net. R=Net/initial gross-stop risk. Expectancy=mean Net.
Holding uses causal entry/exit event knowledge, with no future holding input to
admission. P&L/cost totals are closed-case realized values; distinguish any open
costs/equity if present. Empty sample: P&L/costs/DD=0 for zero exposure; WR/PF/
expectancy/R/AvgWin/AvgLoss/payoff/breakevenWR/holding=null. No-trade performance
is NOT_IDENTIFIABLE; do not report a zero WR or PF as strategy performance.

## Comparison and complete output

Read baseline-C financial outcomes only after recording the first primary outcome.
880 old filled cases are a secondary exact legacy-event probe using the same frozen
profile and empty annotation catalog. Branch mapping is preregistered: direct OB,
aggressive Range and independent SnD styles are inactive/component-only; compatible
styles still WAIT if required evidence is absent. STB edge projected to its source
branch does not prove an exact half-price fill match. Old READY style rejection is
not proof that no later conservative setup or source-permitted alternative existed.
Do not import MediumTermEngine for source admission or re-use its labels.

Show baseline READY/entries/WR/Gross/Net/PF/Expectancy/R/DD/holding and new results,
the old880 ALLOW/REJECT/WAIT breakdown, unmatched new FILLED and removed machine-extra
gates. No matched fills -> no causal attribution to a specific gate. Baseline's
old gross_pnl already includes slippage; add it back once to compare cost-before
Gross, preventing a second slippage subtraction.

Save all RAW candidates, WAIT/REJECT/ALLOW separately, rule/evidence traces, empty
or populated all-trades CSV, cost ledgers, all requested metrics, symbol/direction/
branch/TF/year/month breakdowns, intrabar cases, dataset/preregistration hashes and
QA receipts. All previous661 tests plus new tests; SHA checks; completed candles/
known_at; prefix/future mutation; replay/parity; cash identity; reproducible resume.

After first result, producer bytes and U1–U6/N11 cannot change, regardless of WR,
PF, Net, admissions or WAIT count. Add QA/report artifacts only; seal and commit
this one result; verify read-only --resume-existing, push research branch, STOP.
No second strategy variant, overlays, optimization, main merge, LIVE/private APIs.
`trade_entry_allowed=false` always.
