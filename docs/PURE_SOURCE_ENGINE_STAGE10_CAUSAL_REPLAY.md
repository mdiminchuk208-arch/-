# PURE SOURCE Engine — Stage 10: Causal Replay Adapter + QA

Status: IMPLEMENTED FOR REVIEW

## Goal
Stage 10 creates the deterministic transport between reproducible historical market data and the clean Stage-9 PURE_SOURCE runtime. It is not a new strategy engine and does not reintroduce the historical `source_engine.py` / legacy signal stack.

The canonical flow is:

`healthy MarketCandle series`
→ `closed multi-timeframe prefixes`
→ `ReplayFrame`
→ `causal Stage-2..8 evidence provider`
→ `ReplayEvidenceBatch`
→ `Stage-9 PureSourceRuntime`
→ `per-prefix reproducibility receipts`

`trade_entry_allowed=false` remains invariant.

## Data gate
Each timeframe is audited independently before replay starts:
- chronological order;
- no duplicate opens;
- no gaps / abnormal spacing;
- only closed candles;
- valid OHLC bounds;
- UTC-epoch alignment to the supplied fixed interval;
- consistent exchange/symbol/interval metadata.

All replay series must share one exchange and one symbol. Stage 10 does not download data and does not use private exchange APIs.

## Decision clock
The replay clock is the sorted union of all closed-candle close timestamps across supplied timeframes.

At each decision timestamp:
1. every timeframe advances to the candles that are now closed;
2. same-close candles from different timeframes are all visible before evidence production;
3. the evidence provider receives only prefixes whose closes are `<= decision_at`;
4. no full-dataset hash, future row count or future candle is exposed through `ReplayFrame`.

There is no universal HTF/LTF ladder. Timeframes are data/evidence identities, not a hidden admission hierarchy.

## Evidence order
`ReplayEvidenceBatch` is applied in a fixed causal order:
1. Stage 2–6.5 market objects;
2. Stage-7 setup assessments;
3. Stage-8 execution assessments.

Market objects are topologically registered by `parent_object_ids`. Missing/cyclic parentage fails closed. `SETUP` and `PHYSICAL_IDEA` cannot be smuggled through the market-object batch; they must use Stage-7 wiring.

The Stage-9 runtime remains the authority for:
- future lifecycle rejection;
- PROJECT contamination rejection;
- setup parent/activity checks;
- unresolved blocker preservation;
- SOURCE-ready vs live-permission separation.

## Provider contract
A provider receives only a `ReplayFrame` and returns `ReplayEvidenceBatch`.

The provider does **not** receive the runtime, full dataset or future outcomes. This reduces opportunities for outcome-dependent selection and makes provider output hashable per prefix.

Stage 10 includes one concrete provider:

`StructureLiquidityReplayProvider`

It runs the clean Stage-2 `build_structure_liquidity_snapshot` over each visible timeframe prefix and emits only causal swings, structural liquidity and structure objects.

Stage 10 intentionally does **not** invent automatic evidence for qualitative SOURCE terms needed by later stages. Stage 3–8 evidence providers must use their own source-valid causal resolvers and may return UNKNOWN where SOURCE is not machine-identifiable.

## Reproducibility receipts
Stage 10 records:
- per-series rolling SHA-256;
- combined dataset SHA-256;
- per-decision prefix sizes;
- per-decision prefix SHA-256;
- evidence-batch SHA-256;
- Stage-9 runtime SHA-256;
- object/setup/execution/blocker counts.

The provider never sees the full dataset SHA, so a future-only data mutation cannot legitimately alter an earlier decision through the public replay contract.

## Future-mutation QA
`compare_replay_prefixes(left, right, through=...)` compares only causal receipts at or before the requested cutoff and intentionally ignores future manifest differences.

For an allowed future mutation after the cutoff, all of these must remain identical before the cutoff:
- decision timestamps;
- prefix sizes;
- prefix hashes;
- evidence-batch hashes;
- runtime hashes.

A mutation inside the compared prefix must be detected.

## Same-close multi-timeframe semantics
The underlying Stage-9 `observe_candles` validator expects strict chronology inside one sequence. Therefore Stage 10 validates newly closed candles per timeframe independently, then exposes all updated timeframe prefixes together to the provider at the shared timestamp. This prevents an arbitrary timeframe processing order from becoming trading semantics.

## What Stage 10 does not do
Stage 10 does not:
- use `historical_replay.py` as SOURCE truth;
- call legacy `source_engine.py`;
- select branches using score/PnL/MFE/MAE;
- add transaction-cost admission;
- add Anti-Scalp or project HTF filters;
- use project TP 40/30/30 or cost-adjusted breakeven;
- calculate shared portfolio PnL;
- place exchange orders.

## Test gates
The Stage-10 tests cover:
- prefix-only provider visibility;
- same-close MTF visibility;
- deterministic manifest/replay independent of input series order;
- unhealthy data rejection before provider execution;
- topological object registration;
- missing-parent fail-closed behavior;
- future-object rejection;
- synthetic Stage7 → Stage8 → Stage9 wiring with live permission still false;
- future-only market mutation preserving earlier Stage-2 receipts;
- past-prefix mutation detection;
- cutoff replay with no future receipts.

## Next stage after merge
After Stage 10 is green, the next work is **Stage 11: clean evidence orchestration coverage** — add/test source-causal providers/resolvers for the remaining Stage 3–8 modules and measure the honest funnel of PASS / UNKNOWN / FAIL without PnL optimization. Only after that should the Market Data + Backtest + QA branch calculate baseline performance metrics.
