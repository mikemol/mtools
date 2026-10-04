# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.pycodemod.relations`: which relations a SQL string reads and writes.

Transcribed from substrate's selftest arms (`--relname`, the read/write split, `sql_kind`). Every
case is a DISCRIMINATION, not a hit: asserting only that `node` is found would pass the substring
matcher this replaces, so each fixture plants a near-miss on purpose. Synthetic strings only. The
private helpers (lexer, paren matcher, alias skipper, CTE finder) are witnessed THROUGH the public
readers, with inputs that take each of their branches.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.pycodemod import relations

if TYPE_CHECKING:
    from pathlib import Path

_STMT = (
    "WITH r AS (SELECT 1 AS id) INSERT INTO dec_root (root) "
    "SELECT r.id FROM r JOIN dec_node n ON n.id = r.id "
    "JOIN dec_ref f ON f.head = n.head JOIN core_decoded c ON c.core_id = f.core_id"
)
_RECURSIVE = (
    "WITH RECURSIVE reach(n) AS (SELECT 1 UNION SELECT nc.child_id "
    "FROM node_child nc JOIN reach r ON nc.node_id=r.n) SELECT n FROM reach"
)
_DELETE = (
    "DELETE FROM core_decoded c WHERE EXISTS ("
    "SELECT 1 FROM core_decoded_shadow s WHERE s.core_id = c.core_id)"
)
_SELF_INSERT = (
    "INSERT INTO dec_val (id, v) SELECT n.id, n.v FROM dec_node n "
    "WHERE NOT EXISTS (SELECT 1 FROM dec_val v WHERE v.id = n.id)"
)
_SHIMS = 'X = _T("node", "node_id")\nY = "node precedes node_atom"\nZ = ["node_child"]\n'
_LEXED = "SELECT 'a FROM b' /* FROM c */ -- FROM d\n FROM \"e\""
_COLUMN_LISTED_CTES = "WITH a AS (SELECT 1), B (x, y) AS (SELECT 2, 3) SELECT 1 FROM a, b, c"
_ALIASED = "SELECT 1 FROM a AS x (c1, c2), b y, c WHERE 1"


def test_a_from_target_is_a_relation_and_a_longer_name_is_not() -> None:
    """The first discrimination: `node` is found in `FROM node` and not in `FROM node_child`."""
    assert "node" in relations.sql_relnames("SELECT * FROM node WHERE x=1")
    assert "node" not in relations.sql_relnames("SELECT * FROM node_child")


def test_an_alias_spelled_like_a_relation_is_not_one() -> None:
    """`FROM obs_node node` names `obs_node` once; a word-boundary regex reports `node` twice."""
    assert relations.sql_relnames("SELECT node.id FROM obs_node node") == {"obs_node"}


def test_a_join_target_is_a_relation() -> None:
    """A JOIN introduces one relation, beside the FROM's."""
    assert relations.sql_relnames("SELECT 1 FROM a JOIN b ON b.i=a.i") == {"a", "b"}


def test_a_recursive_cte_name_is_not_a_relation_but_its_base_table_is() -> None:
    """The CTE name appears in a FROM position inside its own definition and is still excluded."""
    assert relations.sql_relnames(_RECURSIVE) == {"node_child"}


def test_plain_and_column_listed_ctes_are_both_excluded() -> None:
    """`X AS (` and `X (cols) AS (` are the only CTE signatures; the unbound `c` remains."""
    assert relations.sql_relnames(_COLUMN_LISTED_CTES) == {"c"}


def test_a_relation_inside_a_derived_table_is_found() -> None:
    """A derived table is recursed into, not skipped wholesale."""
    got = relations.sql_relnames("SELECT count(*) FROM (SELECT n.core_id FROM obs_node n) d")
    assert "obs_node" in got


def test_an_unbalanced_derived_table_is_closed_by_the_bound() -> None:
    """A missing `)` ends the group at the end of the tokens instead of at a wrong paren."""
    assert relations.sql_relnames("SELECT * FROM (SELECT x FROM t") == {"t"}


