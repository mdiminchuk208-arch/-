# Source-fidelity finding — candidate starvation is partly a strategy-translation failure

Status: AUDIT EVIDENCE / REVIEW REQUIRED. This file does not authorize a financial replay or a new strategy version.

## Finding

The v4.1 candidate scarcity cannot be treated as evidence that the supplied trading method naturally produces only tens of opportunities per year. The user-supplied source material and earlier source-evidence plan describe a materially broader visual opportunity universe than the frozen v4.1 deterministic candidate stream.

Source evidence supplied in the Project:
- `Методичка.docx`, pp. 3 and 19: market structure and SFP are described as applicable across timeframes; SFP is a visual reversal pattern around swept swing/range liquidity and requires context.
- `Методичка.docx`, pp. 9-15: OB, Breaker, liquidity and Range are defined through chart geometry and examples; these are not described as once-per-month H1/H4 events.
- `Вставленный текст(20261011-090240).txt`: an earlier source-evidence plan recorded a raw geometric universe of 176,365 proposals and explicitly warned that qualitative concepts such as meaningful liquidity, smooth structural approach, whole impulse and range clarity must not be silently converted into arbitrary numeric thresholds. It prescribed blinded qualitative annotation after objective filtering instead.

Frozen v4.1 output:
- 54 candidates across BTC/ETH over the two-year development window.
- family mix STB 38 / RANGE 10 / SFP 5 / BREAKER 1 / OB 0.
- only 8 candidates ever filled across all nine modeled grids.

## Interpretation

The correct diagnosis is stronger than simple `sample scarcity`:

**v4/v4.1 over-constrained the source strategy during machine translation.** A chain of deterministic prerequisites, H1-only proposal timing, context admission, selected-POI eligibility/first-test rules, target viability, adverse-liquidity handling and pending retirement converted source concepts that were partly visual/contextual into hard WAIT/REJECT gates. The resulting engine is therefore not a faithful frequency representation of the supplied visual method.

This does not prove that every raw proposal is a valid trade and does not authorize forcing a trade count. It does prove that a candidate generator producing only 54 candidates in two years must fail a source-fidelity review before any future profitability conclusions are trusted as representative of the supplied strategy.

## Required correction before any v4.2 financial test

1. Build a **source-fidelity candidate layer** that scans continuously rather than only treating H1 proposal events as the opportunity clock.
2. Keep objective geometry deterministic where the source is exact: completed bars, swings, BOS/CHOCH facts, liquidity sweeps, FVG/IMB geometry, OTE levels, range boundaries/deviation, SFP body-reclaim facts, OB/breaker source relationships.
3. For source concepts that are visual/qualitative, do not invent numeric hard gates. Produce blinded chart packets containing only bars and objects known at decision time and classify them with the visual annotation protocol.
4. Generate and retain candidate chart windows for the relevant M15/H1/H4/D1 context, with the option for a lower trigger timeframe only if separately source-justified and preregistered.
5. Before P&L, report opportunity coverage by day/week/month, product, direction, family and timeframe, plus every rejection reason. A future engine that again collapses to tens of candidates per year must STOP for source-fidelity failure before financial testing.
6. Do not manufacture one trade per day merely to hit a count. The sanity target is that the engine must discover the recurring chart setups described by the source; trade frequency is an output of faithful detection, not a forced parameter.

## Consequence for current audit

Independent review of `MACHINE_STRATEGY_V4_1_FAILURE_AUDIT_V1` must now explicitly decide whether this source-fidelity mismatch is accepted as a primary causal finding. A future design gate, if authorized, must start from source-faithful visual/objective setup detection rather than from incremental tuning of the v4.1 admission thresholds.
