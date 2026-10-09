# Strategy Engine — remaining source-alignment gaps

Date: 2026-10-09
Status: current source-gate policy is intentionally fail-closed. These are fidelity gaps, not permission to loosen entry safety.

## Closed in current source-gate policy

- Automatic gap/POI research proxy can no longer produce canonical `READY_FOR_VIRTUAL_ENTRY`.
- Canonical READY requires explicit source-qualified levels and auditable `SourceQualification`.
- Required source context currently includes structure path, Order Flow alignment, opposing-liquidity clearance, Premium/Discount attestation, zone freshness semantics, source POI kind, source entry path and evidence.
- Conservative HTF→LTF path enforces LTF 1–15m and HTF 15m–1D.
- Demand/Supply direction is enforced.
- Frozen research artifacts remain readable but cannot become canonical source trades by omission.
- Runtime remains BACKTEST/SHADOW only and `trade_entry_allowed=false`.
- Repeated `ORDER_BLOCK` tests no longer use `fresh_untested` as an unconditional universal veto: a second test is admitted only with a separate causal LTF-reaction proof that is known before source qualification/entry availability. Demand/Supply remain fresh-only.

## Gap A — repeated Order Block tests — CLOSED IN `0.4.22-source-gate.3`

Source support:

- The Advanced trading-tools material says the first OB test is the normal case (about 90%).
- A repeated OB entry can still be considered after a separately confirmed lower-timeframe reaction.

Implemented contract:

1. `SourceQualification` carries explicit repeat-test fields:
   - `repeat_test_ltf_reaction_confirmed`;
   - `repeat_test_ltf_reaction_known_at`;
   - `repeat_test_ltf_reaction_evidence`.
2. `ORDER_BLOCK` with `fresh_untested=false` remains blocked unless all repeat-reaction proof is explicitly present.
3. The reaction timestamp must be timezone-aware and no later than the enclosing source qualification; `QualifiedLevels` already requires source qualification to be known no later than level availability. This keeps the proof causal before a snapshot can use it.
4. Repeat-test proof is rejected for non-`ORDER_BLOCK` POI kinds. Demand/Supply therefore keep their dedicated strict fresh/untested rule.
5. Repeat reaction evidence is carried into canonical signal audit evidence and the reason is labelled `SOURCE_OB_REPEAT_TEST_LTF_REACTION_CONFIRMED`, not `SOURCE_POI_FRESH`.
6. Research auto-level proxies remain non-canonical and have no path to self-certify this caller/source proof.
7. Regression coverage includes first test, unproved second test, proved second test, LONG/SHORT symmetry, future/non-causal timestamp rejection, missing evidence and Demand/Supply exclusion.

Safety boundary is unchanged: this only affects offline canonical virtual qualification; `trade_entry_allowed=false`, LIVE/private execution remain absent.

## Gap B — Premium/Discount scope

Source support:

- Demand/Supply material explicitly requires Supply for sells in Premium and Demand for buys in Discount.
- OTE/Premium/Discount is important context in the supplied methodology.
- The source set does not justify turning one universal `premium_discount_valid=true` flag into an identical hard rule for every possible POI kind/path without path-specific semantics.

Current runtime state:

- Canonical source qualification currently requires `premium_discount_valid=true` for every POI kind.
- This is safe but may create false negatives for some source paths.

Required implementation before loosening:

1. Make Premium/Discount requirements path/POI-specific rather than silently universal.
2. Demand/Supply must retain the strict directional Premium/Discount gate.
3. For OB/Breaker/STB-BTS/Range, encode only what the corresponding supplied source actually requires.
4. Add tests proving no path is relaxed merely because the universal flag was removed.

## Gap C — caller assertion vs automated source proof

`SourceQualification` is an auditable caller assertion, not yet a complete automatic detector for qualitative source concepts.

Still to automate causally:

- active Order Flow;
- meaningful opposing liquidity against setup;
- source-complete POI taxonomy beyond gap/FVG research proxy;
- path-specific freshness semantics beyond the now explicit repeated-OB exception;
- path-specific Premium/Discount semantics;
- first opposing source-valid FTA rather than requiring a software-shaped three-target pattern;
- range-specific 80/20 exit model as a source path, separated from project 40/30/30 overlay.

Until these detectors exist and pass regression/backtest evidence, automatic research output must remain non-canonical.

## Historical seven-trade audit status

The prior seven virtual trades are historical research evidence only. Their execution causality/accounting had been validated, but full source compliance was not.

Current classification rule:

- `SOURCE_VALID_LOSS`: only after all methodology gates can be proven from retained pre-entry evidence.
- `FALSE_POSITIVE_IMPLEMENTATION`: when retained evidence proves the software admitted a trade that the source would have rejected/postponed.
- `UNCERTAIN_SOURCE`: when retained artifacts are insufficient to prove all source gates.

Known facts from the prior run:

- seven closed research trades;
- five stopped;
- two reached TP1 and then stopped;
- no TP2/TP3 completions;
- two mappings used `240/60`, which is outside the supplied conservative HTF→LTF execution guidance of 1–15m LTF and therefore cannot be labelled source-conservative;
- the previous auto-level route was a gap/POI research proxy and lacked the now-required source qualification for Order Flow, opposing liquidity, POI taxonomy and other context gates.

Therefore none of the seven may be promoted to `SOURCE_VALID_LOSS` merely from the old execution report. They remain research evidence pending per-trade pre-entry source reconstruction; `240/60` entries are specifically non-conservative under the supplied conservative mapping.

## Non-source overlays that remain explicit

- global TP1/TP2/TP3 40/30/30;
- TP1 → cost-adjusted breakeven;
- score threshold/re-entry score;
- software numeric OB aggression thresholds;
- gap-only POI/target proxies used in research;
- risk above the primary SW.BAND 0.25–2% range;
- any exact TF mapping not directly stated by the source.

These may be researched as product policies, but must not be relabelled as source rules.
