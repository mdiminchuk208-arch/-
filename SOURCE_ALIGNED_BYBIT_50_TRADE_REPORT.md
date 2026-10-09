# Source-aligned Bybit validation: blocked before backtest

Date: 2026-10-09 (Asia/Yekaterinburg). Market timestamps remain UTC.
Starting main: `afad46723f7bb87c5dfae0c24b80c6bec81de902`.
User checkpoint `b86fd7de0bccaae1e48fdc5ff74c6b9ceb59b074` is its ancestor.

## What has actually been established

The original `Криптология.zip` and its PDF/DOCX materials are absent from this
checkout and the files attached to this task. The six retained code archives
contain no PDF/DOCX documents. Earlier source summaries claim a prior review;
this task has not independently reread or verified those originals. Their
interpretations cannot substitute for the requested primary-source audit.

The current strategy marker is `0.4.22-source-gate.2`. It rejects automatic
research POI proxies as canonical READY. Explicit source qualification is still
a caller assertion, not complete causal automation of the methodology. Active
Order Flow, meaningful opposing liquidity, source-complete POI/FTA, repeated OB
semantics and setup-specific exits remain incomplete as documented in
`SOURCE_ALIGNMENT_GAPS_2026-10-09.md`.

No strategy behavior has been changed in this continuation. In particular,
canonical TP 40/30/30, existing SL and cost-adjusted BE after TP1 are preserved.
The attached request also discusses Range 80/20 and source-specific exits;
these cannot replace the explicitly frozen canonical exit model here. No
experimental policy is selected from performance. LIVE/private API are unused;
`trade_entry_allowed=false` remains invariant.

## Dataset verification

`data/reports/source_validation_qa_2026_10_09/dataset_integrity.json` records:

- All 34 public research series match their registered stored SHA256 and
  decompressed CSV SHA256. Binance remains a separate retrospective cohort.
- All 40 native Bybit series pass exchange/symbol/interval identity, closed-bar,
  positive OHLC envelope, increasing timestamp and timeframe-alignment checks.
  They contain 993,575 candles across multiple TFs, with zero detected gaps.
  Counts across TFs are not independent market observations.
- The Bybit mirror's recorded 202 native-HTF discrepancies remain in the earlier
  independent-check report. They are not hidden by the stored-SHA check.
- No gaps were filled, candles invented or datasets overwritten.

The public read-only Bybit time endpoint and public archive index both failed
with proxy tunnel HTTP 403 in this instance. Details are in
`public_bybit_connectivity.json`. No private endpoints, tokens or orders were
used. API/archive access would require environment network access to
`api.bybit.com` / `public.bybit.com`, followed by actual source/instrument/coverage
verification; this failed request does not establish which new period is available.

## Historical trade audit

`data/reports/source_trade_recheck_2026_10_09/closed_trade_source_audit.jsonl`
enumerates all 714 real-history CLOSED **artifact instances** found in 409 files.
Eight constructed-test instances are excluded. Repeated checks, overlapping
windows, cost/risk variants and exit counterfactuals remain separate and are not
pooled into a purported 714-trade account. Each row retains the full trade,
artifact SHA, causal pre-entry signal evidence where available, fees, exits,
classification and unknown source-context fields.

Across artifact instances, 671 are `UNCERTAIN_SOURCE`. The other 43 have a
`FALSE_POSITIVE_IMPLEMENTATION` classification strictly scoped to a
**source-conservative entry claim**: their LTF is outside the retained 1–15m
description. This does not mean a correctly labelled research mapping is
forbidden by every possible source path. No instance is certified as an
original-material `SOURCE_VALID_WIN` or `SOURCE_VALID_LOSS`.

The seven original stage3 development trades are:

| HTF/LTF | Symbol | Direction | Net PnL | Classification scope |
| --- | --- | --- | ---: | --- |
| 15/5 | XRPUSDT | SHORT | +9.8622 | UNCERTAIN_SOURCE |
| 60/5 | XRPUSDT | SHORT | -23.4000 | UNCERTAIN_SOURCE |
| 60/15 | AVAXUSDT | LONG | -23.4000 | UNCERTAIN_SOURCE |
| 240/5 | BNBUSDT | LONG | -23.4000 | UNCERTAIN_SOURCE |
| 240/15 | BNBUSDT | LONG | -23.4000 | UNCERTAIN_SOURCE |
| 240/60 | BTCUSDT | SHORT | +11.1659 | Not a source-conservative LTF example |
| 240/60 | AVAXUSDT | SHORT | -23.6233 | Not a source-conservative LTF example |

