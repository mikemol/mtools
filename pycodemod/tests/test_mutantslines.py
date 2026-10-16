# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mutantslines.unapplied`: a declaration whose pattern left its file is named.

⚑ THE CONTROLS: a pattern that still occurs is NOT named (else every line is stale), a comment and
a blank line are skipped, and a malformed or unreadable line is reported rather than passed over.
"""

from __future__ import annotations

from mikemol.pycodemod import mutantslines

_FILES = {"a.py": "except OSError:\n    pass\n"}


def _read(name: str) -> str | None:
    return _FILES.get(name)


def test_a_pattern_that_still_occurs_is_not_named() -> None:
    """The control: an applied declaration yields nothing."""
    assert mutantslines.unapplied("a.py|keep|except OSError:|x|def=f\n", _read) == []


def test_a_pattern_that_left_its_file_is_named() -> None:
    """The case: the text the regex looked for is gone."""
    lines = "a.py|gone|except \\(OSError, ValueError\\):|x|def=f\n"
    assert mutantslines.unapplied(lines, _read) == ["a.py::gone"]


def test_comments_and_blank_lines_are_skipped() -> None:
    """A header is not a declaration."""
    assert mutantslines.unapplied("# note\n\n", _read) == []


def test_a_malformed_line_is_reported() -> None:
    """Four fields is not a declaration the runner can read."""
    assert mutantslines.unapplied("a.py|n|p|r\n", _read) == ["a.py|n|p|r::malformed"]


def test_an_unreadable_file_is_reported() -> None:
    """A file the reader cannot give is named, not treated as applied."""
    assert mutantslines.unapplied("b.py|n|p|r|def=f\n", _read) == ["b.py::n::unreadable"]
