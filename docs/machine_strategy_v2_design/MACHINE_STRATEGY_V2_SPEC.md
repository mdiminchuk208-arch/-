# Machine Strategy v2

Original v1/v1.1 remains the immutable source reference. This is a deterministic machine interpretation, not exact Original. All selectors not uniquely dictated by source are MACHINE_RULE_PRE_BACKTEST. Do not promote them to SOURCE_RULE.

Preserve SFP, OB, Breaker, STB/BTS, Range, FVG/IMB, liquidity, BOS, CONF, OTE/PD, FTA, FIRST_TEST_ONLY, fixed stop and M15/H1/H4/D1. Formation TFs are H1/H4; H1 decision and M15 refinement apply consistently. Missing observations cause defined WAIT/reject outcomes rather than discretion. Every critical selector has a total rule, deterministic tie-break and causal known_at.

The rule registry is normative together with frozen executable core; specialized documents identify the exact rule IDs. SOURCE_CITATIONS.json preserves primary file/page/hash/literal passages. No historical results, labels, fitted winners, future candles or profitability subgroups are design inputs. Design QA uses synthetic prefixes only.

Historical price/quantity verification is separate. Theoretical unrounded execution, relative stop/boundary epsilon and modeled costs require explicit Stage 2 registration. No historical exchange-realistic execution assertion. No automatic production or real orders; trade_entry_allowed=false.
