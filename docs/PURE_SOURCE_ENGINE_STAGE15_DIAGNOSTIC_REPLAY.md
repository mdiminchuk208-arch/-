# PURE SOURCE Stage 15 — diagnostic end-to-end replay

Base: Stage14 merge `9d00c817e6bbf21dcc216d7ef4d0b71554db1c04` (PR #17).

Stage 15 adds a deterministic audit artifact over the existing Stage14 causal execution replay. It does **not** add or change SOURCE rules, select a trade, calculate PnL, choose a missing entry quote, invent ATR, invent FTA, choose full/partial exit allocation, apply PROJECT overlays, or permit PAPER/LIVE/private exchange execution.

## Purpose

The Stage14 adapter already transports typed SFP/FVG parents into the frozen Stage8 execution-semantics contract while preserving the unresolved boundary. Stage15 makes that end-to-end state reproducible and auditable by freezing:

- replay/provider versions;
- dataset SHA-256;
- first/last decision timestamps;
- receipt count and evidence-batch count;
- chained hashes of prefix/evidence/runtime receipts;
- final runtime hash and object/setup/execution-plan counts;
- explicit unresolved observation reasons across OBJECT / SETUP / EXECUTION layers;
- the fail-closed flags `baseline_identifiability=NOT_IDENTIFIABLE`, `trade_entry_allowed=false`, `financial_run=false`.

A Stage14 execution assessment may be `PASS` while remaining non-executable. Stage15 therefore records unresolved execution reasons without converting that PASS into READY. In particular, the known Stage14 blockers remain visible:

- `SFP_ENTRY_QUOTE_WITHIN_NEW_POI_UNRESOLVED`;
- `WAIT_SFP_ATR_EVIDENCE`;
- `WAIT_FIRST_TROUBLE_AREA`.

## Verified repeat / resume boundary

`verify_source_diagnostic_resume` validates an existing artifact fingerprint and repeats the exact causal replay against supplied immutable market data. It verifies version, provider, dataset, receipt chain, evidence chain, final runtime and final artifact hashes.

This is deliberately **verification**, not deserialization of mutable strategy state and not a computation shortcut. A true incremental runtime checkpoint/resume contract remains a separate future technical task and must not be inferred from Stage15.

## Classification

All Stage15 behavior is `TECHNICAL_NORMALIZATION` / QA transport:

- deterministic diagnostic aggregation;
- chained causal receipt fingerprints;
- artifact self-fingerprint verification;
- exact repeated-replay verification.

No `SOURCE_RULE` is added or modified. No `PROJECT_POLICY` is applied.

The PURE SOURCE baseline remains `NOT_IDENTIFIABLE`. A financial simulator/backtest remains blocked until source-supported execution and exit alternatives plus required qualitative/context inputs are sufficiently identified. Historical performance must not be used to fill those gaps.
