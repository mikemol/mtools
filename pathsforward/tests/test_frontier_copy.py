# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The frontier walk carried inside pathsforward is byte-identical to the frontier dist's module.

mtools:W1135. ⚑ A COPY IS ALLOWED ONLY WHILE IT CANNOT DRIFT: pathsforward is installed on its own
and cannot import a sibling dist, so `frontier_walk.py` is a generated copy of
`mikemol.frontier.walk`, and this test fails the gate when the two differ. Refresh it with
`cp frontier/src/mikemol/frontier/walk.py pathsforward/src/mikemol/pathsforward/frontier_walk.py`.
"""

from __future__ import annotations

import os
from pathlib import Path

_COPY = Path(__file__).parents[1] / "src/mikemol/pathsforward/frontier_walk.py"
_REL = "frontier/src/mikemol/frontier/walk.py"


def _original() -> Path:
    """Find the dist's module: the bazel-declared path, else the checkout beside this dist.

    Returns:
        the path of `mikemol.frontier.walk`.

    """
    named = os.environ.get("FRONTIER_WALK")
    if named:
        return Path(named)
    return Path(__file__).parents[2] / _REL


def test_the_copy_is_byte_identical_to_the_frontier_module() -> None:
    """Both files exist and hold the same bytes."""
    original = _original()
    assert original.is_file(), original
    assert _COPY.read_bytes() == original.read_bytes()
