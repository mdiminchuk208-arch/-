"""Run the complete suite while suppressing unsolicited product stdout."""

import contextlib
import os
import sys
import unittest
from pathlib import Path

root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root))
with open(os.devnull, "w") as null, contextlib.redirect_stdout(null):
    suite = unittest.defaultTestLoader.discover(str(root / "tests"))
    result = unittest.TextTestRunner(stream=sys.stderr, verbosity=1).run(suite)
sys.exit(not result.wasSuccessful())
