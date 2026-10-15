# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Put the distribution root on sys.path so tests/test_capture.py can import differential/ (W193).

⚑ Every runner reaches it the same way: the host pytest, //pycodemod:test_capture, :venv and
:mutants each run with a different cwd, and only this file's own location is common to all.

⚑ AN UNPACKED SDIST HAS NO differential/ (W1232): that tree holds captured cases with host paths
the release privacy judge withholds, so it is not shipped, and the three modules that import it
cannot even be collected there. They are left out of the run when `PKG-INFO` sits at the
distribution root (true only of an sdist) and run everywhere else, the gate and the mutation
sandbox included.
"""

import sys
from pathlib import Path

_DIST = Path(__file__).parent.parent
sys.path.insert(0, str(_DIST))

collect_ignore = (
    ["test_capture.py", "test_funcnames.py", "test_split_differential.py"]
    if (_DIST / "PKG-INFO").is_file()
    else []
)
