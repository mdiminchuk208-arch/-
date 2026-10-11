"""Bounded gated continuation; each version/stage gets QA, seal and commit before dependencies."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from build_machine_strategy_improvement_design import CODE as DESIGN_CODE
from commit_machine_research_stage import commit
from machine_strategy_research_io import read, verify_machine
from original_v1_1_financial_data import ROOT
from run_machine_strategy_research import CODE, dest

PYTHON = sys.executable
RUFF = str(Path(sys.executable).with_name("ruff"))
MYPY = str(Path(sys.executable).with_name("mypy"))


def run(command, log):
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w") as stream:
        subprocess.run(
            command, cwd=ROOT, check=True, stdout=stream, stderr=subprocess.STDOUT
        )


def qa(directory, code):
    logs = directory / "qa"
    logs.mkdir(parents=True, exist_ok=True)
    commands = {
        "full_unittest": [[PYTHON, "-m", "unittest", "discover", "-s", "tests", "-v"]],
        "ruff": [
            [RUFF, "check", "src", "--select", "E9,F63,F7,F82"],
            [RUFF, "check", *code],
        ],
        "compile": [[PYTHON, "-m", "compileall", "-q", "src", "tests", "scripts"]],
        "mypy": [[MYPY, "src"]],
        "frozen_parent_resume": [
            [
                PYTHON,
                "scripts/verify_original_strategy_spec_v1_1.py",
                "--resume-existing",
            ]
        ],
    }
    for name, cmds in commands.items():
        with (logs / (name + ".log")).open("w") as stream:
            for command in cmds:
                subprocess.run(
                    command,
                    cwd=ROOT,
                    check=True,
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                )


def stage(version, name):
    directory = dest(version, name)
    if (directory / "freeze_manifest.json").exists():
        verify_machine(directory)
        print("RESUME_FROZEN", version, name, flush=True)
        return
    replay = Path("/tmp") / (
        "machine_" + version.replace(".", "_") + "_" + name + "_final_replay"
    )
    if name == "design":
        command = [
            PYTHON,
            "scripts/build_machine_strategy_improvement_design.py",
            "--version",
            version,
        ]
        code = DESIGN_CODE
        message = "Freeze Machine Strategy " + version + " design"
    else:
        command = [
            PYTHON,
            "scripts/run_machine_strategy_research.py",
            "--version",
            version,
            "--stage",
            name,
        ]
        code = CODE
        message = (
            "PRE_OUTCOME_MACHINE_STRATEGY_" + version.upper().replace(".", "_")
            if name == "pre_outcome"
            else "Freeze Machine Strategy " + version + " financial result"
            if name == "result"
            else "Freeze Machine Strategy " + version + " robustness analysis"
        )
    print("STAGE_BEGIN", version, name, flush=True)
    run(command, Path("/tmp") / ("machine_" + version + "_" + name + "_build.log"))
    run(
        command + ["--replay-output", str(replay)],
        Path("/tmp") / ("machine_" + version + "_" + name + "_replay.log"),
    )
    qa(directory, code)
    run(
        command + ["--validate-replay", str(replay)],
        Path("/tmp") / ("machine_" + version + "_" + name + "_validate.log"),
    )
    run(
        command + ["--seal"],
        Path("/tmp") / ("machine_" + version + "_" + name + "_seal.log"),
    )
    commit(directory, message)
    run(
        command + ["--resume-existing"],
        Path("/tmp") / ("machine_" + version + "_" + name + "_resume.log"),
    )
    run(
        ["git", "push", "origin", "medium-term-source-research"],
        Path("/tmp") / ("machine_" + version + "_" + name + "_push.log"),
    )
    if name == "result":
        m = read(directory / "METRICS.json")
        print(
            "RESULT",
            version,
            {
                k: m[k]
                for k in (
                    "cases",
                    "filled",
                    "CLOSED",
                    "WR_percent",
                    "PF_net",
                    "Expectancy_R",
                    "Net_R_ex_funding",
                    "MaxDD_R",
                )
            },
            flush=True,
        )
    if name == "robustness":
        print(
            "GATE",
            version,
            read(directory / "ROBUSTNESS.json")["failure_reasons"],
            flush=True,
        )
    print("STAGE_END", version, name, flush=True)


def main():
    for version, previous in (("v2.1", "v2"), ("v2.2", "v2.1")):
        if (
            read(dest(previous, "robustness") / "ROBUSTNESS.json")[
                "research_quality_gate"
            ]
            == "PASS"
        ):
            print("NO_IMPROVEMENT_TRIGGER", previous, flush=True)
            break
        for name in ("design", "pre_outcome", "result", "robustness"):
            stage(version, name)


if __name__ == "__main__":
    main()
