# Phase 1.4.3 v0.4.3 changelog

## Recheck findings fixed
1. The previous wording overstated SFP coverage. The source allows external liquidity from both range boundaries and structural swings; current code only maps structural-swing liquidity. This limitation is now explicit in reports/readme and blocks Entry Engine completeness claims until the Range engine exists.
2. Opportunity de-duplication in v0.4.2 was only inside one HTF/LTF report. It is now explicitly labeled `PAIR_LOCAL_EXACT_LTF_BOS`; global/cross-pair clustering remains a required later gate rather than being implied complete.
3. A previously unhandled edge case allowed one outside candle that swept both structural sides to potentially produce opposite SFP formations. Phase 1.4.3 preserves raw high/low sweeps but marks both episodes `AMBIGUOUS_DUAL_SIDE_SWEEP` and emits no directional SFP from that candle.

## Safety
Actual trade entry remains disabled.
