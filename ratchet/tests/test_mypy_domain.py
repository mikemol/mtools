# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The ratchet's mypy domain, as a cached bazel test instead of a mutate-in-place witness (W1711).

⚑ THE DOMAIN WITNESS PROVED TWO THINGS ABOUT `//ratchet:mypy`, AND EACH IS NOW ITS OWN CHEAP ARM.
(1) A content change to the transitive module `state.py` reaches the mypy action: it was shown by
planting bytes in the tracked file and re-running bazel, which no sandbox can do. The same fact is
stated by the graph itself: `deps(//ratchet:mypy)` lists every file the action declares, so the
victim being in that list IS the reachability, read from a `genquery` whose output bazel caches and
reruns only when the graph changes. (2) A defect planted in an imported module reaches the
importer's verdict: shown here by running mypy over a copy, green before the plant and red after.

⚑ THE QUERY IS A FILE THE BUILD HANDS IN (`MYPY_DOMAIN`), not a call to bazel, so no nested bazel
runs in the sandbox. ⚑ AND THE CONTROL IS A FILE THE DOMAIN SHOULD NOT HOLD: a check that finds
everything proves nothing, so `README.md`, which mypy does not read, must be absent.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

DOMAIN_ENV = "MYPY_DOMAIN"
VICTIM = "//ratchet:src/mikemol/ratchet/state.py"
OUTSIDE = "//ratchet:README.md"
TIMEOUT_S = 300
GOOD = "def value() -> int:\n    return 1\n"
BAD = 'def value() -> int:\n    return "not an int"\n'
USER = "from lib import value\n\nx: int = value()\n"


def _domain() -> set[str]:
    return set(Path(os.environ[DOMAIN_ENV]).read_text(encoding="utf-8").split())


def _mypy(directory: Path) -> int:
    done = subprocess.run(
        [sys.executable, "-m", "mypy", "--strict", "user.py"],
        cwd=directory,
        capture_output=True,
        check=False,
        timeout=TIMEOUT_S,
    )
    return done.returncode


# ⚑ THE TWO QUERY ARMS RUN WHERE BAZEL HANDS THE FILE IN AND NOWHERE ELSE: the pre-commit's plain
# `pytest` of this dist has no genquery output, and a KeyError there refused W1711's gate. The
# third arm needs no file and runs everywhere.
needs_query = pytest.mark.skipif(
    DOMAIN_ENV not in os.environ, reason="the genquery output is handed in by bazel only"
)


@needs_query
def test_the_transitive_victim_is_in_the_mypy_domain() -> None:
    """Arm 1: a change to `state.py` reaches the action, because the graph declares it."""
    assert VICTIM in _domain()


@needs_query
def test_a_file_mypy_does_not_read_is_not_in_the_domain() -> None:
    """The control: the query holds not every label, so holding the victim means something."""
    assert OUTSIDE not in _domain()


def test_a_defect_planted_in_an_imported_module_reaches_the_importers_verdict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Arm 2: green over the copy before the plant, red after it, in an imported module."""
    monkeypatch.delenv("MYPYPATH", raising=False)
    (tmp_path / "user.py").write_text(USER, encoding="utf-8")
    (tmp_path / "lib.py").write_text(GOOD, encoding="utf-8")
    assert _mypy(tmp_path) == 0
    (tmp_path / "lib.py").write_text(BAD, encoding="utf-8")
    assert _mypy(tmp_path) != 0
