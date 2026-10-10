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

Full request SHA256: `3bfbb31bbd15a4078faa9225f10a76a4e2fd1999ffc948f45435e4f6eb2de871`.
