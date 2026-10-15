# Source Strategy Rebuild v1 — authority

State: `SOURCE_STRATEGY_REBUILD_STAGE_1_SOURCE_FREEZE`.

## Purpose

Rebuild the trading strategy from the user-provided source material before any profitability work. Previous machine versions v2/v2.1/v2.2/v3/v4/v4.1 remain frozen historical implementations and are **not** authoritative interpretations of the strategy.

## Primary source

`Методичка.docx`, 22 pages, supplied by the user.

The source is treated literally. General trading knowledge, previous machine heuristics, old outcome labels, previous profitable/losing slices and post-result observations may not silently modify a source rule.

## Separation of concerns

### SOURCE
Only rules supported by the supplied strategy material:
- market structure;
- BOS / CHOCH relationships;
- Order Block;
- Imbalance;
- Breaker;
- liquidity concepts;
- Range / Deviation;
- OTE / Fibonacci levels;
- SFP;
- AMD context where the source supports it.

### TECHNICAL_NORMALIZATION
Machine definitions required only because human language is not numerically complete. Every normalization must be explicit, versioned, source-linked and distinguishable from SOURCE. A normalization may not be presented as if the source itself specified the threshold.

### PROJECT_OVERLAY
Rules belonging to the bot/platform rather than the strategy source, including:
- venue/exchange assumptions;
- fees/slippage/funding models;
- account/risk controls;
- compatibility grids;
- target qualification metrics;
- the user's frequency sanity requirement;
- PAPER/LIVE safety gates.

PROJECT_OVERLAY must never decide whether a historical chart formation exists as a SOURCE setup.

## Forbidden carry-over

Do not import as strategy truth:
- v2/v3/v4/v4.1 admission filters merely because they existed;
- v4.1 H1/H4-only opportunity restriction;
- old outcome-derived family/direction preferences;
- old `WAIT/REJECT` states that were not directly source-supported;
- old profitability labels, WIN/LOSS, MFE/MAE or P&L;
- old arbitrary lifetime/cooldown rules;
- any hidden numerical threshold for qualitative source words.

## Safety

This rebuild is pre-financial. `trade_entry_allowed=false`. No PAPER/LIVE/private exchange API/orders/platform reconnection is authorized by this stage.
