# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-wheel check`: one JSON line per artifact, exit 1 if PyPI would refuse any (W1187).

The output is machine-readable on purpose: the publish preflight (W1151) reads these lines as live
facts rather than parsing prose, and a CI log of them is a diffable record of what every dist's
metadata said on the day it was built.

CONSUMED BY: `mikemol.pkgbuild.wheel.main`.
"""

import json
import sys
from collections.abc import Sequence
from pathlib import Path

from mikemol.pkgbuild import metacheck


def run(paths: Sequence[str]) -> int:
    """Check each artifact and print its verdict as one JSON line.

    Returns:
        0 when every artifact is clean, else 1.

    """
    verdicts = [metacheck.verdict(Path(p)) for p in paths]
    sys.stdout.writelines(json.dumps(v, sort_keys=True) + "\n" for v in verdicts)
    return 0 if all(v["ok"] for v in verdicts) else 1
