# PURE SOURCE Stage 14 — execution semantics transport

Base: Stage13 merge `5e40bebcded754081bb02f219df0c828ee075253`, PR #16. Its exact head `18bed33e97b497e44eb554832d69b0fcce1a7577` passed compile,758unit tests and safety in Actions 39021501525 before merge.

A separate provider extends Stage13. Stage1–13 code, SOURCE rules and historical artifacts remain unchanged. It connects immutable historical SFP/BOS/FVG assemblies to the frozen Stage8 SFP planner using the actual typed SFP and FVG zone. Historical plan capture does not assert current context eligibility; current setup observations remain separate.

## Explicit execution boundary

The existing Stage8 contract captures SOURCE permissions: new-POI zone entry (SW8 p5), ATR-based SFP stop (SW12 p12–13), body-close SFP invalidation and FTA exit concepts. It does not supply an exact entry quote within the zone, a complete ATR evidence/normalization contract or a known FTA from absent inputs. The adapter passes `atr=None` and `fta=None`, never an arbitrary ATR period, zone midpoint, future target or fabricated price.

Every resulting plan retains these reasons:

- SFP_ENTRY_QUOTE_WITHIN_NEW_POI_UNRESOLVED;
- WAIT_SFP_ATR_EVIDENCE;
- WAIT_FIRST_TROUBLE_AREA.

Stage8 assessment PASS means SOURCE_EXECUTION_SEMANTICS_CAPTURED, **not execution_ready**. Plans have quote=None, unresolved stop and WAIT_FTA. Even with a supplied FTA the frozen contract retains full-versus-partial/remainder ambiguity; this adapter chooses neither. No TP40/30/30, cost breakeven, AntiScalp, fee gate or portfolio admission is present. Meaningful liquidity/context/qualitative setup gaps also remain unresolved.

No plan is registered before its setup and causal parents. Observation receipts are never backdated to intrinsic known_at. Future context invalidation or additional POI cannot change a historical plan, its stable setup identity or its earlier receipt. Missing typed parents stay UNKNOWN; other setup branches remain UNKNOWN in Stage13 until source-qualified evidence exists.

## Classification and validation

New behavior is TECHNICAL_NORMALIZATION transport, typed parent binding and explicit diagnostic separation. No SOURCE_RULE is added/changed, and no PROJECT_POLICY is applied. Baseline remains NOT_IDENTIFIABLE; `trade_entry_allowed=false`; no financial simulation/private API/PAPER/LIVE.

Dedicated tests cover real causal planning, PASS/readiness separation, mirrored LONG/SHORT, historical plan retention under later invalidation/ambiguity, independent prefixes, deterministic input order and diagnostic hashing. Full compile/unit/safety/lint/format and independent read-only review are required. Synthetic traces/funnels and the Stage13-linked freeze are under `docs/pure_source_stage14_qa_v1/`. Full exact-head GitHub Actions must pass before merge.

Next: diagnostic end-to-end replay and verified artifact resume. A financial simulator remains blocked until source-supported exact execution/exit alternatives and qualification inputs are sufficient; these gaps cannot be closed by historical performance.
