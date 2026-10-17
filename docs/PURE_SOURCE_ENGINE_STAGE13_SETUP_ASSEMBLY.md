# PURE SOURCE Stage 13 — causal setup assembly

Base: Stage12 merge `a17c66eb48b595bc25a74d46f43a97634fae811f`, PR #15. Its exact head `8040a33a3f200fb5557f8f9cdf8402f2bae1f49c` passed all CI steps, including safety, in Actions 39020649164.

A separate provider extends the Stage12 batch. Stage1–12 files and SOURCE semantics remain frozen. No execution plan, financial simulation or order is produced; `trade_entry_allowed=false`.

## Objects, events and assembly

Stage2 interleaved swing geometry supplies structure history. SW5 p4–5 (`MS_BOS_CONTEXT_001`) supplies body-close BOS beyond a protected point. An event requires a previously known active structure; its ID contains that parent and the actual trigger close. The first break invalidates that identity once. Repeated beyond-point closes are not repeated BOS events. This event deduplication is lifecycle bookkeeping, not a first-take or re-entry trading restriction.

Geometry first known after an already observed body breach of its protected swing is retained formation-valid but inactive at its own known_at. Search begins at the protected swing's known_at, never before its existence. Confirmation-close breaches and earlier breach/reclaim are both covered. No lifecycle event is backdated and no BOS is fabricated before the structure existed. A reclaim does not silently reactivate the same identity. CONF selection remains unresolved.

For every Stage11 SFP and every available Stage12 strict-lower candidate, the provider supplies directional causal BOS and typed FVG parents to the unchanged Stage7 `assemble_sfp_ltf_bos_new_poi`. No TF winner or branch ranking is selected. Each causal information arrival is evaluated; previously unique assemblies remain immutable historical facts if a later POI makes selection nonunique, or SFP later invalidates. Separate current observations expose FAIL/UNKNOWN without deleting historical evidence.

SFP intrinsic known_at can be the confirmation candle open; this closed-only transport first observes it at that candle close. Historical reconstruction never emits a receipt before actual observation. Missing expected context data yields WAIT_SOURCE_CLOSED_CONTEXT_DATA, not a chosen pattern lifetime. All parent IDs, BOS references and typed geometry are retained and hashed in the replay batch.

## Qualification boundary

Assembly PASS is conditional structural evidence, **not qualified trade eligibility**. Meaningful liquidity, full context qualification, freshness/re-entry and discretionary geometry are unresolved. Only SFP + known BOS + unique source FVG can currently assemble from these data-only parents. Other source-supported branches explicitly remain UNKNOWN pending qualified objects/chain evidence. Their absence does not invalidate any existing object.

No stop, entry quote, FTA, READY, fill or cancellation policy is inferred. Baseline remains NOT_IDENTIFIABLE. Later execution integration must retain source-permitted alternatives and unresolved inputs.

## Classification and QA

Existing SOURCE_RULEs are reused unchanged. New rules are TECHNICAL_NORMALIZATION: first-break event identity; inactive-at-known lifecycle consistency; exhaustive lower-TF observation; retaining immutable setup history independently from prospective status; closed-observation timing. No PROJECT_POLICY is introduced.

Eleven dedicated tests cover causal parent chains, mirrored LONG/SHORT, unique BOS identity, source-reference traceability, qualitative UNKNOWNs, later invalidation/nonunique POI, independent MTF prefixes/future suffixes, missing context and both late-born broken-structure cases. Raw synthetic evidence is QA only, never historical trade counts. Full compile/unit/safety checks and an independent read-only review precede a green exact-head CI merge. Freeze files: `docs/pure_source_stage13_qa_v1/`.
