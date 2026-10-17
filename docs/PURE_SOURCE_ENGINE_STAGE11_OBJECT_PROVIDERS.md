# PURE SOURCE Stage 11 — causal object providers

Scope: Stage-2 structure/liquidity + Stage-3 structural-liquidity SFP + Stage-5 IMB/FVG, connected to the Stage-10 closed-prefix transport. This is object evidence, not a completed trade strategy or profitability run. `trade_entry_allowed=false`.

Base: Stage-10 merge `016f2a38e35ea95ae50d69a86cb3caab45f715d5`, PR #13, Actions run [39018992398](https://github.com/mdiminchuk208-arch/-/actions/runs/39018992398). All compile/unit/safety steps passed for head `0db00ce529646d1199c8ffd71c6a0626f26c953b` before merge. Stage1–10 code and source registries remain unchanged by Stage11.

## Canonical interfaces

- `SourceObjectReplayProvider.produce(ReplayFrame)` is stateless and consumes closed prefixes only.
- `ObjectReplayEvidenceBatch` extends the existing dataclass batch with typed object assessments. Stage10 fingerprints these fields along with the actual objects. No UNKNOWN object status is misrepresented as a Stage-7 setup assessment.
- `run_source_object_replay(...)` retains complete emitted batches including typed SFP/FVG geometry and lifecycle references and Stage10 reproducibility receipts. Its recording history is output-only and is never an input to detection.
- `assessment_counts()` counts per-close observations, including rejected candidate windows and missing-input observations. These counts are not unique objects, READY, FILLED or CLOSED trades.

All historical SFP/FVG formations remain in each later batch, including invalidated SFPs. Stage2 still emits its latest structure snapshot; Stage9 retains every earlier registered structure in its append-only registry. Missing later trade conditions never delete an earlier market object.

## SOURCE rules reused without reinterpretation

| Existing rule | Classification | Primary/source reference |
|---|---|---|
| SFP external structural liquidity, body reclaim, immediate next open | SOURCE_RULE | SW8 p5; raw `16.clean.txt` P0068–P0087 |
| SFP body-close invalidation beyond pattern extreme | SOURCE_RULE | SW12 p13; Stage3 contract |
| SFP any TF; H1+ preferred, not mandatory | SOURCE_RULE | SW8 raw P0102–P0104; Stage3 contract |
| IMB three-candle wick-gap geometry | SOURCE_RULE | Методичка p11; SW8 p1–3 |
| Structural swings/liquidity | SOURCE_RULE | Existing Stage2 SW5/SW6 citations |

Existing Stage3 normalization maps the pattern extreme to the sweep-candle extreme (`TN_SFP_PATTERN_EXTREME_SWEEP_CANDLE`). Existing strict penetration and positive-gap normalizations remain explicitly technical. New transport normalizations are registered in `config/pure_source_object_provider_v2.json`; none is an admission rule.

## Two clocks for SFP

SOURCE formation/known_at is the immediate next candle OPEN. The Stage10 transport exposes closed candles only. It therefore observes that opening fact at the next candle CLOSE, retaining both intrinsic object timestamps and the later assessment observed_at. The provider never synthesizes an unavailable opening event or inserts a historical receipt/READY. A pattern may already be invalidated when first observed by this closed-only transport; its formation remains valid and historical state remains reconstructible.

## Explicit coverage gaps

| Family | Missing input; no automatic replacement |
|---|---|
| EQH/EQL | Source-qualified substructure pairing and reasonable-tilt provenance |
| OB | Aggressive impulse/large-body-small-wicks provenance, contextual parents and BOS |
| Breaker | Source-valid OB and reversal/confirmation evidence |
| Range | Source-qualified endpoints, strength, midpoint reaction, internal-structure evidence |
| STB/BTS | Manipulation segmentation and full-engulf provenance |
| Demand/Supply | Source-qualified last-movement segmentation |
| OTE/PD | Source-qualified impulse/dealing-range anchors; existing Stage5 geometry remains available for typed inputs |
| Meaningful/adverse liquidity | Contextual SOURCE meaning, not a fitted distance/significance threshold |

These observations remain UNKNOWN. They are not FAIL formation verdicts and do not erase other objects. No arbitrary OHLC/ATR/tick threshold supplies qualitative provenance.

The inherited SFP detector evaluates each known external structural reference using its SOURCE pattern conditions. Stage11 does not invent a first-take, freshness, repeated-test or trade re-entry rule. Repeated patterns and opposite alternatives remain evidence. PASS here means that the existing pattern contract passed, conditional on its structural reference; meaningful liquidity, context selection, re-entry and trade eligibility are not thereby resolved. Range-boundary SFP requires a real source-qualified Range and is not fabricated from arbitrary extrema.

## QA and continuation

Eleven dedicated tests cover independent truncation at every fixture prefix, future suffix/OHLC mutation, next-open observation delay, causal parents, append-only invalidation, retained formation validity, deterministic MTF ordering, no repeated higher-TF observations, diagnostics hashing, malformed/future prefix rejection and no legacy/exchange dependency.

The immutable synthetic trace and QA receipts are under `docs/pure_source_stage11_qa_v1/`. They are marked SYNTHETIC_QA, never historical strategy results. Main baseline verdict remains NOT_IDENTIFIABLE. Stage11 does not choose entry/SL/exit variants, generate SOURCE-ready trades, run P&L, or enable live/private execution.

Next implementation scope is explicit multi-timeframe evidence composition using source-valid parents, without a universal TF ladder or branch ranking. Later setup/execution providers must retain multiple permitted variants and SOURCE UNKNOWNs. No financial simulator can silently fill the outstanding stop, exit/remainder, branch/context, meaningful-liquidity, qualitative-geometry or re-entry gaps.

Local full QA:737unit tests PASS,11dedicatedprovider tests PASS, compile/safety/lint PASS. Actual read-only reviewer /root/pure_source_stage10_review independently accepted the final typed evidence/lifecycle output after11targetedtests. GitHub Actions must pass on the exact published head before merge.
