# Phase 1.4.16 v0.4.16 — Range Directional Geometry Normalization

## Goal

Fix a concrete Range Detection normalization defect discovered during the Phase 1.4.15 real-data chart/audit pass, without changing Entry Engine logic or introducing profitability-driven thresholds.

## Finding from retained real data

The Phase 1.4.15 candidate builder selected the correct *types* of source boundaries but then normalized prices with `min/max` without first checking whether the source-defined directional geometry was preserved.

This allowed inverted boundary pairs to become apparently valid ranges. Example from BTCUSDT 60m:

- impulse direction: `DOWN`;
- boundary #1: swing low `88813.0`;
- boundary #2: later swing high `88389.8`;
- the later "high" is below the earlier "low";
- old code nevertheless converted the pair to lower=`88389.8`, upper=`88813.0`.

That silently swapped the economic roles of the source-defined boundaries.

## Normalization fix

A causal, non-numeric geometry guard is applied before lower/upper normalization:

- `UP`: boundary #1 is the impulse-end swing high and boundary #2 is the later correction swing low; therefore `first_boundary_price > second_boundary_price` must hold.
- `DOWN`: boundary #1 is the impulse-end swing low and boundary #2 is the later correction swing high; therefore `first_boundary_price < second_boundary_price` must hold.
- equal or inverted pairs are rejected before `min/max` is applied.

This is a structural consistency rule, not a trading threshold and not a symbol-specific exception.

## Real-data regression check

On the retained BTCUSDT 60m 240-day file:

- Phase 1.4.15: ranges=`232`, ever-validated=`151`, boundary SFP=`28`;
- Phase 1.4.16: ranges=`227`, ever-validated=`150`, boundary SFP=`28`;
- five inverted candidates were removed (old range IDs `4`, `82`, `94`, `150`, `206`).

On retained BTCUSDT 240m:

- before: ranges=`57`, ever-validated=`31`, boundary SFP=`7`;
- after: ranges=`57`, ever-validated=`31`, boundary SFP=`7`.

The fix is therefore narrow on the checked data and does not alter valid BTC 240m behavior.

## Reporting namespace

`analyze_mtf_sfp.py` now defaults to `data/reports/phase1_4_16` so a current run does not overwrite earlier Phase 1.4.14 evidence by default.

The cross-asset harness also defaults to the Phase 1.4.16 report namespace and reports version `0.4.16`.

## Blocker status

`RANGE_DETECTION_NORMALIZATION_NOT_VALIDATED` remains OPEN.

Reason: this patch fixes a demonstrated geometry defect, but the conservative BOS strong-impulse proxy still requires broader real-data/chart validation before the whole Range Detection normalization can be declared validated.

Still open:

- `RANGE_DETECTION_NORMALIZATION_NOT_VALIDATED`
- `RANGE_BOUNDARY_CLARITY_THRESHOLD_NOT_FORMALIZED`
- `RANGE_RETIREMENT_REDRAW_LIFECYCLE_NOT_FORMALIZED`
- `ENTRY_ZONE_SL_TARGET_RR_NOT_IMPLEMENTED`

## Safety

- `trade_entry_allowed=false` remains unchanged.
- No Entry Engine implementation was added.
- No ATR/percentage impulse threshold was invented.
- No boundary-clarity number was invented.
- No symbol-specific override was added.

## Version

- Package: `0.4.16`
- Source Rule Registry: `phase1.4.16-0.4.16`
