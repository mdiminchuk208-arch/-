# Offline reproduction

Run from the repository root using the configured environment:

```sh
python scripts/original_v1_1_execution_metadata_v3.py
python scripts/original_v1_1_execution_metadata_v3.py --replay-output /tmp/crypto_metadata_v3_replay
python -m unittest discover -s tests -v
ruff check src --select E9,F63,F7,F82
ruff check scripts/original_v1_1_execution_metadata_v3.py tests/test_original_v1_1_execution_metadata_v3.py
python -m compileall -q src tests scripts
mypy src
python scripts/verify_original_strategy_spec_v1_1.py --resume-existing
python scripts/original_v1_1_execution_metadata_v3.py --validate-replay /tmp/crypto_metadata_v3_replay
python scripts/original_v1_1_execution_metadata_v3.py --seal
python scripts/original_v1_1_execution_metadata_v3.py --resume-existing
```

Check all QA command exit statuses and save logs in qa before validating/sealing. After seal use verified resume only. Replay is offline; two targeted retrieval snapshots are inputs and are not downloaded again. Field contracts and the complete unchanged primary literals are replayed independently. Inherited unrestricted lint findings are documented in frozen v4 QA; no predecessor file is reformatted. Parent/code/output/log/closed-namespace hashes are required by the manifests. No financial CLI is called.
