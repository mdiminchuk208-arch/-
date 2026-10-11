# Bootstrap Codex for Crypto Bot

Work only on branch `machine-v3-research`.

## 1. Read project control
Read in this order:
1. `AGENTS.md`
2. `.codex/config.toml`
3. `.agents/skills/crypto-strategy-research/SKILL.md`
4. `agent_control/OBJECTIVE.md`
5. `agent_control/CURRENT_STATE.md`
6. `agent_control/NEXT_TASK.md`
7. `agent_control/STATUS.md`

## 2. Verified ECC runtime
The stock cloud Codex home is read-only and cannot persist native plugin installation.
Use the verified writable ECC profile instead:

- launcher: `/workspace/ecc-setup/codex-ecc`
- CODEX_HOME: `/workspace/ecc-setup/codex-home`
- ECC plugin: `ecc@ecc` version `2.2.3`
- ECC skills: 348 unique enabled entries verified
- `features.plugins=true`
- `features.multi_agent=true`

The prepared profile passed repeated install/cache/skills checks.
Do not reinstall into `/run/codex-environment/codex-home`.

## 3. Trust requirement
Project-local config at `/workspace/.codex` is currently disabled until `/workspace` is trusted in `/workspace/ecc-setup/codex-home/config.toml`.
Before relying on repository-local role definitions, add `/workspace` as a trusted project using the supported Codex trust configuration for this CLI version, then verify with `config/read` that project-local `.codex` config is effective.

Do not bypass trust globally. Trust only `/workspace` for this project.
ECC hooks remain untrusted unless separately reviewed; do not enable hooks just to continue research.

## 4. Branch and repository state
The old cloud session may still be on `medium-term-source-research` at frozen HEAD `ba65e91c2b1675f48e80ac785bb3adf89d17bb0b`.
Before research:

```bash
git fetch origin
git switch machine-v3-research
git pull --ff-only origin machine-v3-research
```

Confirm the working tree is clean and branch is exactly `machine-v3-research`.

## 5. Multi-agent workflow
After trust verification, use these project roles when available:
- `strategy_explorer` — frozen evidence and failure mechanisms
- `execution_auditor` — LONG/SHORT symmetry, accounting and execution bugs
- `backtest_reviewer` — independent QA and anti-overfit review
- `strategy_designer` — only after failure-audit freeze and only if evidence justifies v3 design

ECC skills may supplement these roles, especially verification, TDD/evals, security, and research workflows.

## 6. Immediate task
Execute `agent_control/NEXT_TASK.md` completely.

Do NOT design v3 before the failure audit is complete and frozen.
Do NOT alter frozen v2/v2.1/v2.2 artifacts.
Do NOT enable paper/live trading.
Do NOT use private exchange APIs.

## 7. Completion contract
Before stopping:
- create the required failure-audit artifacts;
- run deterministic QA/replay checks;
- update `agent_control/STATUS.md` and `agent_control/CURRENT_STATE.md`;
- commit and push to `machine-v3-research`;
- record the final commit SHA, key findings, unresolved risks, and whether a v3 design is justified.
