# Repository agent instructions

These instructions apply to automated/code agents working in this repository.

## PURE SOURCE strategy work

Before changing any PURE SOURCE strategy file, read:

1. `PURE_SOURCE_CURRENT_STATUS.md`
2. `config/pure_source_identifiability_frontier_v2.json`
3. the relevant staged PURE SOURCE design document under `docs/`

For source truth, use this priority only:

`Методичка → SW5 → SW9 → SW11 → SW12 → SW22 → other confirmed ORIGINAL SOURCE materials → SOURCE Rule Registry`.

Repository code, historical Bybit runs, `README.md`, `CONTINUATION_STATUS.md`, old reports and historical PnL are implementation/evidence only. They may not resolve SOURCE ambiguity.

Hard boundaries:

- `OBJECT VALIDITY != TRADE ELIGIBILITY`;
- closed-candle, no-look-ahead causality must be preserved;
- preserve `formation_at`, `known_at`, `confirmed_at`, `invalidated_at` semantics;
- classify additions as `SOURCE_RULE`, `TECHNICAL_NORMALIZATION`, or `PROJECT_POLICY`;
- do not put `PROJECT_POLICY` into PURE SOURCE baseline;
- do not choose among SOURCE-permitted variants using PnL, win rate, PF, expectancy, score or ranking;
- qualitative SOURCE concepts must not be replaced by arbitrary OHLC/ATR/tick/percentage thresholds;
- unresolved source semantics remain `UNRESOLVED`/`UNKNOWN`, never guessed `PASS`;
- `trade_entry_allowed=false` must remain fail-closed;
- no PURE SOURCE PAPER/LIVE/private exchange execution or real orders.

Explicit PROJECT overlays that are forbidden inside PURE SOURCE include Anti-Scalp, edge-cost admission, fee/slippage admission filters, project HTF admission, scoring/ranking, portfolio/correlation/daily-loss/leverage policy, TP 40/30/30, project breakeven and project re-entry filters.

Finite, explicit SOURCE alternatives may be represented as separate stable branches without ranking or declaring a winner.

Run the repository Strategy Engine validation workflow/tests after strategy changes. Do not weaken a causality, dataset-identity, fingerprint or safety assertion merely to make a test pass.

## Platform / backend work

Platform/backend/site code may consume Strategy Engine outputs but must not redefine SOURCE trading semantics. Keep real trading disabled unless a separate future project decision explicitly changes the safety boundary.
