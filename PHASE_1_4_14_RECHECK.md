# Phase 1.4.14 v0.4.14 — Recheck

## Scope

This recheck validates the new cross-asset robustness infrastructure only. It does not claim that the ten-symbol real-data gate has already been completed.

## Automated QA

- Full unittest suite: **198/198 PASS**.
- `python -B -m compileall -q src scripts tests`: PASS.
- `scripts/analyze_cross_asset_robustness.py --help`: PASS.
- Source Rule Registry: `phase1.4.14-0.4.14`.
- Registry: **82 rules / 82 unique IDs**:
  - 25 `SOURCE_RULE`;
  - 50 `TECHNICAL_NORMALIZATION`;
  - 7 `BACKTEST_PARAMETER`.
- Existing source rules retain provenance.

## Smoke run

A real-data infrastructure smoke run was completed using the packaged BTCUSDT and ETHUSDT Bybit histories over a common short evaluation slice:

- evaluation: 30 days;
- suffix: 20 days;
- stabilization: 7 days;
- analysis warm-up: 20 days;
- production mode: `SOURCE_CONSERVATIVE`.

Results:

- BTCUSDT: all per-symbol invariants PASS;
- ETHUSDT: all per-symbol invariants PASS;
- production recovery ancestry: none;
- MTF runtime: PASS for 60->5 and 240->15;
- `trade_entry_allowed`: false for every generated MTF candidate/opportunity;
- overall cross-asset gate: **OPEN**, as expected, because SOL/XRP/BNB/DOGE/ADA/LINK/AVAX/LTC real-data inputs are not packaged.

The smoke output is retained under:

`data/reports/phase1_4_14/smoke_btc_eth_30d/`

## Important interpretation

The short BTC/ETH smoke verifies the runner, not broad market representativeness. It is not used to close `CROSS_ASSET_ROBUSTNESS_NOT_VALIDATED`.

The final gate requires the complete default ten-symbol basket on real data. No synthetic aliasing, cloned BTC/ETH data or event-count threshold is accepted as a substitute.

## Source / normalization boundary

No new SOURCE_RULE was added. The two Phase 1.4.14 registry entries are `TECHNICAL_NORMALIZATION` entries that document:

1. the project QA basket;
2. the invariant-only cross-asset gate policy.

No profitability, winrate, BOS-count, SFP-count or `BROKEN`-duration threshold was invented.

## Gate status

| Gate | Status | Reason |
|---|---|---|
| Recovery ablation | CLOSED | Frozen in Phase 1.4.13. |
| Global clustering | CLOSED | Production exact-time clustering frozen in Phase 1.4.13. |
| Cross-asset robustness | OPEN | Harness is complete, but 8/10 required real-data symbol histories are not packaged. |
| Range detection normalization | OPEN | Cross-asset harness deliberately does not pretend to validate qualitative Range machine assumptions. |
| Range boundary clarity | OPEN | No source-defined numeric clarity threshold. |
| Range exit/re-entry lifecycle | OPEN | Source does not fully formalize permanent retirement/redraw/renewal. |
| Entry Zone / SL / TP / RR | OPEN | Entry Engine not implemented. |

## Safety boundary

`trade_entry_allowed=false` remains mandatory. Phase 1.4.14 adds no private exchange credentials, order placement, paper execution or live execution.

## Readiness

**NOT_READY_FOR_PHASE_1_5**.

Next required evidence: fetch the remaining eight symbols on 5m/15m/60m/240m and run the full 240-day cross-asset audit. Only after that evidence exists may the cross-asset blocker be considered for closure.
