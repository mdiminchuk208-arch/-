# ORIGINAL_STRATEGY_SPEC v1.1

Source-faithful executable profile frozen before outcome. Frozen v1 remains NOT_IDENTIFIABLE. Exact historical original remains NOT_IDENTIFIABLE. User choices do not become SOURCE_RULE.

# User resolution decisions — PRE_BACKTEST

## U1 — EXIT

Category: USER_RESOLUTION_PRE_BACKTEST.

FULL_CONTEXTUAL_FTA_EXIT: 100% at nearest known opposing contextual POI, all eligible TF. Range: source80% inside opposite boundary and remaining20% in same zone; optional breakout remainder disabled.

Source permits/supports: S_FTA, S_FTA_EXIT_OPTIONS, S_RANGE_EXIT; selection is user authority.

## U2 — STOP

Category: USER_RESOLUTION_PRE_BACKTEST.

FIXED_INITIAL_PROTECTIVE_STOP; OB source extreme; Breaker raid/impulse extreme; SFP ATR14 from pattern extreme; STB manipulation raid; Range deviation/invalidation; nonunique anchor WAIT_UNRESOLVED_STOP_GEOMETRY. No TP1→BE.

Source permits/supports: S_STOP_FIXED, S_OB_DIRECT_STOP, S_BREAKER_STOPS, S_SFP_STOP, S_SFP_BODY_EXIT; selection is user authority.

## U3 — ENTRY_BRANCH

Category: USER_RESOLUTION_PRE_BACKTEST.

OB reaction→M15 BOS→new POI; SFP completed pattern→M15 BOS→source entry search; Range reclaim/return/retest; STB0.5; confirmed Breaker/conservative SL. First complete physical idea, others confluence; material conflict WAIT_BRANCH_CONFLICT; no fitted priority.

Source permits/supports: S_OB_CONS_TRIGGER, S_SFP_REFINE, S_RANGE_CONSERVATIVE, S_STB_ENTRY, S_BREAKER_FORMATION; selection is user authority.

## U4 — TIMEFRAMES

Category: USER_RESOLUTION_PRE_BACKTEST.

Scan M15/H1/H4/D1. D1 global, H4 local/context, H1 primary, M15 refinement and supported setups. No mandatory ladder/formal owner/all-TF trend alignment. Conservative refinement only M15, strictly lower; M15 OB/SFP needing lower refinement waits, not a source prohibition. No M1/M5 in this executable profile.

Source permits/supports: S_FRACTAL, S_SFP_TF, S_OB_CONS_TF, S_MEDIUM_PREFERENCE; selection is user authority.

## U5 — LIQUIDITY_GEOMETRY

Category: USER_RESOLUTION_PRE_BACKTEST.

ADVERSE→WAIT_SWEEP; TARGET_OR_FUEL/NEUTRAL not blockers; UNKNOWN→WAIT_UNRESOLVED_LIQUIDITY_CONTEXT. After sweep revalidate, no auto entry. No old751 blanket filter, no loss deletion or hidden thresholds. Qualitative geometry requires explicit causal source evidence; insufficient evidence UNKNOWN/WAIT.

Source permits/supports: S_ADVERSE_BLOCK, S_ADVERSE_WAIT, S_EQ_STRUCTURE, S_POOL_SCOPE, S_OB_APPROACH; selection is user authority.

## U6 — REENTRY

Category: USER_RESOLUTION_PRE_BACKTEST.

FIRST_TEST_ONLY. Consumed OB/POI cannot be reused. New formation+confirmation+new POI identity and full validation only; no cooldown/random90%/retry count.

Source permits/supports: S_OB_FIRST_TEST, S_SND_FORMATION; selection is user authority.


## Registered machine conventions

- N11_ENTRY: Proximal entry edge for source new-POI/Breaker/Range retest; STB midpoint. Round inside POI to instrument tick. Selects one source-permitted limit price, never a market fill. Rationale: Smallest explicit quote convention; no optimized intrazone offset.
- N11_TARGET: Non-Range opposing POI proximal edge, first along direction; tied price preserves all IDs. Range target smallest tick strictly inside opposite source boundary, or nearer explicit source-defined contextual FTA supplied by Range exit evidence; both80/20 at that same price. Rationale: Minimum representable inside distance; no fitted near-boundary percentage.
- N11_STOP_TICK: Non-SFP strictly beyond source extreme by minimum representable tick; SFP ATR stop round outward to tick, no extra percentage buffer. Instrument tick metadata must be causally known. Rationale: An extreme is not a tradable strictly-beyond price without tick convention.
- N11_ATR_SMA14: SMA of14 True Ranges, 15 contiguous completed pattern-TF bars ending at raid CLOSE. Previous close included; latestOHLC equals pattern. ATR frozen before confirmation and entry. Rationale: Request fixes14 bars but not smoother; rolling mean avoids recursive seed/warmup assumptions.
- N11_BODY_TF: SFP manual body invalidation uses completed pattern-TF CLOSE only, strict beyond extreme. Rationale: Source does not exhaustively arbitrate all candle TF; pattern-TF convention stated explicitly.
- N11_IDENTITY: SHA256(symbol, contextual structural origin ID, original idea POI canonical ID) physical key; setup key adds direction, formation and confirmation IDs. Evidence adapters must use stable canonical source IDs. Refined entry POI references parent idea POI. Consumed zone and formation cannot be relabelled as new setup. First complete validation event owns plan; no branch token in identity. Rationale: Prevents duplicate branch trades without lifetime symbol ban or time cooldown.
- N11_BATCH: Evaluate complete same-event branch set; conflict before tie selection. Equivalent plans use earliest validation event; lexical branch label only labels identical-plan provenance. Later conflict blocks new admission and preserves previously observed state. Rationale: Total deterministic ordering of equivalent plans, not financial branch ranking.
- N11_EVIDENCE: Typed source_validated causal annotations supply meaningful liquidity, tilt, smooth approach, whole impulse, range clarity, protected endpoints and branch confirmation. Missing/future/nonunique evidence waits. No quantitative qualitative classifier claimed. Inventory attestation covers known prefix only. Rationale: User explicitly requires WAIT rather than materially arbitrary thresholds.
- N11_EVENTS: Strictly ordered causal quotes drive synthetic limit/SL/FTA lifecycle. Bar simultaneous touches or unobserved fill ordering WAIT_INTRABAR_ORDER; no assumed SL-first/TP-first. Rationale: Causal lifecycle contract, not an exchange fill model; monetary costs outside source.
- N11_SOURCE_SCOPE: Primary setup-specific SW9/SW12 contracts retain v1 source hierarchy. DOC19 stronger OB/Breaker IMB and DOC20 BE alternatives stay visible and inactive; not universal AND gates. Rationale: Resolve profile scope explicitly without claiming the historical original unique.

## Explicit limits

- No unique automatic source algorithm for meaningful liquidity/smooth approach/whole impulse/range clarity/structural endpoints.
- Without explicit causal source-validated evidence these cases WAIT; no inferred boolean annotations from the old engine.
- Canonical POI/context/formation IDs and complete contextual inventory require a source-faithful adapter; no historical performance validation done.
- OHLC simultaneous event order unresolved: WAIT_INTRABAR_ORDER; no exchange fill realism claimed.
