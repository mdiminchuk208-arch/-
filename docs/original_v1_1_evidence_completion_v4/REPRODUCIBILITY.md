# Reproducibility

From repository root with the configured Python environment:

```sh
python scripts/original_v1_1_evidence_completion_v4.py
python scripts/original_v1_1_evidence_completion_v4.py --replay-output /tmp/crypto_evidence_v4_replay
python -m unittest discover -s tests -v
ruff check src --select E9,F63,F7,F82
ruff check scripts/original_v1_1_evidence_completion_v4.py tests/test_original_v1_1_evidence_completion_v4.py
python -m compileall -q src tests scripts
mypy src
python scripts/verify_original_strategy_spec_v1_1.py --resume-existing
python scripts/original_v1_1_evidence_completion_v4.py --validate-replay /tmp/crypto_evidence_v4_replay
python scripts/original_v1_1_evidence_completion_v4.py --seal
python scripts/original_v1_1_evidence_completion_v4.py --resume-existing
```

QA commands have their exit statuses checked and logs saved in qa before validation/seal. Once frozen use verified --resume-existing; do not rebuild or modify the namespace. Replay is offline and requires exact pinned Stage 1 and parent manifests. No financial entry point is invoked.

Full-repository lint was additionally attempted: 555 existing findings in legacy scripts/tests; the complete log is retained as qa/ruff_full_repository_existing_failures.log. Immutable predecessor files are not reformatted. An unrestricted src check also found 74 existing findings, retained in qa/ruff_src_existing_failures.log. Acceptance uses fatal-error rules for inherited src and full configured rules for new Stage 2 code/tests.
