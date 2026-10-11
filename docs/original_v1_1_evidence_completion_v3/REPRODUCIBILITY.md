# Reproducibility

Use repository root and its Python environment (stdlib runtime, Python ≥3.11).

1. `python scripts/run_original_v1_1_evidence_completion_v3.py --resume-existing`
   verifies the closed v3 namespace, code/tests, parent manifest chains and exact dataset hashes;
   it does not rerun source evaluation or financial computation.
2. `python scripts/run_original_v1_1_evidence_completion_v3.py --replay-output /tmp/v3-fresh-replay`
   reconstructs the full fixed cohort source evidence in a fresh destination and preserves
   already frozen output. Every generated file must match QA_RECEIPT replay hashes byte-for-byte.
3. `python -m unittest discover -s tests -v` runs all regression tests. Financial fixtures in
   inherited tests are synthetic unit tests, never a historical financial run.
4. `python scripts/materialize_original_v1_1_evidence_completion_v3.py --unit-id ID --output /tmp/new-unit.json`
   materializes only that unit's complete causal visible prefixes, with no future candles.

Gzip mtime=0, empty embedded filename; compact sorted JSON; stable object and annotation IDs;
chronological frozen raw order; sorted signature order for units. No network/metadata search,
manual editing of historical labels, random values or outcome data is needed for a replay.
Parent invariance includes v1/v1.1/v2/recovery, first result and baseline/Source Audit archive
hashes. The namespace manifest is created only after full QA and excludes only itself.
Run output, reports, QA receipts, provenance, source dependency pointers and all new code/tests
are sealed. Publication commit is on medium-term-source-research; main is unchanged.
