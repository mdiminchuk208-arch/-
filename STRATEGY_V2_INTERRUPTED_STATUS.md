# V2 checkpoint preserved at user's stop

The user stopped V2 work and supplied a new medium-term horizon task. No further
V2 rule search, test evaluation or candidate selection is authorized by that stop.

Baseline main remains dab8d254aaf4babc07659e3d03d14b269445767b. V2 rules and
label-free TEST predictions were committed in
e569909556e059c3f704d6ebe6f1f2e1b2616871 before one TEST opening.

Completed artifacts under data/reports/strategy_v2_2026_10_10:
all 16,333 CLOSED feature rows, 18 censored OPEN rows, TRAIN/VALIDATION search,
frozen rules/models/predictions, single TEST results, complete case/robustness/
cost-stress exports and independent QA. TREE_D3_L200: 297 CLOSED, 201 WIN,
96 LOSS, WR .6767676768, PF 1.004265664, expectancy .0319289561 USDT,
Net PnL 9.482899964 USDT. The validation-selected primary remains SFP with
friction_R <= .15 and sweep_ATR >= .1: 297 CLOSED, WR .3905723906,
PF .8992241374, expectancy -1.4371248765, Net -426.8260883 USDT.
No target gate passed. This is a V2 held-out DEVELOPMENT test on already inspected
2026 history, not fresh market OOS. Do not select a new rule using its TEST.

Independent QA passed: 16,851 baseline Git blobs unchanged, 40 exact dataset
hashes / 993,575 candles, 243 prefix/future checks, all 16,351 causal expected
costs and 16,333 realized cost/R ledgers, independent SciPy Wilson and Decimal
drawdown. 556 tests pass, mypy 50 source files, compileall pass, Ruff exactly
555 inherited findings with zero new findings. All failed and passed logs remain.

The report renderer was written and linted but NOT RUN when the user stopped.
STRATEGY_V2_70WR_ANALYSIS.md and the final aggregate V2 delivery receipt are not
published outputs. Preserve the renderer and existing artifacts; do not claim a
completed V2 report. Medium-term research is a separate new task and must retain
the prior data, code, protocols, tests and frozen results.

Safety remains trade_entry_allowed=false; no LIVE/private API/orders.
