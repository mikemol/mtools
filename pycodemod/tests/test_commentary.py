# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.pycodemod.commentary`: the census, its kinds, its blocks and the gate.

⚑⚑ EVERY READER IS ASKED ABOUT A FILE IT CANNOT READ, beside one it can: an empty result must be
distinguishable from a blind one.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.pycodemod import commentary

if TYPE_CHECKING:
    from pathlib import Path

_MODULE = '''"""Module doc.

⚑ A MODULE NOTE
continues here.
"""


class Box:
    """⚑ A CLASS NOTE."""

    def inner(self) -> None:
        # ⚑ INSIDE `inner` and `--flag`
        if self:
            "⚑ AN IF-BODY STRING IS PAYLOAD"
        print("⚑ PRINTED")


async def later() -> None:
    """⚑ AN ASYNC NOTE."""
'''


def _write(tmp_path: Path, name: str, text: str) -> str:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def _unreadable(tmp_path: Path) -> str:
    path = tmp_path / "latin.py"
    path.write_bytes(b"# \xe9\n")
    return str(path)


def test_a_mark_is_bounded_only_where_it_is_alphanumeric() -> None:
    """⚑⚑ `NB` must not fire inside "UNBALANCED"; `⚑` must still fire with no word boundary."""
    assert commentary.mark_hit("NB", "an NB note")
    assert not commentary.mark_hit("NB", "UNBALANCED")
    assert not commentary.mark_hit("NB", "NBX")
    assert commentary.mark_hit("⚑", "x⚑y")
    assert commentary.mark_hit("⚑NB", "x⚑NB y")
    assert not commentary.mark_hit("⚑NB", "x⚑NBy")
    assert commentary.mark_hit("NB⚑", "x NB⚑y")
    assert not commentary.mark_hit("NB⚑", "xNB⚑y")
    assert not commentary.mark_hit("", "anything")


def test_the_key_is_the_sentence_not_the_bytes() -> None:
    """A re-indented, re-commented line keys to the same sentence."""
    assert commentary.commentary_key("    # ⚑  A   note") == "⚑ A note"
    assert commentary.commentary_key('  """ ⚑ A note') == "⚑ A note"
    assert commentary.commentary_key(":'⚑ A note  ") == "⚑ A note"


def test_the_census_counts_every_marked_line_and_reports_the_unread(tmp_path: Path) -> None:
    """⚑ Marked lines in comments, docstrings and printed strings all count; unread is named."""
    one = _write(tmp_path, "one.py", "# ⚑ same\nx = 1\n    # ⚑ same\nprint('⚑ other')\n")
    empty = _write(tmp_path, "empty.py", "x = 1\n")
    latin = _unreadable(tmp_path)
    paths = [one, empty, latin]
    got = commentary.commentary_census(paths)
    assert got.rows == [commentary.CensusRow(one, 3, 2)]
    assert got.texts == {"⚑ same": [(one, 1), (one, 3)], "print('⚑ other')": [(one, 4)]}
    assert got.nfiles == len(paths)
    assert got.unread == [latin]


def test_the_census_honours_a_widened_mark_set(tmp_path: Path) -> None:
    """A caller's marks replace the default; the default alone does not see them."""
    path = _write(tmp_path, "nb.py", "# NB: read me\n")
    assert commentary.commentary_census([path]).rows == []
    widened = commentary.commentary_census([path], marks=("NB",))
    assert widened.rows == [commentary.CensusRow(path, 1, 1)]


def test_kinds_file_each_mark_where_it_lives(tmp_path: Path) -> None:
    """⚑⚑ Docstrings of module, class and def are documentation; an if-body string is payload."""
    path = _write(tmp_path, "mod.py", _MODULE)
    got = commentary.commentary_kinds([path, _unreadable(tmp_path)])
    assert [h.line for h in got.docstring] == [3, 9, 19]
    assert [h.line for h in got.comment] == [12]
    assert [h.text for h in got.executable] == [
        '⚑ AN IF-BODY STRING IS PAYLOAD"',
        'print("⚑ PRINTED")',
    ]
    assert got.unparsed == []
    assert got.unread == [str(tmp_path / "latin.py")]


