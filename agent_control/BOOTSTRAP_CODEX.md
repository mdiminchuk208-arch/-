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

## 2. ECC availability
If the Codex CLI supports native plugins, check:

```bash
codex plugin list --json
```

If ECC is not registered and marketplace/plugin commands are supported, install from the canonical repository:

```bash
codex plugin marketplace add affaan-m/ECC
codex plugin add ecc@ecc
codex plugin list --json
```

If native plugin support is unavailable, DO NOT block the research task. Continue using the repository-local `.codex` roles, `.agents/skills`, and `AGENTS.md`. Do not use legacy sync unless specifically needed and reviewed.

Do not copy secrets or user credentials into the repository.

## 3. Multi-agent workflow
Use project roles when available:
- `strategy_explorer` for frozen evidence and failure mechanisms;
- `execution_auditor` for LONG/SHORT symmetry and accounting/execution bugs;
- `backtest_reviewer` for independent QA and anti-overfit review;
- `strategy_designer` only after failure audit freeze and only if the evidence justifies v3 design.

## 4. Immediate task
Execute `agent_control/NEXT_TASK.md` completely.

Do NOT design v3 before the failure audit is complete and frozen.
Do NOT alter frozen v2/v2.1/v2.2 artifacts.
Do NOT enable paper/live trading.

## 5. Completion contract
Before stopping:
- create the required failure-audit artifacts;
- run deterministic QA/replay checks;
- update `agent_control/STATUS.md` and `agent_control/CURRENT_STATE.md`;
- commit and push to `machine-v3-research`;
- record the final commit SHA, key findings, unresolved risks, and whether a v3 design is justified.