Of the five losses, four remain uncertain-source and one has the conditional
240/60 incompatibility above. **Zero losses are proven source-valid.** This is
an evidence count, not a claim that the methodology would never lose.

The mechanical cause of recorded losses is measurable: the saved adverse-price
stop executions plus allocated fees reconcile their net PnL. Two of seven
trades took TP1 and later stopped the remainder near cost-adjusted BE; five
stopped without completing TP2/TP3. A recorded stop does not explain why a
source-valid setup lost, because source validity itself is not proven. Missing
Order Flow or liquidity evidence establishes missing proof; it does not prove
those market conditions were objectively adverse.

False negatives remain `UNDETERMINED`. Gap-only POI, three-gap targets and
universal freshness can miss valid methodology paths, but no count of missed
source-valid opportunities or missed winners is inferred without primary
materials and complete causal detectors.

## OLD versus current engine; requested first 50 CLOSED trades

The old development funnel is retained: 27,974 setups → 40 research READY →
7 entries → 7 CLOSED across independent mappings. These are not a validated
source-methodology sample.

The current engine's fail-closed source gate is covered by the full regression
suite. It cannot silently promote those old automatic research signals to
canonical trades. This prevents an unsupported methodology claim, but does not
establish that every old opportunity was invalid or that all true source
opportunities are now detected.

A **new complete source-aligned Bybit backtest has not been run**. Its required
source audit and detectors are unfinished. No funnel, win rate, PF, expectancy,
R, PnL or DD from such a run is fabricated. The first 50 source-valid CLOSED
trades are therefore **not obtained / not measured**; this is a source-evidence
blocker, not proof that the available history contains zero opportunities.

Next required input is the original `Криптология.zip` (and the actual Fibonacci
module if available, rather than its shortcut). Recheck all primary materials,
resolve source-specific policy requirements while preserving the frozen project
baseline, then implement and test causal source detectors before the Bybit
validation and old/new performance comparison.

## Reusable research continuation

The separate frozen research is already complete. See
`data/reports/continuation_recheck_2026_10_09_final/resume_validation.json`
and its log. The helper reconstructs all 57 protected source/config files from
the registered Git commit, verifies the original hashes and runs continuation
in an ignored temporary runtime. Main is never reset. Saved reports are copied;
existing history and evidence are preserved.

```bash
/workspace/crypto-bot-venv/bin/python scripts/verify_frozen_research_resume.py \
  --workers 4 --output data/reports/my_fresh_resume_validation
/workspace/crypto-bot-venv/bin/python scripts/audit_saved_source_trades.py \
  --output data/reports/my_fresh_trade_source_audit
```

Use fresh output directories to preserve earlier receipts. The ordinary research
runner's hash guard correctly rejects current main because two protected files
evolved after the historical freeze. Do not update expected hashes or restore
old source over current main to bypass that guard.

## Final validation of this continuation

- Full suite: **448 PASS**; compileall, Ruff E9/F and mypy pass.
- 1,161 artifact manifests covering 8,147 file references verify. Legacy cases
  without individual manifests additionally match their saved Git objects:
  14,332 historical Git blobs checked. All 1,452 execution scenario source
  hashes and window/input contexts match their saved canonical cases.
- The continuation pipeline completes all 45 registered studies; all 21
  checkpoint fingerprints match and saved exit cases reuse verified artifacts.
- Current main rejects all seven old unqualified automatic READY signals.
  This is a gate check, not a new market backtest or proof of missed/winning
  opportunities. Evidence is in `main_safety_and_old_signal_gate.json`.
- All 57 source/config files match the starting main commit. The historical
  57-file frozen runtime also passes its separate original hash guard. No
  existing source/data/research artifacts were changed by the validation.

QA logs and receipts are in `data/reports/source_validation_qa_2026_10_09/`.
The only existing test-file edit removes an unused import that prevented Ruff
from passing; all test cases are retained. New regression tests cover evidence
cutoffs, exclusion of constructed data and refusal to accept corrupted frozen
source/recorded artifacts.