def test_from_inside_an_expression_names_no_relation() -> None:
    """`EXTRACT(EPOCH FROM ts)` is an expression scope; only the outer FROM is a relation."""
    assert relations.sql_relnames("SELECT extract(epoch FROM ts) FROM event") == {"event"}


def test_is_distinct_from_names_no_relation() -> None:
    """`IS [NOT] DISTINCT FROM` is not a relation introducer; `SELECT DISTINCT x FROM t` is."""
    not_distinct = "SELECT 1 FROM core_decoded c WHERE c.dec IS NOT DISTINCT FROM s.dec"
    assert relations.sql_relnames(not_distinct) == {"core_decoded"}
    assert relations.sql_relnames("SELECT 1 FROM obs o WHERE o.v IS DISTINCT FROM p.v") == {"obs"}
    assert relations.sql_relnames("SELECT DISTINCT x FROM t") == {"t"}


def test_a_subquery_nested_in_an_expression_still_counts() -> None:
    """The scope is decided per paren by its first token, so the nested SELECT re-enters it."""
    assert "t" in relations.sql_relnames("SELECT coalesce((SELECT max(x) FROM t), 0) FROM u")


def test_a_table_function_is_not_a_stored_relation() -> None:
    """The trailing `(` tells `generate_series(1,3)` from a relation in a FROM position."""
    assert relations.sql_relnames("SELECT * FROM generate_series(1,3) g") == set()


def test_write_positions_name_their_target() -> None:
    """INSERT INTO (with a column list), UPDATE and DROP TABLE all name the relation they hit."""
    got = (
        relations.sql_relnames("INSERT INTO terms (a) VALUES (1)")
        | relations.sql_relnames("UPDATE core_fp SET mtime=1")
        | relations.sql_relnames("DROP TABLE IF EXISTS obs_node")
    )
    assert got == {"terms", "core_fp", "obs_node"}


def test_a_quoted_dotted_name_is_the_last_part_lowercased() -> None:
    """`FROM "Main"."Node"` is the relation `node`, schema qualifier dropped."""
    assert relations.sql_relnames('SELECT 1 FROM "Main"."Node" n') == {"node"}


def test_a_doubled_quote_in_a_quoted_name_is_one_quote() -> None:
    """The lexer keeps a quoted identifier whole and the name unquotes it."""
    assert relations.sql_relnames('SELECT 1 FROM "a""b"') == {'a"b'}


def test_comments_and_strings_hide_keywords_from_the_lexer() -> None:
    """A comment hides a FROM; a string holds one without being read as it."""
    assert relations.sql_relnames(_LEXED) == {"e"}


def test_aliases_are_skipped_with_their_column_lists() -> None:
    """`AS x (c1, c2)`, a bare alias, and a keyword that is no alias all leave the list intact."""
    assert relations.sql_relnames(_ALIASED) == {"a", "b", "c"}
    assert relations.sql_relnames("SELECT 1 FROM a AS, b") == {"a", "b"}


def test_a_delete_target_is_a_write_and_not_also_read() -> None:
    """DELETE's target follows `FROM`, the token that introduces every read."""
    writes, reads = relations.sql_rw(_DELETE)
    assert writes == {"core_decoded"}
    assert reads == {"core_decoded_shadow"}


def test_an_insert_target_may_also_be_read() -> None:
    """The self-terminating rung idiom reads what it writes; the sets are not made disjoint."""
    writes, reads = relations.sql_rw(_SELF_INSERT)
    assert writes == {"dec_val"}
    assert reads == {"dec_node", "dec_val"}


def test_an_update_target_is_a_write_and_its_from_is_a_read() -> None:
    """UPDATE ... FROM splits the two roles in one statement."""
    got = relations.sql_rw("UPDATE core_fp SET mtime = o.mtime FROM obs o WHERE o.id = core_fp.id")
    assert got == ({"core_fp"}, {"obs"})


