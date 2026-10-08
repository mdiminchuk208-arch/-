# Phase 1.4.1 — full recheck corrections

This is a corrective release of Phase 1.4 after code/source/API re-review.

## Fixed
- Added explicit LTF observation bounds to the MTF linker.
- A finite experimental wait window is no longer marked `EXPIRED` when the dataset ends before the deadline; it is `RIGHT_CENSORED_BEFORE_DEADLINE`.
- HTF SFPs outside available LTF coverage are labeled `LTF_COVERAGE_MISSING_AT_SFP` rather than linked to unrelated later data.
- Added an evaluation-window boundary so older loaded data can serve as warm-up context without being counted as test candidates.
- Added `--evaluation-days` to the MTF analyzer. Recommended local Phase-1.4.1 run: load 60 days, evaluate the last 30.
- Added explicit reporting of `unique_ltf_bos_count` and `shared_bos_link_count` so one BOS linked to multiple prior SFP contexts is not mistaken for multiple trades.
- Empty HTF/LTF CSV files now block analysis cleanly instead of causing an index error.
- Package/registry/User-Agent versions synchronized to 0.4.1.

## Still intentionally unresolved
- Exact HTF->LTF mapping is a BACKTEST_PARAMETER, not a source rule.
- The source gives no maximum SFP->BOS wait window.
- A matched LTF BOS only unlocks entry search; it is not yet an order or complete entry candidate.
- One BOS may observationally link to several SFP contexts. Opportunity de-duplication will be handled later rather than invented as a source rule now.
