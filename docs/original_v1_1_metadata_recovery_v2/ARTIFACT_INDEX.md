# Stage A STOP artifact index

This is metadata recovery evidence, not an Evidence v3 eligibility freeze.

- HISTORICAL_INSTRUMENT_METADATA_v2.json: BTC/ETH full requested interval map, UNKNOWN values; separate partial tick-change observations.
- HISTORICAL_METADATA_EVIDENCE_REPORT.md: primary references, title/body date discrepancies, missing complete period proof and precise Gate A STOP.
- STAGE_A_STOP_STATUS.json: inherited v2 counts, blocker breakdown, annotation units NOT_RUN, Stage B–H NOT_RUN, no finance.
- QA_REPORT.md / QA_RECEIPT.json / qa/: 769 tests, static checks, frozen strategy/audit verification, replay receipt.
- REPRODUCIBILITY.md: offline build/replay and verified --resume-existing.
- recovery_manifest.json: sealed artifact membership/hashes; excludes itself to avoid circular hash.
- provenance/user_request.txt: exact user instruction, including original CRLF.
- provenance/HISTORICAL_METADATA_SEARCH_RECEIPT_v2.json / REPOSITORY_METADATA_PATH_INDEX.json: scoped project and official Git searches, pins, public network attempts.
- provenance/OFFICIAL_INSTRUMENT_*.mdx / OFFICIAL_DOCUMENT_EXAMPLE_ASSESSMENT.json: five complete immutable official documentation versions and projected metadata samples.
- provenance/OFFICIAL_INSTRUMENT_HISTORY.log / OFFICIAL_FILTER_DIFFS.log / OFFICIAL_FILTER_CHANGE_SEARCH.log / OFFICIAL_CHANGELOG_v5.mdx: document history and change-search evidence.
- provenance/ANNOUNCEMENT_RECOVERY_RECEIPT.json / ANNOUNCEMENT_SEARCH_HIT_INDEX.json: six searches, all pages, 154 unique hits, 72 retrieved historical derivative notices.
- provenance/announcement_query_*.request.json / *.response.json: exact public search requests and responses.
- provenance/announcement_article_*.html / *.text.txt: complete public HTML and extracted literal bodies for 72 notices.
- provenance/PARTIAL_METADATA_SOURCE_ASSESSMENT.json: two exact target-symbol tick-change notices; no full VERIFIED interval.
- Other provenance HTML/JS/headers/responses: public frontend search schema, initial probes, official price-limit reference; transient public cookies redacted from headers.
- scripts/collect_original_v1_1_metadata_recovery_v2.py: guarded initial repository/Git/public source collection.
- scripts/collect_original_v1_1_metadata_announcements_v2.py: public announcement search and retrieval.
- scripts/audit_original_v1_1_metadata_recovery_v2.py: offline reports, STOP audit, seal, resume.
- tests/test_original_v1_1_metadata_recovery_v2.py: 16 Stage A metadata/STOP safety tests.

All individual paths and SHA256 hashes are enumerated in recovery_manifest.json. Frozen original spec/profile,
Evidence v2, first financial preregistration/result, baseline and Source Fidelity Audit remain unchanged.