def test_a_plain_select_writes_nothing_and_drop_table_reads_nothing() -> None:
    """The two empty halves."""
    assert relations.sql_rw("SELECT 1 FROM event e JOIN obs o ON o.id = e.id") == (
        set(),
        {"event", "obs"},
    )
    assert relations.sql_rw("DROP TABLE IF EXISTS obs_node") == ({"obs_node"}, set())


def test_writes_and_reads_are_exactly_the_relnames_and_a_cte_is_in_neither() -> None:
    """The projection identity: the three views cannot drift apart."""
    writes, reads = relations.sql_rw(_STMT)
    assert writes | reads == relations.sql_relnames(_STMT)
    assert "r" not in writes | reads
    assert relations.sql_rel_roles(_STMT) == {(n, "w") for n in writes} | {(n, "r") for n in reads}


def test_the_head_is_depth_aware() -> None:
    """A leading CTE or a column list does not hide the statement's own head."""
    assert relations.sql_kind("WITH r AS (SELECT 1) INSERT INTO t (a) SELECT 1 FROM r") == "insert"
    assert relations.sql_kind(_DELETE) == "delete"
    assert relations.sql_kind("INSERT INTO dec_val (id, v) SELECT 1, 2") == "insert"
    assert relations.sql_kind("SELECT 1 FROM event") == "select"
    assert not relations.sql_kind("not a statement")


def test_is_sql_is_judged_by_a_parser_not_a_head_keyword() -> None:
    """Prose that clears the head test fails to parse; an absent schema and a placeholder pass."""
    assert not relations.is_sql("WITH RECURSIVE +")
    assert not relations.is_sql("")
    assert not relations.is_sql("node precedes node_atom")
    assert not relations.is_sql("SELECT FROM WHERE")
    assert relations.is_sql("SELECT * FROM node_that_is_not_there")
    assert relations.is_sql("DELETE FROM obs WHERE core_id = %s")
    assert relations.is_sql("  SELECT 1;")


def test_the_shim_spelling_is_found_as_a_name_and_prose_containing_it_is_not(
    tmp_path: Path,
) -> None:
    """Exact equality, not substring: `node precedes node_atom` and `node_child` are not hits."""
    path = tmp_path / "shim.py"
    path.write_text(_SHIMS, encoding="utf-8")
    got = relations.relname_sites([str(path)], "node")
    assert [(r.kind, r.line, r.role, r.value) for r in got.rows] == [("name", 1, "arg", "node")]
    assert got.skipped == []


def test_a_sql_literal_and_its_shim_spelling_are_both_sites(tmp_path: Path) -> None:
    """One question, two spellings; a docstring is never a site, and sites sort by line."""
    path = tmp_path / "both.py"
    path.write_text(
        '"""SELECT * FROM node."""\n'
        'RELS = ("node",)\n'
        'QUERY = "SELECT n.id FROM obs_node n JOIN node ON node.id = n.id"\n'
        'OTHER = "SELECT * FROM node_child"\n',
        encoding="utf-8",
    )
    got = relations.relname_sites([str(path)], "node")
    assert [(r.line, r.kind, r.role) for r in got.rows] == [
        (2, "name", "decl"),
        (3, "sql", "other"),
    ]


def test_relname_sites_reports_the_files_it_could_not_read(tmp_path: Path) -> None:
    """A skipped file is returned, not swallowed."""
    bad = tmp_path / "bad.py"
    bad.write_text("def (:\n", encoding="utf-8")
    got = relations.relname_sites([str(bad), str(tmp_path / "absent.py")], "node")
    assert got.rows == []
    assert [s.why for s in got.skipped] == ["unparseable", "unreadable"]


@pytest.mark.parametrize("text", ["", "   ", "-- only a comment"])
def test_an_empty_statement_references_nothing(text: str) -> None:
    """The degenerate inputs give the empty answer from every public reader."""
    assert relations.sql_rel_roles(text) == set()
    assert relations.sql_rw(text) == (set(), set())
    assert not relations.sql_kind(text)
