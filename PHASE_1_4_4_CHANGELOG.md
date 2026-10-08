# Phase 1.4.4 v0.4.4 changelog

1. Coverage audit now distinguishes leading/trailing boundary shortfall from internal gaps and prints missing expected UTC opens.
2. Added equal-real-time SFP->BOS wait budgets (`--wait-minutes`) alongside LTF-bar experiments.
3. Candidate/report outputs now carry elapsed minutes and effective wait minutes.
4. Added LTF BOS inventory and `bos_diagnostic.csv` for zero/low-confirmation QA (diagnostic-only; no retroactive validation).
5. Added cross-pair global opportunity clustering after all requested HTF/LTF reports for one symbol are built.
6. Exact-timestamp clustering is deterministic; positive clustering windows are BACKTEST_PARAMETER.
7. Global clustering is cross-pair only and never collapses distinct opportunities from the same pair.
8. Trade Entry remains blocked; Range-boundary SFP and Entry Zone/SL/targets/RR remain pending.