def test_kinds_file_an_untokenizable_source_as_unparsed(tmp_path: Path) -> None:
    """A file the tokenizer refuses keeps its marks, under `unparsed`."""
    path = _write(tmp_path, "open.py", 'x = """⚑ never closed\n')
    got = commentary.commentary_kinds([path])
    assert got.unparsed == [commentary.Hit(path, 1, 'x = """⚑ never closed')]
    assert got.comment == []


def test_kinds_skip_a_file_with_no_marks(tmp_path: Path) -> None:
    """An unmarked file, even an untokenizable one, contributes nothing to any kind."""
    path = _write(tmp_path, "open.py", 'x = """never closed\n')
    assert commentary.commentary_kinds([path]) == commentary.Kinds()


def test_scope_index_names_the_innermost_owner() -> None:
    """Nested defs are qualified and win over their parents; module lines have no owner."""
    got = commentary.scope_index(_MODULE)
    assert (got[8], got[12], got[19]) == ("Box", "Box.inner", "later")
    assert 1 not in got
    assert commentary.scope_index("def (:\n") == {}


def test_cited_symbols_are_backticked_flags_and_names() -> None:
    """Backticks cite; bare capitals are emphasis."""
    text = "SEE `--roundtrip`, `-v`, `mod.fn()` and `x` but not SET or `9x`"
    assert commentary.cited_symbols(text) == ["--roundtrip", "-v", "mod.fn()", "x"]


def test_a_block_runs_to_a_blank_a_quote_or_the_next_mark(tmp_path: Path) -> None:
    """⚑⚑⚑ A paragraph is one incident, carrying its owner and its citations."""
    path = _write(tmp_path, "mod.py", _MODULE)
    got = commentary.commentary_blocks([path, _unreadable(tmp_path)])
    assert [(b.start, b.end, b.enclosing) for b in got.found] == [
        (3, 4, None),
        (9, 9, "Box"),
        (12, 13, "Box.inner"),
        (14, 14, "Box.inner"),
        (15, 15, "Box.inner"),
        (19, 19, "later"),
    ]
    assert got.found[0].text == "⚑ A MODULE NOTE continues here."
    assert got.found[2].cited == ["--flag", "inner"]
    assert got.unread == [str(tmp_path / "latin.py")]


def test_consecutive_marks_are_separate_blocks(tmp_path: Path) -> None:
    """A marked line ends the block before it; an unparseable file still yields blocks."""
    path = _write(tmp_path, "two.py", "# ⚑ one\n# ⚑ two\ndef (:\n")
    got = commentary.commentary_blocks([path])
    assert [(b.start, b.end, b.enclosing) for b in got.found] == [(1, 1, None), (2, 3, None)]


def test_the_gate_names_what_a_split_lost_and_where_it_came_from(tmp_path: Path) -> None:
    """⚑ A set difference across a revision; an absent path is listed, not an error."""
    kept = _write(tmp_path, "kept.py", "# ⚑ kept\n# ⚑ new\n")
    sibling = _write(tmp_path, "sibling.py", "# ⚑ moved\n")
    baseline = {"kept.py": "# ⚑ kept\n    # ⚑   moved\n# ⚑ dropped\n"}
    got = commentary.commentary_lost([kept, sibling], tmp_path, baseline.get)
    assert got.lost == ["⚑ dropped"]
    assert got.gained == ["⚑ new"]
    assert (got.n_before, got.n_after) == (3, 3)
    assert got.origins["⚑ dropped"] == ["kept.py"]
    assert got.absent_before == ["sibling.py"]
    assert got.unread == []


def test_the_gate_matches_both_sides_with_one_matcher(tmp_path: Path) -> None:
    """⚑⚑ With mark `NB`, "UNBALANCED" is not a mark before OR after: nothing is lost."""
    path = _write(tmp_path, "a.py", "# UNBALANCED\n# NB kept\n")
    before = {"a.py": "# UNBALANCED\n# NB kept\n"}
    got = commentary.commentary_lost([path], tmp_path, before.get, marks=("NB",))
    assert got.lost == []
    assert (got.n_before, got.n_after) == (1, 1)


def test_the_gate_reports_an_unreadable_file(tmp_path: Path) -> None:
    """A file unreadable NOW is reported, not read as having lost everything silently."""
    latin = _unreadable(tmp_path)
    got = commentary.commentary_lost([latin], tmp_path, {"latin.py": "# ⚑ was\n"}.get)
    assert got.unread == [latin]
    assert got.lost == ["⚑ was"]
