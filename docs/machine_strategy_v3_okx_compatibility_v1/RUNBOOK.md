# Frozen compatibility runbook

Use /workspace/crypto-bot-venv/bin/python from the repository root. ECC ecc@ecc 2.2.3 remains enabled; hooks remain inactive. Roles run via the cloud collaboration tools with the project TOML role instructions, not claimed as native ECC CLI model launches.

Before outcomes: build_okx_v3_compatibility_v1.py --prepare, then --qa; two independent read-only reviews; --freeze-ready; commit and push. After commit only: scripts/okx_v3_compatibility_runner_v1.py --run-historical-once --expected-ready-manifest-sha256 EXTERNALLY_RECORDED_SHA --ready-freeze-commit COMMIT_SHA.

Outputs go exclusively to docs/machine_strategy_v3_okx_financial_validation_v1. Freeze namespace is immutable. Never log changing stdout inside that output namespace. RUN_AUTHORITY.json forbids a second unrelated run. Each catalog/case/segment/result checkpoint emits RUN_CHECKPOINT_SHA256. For interrupted work, pass --resume-run --expected-run-checkpoint-sha256 THE_EXTERNALLY_RECORDED_CHECKPOINT_SHA with the same READY SHA and commit. Completed segments are hash-verified and skipped; partial prefixes must match exact bytes, membership, canonical catalog and IDs. Missing/stale/torn checkpoints stop; do not silently trust or truncate them. Frozen READY may also be checked with --resume-existing --expected-manifest-sha256 EXTERNAL_SHA.

Every emitted case and all nine modeled states are retained. Unresolved eligibility/fill/closure or filled unknown forces STOP; CLOSED-subset financial statistics are diagnostic. Both R-ledger and cash sums must be positive; primary PF is R PF. No scenario, threshold, branch or direction may be changed after outcomes. Any later repair requires a separately named preregistered version. OOS/PAPER/LIVE remain unauthorized.
