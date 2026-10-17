# PURE SOURCE Stage 19 — priority-1 rule ledger and conflict audit

Base: Stage18 merge `61d6693a993eb28b4d40b58baa4073566cae01b4`, PR21. Its exact head `e4ee7e39d0a04cceb056d08411d989f27b58952d` passed all CI steps in Actions39048274504; local799tests and14independent annotation-contract tests passed.

This stage documents SOURCE reconstruction; it does not change market-object/setup/execution behavior or treat prose as an executable trading filter. The source priority remains Methodichka > SW5 > SW9 > SW11 > SW12 > SW22 > verified originals > registry. Registry/code/historical results cannot override the original material.

## Evidence coverage and artifact map

`docs/pure_source_stage19_ledger_v1/` contains:

- METHODICHKA_RULE_LEDGER.json:47cited rule/concept records with exact source meaning, source role, semantic machine state, missing inputs and SOURCE-vs-TN lifecycle separation;
- METHODICHKA_RULE_TABLE.csv: requested rule/source/paragraph/meaning/machine-state/classification/inputs/output/known_at/invalidated_at/unresolved columns;
- METHODICHKA_PARAGRAPH_COVERAGE.csv: all171main-document paragraphs, including headings, definitions, educational cautions and illustrative text; exact paragraph hash and raw/clean locator mapping;
- METHODICHKA_VISUAL_LEDGER.json: all31distinct figures inspected once, all41rawmedia/reference relationships retained (10byte-identical fallbacks), source hashes and bounded caption/geometry conclusions;
- PRIMARY_SOURCE_COMPARISON.json: five primary PDF/text identities,14findings and76short exact page/block citations;
- SECONDARY_SOURCE_COMPARISON.json:26exact citations from SW6,SW8,SW10 and verified Demand/Supply originals;
- SOURCE_CONFLICT_REGISTRY.json: scope, precedence, literal/asymmetric wording and visual refinements without deleting lower-priority alternatives;
- AGENT_LEDGER.json: actual focused agents/roles, disjoint source ownership, files/evidence/decisions/uncertainty/tests/dependencies.

The source analyst read all Methodichka main-document text and all31distinct figures. Raw DOCX contains172nonempty normalized paragraphs; the clean extraction has171because one duplicate P0095 was removed. All other text aligned. P-number locators refer to clean extraction, not DOCX paragraph indices. The local archive hash matches the extraction manifest; it differs from the separate archive named in the original freeze. The exact Methodichka DOCX entry hash matches both records. No whole-archive byte-identity claim is made.

Primary comparison covers text with page/block citations and verifies the retained PDFs/texts; it is not a new claim that every primary-PDF illustration has been independently interpreted. Unknown visual/context-dependent semantics remain unknown. Source figures are teaching schematics/examples, not market-history outcomes or data annotations.

## What source evidence closes

- The illustrated Methodichka Range path (image23 after P0130) is deviation -> return/structure break -> retest/entry from last pre-break OB; its caption targets the opposite Range boundary. It is explicitly one setup, not the exclusive Range strategy.
- Range examples show both high-first/low-second and low-first/high-second boundaries. No universal high-before-low order may be inferred.
- LONG OTE illustration fixes level coordinates0=high,1=low and0.705–0.79near the low, conditional on qualified anchors. Literal text wording is retained. Click order does not define a new coordinate rule; unshown SHORT and anchor qualification remain unresolved.
- An illustrated whole-candle OB zone supports known full-candle geometry without a numeric body/wick threshold. Tilted EQL figure corroborates permitted tilt without quantifying reasonable tilt.
- The pictured three-candle SFP has third-candle body engulf. That is an illustrated instance; a universal mandatory engulf requirement is UNKNOWN. The optional fourth candle is not labeled by those figures.

## What remains unresolved

The source permits multiple entry/stop/full-partial/ATR/STB variants without unique precedence. Exact inside-zone quotes, beyond-anchor buffers, partial fractions/remainder termination, qualified impulse/context/liquidity, generic re-entry and actual causal market annotations are still missing. The ledger preserves these gaps. An educational caution or plotted example is not converted into a hard admission rule. Semantic EXPLICIT means wording is explicit; operational_input_state remains UNKNOWN and no executable trade rule is claimed by the ledger.

## QA contract and boundaries

`validate_source_rule_ledger` is a read-only audit helper. It checks15retained source files, archive/frozen raw-entry links,189exact text excerpts, complete paragraph/image hash coverage and cross-table lifecycle/classification/safety consistency. It parses `word/document.xml` separately from headers/footers, whose P-numbering restarts. It does not use OCR, assert human annotation truth, or create market objects.

Visual caption interpretations are a named human/source audit. CI checks their source-image hashes/relationships against the original extraction manifest; this is not a fresh byte/vision audit of absent raw DOCX assets. The original analyst handoffs and raw images remain retained in the workspace. Software closed-prefix availability is TECHNICAL_NORMALIZATION, not a timestamp invented by SOURCE.

Fourteen targeted regressions cover exact quote/hash/coverage/classification/CSV/visual tampering, source priority, report safety, source/page/block attribution, extraction linkage and read-only reproducibility. Full suite, compile, safety, independent review and green exact-head CI precede merge. Parent-linked freeze is separate under `docs/pure_source_stage19_qa_v1/`.

All audit/ledger transport behavior is TECHNICAL_NORMALIZATION. SOURCE_RULE records describe verified original meaning; no new runtime SOURCE rule or PROJECT_POLICY is installed. No profitability/financial/historical replay is run. `NOT_IDENTIFIABLE`, `trade_entry_allowed=false`, financial/PAPER/LIVE/private API=false.

Next: bind Stage18 claims to actual closed parent/candle evidence and first ingestion time, preserving historical/prefix equivalence; then migrate qualified object consumers incrementally. Missing annotations must yield UNKNOWN, never automatic PASS.
