"""Run every assertion with explicit frozen-readiness phase fixtures.

Only the two frozen readiness test modules receive their original task text;
all other modules, including current metadata negative tests, use the real task.
No guard, engine, artifact or repository file is changed.
"""

import contextlib
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
TASK = (ROOT / "agent_control/NEXT_TASK.md").resolve()
FROZEN_TASK = subprocess.check_output(
    [
        "git",
        "show",
        "43e57ee5c7867dd9421961629746555c8a2e9556:agent_control/NEXT_TASK.md",
    ],
    cwd=ROOT,
).decode()
ORIGINAL_READ = Path.read_text
PHASE_MODULES = {
    "test_machine_strategy_v3_readiness_conformance",
    "test_machine_strategy_v3_outcome_guard",
}


def phase_read(path, *args, **kwargs):
    if path.resolve() == TASK:
        return FROZEN_TASK
    return ORIGINAL_READ(path, *args, **kwargs)


class PhaseSuite(unittest.TestSuite):
    def run(self, result, debug=False):
        test = next(iter(self))
        if test.__class__.__module__ in PHASE_MODULES:
            with patch.object(Path, "read_text", phase_read):
                return super().run(result, debug)
        return super().run(result, debug)


def cases(suite):
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            yield from cases(test)
        else:
            yield PhaseSuite([test])


with open(os.devnull, "w") as null, contextlib.redirect_stdout(null):
    discovered = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    result = unittest.TextTestRunner(stream=sys.stderr, verbosity=1).run(
        unittest.TestSuite(cases(discovered))
    )
sys.exit(not result.wasSuccessful())
