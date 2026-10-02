# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Put the distribution root on sys.path so tests/test_capture.py can import differential/ (W193).

⚑ Every runner reaches it the same way: the host pytest, //pycodemod:test_capture, :venv and
:mutants each run with a different cwd, and only this file's own location is common to all.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
