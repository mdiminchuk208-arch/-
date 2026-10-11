# Agent Status

State: ECC_RUNTIME_READY_NEEDS_PROJECT_TRUST_AND_BRANCH_SWITCH

Branch target: `machine-v3-research`

Verified cloud ECC runtime:
- launcher: `/workspace/ecc-setup/codex-ecc`
- CODEX_HOME: `/workspace/ecc-setup/codex-home`
- `ecc@ecc` v2.2.3 installed and enabled
- 348 unique ECC skills enabled with no read errors
- Codex plugins feature: stable/true
- Codex multi-agent feature: stable/true
- repeatable installation/cache verification: PASS

Remaining runtime setup before failure audit:
1. publish/persist the prepared cloud environment snapshot if the environment UI requires publication;
2. trust `/workspace` in the writable ECC profile so repository-local `/workspace/.codex` config and named project roles can load;
3. switch repository from `medium-term-source-research` to `machine-v3-research` and pull latest;
4. verify project config and named roles are effective;
5. run `agent_control/NEXT_TASK.md` to completion.

ECC hooks remain untrusted and are not required for the failure audit.
No v3 strategy design has been authorized yet.
No paper/live trading is allowed.
