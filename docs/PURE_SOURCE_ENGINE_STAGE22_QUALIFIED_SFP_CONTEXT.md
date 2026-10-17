# PURE SOURCE Stage22 — bound SFP liquidity context

Parent: Stage21 qualified EQH/EQL consumer, PR24 merge `301e65a5c2e8b798e2d7ec20936f1812961673fd`; exact head `ef5a405384d83eb009329a6f0f98ea39ce9e4d6c` passed Actions39069415206. Stage22 is a new explicit diagnostic adapter; previous frozen consumers are unchanged. New checks are TECHNICAL_NORMALIZATION, with no new SOURCE rule or PROJECT policy.

## SOURCE boundary

Stage19 Methodichka records M_SFP_SHAPE, M_SFP_LIQUIDITY, M_SFP_REVERSAL, M_SFP_TIMEFRAMES and M_SFP_CONTEXT preserve P0158–P0162. SFP is originally three candles with an optional fourth directional confirmation, applies on all timeframes and requires relevant liquidity point/zone context. Exact body establishment and which three candles qualify are unresolved. Illustrated third-body engulf is not made universal.

The existing SW8 next-open producer is one structural transport. Its presence does not prove the full priority1 pattern, and its legacy `requires_ltf_bos` property is not promoted to a universal priority1 rule. Stage22 keeps `priority1_pattern_status=UNKNOWN` regardless of context status. A context PASS remains a statement about the particular relevant liquidity context only.

## Consumer

`assess_bound_sfp_context` reconstructs the actual canonical batch from the supplied closed replay frame. It accepts an explicit SFP object ID and annotation window; no caller-supplied synthetic object, boolean or generic evidence ID substitutes for the canonical subject.

The exact subject set contains the SFP transport and its actual liquidity parent. The window must cover the sweep and closed confirmation transport. All timeframe prefixes have consistent fixed duration, continuity, closed-data membership and positive market prices. These are input-integrity checks, not entry filters. There is no H1 floor or preferred-timeframe gate.

The internal lookup uses SFP_LIQUIDITY_CONTEXT with TRADE_CONTEXT scope and exact market, timeframe, subjects and window. Every available receipt is rebound to actual closed data and canonical ancestry. Full claim, scope/window metadata, witness bytes, content/context hashes and first-observation availability remain in the returned envelope. Late delivery cannot backfill a prior query. Missing/conflicting evidence stays UNKNOWN; no author or latest annotation wins.

Transport intrinsic known time, closed-replay observable time, annotation context known time and current transport lifecycle are separate fields. A later invalidation leaves past context and formation history intact. Context FAIL does not retroactively delete a structural transport. The consumer does not mutate the journal or select a winning SFP/pool among candidates.

The Stage20 caller-clock, non-durable ingestion and unauthenticated annotation truth/authorship/blindness boundaries remain explicit. A context annotation is not a numeric proxy, verified market truth merely because it has a hash, or a trade permission.

## Safety and remaining work

Result fields `trade_entry_allowed=false` and `execution_ready=false` are immutable. A context PASS cannot change `priority1_pattern_status=UNKNOWN`. Default providers, setup branches, stops, FTA allocation, exit/remainder and re-entry logic remain frozen. No financial replay is run.

The next independent safe step is diagnostic provider integration of these explicit bound consumers, preserving first-arrival clock progression and provenance in deterministic replay artifacts. Market annotation inputs remain absent; other family movement/anchor relations, full priority1 SFP geometry, execution coordinates and remainder/re-entry semantics remain UNRESOLVED. Baseline stays NOT_IDENTIFIABLE.

Targeted QA includes actual subject/parent membership, wrong semantic/scope injection, windows requiring closed transport, content tampering, late/conflicting/missing/negative context, historical lifecycle, prefix/future mutation/repeat/input-order, and mirrored LONG/SHORT plus M1/H1 transport. Synthetic annotations do not establish source-valid historical trades. Full QA, independent review and freeze are under `docs/pure_source_stage22_qa_v1/`.
