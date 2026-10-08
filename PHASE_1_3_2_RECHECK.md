# Phase 1.3.2 — final QA

## What was rechecked

- Uploaded Market Structure Advanced source.
- Uploaded Liquidity source.
- Uploaded Trading Tools Base SFP source.
- Existing Phase 1.3.1 BOS/CONF logic and no-lookahead regression.
- Liquidity lifecycle and duplicate-SFP behavior.
- Reporting and Source Rule Registry.

## Important correction to the previous interpretation

The source does not justify discarding ordinary confirmed three-candle swings via an invented "significance" threshold. A Swing is defined as a structural point. SFP may form on structural highs/lows on any timeframe; H1+ is only stated as preferred for searching.

Therefore this build solves the duplicate problem without an arbitrary significance filter:

1. every confirmed swing remains auditable structural liquidity on its timeframe;
2. each level can be first-swept only once;
3. same candle + same side sweeps are grouped into one episode;
4. one episode can emit at most one SFP formation;
5. raw individual liquidity takes remain in the event log;
6. M1 formations are labelled below the source-preferred H1+ search timeframe;
7. SFP formation is not treated as a trade signal: LTF BOS remains required.

## Automated QA

- 69/69 tests pass.
- `python -m compileall` passes.
- Rule Registry JSON parses and all rule IDs are unique.
- Existing causal-prefix/no-lookahead test still passes.
- New tests cover multi-level one-candle sweep deduplication, lifecycle resolution, unresolved last-candle sweeps, and H1 timeframe preference.

## Still intentionally blocked

- SFP -> LTF BOS entry pipeline.
- HTF/LTF multi-timeframe orchestration.
- Real-market automatic OB validation.
- Profit backtest / P&L claims.
