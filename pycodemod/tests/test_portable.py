# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for portable: an injected probe judges SQL literals; no database is opened.

The recorded verdicts are the shapes measured against a live postgres at the origin (2026-08-06):
the sqlite `?` paramstyle, `INSERT OR IGNORE` and `PRAGMA` are syntax errors, `GROUP_CONCAT` and
`LIKELIHOOD` are undefined functions, `rowid` is an undefined column, and an undefined table is a
fact about the store, so it is not a blocker.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pytest

from mikemol.pycodemod import portable as pt

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


class PgSyntaxError(Exception):
    """A scripted engine error: SQLSTATE 42601."""

    sqlstate: str | None = "42601"


class PgUndefinedTableError(Exception):
    """A scripted engine error: SQLSTATE 42P01."""

    sqlstate: str | None = "42P01"


class PgDuplicateTableError(Exception):
    """A scripted engine error: SQLSTATE 42P07."""

    sqlstate: str | None = "42P07"


class PgOperationalError(Exception):
    """A scripted client-side failure that carries no SQLSTATE."""

    sqlstate: str | None = None


@dataclass
class FakeConnection:
    """Records transaction blocks and executed statements; raises scripted errors per statement."""

    script: dict[str, Exception] = field(default_factory=dict)
    log: list[str] = field(default_factory=list)

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Log the begin and end of one transaction block."""
        self.log.append("begin")
        try:
            yield
        finally:
            self.log.append("end")

    def execute(self, text: str) -> None:
        """Log the statement, then raise its scripted error if it has one."""
        self.log.append(text)
        if text in self.script:
            raise self.script[text]


_RECORDED = {
    "SELECT a FROM t WHERE b = ?": pt.Verdict(pt.ERROR, "Syntax"),
    "INSERT OR IGNORE INTO t VALUES (1)": pt.Verdict(pt.ERROR, "Syntax"),
    "SELECT GROUP_CONCAT(a) FROM t": pt.Verdict(pt.ERROR, "UndefinedFunction"),
    "SELECT rowid FROM t": pt.Verdict(pt.ERROR, "UndefinedColumn"),
    "SELECT LIKELIHOOD(1, 0.5)": pt.Verdict(pt.ERROR, "UndefinedFunction"),
    "SELECT a FROM missing": pt.Verdict(pt.ABSENT, "42P01"),
    "SELECT 1": pt.Verdict(pt.OK),
}


def _recorded(text: str) -> pt.Verdict:
    return _RECORDED[text]


def _recorded_probe() -> pt.Probe:
    return pt.Probe(explain=_recorded, execute_ddl=_recorded, reason="")


def _write(tmp_path: Path, name: str, text: str = "x = 1\n") -> str:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def _rows(rows: list[tuple[int, str]]) -> pt.Literals:
    def literals(_path: str) -> list[tuple[int, str]]:
        return rows

    return literals


def test_recorded_engine_verdicts_decide_the_blockers(tmp_path: Path) -> None:
    """⚑⚑ Syntax, undefined function and undefined column block; absent table and ok do not."""
    rows = list(enumerate(_RECORDED, start=1))
    got = pt.portable_sites([_write(tmp_path, "m.py")], _rows(rows), _recorded_probe())
    assert [(b.line, b.blocker) for b in got.blockers] == [
        (1, "Syntax"),
        (2, "Syntax"),
        (3, "UndefinedFunction"),
        (4, "UndefinedColumn"),
        (5, "UndefinedFunction"),
    ]
    assert not got.degraded


def test_an_engine_error_with_no_pattern_reports_a_stated_remedy(tmp_path: Path) -> None:
    """⚑ LIKELIHOOD matches no pattern, so the engine's verdict stands with an honest remedy."""
    rows = [(1, "SELECT LIKELIHOOD(1, 0.5)")]
    got = pt.portable_sites([_write(tmp_path, "m.py")], _rows(rows), _recorded_probe())
    assert [b.remedy for b in got.blockers] == [pt.NO_REMEDY]


def test_the_matching_pattern_supplies_the_remedy_for_an_engine_error(tmp_path: Path) -> None:
    """⚑ The engine decides that GROUP_CONCAT blocks; the pattern list only words the remedy."""
    rows = [(3, "SELECT GROUP_CONCAT(a) FROM t")]
    got = pt.portable_sites([_write(tmp_path, "m.py")], _rows(rows), _recorded_probe())
    assert [b.remedy for b in got.blockers] == ["use string_agg"]


