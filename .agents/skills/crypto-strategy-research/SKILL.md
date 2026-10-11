---
name: crypto-strategy-research
description: Audit frozen Crypto Bot strategies, preserve causal evidence, and separate diagnosis from pre-outcome strategy design and validation.
---

# Crypto Strategy Research Skill

Use this skill for all Machine Strategy research in Crypto Bot.

## Core separation
Never collapse these phases:
1. retrospective diagnosis of a frozen version;
2. design of a new version;
3. pre-outcome freeze/preregistration;
4. financial backtest;
5. robustness;
6. independent OOS/forward validation;
7. paper qualification;
8. real-trading readiness.

A later phase may read earlier frozen results, but an earlier-phase artifact must never be rewritten after outcome is known.

## Failure audit protocol
For a failed frozen version:
- decompose gross edge, fees, slippage, and net edge;
- inspect LONG/SHORT, BTC/ETH, branch, TF, year/month, entry/exit reason, stop distance, target distance, hold time, and fill status;
- check implementation symmetry before concluding the market itself is asymmetric;
- inspect extreme R values and tiny risk denominators;
- distinguish signal-quality failure from position-construction failure and cost failure;
- report concentration and sample-size limitations.

Diagnostics may identify hypotheses, not production rules.

## New-version design protocol
A new rule is permitted only when:
- it has a causal market-structure, execution, or risk rationale;
- it is expressible using information available at decision time;
- its exact definition is frozen before viewing the new version result;
- it is not selected from a large threshold sweep over the same development history.

If a rule is inspired by a retrospective subgroup, explicitly mark that history as development data. The new rule requires new pre-outcome testing and independent validation before production claims.

## Validation hierarchy
Development backtest -> robustness -> untouched OOS/forward -> paper trading -> real readiness.

Do not count historical CLOSED trades as paper evidence.
Do not treat backtest profitability as guaranteed future profit.

## Required invariants
- completed candles only;
- causal known_at timestamps;
- no future features;
- deterministic replay;
- prefix/future-mutation tests where applicable;
- frozen dataset/config hashes;
- explicit cost and execution assumptions;
- no hidden funding or exchange metadata assumptions;
- `trade_entry_allowed=false` until explicit real activation.

## Quality decision
Prefer a strategy with modest but stable positive expectancy, PF above 1 after costs, reasonable drawdown, sufficient sample, and broad stability over a strategy with a spectacular in-sample metric concentrated in a tiny subgroup.

If no statistically credible edge is found, return STOP and the evidence. Never fabricate profitability.
