# Artifact index

Core contracts: EVIDENCE_ADAPTER_V2_SPEC.md, EVIDENCE_CAPABILITY_MATRIX.csv, OBJECTIVE_SOURCE_DETECTORS.md, CANONICAL_ID_CONTRACT.md, QUALITATIVE_EVIDENCE_ANNOTATION_PROTOCOL_v1.md, ANNOTATION_SCHEMA_v1.json, SOURCE_CITATION_INDEX.json.

Evidence output: EVIDENCE_FUNNEL.json, BREAKDOWNS.csv, OBJECTIVE_EVIDENCE_CASES.jsonl.gz, OLD880_EVIDENCE_RECHECK.csv, DATASET_VERIFICATION.json, PARENT_INVARIANCE.json, CONSUMED_STATE_REGISTRY.json.

Blinded pack: candidates.jsonl.gz, BATCHING.json, candles/ (8 archives), objects/ (8 archives), previous_levels/ (2 archives). Shared archives are accessed only via per-candidate cutoff-enforcing materializer.

Gaps/delivery: REMAINING_EVIDENCE_GAPS.md, QA_REPORT.md, QA_RECEIPT.json, REPRODUCIBILITY.md, freeze_manifest.json.

Provenance: exact user request, pinned official Bybit instrument API schema/sample, metadata search receipt and public access failure log.

Implementation: scripts/original_v1_1_objective_geometry_v2.py; scripts/original_v1_1_evidence_adapter_v2.py; scripts/run_original_v1_1_evidence_adapter_v2.py; scripts/materialize_original_v1_1_annotation_pack.py; scripts/build_original_v1_1_evidence_adapter_v2_docs.py; scripts/seal_original_v1_1_evidence_adapter_v2.py. Tests: tests/test_original_v1_1_evidence_adapter_v2.py.

Every delivered file, code and test is listed with SHA256 in freeze_manifest.json. Historical freezes/baseline/audit remain in their original namespaces unchanged.
