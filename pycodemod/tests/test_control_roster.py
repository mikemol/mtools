# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.pycodemod.control_roster`: the roster, the SQL form table, the boundary.

⚑⚑ WHAT IS TRANSCRIBED AND WHAT IS AUTHORED. The origin's selftest arms that need only this unit's
data are carried over: the eight groups, an unclassified site never claims a form, and an early
break over rows is `LIMIT 1 / EXISTS`. The origin's completeness arms (roster minus found, found
minus roster) and its kind arms run the census over a planted fixture; the census is a later
commit, so they travel with it. Every arm marked AUTHORED has no origin: the 36-construct count,
the pair-keyed table closure, the boundary operand and the empty-vocabulary arms. ⚑ THE
SKIPPED-FILE ARM IS NOT HERE: this module reads no file, so there is nothing to skip; it belongs
to the reader's commit.
"""

from __future__ import annotations

import ast

from mikemol.pycodemod import control_roster as cr
from mikemol.pycodemod.storeflow import StoreVocab

_GROUPS = 8
_CONSTRUCTS = 36
_VOCAB = StoreVocab(
    readers=frozenset({"execute", "fetchall"}),
    receivers=frozenset({"con"}),
    connections=frozenset({"con"}),
)
_EMPTY = StoreVocab(frozenset(), frozenset(), frozenset())
_READ = "con.execute('SELECT 1').fetchall()"


def _expr(src: str) -> ast.expr:
    return ast.parse(src, mode="eval").body


def test_all_eight_construct_groups_are_represented() -> None:
    """The roster is reported in eight groups a reader can subtract."""
    assert len(cr.CONSTRUCT_GROUPS) == _GROUPS


def test_the_roster_holds_thirty_six_constructs_with_no_duplicate() -> None:
    """AUTHORED: the headline count (the plan said 41; the origin's roster sums to 36)."""
    assert len(cr.CONSTRUCTS) == _CONSTRUCTS
    assert len(set(cr.CONSTRUCTS)) == _CONSTRUCTS


def test_every_sql_form_key_names_a_roster_construct_and_a_declared_kind() -> None:
    """AUTHORED: a table key outside the roster is a form no census can ever emit."""
    constructs = {construct for construct, _kind in cr.SQL_FORM}
    kinds = {kind for _construct, kind in cr.SQL_FORM}
    assert constructs <= set(cr.CONSTRUCTS)
    assert kinds <= set(cr.CONTROL_KINDS)
    assert set(cr.SQL_FORM_EXIT_ROW) == set(cr.EARLY_EXIT_CONSTRUCTS)
    assert set(cr.EARLY_EXIT_CONSTRUCTS) <= set(cr.CONSTRUCTS)
    assert set(cr.LOOP_CONSTRUCTS) <= set(cr.CONSTRUCTS)


def test_an_unclassified_site_never_claims_a_relational_form() -> None:
    """A guess in the form column is noise; the unknowns are the finding."""
    forms = {
        cr.sql_form(construct, "unclassified", loop_is_row=row)
        for construct in cr.CONSTRUCTS
        for row in (True, False)
    }
    assert forms == {"unknown"}


def test_an_early_break_over_rows_is_limit_one_exists() -> None:
    """The three early exits each carry a form when the loop iterates rows."""
    assert cr.sql_form("break", "early-exit", loop_is_row=True) == "LIMIT 1 / EXISTS"
    assert cr.sql_form("continue", "early-exit", loop_is_row=True) == "WHERE NOT (...)"
    assert cr.sql_form("return-in-loop", "early-exit", loop_is_row=True) == "LIMIT 1"


def test_an_early_exit_outside_a_row_loop_is_unknown() -> None:
    """AUTHORED: the loop's provenance is part of the key, not a property of the exit."""
    forms = {
        cr.sql_form(construct, "early-exit", loop_is_row=False)
        for construct in cr.EARLY_EXIT_CONSTRUCTS
    }
    assert forms == {"unknown"}
    assert cr.sql_form("raise", "early-exit", loop_is_row=True) == "unknown"


def test_external_and_mode_kinds_carry_their_fixed_forms_whatever_the_construct() -> None:
    """AUTHORED: those two kinds are decided by kind alone."""
    external = {cr.sql_form(c, "external", loop_is_row=False) for c in cr.CONSTRUCTS}
    mode = {cr.sql_form(c, "mode-branch", loop_is_row=True) for c in cr.CONSTRUCTS}
    assert external == {cr.EXTERNAL_FORM}
    assert mode == {cr.MODE_FORM}


def test_a_row_branch_and_a_row_iteration_take_their_table_forms() -> None:
    """A pair in the table gets its form; a pair outside it is unknown."""
    assert cr.sql_form("if", "row-branch", loop_is_row=False) == "WHERE"
    assert cr.sql_form("for", "row-iteration", loop_is_row=True).startswith("the SELECT itself")
    assert cr.sql_form("if", "row-iteration", loop_is_row=True) == "unknown"


def test_the_python_boundary_keeps_os_environ_as_configuration() -> None:
    """AUTHORED: `os` is an external root, and `os.environ` is still configuration."""
    boundary = cr.PYTHON_BOUNDARY
    assert "os" in boundary.roots
    assert ("os", "environ") in boundary.mode_dotted
    assert ("sys", "argv") in boundary.mode_dotted
    assert "OSError" in boundary.exceptions


def test_content_addressing_is_not_an_external_root() -> None:
    """AUTHORED: external is a claim about reachability, not purity."""
    assert not {"hashlib", "random", "uuid"} & cr.PYTHON_BOUNDARY.roots
    assert {"open", "print"} <= cr.PYTHON_BOUNDARY.names


def test_a_boundary_is_an_explicit_operand_that_can_be_empty() -> None:
    """AUTHORED: nothing names a default; an empty boundary recognises nothing."""
    empty = cr.Boundary(
        roots=frozenset(),
        names=frozenset(),
        attrs=frozenset(),
        exceptions=frozenset(),
        mode_dotted=frozenset(),
        mode_names=frozenset(),
    )
    assert empty != cr.PYTHON_BOUNDARY
    assert not empty.roots
    assert not empty.mode_dotted


def test_a_loop_over_a_store_read_is_a_row_loop() -> None:
    """A direct read, a row name and a one-hop helper each make the iterable rows."""
    assert cr.is_row_loop(_expr("con.execute('SELECT 1')"), set(), set(), _VOCAB)
    assert cr.is_row_loop(_expr("rows"), {"rows"}, set(), _VOCAB)
    assert cr.is_row_loop(_expr("helper(x)"), set(), {"helper"}, _VOCAB)
    assert not cr.is_row_loop(_expr("xs"), set(), set(), _VOCAB)
    assert not cr.is_row_loop(None, {"rows"}, {"helper"}, _VOCAB)


def test_an_empty_vocabulary_makes_no_loop_a_row_loop_and_every_early_exit_unknown() -> None:
    """AUTHORED: the degenerate census claims no row kinds, and says so as `unknown`."""
    loop = _expr(_READ)
    assert cr.is_row_loop(loop, set(), set(), _VOCAB)
    row = cr.is_row_loop(loop, set(), set(), _EMPTY)
    assert not row
    forms = {
        cr.sql_form(construct, "early-exit", loop_is_row=row)
        for construct in cr.EARLY_EXIT_CONSTRUCTS
    }
    assert forms == {"unknown"}
