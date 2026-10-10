# QA — ORIGINAL_STRATEGY_SPEC_v1

Verdict **NOT_IDENTIFIABLE**, этап source contract reconstruction завершён.
Новый profitability backtest не запускался. Нет fit, grid search, выбора по
financial outcomes, новых financial results или удаления751audit trades.
`trade_entry_allowed=false`, production engine не изменён.

| Проверка | Результат | Evidence |
|---|---|---|
| Полная regression suite | 611 tests PASS | `qa/full_unittest.log` |
| Source fidelity после окончательных уточнений checker/spec | 29 tests PASS | `qa/source_fidelity_tests_final.log` |
| Literal citations / source hashes | PASS,13documents | `qa/validation_receipt.json` |
| Registry / tree / stage-source consistency | PASS,84 rules:53SOURCE/12PROJECT/19NORMALIZATION | тот же receipt |
| Tree nodes / contracts | 90 source nodes;8 trade setups + 4 components | tree JSON / branch_contracts.json |
| Synthetic LONG/SHORT evidence | 24 examples, все без ALLOW | `synthetic_LONG_SHORT_examples.json` |
| Causal envelope / prefix / future mutation / replay / modes | PASS в29 tests, для всех 12 paths; future relevant dependency, OPEN-only, native body checks отдельно | source-fidelity test log |
| Conflict registry | 12 conflicts/scopes сохранены; primary BE conflict resolved в scope, не удалён | source_conflict_registry.json |
| Ruff новых3 scripts + test | PASS | `qa/ruff_final.log` |
| Compile этих4 files | PASS | `qa/compile_final.log` |
| mypy production src | PASS,53 source files | `qa/mypy.log` |
| Repeat builder / SHA256 | PASS | `qa/builder_repeatability.json` |
| All archived c2d1Git blobs | PASS,17851 files | validation receipt |
| Baseline19404Git blobs | PASS,17728 files,ни одного изменения | validation receipt |
| Старый sealed audit manifest | PASS,122 artifacts, membership наc2d1 | validation receipt |
| Resume frozen spec | Выполняется перед/после commit; output проверяется; manifest SHA охватывает сам report | verify script |

Full regression run проверял существующий engine и research utilities; после
последнего уточнения component-vs-trade результата и source metadata выполнен
окончательный focused29-test run. По текущим bytes вновь проверены старый Git
tree и literal citations. Existing tests используют свои synthetic/fixture
кейсы; это не новый исследовательский profitability backtest.

130 inline diagram anchors покрывают все122 unique DOCX images. Старый полный
visual review195 media occurrences/54 PDF pages сохранён; targeted re-review
зафиксирован в source_review_receipt.json. Anchor locators приблизительны по
положению image относительно deduplicated paragraphs; original media SHA exact.

Материальные holes остаются: exit/remainder, SL anchor/buffer/ATR, branch/entry
ownership, TF/context selection, meaningful liquidity/qualitative geometry,
re-entry eligibility/identity. Fixtures не устраняют эти holes. Автоматический
market detector для полностью идентифицированной original strategy не создан;
synthetic prefix QA не является доказательством такого detector на real history.

Источники самостоятельно закрывает роли и literal restrictions: SFP anyTF/H1+
preference, conservative LTF1–15M, fixed primary stop, Range80/20 scope,
OB first/repeat distinction и allowed full/partial FTA. Источники не выбирают единственную
комбинацию этих альтернатив. Component-only SnD/FVG/OTE/AMD не превращены в
самостоятельные готовые trading systems.

Все logs, в том числе первоначальные диагностические Ruff findings, сохранены.
После freeze ни builder, ни validator не должны переписывать v1; только strict
`--resume-existing`. Перед реализацией нужен новый identifiable version/freeze.