def test_object_existence_states_are_parsed_absent_and_the_rest_are_errors() -> None:
    """⚑⚑ 42P01 is absent under EXPLAIN; 42P07 and 42710 are absent only for DDL; else error."""
    absent = pt.Verdict(pt.ABSENT, "42P01")
    assert pt.classify_state("42P01", "UndefinedTableError", ddl=False) == absent
    dup = pt.classify_state("42P07", "DuplicateTableError", ddl=False)
    assert dup == pt.Verdict(pt.ERROR, "DuplicateTable")
    dup_ddl = pt.classify_state("42P07", "DuplicateTableError", ddl=True)
    assert dup_ddl == pt.Verdict(pt.ABSENT, "42P07")
    obj = pt.classify_state("42710", "DuplicateObjectError", ddl=True)
    assert obj == pt.Verdict(pt.ABSENT, "42710")
    syntax = pt.classify_state("42601", "SyntaxError", ddl=True)
    assert syntax == pt.Verdict(pt.ERROR, "Syntax")


def test_each_explain_runs_in_its_own_transaction_so_one_error_cannot_poison_the_next() -> None:
    """⚑⚑ A rejection inside one block leaves the next statement its own verdict."""
    con = FakeConnection({"EXPLAIN SELECT bad": PgSyntaxError()})
    probe = pt.connection_probe(con.transaction, con.execute)
    assert probe.explain is not None
    assert probe.explain("SELECT bad") == pt.Verdict(pt.ERROR, "PgSyntax")
    assert probe.explain("SELECT 1") == pt.Verdict(pt.OK)
    assert con.log == ["begin", "EXPLAIN SELECT bad", "end", "begin", "EXPLAIN SELECT 1", "end"]


def test_an_undefined_table_under_explain_is_parsed_absent() -> None:
    """⚑ A table the store lacks is a fact about the store, not the SQL."""
    con = FakeConnection({"EXPLAIN SELECT a FROM nope": PgUndefinedTableError()})
    probe = pt.connection_probe(con.transaction, con.execute)
    assert probe.explain is not None
    assert probe.explain("SELECT a FROM nope") == pt.Verdict(pt.ABSENT, "42P01")


def test_ddl_runs_on_the_named_sandbox_handle_and_never_on_the_explain_handle() -> None:
    """⚑⚑ The EXPLAIN handle sees nothing; a duplicate table on the sandbox is success."""
    live = FakeConnection()
    sandbox = FakeConnection({"CREATE TABLE t (a int)": PgDuplicateTableError()})
    probe = pt.connection_probe(live.transaction, live.execute, sandbox.execute)
    assert probe.execute_ddl is not None
    assert probe.execute_ddl("CREATE TABLE t (a int)") == pt.Verdict(pt.ABSENT, "42P07")
    assert probe.execute_ddl("CREATE TABLE u (a int)") == pt.Verdict(pt.OK)
    assert live.log == []
    assert sandbox.log == ["CREATE TABLE t (a int)", "CREATE TABLE u (a int)"]


def test_a_ddl_syntax_error_is_an_error_verdict() -> None:
    """⚑ Only the object-existence states are forgiven for DDL."""
    sandbox = FakeConnection({"PRAGMA x": PgSyntaxError()})
    probe = pt.connection_probe(sandbox.transaction, sandbox.execute, sandbox.execute)
    assert probe.execute_ddl is not None
    assert probe.execute_ddl("PRAGMA x") == pt.Verdict(pt.ERROR, "PgSyntax")


def test_without_a_named_sandbox_handle_no_ddl_judge_exists() -> None:
    """⚑⚑ DDL execution is never defaulted on: no handle named, no judge, nothing run."""
    con = FakeConnection()
    probe = pt.connection_probe(con.transaction, con.execute)
    assert probe.execute_ddl is None
    assert con.log == []


def test_an_error_with_no_sqlstate_is_reraised_not_classified() -> None:
    """⚑ A dropped socket is not a verdict about the SQL, for EXPLAIN and DDL alike."""
    script: dict[str, Exception] = {
        "EXPLAIN SELECT 1": PgOperationalError(),
        "DROP TABLE t": PgOperationalError(),
    }
    con = FakeConnection(script)
    probe = pt.connection_probe(con.transaction, con.execute, con.execute)
    assert probe.explain is not None
    assert probe.execute_ddl is not None
    with pytest.raises(PgOperationalError):
        probe.explain("SELECT 1")
    with pytest.raises(PgOperationalError):
        probe.execute_ddl("DROP TABLE t")


def test_ddl_literals_go_to_the_ddl_judge_and_dml_to_the_explain_judge(tmp_path: Path) -> None:
    """⚑ The head word picks the judge, case-insensitively."""
    seen: list[str] = []

    def explain(text: str) -> pt.Verdict:
        seen.append("explain:" + text)
        return pt.Verdict(pt.OK)

    def ddl(text: str) -> pt.Verdict:
        seen.append("ddl:" + text)
        return pt.Verdict(pt.OK)

    rows = [(1, "SELECT 1"), (2, "create table t (a int)"), (3, "VACUUM")]
    pt.portable_sites([_write(tmp_path, "m.py")], _rows(rows), pt.Probe(explain, ddl))
    assert seen == ["explain:SELECT 1", "ddl:create table t (a int)", "ddl:VACUUM"]


