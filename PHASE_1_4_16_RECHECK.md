# Phase 1.4.16 v0.4.16 — Recheck

## Automated QA

- Full unittest suite: **206/206 PASS**.
- `python -B -m compileall -q src scripts tests`: PASS.
- `scripts/analyze_mtf_sfp.py --help`: PASS.
- Source Rule Registry: `phase1.4.16-0.4.16`.
- Registry: **85 rules / 85 unique IDs**:
  - 25 `SOURCE_RULE`;
  - 53 `TECHNICAL_NORMALIZATION`;
  - 7 `BACKTEST_PARAMETER`.

## New regression coverage

Mirror tests prove that the candidate builder rejects:

- UP impulse with a later correction swing low at or above boundary #1 high;
- DOWN impulse with a later correction swing high at or below boundary #1 low.

Valid directional geometry remains accepted.

## Retained BTC real-data differential

BTCUSDT 60m:

- old: `232` ranges / `151` ever validated / `28` boundary SFP;
- new: `227` ranges / `150` ever validated / `28` boundary SFP;
- removed inverted candidates: old IDs `4`, `82`, `94`, `150`, `206`.

BTCUSDT 240m:

- unchanged at `57` ranges / `31` ever validated / `7` boundary SFP.

## Safety boundary

- No `trade_entry_allowed=True` assignment exists in source/scripts/tests.
- Cross-Asset freeze from Phase 1.4.15 is preserved.
- Entry Engine remains blocked.

## Readiness

**NOT_READY_FOR_PHASE_1_5**.

Next validation action: rerun BTC/ETH Range audit under Phase 1.4.16 and confirm that no inverted directional boundary geometry remains before expanding Range Detection validation to the full required asset basket.
