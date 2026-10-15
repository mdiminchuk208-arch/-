# Source Strategy Rebuild v1 — import of the frozen original executable profile

This rebuild does not discard the earlier source-fidelity work. It imports provenance-safe parts of `docs/original_strategy_spec_v1_1/` and rejects the later v4/v4.1 strategy drift.

## Source corpus

Authoritative SOURCE rules are those in:
- `original_strategy_rule_registry_v1_1.json` with immutable citations/hashes;
- `branch_contracts.json` and branch source support;
- underlying user-supplied Methodichka / SW / Smart Money source files.

The original registry contains source-backed branches beyond the single Methodichka summary, including SFP, OB, Breaker, STB/BTS, Range, FVG/POI, Supply/Demand/POI, OTE and AMD/context rules. These branches remain part of the rebuild.

## Imported user resolutions U1–U6

All are `USER_RESOLUTION_PRE_BACKTEST`, not SOURCE_RULE.

### U1 EXIT
`FULL_CONTEXTUAL_FTA_EXIT`:
- non-Range: 100% at nearest known opposing contextual POI across eligible TFs;
- Range: frozen 80/20 source-permitted same-zone variant;
- optional breakout remainder disabled.

### U2 STOP
`FIXED_INITIAL_PROTECTIVE_STOP`:
- OB: source extreme;
- Breaker: raid/impulse extreme;
- SFP: ATR14 from pattern extreme;
- STB: manipulation/raid extreme;
- Range: deviation/invalidation extreme;
- nonunique anchor => unresolved stop geometry;
- no TP1→BE in Original profile.

### U3 ENTRY BRANCH
- OB: reaction → M15 BOS → new source-valid POI;
- SFP: completed pattern → M15 BOS → source entry search;
- Range: reclaim/return/retest;
- STB/BTS: 0.5 midpoint;
- Breaker: confirmed Breaker, conservative stop;
- first complete physical idea owns plan; equivalent branches become confluence;
- material branch conflict waits; no fitted financial priority.

### U4 TIMEFRAMES
- M15/H1/H4/D1 source scan;
- D1 global context;
- H4 higher/local context;
- H1 primary medium-term analysis;
- M15 refinement/confirmation and source-valid M15 setups;
- no mandatory universal ladder/all-TF alignment;
- M15 branch requiring strictly-lower refinement records coverage WAIT, not source rejection.

### U5 LIQUIDITY
- ADVERSE → WAIT_SWEEP;
- TARGET_OR_FUEL / NEUTRAL do not block;
- UNKNOWN → unresolved liquidity context;
- after a sweep, fully revalidate; no automatic entry;
- no old fitted/blanket adverse-liquidity labels.

### U6 REENTRY
`FIRST_TEST_ONLY`:
- consumed OB/POI cannot be reused;
- a new trade requires new formation + confirmation + POI identity and full validation;
- no arbitrary cooldown, random retry probability or retry count.

## Imported N11 technical conventions

Preserve their original classification as `TECHNICAL_NORMALIZATION_PRE_BACKTEST`:
- N11_ENTRY
- N11_TARGET
- N11_STOP_TICK
- N11_ATR_SMA14
- N11_BODY_TF
- N11_IDENTITY
- N11_BATCH
- N11_EVIDENCE
- N11_EVENTS
- N11_SOURCE_SCOPE

The rebuild may replace the **mechanism** used by N11_EVIDENCE to obtain objective evidence: source facts that are deterministically derivable from completed OHLC/causal objects must be calculated by code rather than unnecessarily requiring manual annotation. This does not change the source rule or U1–U6 decision.

## Existing evidence adapter baseline

`SOURCE_FAITHFUL_HISTORICAL_EVIDENCE_ADAPTER_v2` is a valid pre-financial baseline and already produced:
- RAW proposals: 176365;
- objective geometry pass: 176365;
- objective source fail: 0;
- objective objects including swings/liquidity pools/FVG/SFP/STB/OB/POI/range;
- no P&L.

Its critical limitation was `EVIDENCE_COMPLETE=0`, caused by unresolved metadata/qualitative/context/entry/inventory evidence. The rebuild goal is to close source-resolvable gaps deterministically before considering any financial run.

## Venue separation

The old adapter's historical Bybit metadata blocker is not allowed to suppress SOURCE formation/coverage in the current rebuild. Venue-specific tick/quantity metadata belongs to executable quote sizing/rounding later. Current project venue is OKX, but source detection must remain venue-agnostic.
