# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.pycodemod.sql`: SQL literals, graded by a caller-supplied executor roster.

Transcribed from substrate's `sql_sites` selftest arms, with synthetic strings. Each case is a
DISCRIMINATION: a grep for a keyword would pass the prose arm, a bare-argument test would fail the
`%` arm, and the origin's `builder` arm passed vacuously, so this one plants a builder call that
HOLDS SQL and fails when the grade is wrong. The private helpers (callee name, argument walk, style
map, statement judge) are witnessed THROUGH `sql_sites`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.pycodemod import relations
from mikemol.pycodemod.sql import SqlConfig, sql_sites

if TYPE_CHECKING:
    from pathlib import Path

_LINES = (
    'LABELS = ["WITH RECURSIVE +", "WITH RECURSIVE (UNION)"]',
    'SCHEMA = "CREATE TABLE modedges (a INTEGER)"',
    "def go(con):",
    '    con.execute("SELECT a FROM modedges")',
    '    QB.run(con, "SELECT b FROM builtq")',
    '    con.execute("DELETE FROM drainq WHERE core_id IN (%s)" % sub)',
    '    execute(con, "SELECT count(*) FROM drainq WHERE core_id = %s" % ph(), (1,))',
    '    other("SELECT c FROM plainq")',
    '    QB.run(con.execute("SELECT d FROM nestq"))',
    '    con.execute("DELETE FROM evq e WHERE e.n = 1 ON CONFLICT")',
    "",
)
_SOURCE = "\n".join(_LINES)
_ROSTER = SqlConfig(
    executors=frozenset({"execute", "rows"}),
    builders=frozenset({"run"}),
)
_EMPTY = SqlConfig(executors=frozenset(), builders=frozenset())


def _file(tmp_path: Path, text: str = _SOURCE) -> str:
    path = tmp_path / "fixture.py"
    path.write_text(text, encoding="utf-8")
    return str(path)


def _grades(tmp_path: Path, ident: str, config: SqlConfig = _ROSTER) -> list[tuple[str, str]]:
    found = sql_sites([_file(tmp_path)], ident, config)
    return sorted((site.style, site.head) for site in found.rows)


def test_a_prose_label_starting_with_a_keyword_is_not_a_site(tmp_path: Path) -> None:
    """`WITH RECURSIVE +` clears a head test; the engine's parser is what rejects it."""
    assert _grades(tmp_path, "RECURSIVE") == []


def test_a_real_statement_is_a_site_and_carries_its_style(tmp_path: Path) -> None:
    """A schema constant is `literal`; the same relation run by an executor is `raw`."""
    assert _grades(tmp_path, "modedges") == [("literal", "CREATE"), ("raw", "SELECT")]


def test_a_builder_call_holding_sql_is_graded_builder(tmp_path: Path) -> None:
    """The origin's builder arm asserted nothing (the call held no SQL); this literal is SQL."""
    assert _grades(tmp_path, "builtq") == [("builder", "SELECT")]


def test_a_builder_grade_needs_the_builder_roster(tmp_path: Path) -> None:
    """With no builders named the same call is a plain `literal`, so the grade is the roster's."""
    config = SqlConfig(executors=frozenset({"execute"}), builders=frozenset())
    assert _grades(tmp_path, "builtq", config) == [("literal", "SELECT")]


def test_an_executor_nested_in_a_builder_wins(tmp_path: Path) -> None:
    """A statement handed to both a builder and an executor is run raw."""
    assert _grades(tmp_path, "nestq") == [("raw", "SELECT")]


def test_a_call_outside_both_rosters_leaves_a_literal(tmp_path: Path) -> None:
    """`other("SELECT ...")` is neither run raw nor built."""
    assert _grades(tmp_path, "plainq") == [("literal", "SELECT")]


def test_a_percent_parameterised_statement_is_a_site_and_raw(tmp_path: Path) -> None:
    """`"... %s" % ph()` is a BinOp inside the argument; `%` is not modulo, the literal is raw."""
    assert _grades(tmp_path, "drainq") == [("raw", "DELETE"), ("raw", "SELECT")]


def test_an_empty_roster_grades_everything_literal(tmp_path: Path) -> None:
    """The roster is an operand: no executors named means nothing is raw."""
    grades = {style for style, _head in _grades(tmp_path, "", _EMPTY)}
    assert grades == {"literal"}


def test_a_statement_sqlite_refuses_needs_a_caller_oracle(tmp_path: Path) -> None:
    """The second judge is supplied, asked only after sqlite refuses, and sees the NULL form."""
    asked: list[str] = []

    def accepts(candidate: str) -> bool:
        asked.append(candidate)
        return "ON CONFLICT" in candidate

    config = SqlConfig(executors=_ROSTER.executors, builders=frozenset(), oracles=(accepts,))
    assert _grades(tmp_path, "evq") == []
    assert _grades(tmp_path, "evq", config) == [("raw", "DELETE")]
    assert "DELETE FROM evq e WHERE e.n = 1 ON CONFLICT" in asked
    assert "SELECT a FROM modedges" not in asked


def test_a_rejecting_oracle_changes_nothing(tmp_path: Path) -> None:
    """An oracle that says no leaves prose and invalid statements out."""
    config = SqlConfig(executors=_ROSTER.executors, builders=frozenset(), oracles=(str.isdigit,))
    assert _grades(tmp_path, "evq", config) == []


def test_the_statement_is_whole_and_whitespace_collapsed(tmp_path: Path) -> None:
    """The full text is kept, not an excerpt; a line break inside it is one space."""
    text = 'Q = """SELECT x\n   FROM wide_relation_name\n   WHERE x > 1"""\n'
    found = sql_sites([_file(tmp_path, text)], "wide", _EMPTY)
    assert [(s.line, s.sql) for s in found.rows] == [
        (1, "SELECT x FROM wide_relation_name WHERE x > 1")
    ]


def test_an_unreadable_file_is_returned_not_dropped(tmp_path: Path) -> None:
    """A syntax error is reported as skipped beside the files that were read."""
    bad = tmp_path / "bad.py"
    bad.write_text("def (:\n", encoding="utf-8")
    found = sql_sites([str(bad), _file(tmp_path)], "modedges", _ROSTER)
    assert [skip.path for skip in found.skipped] == [str(bad)]
    assert [site.style for site in found.rows] == ["literal", "raw"]


def test_statement_text_offers_engines_the_placeholder_free_form() -> None:
    """The shared normaliser: `%s` and `:name` become NULL, a non-head word yields None."""
    assert relations.statement_text("(SELECT %s, :x FROM t)") == "SELECT NULL, NULL FROM t)"
    assert relations.statement_text("hello world") is None
