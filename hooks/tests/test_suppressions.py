# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.hooks.suppressions`: an edit that ADDS a line-scoped suppression.

⚑ EVERY DIRECTIVE HERE IS INSIDE A STRING LITERAL, which is exactly the distinction under test: a
string holding the word is not a comment, so neither this file nor the gate counts it.
"""

from __future__ import annotations

from mikemol.hooks import suppressions

_CLEAN = "x = 1\n"
_NOQA = "x = 1  # noqa: PLR2004\n"
_TYPE_IGNORE = "f(1)  # type: ignore[call-arg]\n"


def test_an_added_noqa_is_reported() -> None:
    """A `# noqa` the edit introduces is reported, with its rule."""
    assert suppressions.added(_CLEAN, _NOQA) == ["noqa: PLR2004"]


def test_an_added_type_ignore_is_reported() -> None:
    """A `# type: ignore` the edit introduces is reported too."""
    assert suppressions.added(_CLEAN, _TYPE_IGNORE) == ["type: ignore[call-arg]"]


def test_existing_debt_does_not_block_an_unrelated_edit() -> None:
    """A directive present before the edit and after it is not an addition: THE DEBT ARM."""
    after = _NOQA + "y = 2\n"
    assert suppressions.added(_NOQA, after) == []


def test_moving_a_directive_is_not_adding_one() -> None:
    """The same directive on a different line is counted once before and once after."""
    before = _NOQA + "y = 2\n"
    after = "y = 2\n" + _NOQA
    assert suppressions.added(before, after) == []


def test_a_second_copy_of_an_existing_directive_is_an_addition() -> None:
    """A count that grows is reported, one entry per extra occurrence."""
    assert suppressions.added(_NOQA, _NOQA + _NOQA) == ["noqa: PLR2004"]


def test_the_word_in_a_string_is_not_a_directive() -> None:
    """`noqa` inside a string literal is not a comment: the tokenizer, not a regex, decides."""
    assert suppressions.added(_CLEAN, 'msg = "# noqa: E501 in a string"\n') == []


def test_file_level_and_other_checker_directives_are_seen() -> None:
    """`ruff: noqa` and `pyright: ignore` are directives as well."""
    after = "# ruff: noqa: E501\nx = 1  # pyright: ignore\n"
    assert suppressions.added(_CLEAN, after) == ["pyright: ignore", "ruff: noqa: E501"]


def test_the_report_names_the_directive_and_the_relief() -> None:
    """The refusal names each added directive and the per-file relief."""
    text = suppressions.report("src/a.py", ["noqa: PLR2004"])
    assert "src/a.py: adds `# noqa: PLR2004`" in text
    assert "per-file-ignores" in text
