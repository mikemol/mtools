# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A pyproject's per-file exemptions are counted one per (file, rule); unread is never zero (W2138).

⚑ THE CONTROLS: an absent table is a real 0, and text that does not parse, a table that is not a
table, and a file whose rules are not a list each read as None, never as 0.
"""

from mikemol.ratchet import exemptions

_THREE = 3
_TWO_FILES = """\
[tool.ruff.lint.per-file-ignores]
"tests/*" = ["assert", "S101"]
"src/a.py" = ["subprocess-without-shell-equals-true"]
"""


def test_two_files_holding_three_rules_count_three() -> None:
    """One per (file, rule), not one per file."""
    assert exemptions.count(_TWO_FILES) == _THREE


def test_an_absent_table_and_an_empty_one_are_a_real_zero() -> None:
    """The file parsed and holds no exemption."""
    assert exemptions.count("") == 0
    assert exemptions.count("[tool.ruff]\nline-length = 100\n") == 0
    assert exemptions.count("[tool.ruff.lint.per-file-ignores]\n") == 0


_MARK = "# " + "noqa"
_TYPE = "# " + "type: ignore[arg-type]"
_RUFF = "# " + "ruff: ignore[assert]"
_TWO = 2


def test_a_comment_that_begins_a_suppression_counts_and_prose_does_not() -> None:
    """W2140: real COMMENT tokens count; a docstring or string that names one does not."""
    clean = 'x = 1\ny = "a ' + _MARK + ' in a string"\n'
    assert exemptions.suppressions(clean) == 0
    assert exemptions.suppressions(f"x = 1  {_MARK}: E501\n") == 1
    assert exemptions.suppressions(f"a = f(1)  {_TYPE}\nb = 2  {_RUFF}\nc = 3\n") == _TWO
    docstring = '"""Prose that says ' + _MARK + ' is forbidden."""\n'
    assert exemptions.suppressions(docstring) == 0
    assert exemptions.suppressions("# unrelated comment about noqa\n") == 0


def test_a_source_that_does_not_tokenize_is_unread_not_zero() -> None:
    """An unterminated bracket cannot be tokenized, so it reads None."""
    assert exemptions.suppressions("x = (1,\n") is None


def test_text_that_does_not_parse_or_has_the_wrong_shape_is_unread() -> None:
    """None is UNREAD: a broken file must not look like a clean one."""
    assert exemptions.count("[tool.ruff") is None
    assert exemptions.count('[tool]\nruff = "x"\n') is None
    assert exemptions.count('[tool.ruff.lint]\nper-file-ignores = "x"\n') is None
    assert exemptions.count('[tool.ruff.lint.per-file-ignores]\n"a.py" = "assert"\n') is None
