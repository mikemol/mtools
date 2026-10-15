# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The frontier walk carried inside pathsforward is byte-identical to the frontier dist's module.

mtools:W1135. ⚑ A COPY IS ALLOWED ONLY WHILE IT CANNOT DRIFT: pathsforward is installed on its own
and cannot import a sibling dist, so `frontier_walk.py` is a generated copy of
`mikemol.frontier.walk`, and this test fails the gate when the two differ. Refresh it with
`cp frontier/src/mikemol/frontier/walk.py pathsforward/src/mikemol/pathsforward/frontier_walk.py`.

⚑ OFF THE CHECKOUT THE TEST SKIPS, WITH ITS REASON (W1227): the gate names the original through
`FRONTIER_WALK` and there a missing file is a failure; from a built sdist, with no sibling
checkout and no variable, there is nothing to compare against, which is a fact about where the
test runs and not a drift.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

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
    if not os.environ.get("FRONTIER_WALK") and not original.is_file():
        pytest.skip("no sibling frontier checkout and FRONTIER_WALK is unset: not a checkout")
    assert original.is_file(), original
    assert _COPY.read_bytes() == original.read_bytes()
