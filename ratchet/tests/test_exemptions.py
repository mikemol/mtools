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


_TRACKED = ["tests/a.py", "tests/b.py", "tests/c.py", "src/a.py"]
_PER_FILE = """\
[tool.ruff.lint.per-file-ignores]
"tests/a.py" = ["assert", "S101"]
"tests/b.py" = ["assert", "S101"]
"tests/c.py" = ["assert", "S101"]
"""
_COLLAPSED = """\
[tool.ruff.lint.per-file-ignores]
"tests/*.py" = ["assert", "S101"]
"""
_NOTHING = """\
[tool.ruff.lint.per-file-ignores]
"zzz/*.py" = ["assert"]
"src/a.py" = ["assert"]
"""
_SIX = 6
_TWO = 2


def test_collapsing_entries_into_a_glob_does_not_change_the_count() -> None:
    """W2387: three files with two rules each is six, and so is one glob matching those three."""
    assert exemptions.count(_PER_FILE, _TRACKED) == _SIX
    assert exemptions.count(_COLLAPSED, _TRACKED) == _SIX
    assert exemptions.count(_COLLAPSED) == _TWO


def test_a_glob_matching_nothing_is_not_free_and_a_plain_key_counts_once() -> None:
    """At least one pair per glob key; a key with no glob character is one pair per rule."""
    assert exemptions.count(_NOTHING, _TRACKED) == _TWO


def test_a_glob_key_head_did_not_have_is_named_and_one_it_had_is_not() -> None:
    """The house `tests/*` stays when HEAD already has it; unread on either side is None."""
    assert exemptions.new_globs(_PER_FILE, _COLLAPSED) == ["tests/*.py"]
    assert exemptions.new_globs(_COLLAPSED, _COLLAPSED) == []
    assert exemptions.new_globs(_PER_FILE, _PER_FILE) == []
    assert exemptions.new_globs("[tool.ruff", _COLLAPSED) is None
    assert exemptions.new_globs(_COLLAPSED, '[tool]\nruff = "x"\n') is None


def test_the_exemption_entries_are_exactly_the_pairs_the_count_counts() -> None:
    """W2306 slice 2: the list is as long as the count, a glob names each file it matches."""
    for text, tracked in (
        (_PER_FILE, _TRACKED),
        (_COLLAPSED, _TRACKED),
        (_COLLAPSED, None),
        (_NOTHING, _TRACKED),
    ):
        listed = exemptions.entries(text, tracked)
        assert listed is not None
        assert len(listed) == exemptions.count(text, tracked)
    collapsed = exemptions.entries(_COLLAPSED, _TRACKED)
    assert collapsed is not None
    assert {file for file, _rule in collapsed} == {"tests/a.py", "tests/b.py", "tests/c.py"}
    assert exemptions.entries("[tool.ruff", _TRACKED) is None