def test_no_probe_degrades_to_pattern_verdicts_and_names_its_reason(tmp_path: Path) -> None:
    """⚑⚑ The positive control: an unreachable probe says why, asserted unconditionally."""
    rows = [(1, "SELECT a FROM t WHERE b = ?"), (2, "SELECT 1"), (3, "PRAGMA foreign_keys")]
    probe = pt.Probe(reason="OperationalError: no store")
    got = pt.portable_sites([_write(tmp_path, "m.py")], _rows(rows), probe)
    assert [(b.line, b.blocker) for b in got.blockers] == [(1, "pattern"), (3, "pattern")]
    assert got.degraded == "OperationalError: no store"


def test_a_reasonless_absent_probe_still_states_that_it_was_not_attempted(tmp_path: Path) -> None:
    """⚑ An absence never reads as a connected zero."""
    got = pt.portable_sites([_write(tmp_path, "m.py")], _rows([]), pt.Probe())
    assert got.degraded == "not attempted"


def test_ddl_with_no_sandbox_is_pattern_ddl_while_dml_is_still_judged(tmp_path: Path) -> None:
    """⚑ A probe that can EXPLAIN but not execute grades DDL by pattern and says `pattern/ddl`."""
    rows = [(1, "PRAGMA foreign_keys"), (2, "SELECT rowid FROM t"), (3, "CREATE TABLE t (a int)")]
    probe = pt.Probe(explain=_recorded)
    got = pt.portable_sites([_write(tmp_path, "m.py")], _rows(rows), probe)
    assert [(b.line, b.blocker) for b in got.blockers] == [
        (1, "pattern/ddl"),
        (2, "UndefinedColumn"),
    ]
    assert not got.degraded


def test_a_generated_file_is_listed_not_judged_and_not_silently_dropped(tmp_path: Path) -> None:
    """⚑ The marker in the first 400 bytes excludes the file from the census and reports it."""
    gen = _write(tmp_path, "g.py", "# GENERATED by a compiler\nx = 1\n")
    got = pt.portable_sites([gen], _rows([(1, "SELECT 1 WHERE a = ?")]), pt.Probe())
    assert got.generated == [gen]
    assert got.blockers == []
    assert gen not in got.core_built


def test_core_func_calls_are_recorded_per_file_with_no_carry_over(tmp_path: Path) -> None:
    """⚑⚑ A Core-only file has no literal blockers and a recorded core_built; a plain one is [].

    The origin kept this on a function attribute, so a loop over files carried one file's value
    into the next; here it is a field of the returned report.
    """
    core = _write(tmp_path, "core.py", "from sa import func\n\nq = func.group_concat(1)\n")
    plain = _write(tmp_path, "plain.py", "x = node.func(1)\n")
    got = pt.portable_sites([core, plain], _rows([]), pt.Probe(explain=_recorded))
    assert got.core_built == {core: [(3, "group_concat")], plain: []}
    assert got.blockers == []


def test_unreadable_undecodable_and_unparseable_files_are_returned_as_skips(
    tmp_path: Path,
) -> None:
    """⚑⚑ Nothing is swallowed: each unjudged file comes back with its reason."""
    missing = str(tmp_path / "nope.py")
    binary = tmp_path / "bin.py"
    binary.write_bytes(b"\xff\xfe\x00bad")
    broken = _write(tmp_path, "broken.py", "def (:\n")
    got = pt.portable_sites([missing, str(binary), broken], _rows([(1, "SELECT ?")]), pt.Probe())
    assert [(s.path, s.why) for s in got.skipped] == [
        (missing, "unreadable"),
        (str(binary), "undecodable"),
        (broken, "unparseable"),
    ]
    assert got.blockers == []


def test_caller_remedies_and_generated_marker_replace_the_defaults(tmp_path: Path) -> None:
    """⚑ Remedy text and the generated marker are operands; the defaults do not leak in."""
    cfg = pt.PortConfig(remedies=((r"\bFOO\b", "use bar"),), generated_marker=r"^//\s*EMITTED")
    emitted = _write(tmp_path, "e.py", "// EMITTED\n")
    plain = _write(tmp_path, "p.py")
    rows = [(1, "SELECT FOO"), (2, "SELECT ?")]
    got = pt.portable_sites([emitted, plain], _rows(rows), pt.Probe(), cfg)
    assert got.generated == [emitted]
    assert [(b.line, b.remedy) for b in got.blockers] == [(1, "use bar")]


def test_blockers_are_ordered_by_path_then_line(tmp_path: Path) -> None:
    """⚑ The report is deterministic whatever order the paths and literals arrive in."""
    b = _write(tmp_path, "b.py")
    a = _write(tmp_path, "a.py")
    rows = [(9, "SELECT ?"), (2, "SELECT ?")]
    got = pt.portable_sites([b, a], _rows(rows), pt.Probe())
    assert [(x.path, x.line) for x in got.blockers] == [(a, 2), (a, 9), (b, 2), (b, 9)]
