# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `docshape`: it splits what it can, refuses what it cannot, and keeps every word.

W1044. ⚑ EVERY SPLIT IS CHECKED AGAINST THE DOCSTRING'S WORDS: the parsed docstring's words before
and after must be identical, so a split that dropped or reordered text fails whatever its layout.
"""

from __future__ import annotations

import ast

from mikemol.pycodemod import docshape

_NARROW = 60
_DOCSTRINGS_IN_THE_FILE = 3
_TAIL = "\n\n    Returns:\n        nothing.\n\n    " + '"' * 3


def _words(source: str) -> list[list[str]]:
    """Read every docstring's words, in tree order.

    Returns:
        one word list per documented module, class or function.

    """
    tree = ast.parse(source)
    return [
        (ast.get_docstring(node, clean=False) or "").split()
        for node in ast.walk(tree)
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    ]


def _split(source: str) -> str:
    """Plan a file, require that no word moved, and return the candidate.

    Returns:
        the planned text.

    """
    planned = docshape.plan(source)
    assert _words(planned.text) == _words(source)
    return planned.text


def test_a_two_line_paragraph_splits_at_its_first_sentence_end() -> None:
    """The summary takes the first sentence; the rest follows a blank line."""
    source = 'def f() -> None:\n    """Do the thing here.\n    Then the other thing too.\n    """\n'
    assert _split(source) == (
        'def f() -> None:\n    """Do the thing here.\n\n    Then the other thing too.\n    """\n'
    )


def test_a_summary_on_the_second_line_is_split_in_place() -> None:
    """A docstring that opens with a bare quote keeps its opening line."""
    source = 'def f() -> None:\n    """\n    One. Two\n    three.\n    """\n'
    assert _split(source) == 'def f() -> None:\n    """\n    One.\n\n    Two three.\n    """\n'


def test_a_closing_quote_after_the_last_word_stays_there() -> None:
    """The remainder's last line takes the closing quote when the paragraph ended the docstring."""
    source = 'def f() -> None:\n    """First.\n    Second."""\n'
    assert _split(source) == 'def f() -> None:\n    """First.\n\n    Second."""\n'


def test_later_paragraphs_are_untouched() -> None:
    """Only the first paragraph changes; what follows the blank line is byte-for-byte."""
    source = 'def f() -> None:\n    """A. B\n    c.\n\n    Returns:\n        nothing.\n\n    """\n'
    assert _split(source).endswith(_TAIL + "\n")


def test_a_correct_docstring_is_left_alone_and_nothing_is_counted() -> None:
    """A summary already followed by a blank line, and a one-line docstring, plan no change."""
    source = (
        'def f() -> None:\n    """Summary.\n\n    More.\n    """\n\n\n'
        'def g() -> None:\n    """One."""\n'
    )
    planned = docshape.plan(source)
    assert (planned.text, planned.changes, planned.worklist) == (source, 0, ())


def test_the_remainder_is_wrapped_at_the_width() -> None:
    """A long remainder breaks into lines no wider than the width, indent included."""
    words = " ".join(["word"] * 40)
    source = f'def f() -> None:\n    """Head.\n    {words}\n    """\n'
    planned = docshape.plan(source, _NARROW)
    assert planned.changes == 1
    assert all(len(line) <= _NARROW for line in planned.text.splitlines())
    assert _words(planned.text) == _words(source)


def test_a_backslash_refuses_the_paragraph() -> None:
    """Joining lines around a backslash could change meaning, so it is a worklist row."""
    source = 'def f() -> None:\n    """Head \\\n    tail. More.\n    """\n'
    planned = docshape.plan(source)
    assert (planned.text, planned.changes) == (source, 0)
    assert planned.worklist[0][1] == "f"
    assert "backslash" in planned.worklist[0][2]


def test_an_indented_or_bulleted_continuation_refuses() -> None:
    """Layout that carries meaning (a list, a doctest, a code block) is never joined."""
    bullet = 'def f() -> None:\n    """Head line\n    - item one\n    - item two\n    """\n'
    indented = 'def g() -> None:\n    """Head line\n        code here\n    """\n'
    for source in (bullet, indented):
        planned = docshape.plan(source)
        assert (planned.text, planned.changes) == (source, 0)
        assert "indented or opens a bullet" in planned.worklist[0][2]


def test_a_paragraph_with_no_split_point_is_a_worklist_row() -> None:
    """One sentence over two lines, with no colon, has nowhere to split."""
    source = 'def f() -> None:\n    """A single sentence\n    over two lines.\n    """\n'
    planned = docshape.plan(source)
    assert (planned.text, planned.changes) == (source, 0)
    assert "no sentence end" in planned.worklist[0][2]


def test_a_colon_is_the_fallback_split_point_and_a_dash_is_not() -> None:
    """With no sentence end that leaves a remainder, ': ' splits; ' - ' would drop the dash."""
    dash = 'def f() -> None:\n    """Name - what it does\n    and more.\n    """\n'
    colon = 'def g() -> None:\n    """Name: what it does\n    and more.\n    """\n'
    split_colon = 'def g() -> None:\n    """Name:\n\n    what it does and more.\n    """\n'
    assert _split(colon) == split_colon
    assert docshape.plan(dash).changes == 0


def test_a_summary_wider_than_the_width_is_refused() -> None:
    """The verb never trades D205 for E501."""
    sentence = " ".join(["long"] * 30) + "."
    source = f'def f() -> None:\n    """{sentence}\n    More text.\n    """\n'
    planned = docshape.plan(source, _NARROW)
    assert (planned.text, planned.changes) == (source, 0)
    assert "over" in planned.worklist[0][2]


def test_methods_classes_and_the_module_are_all_planned_bottom_up() -> None:
    """Several docstrings in one file are split in one pass, and the words all survive."""
    source = (
        '"""Module head.\nMore module.\n"""\n\n\n'
        'class K:\n    """Class head.\n    More class.\n    """\n\n'
        '    def m(self) -> None:\n        """Method head.\n        More method.\n        """\n'
    )
    planned = docshape.plan(source)
    assert planned.changes == _DOCSTRINGS_IN_THE_FILE
    assert _words(planned.text) == _words(source)
    assert planned.text.count("\n\n") > source.count("\n\n")


def test_a_second_pass_changes_nothing() -> None:
    """The planner is idempotent: its own output plans no further change."""
    source = 'def f() -> None:\n    """Head.\n    Tail words.\n    """\n'
    once = docshape.plan(source).text
    again = docshape.plan(once)
    assert (again.text, again.changes) == (once, 0)


def test_a_file_that_does_not_parse_is_returned_with_a_row() -> None:
    """A syntax error is a worklist row, never a traceback."""
    planned = docshape.plan("def (:\n")
    assert (planned.text, planned.changes, planned.worklist) == (
        "def (:\n",
        0,
        ((0, "<file>", "does not parse"),),
    )


def test_a_raw_prefix_and_single_quotes_are_kept() -> None:
    """The opening prefix and quote style are carried through unchanged."""
    source = "def f() -> None:\n    r'''Head.\n    Tail.\n    '''\n"
    assert _split(source) == "def f() -> None:\n    r'''Head.\n\n    Tail.\n    '''\n"
