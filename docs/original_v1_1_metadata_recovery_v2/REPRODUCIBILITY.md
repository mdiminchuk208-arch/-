# Reproducibility

From repository root, use /workspace/crypto-bot-venv/bin/python.
Offline report generation from saved provenance: python scripts/audit_original_v1_1_metadata_recovery_v2.py --build.
Existing outputs are protected. Fresh offline replay: python scripts/audit_original_v1_1_metadata_recovery_v2.py --replay-output /tmp/metadata_stage_a_replay.
Hash-check frozen delivery, parents and dataset: python scripts/audit_original_v1_1_metadata_recovery_v2.py --resume-existing.
QA and seal: --validate followed by --seal. Neither imports financial accounting nor runs a financial backtest.

Source collection scripts are retained. Initial collector expects complete official Git clones at
/tmp/bybit_metadata_recovery_docs and /tmp/bybit_metadata_recovery_pybit; both remotes and pinned heads are
in provenance/HISTORICAL_METADATA_SEARCH_RECEIPT_v2.json. Use a separate checkout/namespace for any future
collection: sealed namespace cannot be overwritten. Announcement collector uses public search POSTs only,
with schema pinned to the saved public frontend JS. All raw bodies, requests, literal content, commit history,
query counts and partial manual assessment are retained. Transport response cookies are redacted; original
header digests are preserved in the initial search receipt. Report replay consumes saved inputs, not today's web.

Full regression tests include inherited synthetic accounting unit fixtures; this is not financial history execution.
The manifest seals the STOP evidence and its scripts/tests/QA logs; it is not an Evidence v3 financial eligibility freeze.
