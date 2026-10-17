# Stage23.1 J / CI compatibility report

Owned changes: `.github/workflows/strategy-engine-validation.yml`, `src/crypto_bot/strategy/source_qualified_sfp_context_v1.py`, `src/crypto_bot/strategy/source_qualified_liquidity_v1.py`, `tests/test_source_qualified_sfp_context_v1.py`.

Cause: CPython3.14 changed `dataclasses.replace` rejection of `init=False` keyword fields from ValueError to TypeError. The safety flags now use constructor defaults False and explicit domain validation (`value is False`), yielding stable ValueError while retaining frozen instances. Regressions cover both constructors and replace, reject True/0/1/None/"false", and check frozen assignment. The original context-PASS/trade-enable rejection is preserved.

Installed with `uv python install 3.11 3.14` using uv0.12.19, inherited proxy/CA settings and TLS verification. Actual versions: CPython3.11.16 and CPython3.14.7. Paths:

- `/home/agent/.local/share/uv/python/cpython-3.11-linux-x86_64-gnu/bin/python3.11`
- `/home/agent/.local/share/uv/python/cpython-3.14-linux-x86_64-gnu/bin/python3.14`

From `/workspace/-`, for each interpreter:

```sh
PYTHONPATH=src:tests "$PYTHON" -m unittest -v test_source_qualified_sfp_context_v1 test_source_qualified_liquidity_v1 test_source_qualified_replay_v1
"$PYTHON" -m compileall -q src scripts tests
```

Both targeted runs PASS46tests; compileall PASS both. Logs: `targeted-python311.log`, `targeted-python314.log`, `compile-python311.log`, `compile-python314.log`. No full suite run by this agent.

The workflow safety invariant was also run under each interpreter: fixed-string recursive grep for `trade_entry_allowed=True` in runtime Python source followed by the existing Python path/text assertion. Both PASS; `safety-python311.log`, `safety-python314.log`.

`/workspace/crypto-bot-venv/bin/ruff check` with `--select E9,F`, `ruff format --check` for the three owned Python files, and scoped `git diff --check` PASS.

CI now runs3.11 full discovery and3.14 `test_*source*.py` plus `test_causal_object_core.py`, with compileall and safety invariant on both. This includes all PURE_SOURCE, qualified-consumer/replay, archive/source-integrity and source-geometry tests without a custom runner. The complete3.14 CI selection remains for consolidated root validation.

No dependency/metadata changes or upper Python bound. No environment blocker. No commits. Historical Stage21/22 freeze manifests remain historical evidence; Stage23.1 authorized correction hashes belong in the new audit manifest, without rewriting old hashes. No SOURCE materials, claim/archive/ledger files or freeze artifacts changed by this agent.
