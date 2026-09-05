# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Shared fixtures, and the pandoc gate.

⚑⚑ PANDOC IS A SYSTEM BINARY, NOT A WHEEL, so it cannot be a declared dependency and a test
machine may legitimately lack it. The tests that need it are MARKED and skipped with a reason —
never passed silently, because a green run on a machine that could not parse markdown is a
report about the machine wearing a report about the code.

⚑ THE MARKER IS REGISTERED IN `pyproject.toml` AND `--strict-markers` IS ON, so a typo in the
marker name is an error rather than an unregistered no-op. A test claiming a property nothing
enforces reads as covered, which is the same class as a lint rule nobody declared.
"""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


def pytest_runtest_setup(item: pytest.Item) -> None:
    """Skip pandoc-marked tests when the binary is absent, saying so."""
    if item.get_closest_marker("needs_pandoc") and shutil.which("pandoc") is None:
        pytest.skip("pandoc is not installed on this machine (a SYSTEM dependency)")


# ⚑⚑ CALLED, NOT BARE, AND THE DIFFERENCE IS A TYPE. `pytest.fixture` is OVERLOADED — bare, mypy
# cannot pick an overload and the decorated function collapses to `Any`, taking the fixture's
# return type with it. Every consuming test then reads an untyped value while looking perfectly
# annotated. The parentheses select the no-argument overload, and `fixture-parentheses` in
# `pyproject.toml` is where ruff was TOLD rather than suppressed.
#
# ⚑ THIS WAS INVISIBLE UNTIL `mypy_path` MADE THE PACKAGE RESOLVE. While that import failed
# everything here was already `Any`, so one more source of it changed nothing observable.
@pytest.fixture()
def doc(tmp_path: Path) -> Path:
    """Return a factory-free path for a document a test writes itself.

    ⚑ EACH TEST WRITES ITS OWN FIXTURE CONTENT. A shared corpus of sample documents makes a
    failing test require reading a second file to understand, and makes an edit for one test
    silently change another's subject.

    ⚑⚑ AND IT RETURNS RATHER THAN YIELDS, WHICH IS A CLAIM ABOUT LIFETIME. A generator fixture
    announces a teardown phase; this one has none — `tmp_path` owns the cleanup. Yielding said
    there was something to undo here, so a reader looking for the teardown would find nothing
    and could not tell whether it was missing or unnecessary.
    """
    return tmp_path / "doc.md"
