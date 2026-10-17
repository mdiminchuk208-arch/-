# PURE SOURCE Stage 12 — causal MTF evidence composition

Base: Stage11 merge `a3a2faab1dedbf674af0ae3b4e6acd2fb09fda1a`, PR #14. Actions [39019791554](https://github.com/mdiminchuk208-arch/-/actions/runs/39019791554) completed compile,737unit tests and safety successfully for exact head `45c80ec39d59f99226ec776dd06665e83916bd0f` before merge.

Stage12 adds a separate provider. Stage1–11 files and SOURCE semantics are unchanged. `trade_entry_allowed=false`; no orders/private API, financial run, portfolio, fee admission, ranking or project HTF rule.

## Composition contract

`MtfSourceReplayProvider` consumes validated Stage10 ReplayFrame prefixes and returns `MtfReplayEvidenceBatch`, retaining all Stage11 typed geometry, objects and assessments. New dataclass fields are included in the unchanged Stage10 evidence-batch fingerprint. A fresh output-only recorder preserves full batches per run.

- A timeframe view describes its latest visible close and current batch object IDs. It is not a selected context, an assertion of active structure, or a replacement for Stage9's full append-only registry.
- An unavailable higher-TF prefix has no objects or refinement relation.
- All strict-lower duration pairs are retained once both prefixes are visible. They are candidates only: no H1/H4 ladder, preferred entry TF, direction override, branch admission or priority is chosen.
- Existing Stage7 `LowerTimeframePair` validates the duration relation. SOURCE branch checks remain in Stage7; for example, the source-explicit conservative OB M1–M15 scope is not generalized to every setup.
- Duplicate duration aliases are rejected instead of becoming two physical contexts. Original timeframe labels and stable object IDs remain unchanged.

## Market-data audit, separate from SOURCE eligibility

For each declared lower/higher pair, compare exact OHLC when fixed intervals tile and the complete lower prefix covering a higher candle is observable. A discrepancy fails the data replay closed, at the decision where the contradictory higher candle first becomes visible. No price tolerance is fitted.

Incomplete visible coverage or nonintegral grids produce UNKNOWN, not a false PASS. Nonintegral grids do not remove a strictly lower candidate relationship. PASS means complete visible **OHLC** tiles agree; it does not certify volume reconstruction, exchange session rules, missing history, source context or execution validity. Timestamps/duration/future/continuity checks remain the Stage10 data boundary; direct composition additionally rejects future prefixes and declared duration mismatches.

## Classification

All new logic is TECHNICAL_NORMALIZATION/infrastructure: causal prefix views, exhaustive unselected duration relations, physical-duration alias uniqueness, and fixed-grid OHLC consistency. No new trading SOURCE_RULE or PROJECT_POLICY is introduced. Existing source permissions and unresolved context/TF choices remain explicit.

## QA

Ten tests cover all available lower-TF alternatives; same-close ordering; future HTF exclusion; each O/H/L/C mismatch; partial/nonintegral coverage; alias duplication; independent MTF truncations; future OHLC suffix mutation; input-order determinism; causal object views; diagnostic fingerprints; malformed duration/future prefix rejection. Independent read-only reviewer `/root/pure_source_stage10_review` additionally checked mixed complete/incomplete tiles and causal mismatch timing; no material findings.

Synthetic traces and a freeze manifest are stored under `docs/pure_source_stage12_qa_v1/`. They are synthetic data-quality evidence, not historical trade counts. A green full GitHub Actions gate on the exact PR head is required before merge.

Next: source setup orchestration over causal parents. Qualitative object provenance, context/branch alternatives, entry/stop/exit/remainder and re-entry gaps must stay UNKNOWN/UNRESOLVED. A duration relation or successful OHLC audit cannot resolve any of them. Baseline remains NOT_IDENTIFIABLE.

Local QA:747full-suite tests PASS,10dedicated MTF tests PASS, compile/safety/lint PASS. No SOURCE-rule or Stage1–11 file changed.
