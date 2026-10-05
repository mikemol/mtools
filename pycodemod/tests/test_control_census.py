# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.pycodemod.control_census`: every control-flow site, typed.

⚑⚑ WHAT IS TRANSCRIBED AND WHAT IS AUTHORED. Transcribed from the origin's `--control` selftest
arms, over the origin's planted-construct fixture kept verbatim (`_FIXTURE`): roster completeness
in both directions, the eight groups, the kind arms (row loop, row-branch beside mode-branch,
comp-if over rows, `with open`, `except OSError`, the subprocess hop, `sys.exit`, yield, a
comprehension over an argument), the early exits and the `LIMIT 1 / EXISTS` form, the mutation
(delete the break and its guard, the count drops by exactly two), the `unknown` column and the
kinds-in-roster arm. The origin's `relalg_sites` blindness arm is not transcribed: it needs a mode
this port does not carry. Arms marked AUTHORED have no origin: the skipped-file arms
(unparseable, unreadable, undecodable), the empty-`StoreVocab` and empty-`Boundary` arms, the
governing-expression arms, the trailing return, the `else` line, `elif`, the equality of a site,
and the ordering over several files. ⚑ The origin has no desync assertion, so there is none to
witness.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.pycodemod.control_census import Site, control_sites
from mikemol.pycodemod.control_roster import (
    CONSTRUCT_GROUPS,
    CONSTRUCTS,
    CONTROL_KINDS,
    PYTHON_BOUNDARY,
    Boundary,
)
from mikemol.pycodemod.referents import referents
from mikemol.pycodemod.storeflow import StoreVocab

if TYPE_CHECKING:
    from pathlib import Path

_GROUPS = 8
_VOCAB = StoreVocab(
    readers=frozenset({"execute", "fetchall"}),
    receivers=frozenset({"con"}),
    connections=frozenset({"con"}),
)
_NO_VOCAB = StoreVocab(readers=frozenset(), receivers=frozenset(), connections=frozenset())
_NO_BOUNDARY = Boundary(
    roots=frozenset(),
    names=frozenset(),
    attrs=frozenset(),
    exceptions=frozenset(),
    mode_dotted=frozenset(),
    mode_names=frozenset(),
)

_FIXTURE = """
import os
import subprocess
import sys

VERBOSE = False


def rows_loop(con, additive, dry_run):
    out = []
    for cid, sym in con.execute("SELECT cid, sym FROM node"):
        if sym is None:
            continue
        if sym == "x":
            break
        if sym == "y":
            return out
        out.append((cid, sym))
    else:
        out.append(None)
    if additive:
        out.sort()
    elif dry_run:
        out = []
    else:
        out = out[:1]
    n = len(out) if additive else 0
    while n > 0:
        n -= 1
    else:
        n = 0
    return out


def guards(con, path, want=None):
    if not path:
        return None
    if VERBOSE:
        print(path)
    assert os.path.exists(path)
    try:
        with open(path, "rb") as fh:
            blob = fh.read()
    except OSError:
        raise ValueError("nope")
    else:
        blob = blob
    finally:
        blob = blob or b""
    rows = con.execute("SELECT a FROM t").fetchall()
    keep = [r for r in rows if r[0] > 0]
    every = all(r[0] for r in rows)
    some = any(r[0] == 1 for r in rows)
    first = next((r for r in rows if r[0]), None)
    filt = filter(lambda r: r[0], rows)
    d = {}
    got = d.get("k", "dflt")
    bare = d.get("k")
    label = want or "unnamed"
    other = want or path
    both = want and path
    match len(rows):
        case 0:
            label = "empty"
        case _:
            label = "some"
    if not rows:
        raise RuntimeError("empty")
    return keep, every, some, first, filt, got, bare, label, other, both, blob


def shell(cmd):
    p = subprocess.run(cmd, capture_output=True)
    if p.returncode:
        sys.exit(1)
    return p.stdout


def gen(con):
    for r in con.execute("SELECT a FROM t"):
        yield r[0]
    yield from con.execute("SELECT b FROM t")


def pure(xs):
    return [x for x in xs if x]
"""
_BREAK_AND_GUARD = '        if sym == "x":\n            break\n'


def _write(tmp_path: Path, src: str, name: str = "case.py") -> str:
    target = tmp_path / name
    target.write_text(src, encoding="utf-8")
    return str(target)


def _sites(tmp_path: Path, src: str = _FIXTURE) -> list[Site]:
    return control_sites([_write(tmp_path, src)], _VOCAB, PYTHON_BOUNDARY).sites


def _keys(sites: list[Site]) -> set[tuple[str, str, str]]:
    return {(s.scope, s.construct, s.kind) for s in sites}


def test_every_construct_in_the_roster_is_found_in_the_fixture(tmp_path: Path) -> None:
    """The roster minus the constructs found is empty: the walker still sees every one."""
    found = {s.construct for s in _sites(tmp_path)}
    assert sorted(set(CONSTRUCTS) - found) == []


def test_the_roster_and_the_fixture_agree_in_both_directions(tmp_path: Path) -> None:
    """The constructs found minus the roster is empty: the walker emits nothing unlisted."""
    found = {s.construct for s in _sites(tmp_path)}
    assert sorted(found - set(CONSTRUCTS)) == []


def test_all_eight_construct_groups_are_represented() -> None:
    """The roster the fixture is checked against has eight groups."""
    assert len(CONSTRUCT_GROUPS) == _GROUPS


def test_a_loop_over_query_rows_is_row_iteration(tmp_path: Path) -> None:
    """`for cid, sym in con.execute(...)` is the SELECT itself."""
    assert ("rows_loop", "for", "row-iteration") in _keys(_sites(tmp_path))


def test_a_branch_on_row_content_is_a_where(tmp_path: Path) -> None:
    """`if sym is None` reads a row name."""
    assert ("rows_loop", "if", "row-branch") in _keys(_sites(tmp_path))


def test_a_branch_on_an_argument_is_a_mode_branch_in_the_same_function(tmp_path: Path) -> None:
    """`if additive` is not SQL at all, beside the row branches of the same function."""
    assert ("rows_loop", "if", "mode-branch") in _keys(_sites(tmp_path))


def test_a_comprehension_guard_over_rows_is_a_where(tmp_path: Path) -> None:
    """`[r for r in rows if r[0] > 0]` filters rows."""
    assert ("guards", "comp-if", "row-branch") in _keys(_sites(tmp_path))


def test_with_open_is_the_external_boundary(tmp_path: Path) -> None:
    """A `with open(...)` is the irreducible half."""
    assert ("guards", "with", "external") in _keys(_sites(tmp_path))


def test_except_oserror_is_external_on_the_type(tmp_path: Path) -> None:
    """The handler body raises a `ValueError`, yet the clause is the boundary's on its type."""
    assert ("guards", "except", "external") in _keys(_sites(tmp_path))


def test_a_branch_one_hop_from_a_subprocess_is_external(tmp_path: Path) -> None:
    """`p = subprocess.run(...)` then `if p.returncode:` names no external module itself."""
    assert ("shell", "if", "external") in _keys(_sites(tmp_path))


def test_sys_exit_is_external_not_work_for_the_engine(tmp_path: Path) -> None:
    """`sys.exit(1)` is an exit construct and is filed external, never as a read."""
    assert ("shell", "exit", "external") in _keys(_sites(tmp_path))


def test_yielding_query_rows_is_row_iteration(tmp_path: Path) -> None:
    """`yield r[0]` over a store cursor is the SELECT's own output."""
    assert ("gen", "yield", "row-iteration") in _keys(_sites(tmp_path))


def test_a_comprehension_over_a_plain_argument_is_not_a_mode_branch(tmp_path: Path) -> None:
    """`[x for x in xs if x]` stays honestly unclassified, in both the loop and the guard."""
    keys = _keys(_sites(tmp_path))
    assert ("pure", "comp-for", "unclassified") in keys
    assert ("pure", "comp-if", "unclassified") in keys


def test_the_early_exits_are_exactly_break_continue_and_return_in_loop(tmp_path: Path) -> None:
    """Of the fixture, only those three constructs are early exits."""
    exits = sorted(s.construct for s in _sites(tmp_path) if s.kind == "early-exit")
    assert exits == ["break", "continue", "return-in-loop"]


def test_an_early_break_over_rows_is_limit_one_exists(tmp_path: Path) -> None:
    """The exit's form depends on the enclosing loop iterating rows."""
    forms = {s.construct: s.sqlform for s in _sites(tmp_path) if s.kind == "early-exit"}
    assert forms["break"] == "LIMIT 1 / EXISTS"


def test_removing_the_break_removes_exactly_the_break_and_its_guard(tmp_path: Path) -> None:
    """The count moves by two: the `break` and the `if` that guards it."""
    before = _sites(tmp_path)
    after = _sites(tmp_path, _FIXTURE.replace(_BREAK_AND_GUARD, ""))
    assert (sum(s.construct == "break" for s in after), len(before) - len(after)) == (0, 2)


def test_an_unclassified_site_never_claims_a_relational_form(tmp_path: Path) -> None:
    """The `unknown` column: a guess there would read like analysis."""
    forms = {s.sqlform for s in _sites(tmp_path) if s.kind == "unclassified"}
    assert forms == {"unknown"}


def test_every_kind_reported_is_in_the_declared_roster(tmp_path: Path) -> None:
    """No site carries a kind outside `CONTROL_KINDS`."""
    assert {s.kind for s in _sites(tmp_path)} - set(CONTROL_KINDS) == set()


def test_an_unparseable_file_comes_back_as_a_skip_not_an_empty_result(tmp_path: Path) -> None:
    """AUTHORED: a syntax error is reported, and contributes no site."""
    bad = _write(tmp_path, "def broken(:\n", "bad.py")
    result = control_sites([bad], _VOCAB, PYTHON_BOUNDARY)
    assert (result.sites, [(s.path, s.why) for s in result.skipped]) == (
        [],
        [(bad, "unparseable")],
    )


def test_an_unreadable_file_comes_back_as_a_skip(tmp_path: Path) -> None:
    """AUTHORED: a path that does not exist is reported with its reason."""
    missing = str(tmp_path / "missing.py")
    result = control_sites([missing], _VOCAB, PYTHON_BOUNDARY)
    assert (result.sites, [(s.path, s.why) for s in result.skipped]) == (
        [],
        [(missing, "unreadable")],
    )


def test_an_undecodable_file_comes_back_as_a_skip(tmp_path: Path) -> None:
    """AUTHORED: bytes that are not UTF-8 are reported apart from an unparseable file."""
    target = tmp_path / "latin.py"
    target.write_bytes(b"x = '\xe9'\n")
    result = control_sites([str(target)], _VOCAB, PYTHON_BOUNDARY)
    assert [s.why for s in result.skipped] == ["undecodable"]


def test_a_skipped_file_does_not_hide_the_files_beside_it(tmp_path: Path) -> None:
    """AUTHORED: the good file's sites and the bad file's skip arrive together."""
    good = _write(tmp_path, "if x:\n    pass\n", "good.py")
    bad = _write(tmp_path, "def broken(:\n", "bad.py")
    result = control_sites([bad, good], _VOCAB, PYTHON_BOUNDARY)
    assert ({s.path for s in result.sites}, [s.path for s in result.skipped]) == ({good}, [bad])


def test_an_empty_store_vocab_yields_no_row_kinds(tmp_path: Path) -> None:
    """AUTHORED: with nothing named as a store read, no site is a row site."""
    src = _write(tmp_path, _FIXTURE)
    kinds = {s.kind for s in control_sites([src], _NO_VOCAB, PYTHON_BOUNDARY).sites}
    assert kinds & {"row-iteration", "row-branch"} == set()


def test_an_empty_store_vocab_gives_an_early_exit_no_relational_form(tmp_path: Path) -> None:
    """AUTHORED: no row loop is recognised, so a `break` is an early exit reporting `unknown`."""
    src = _write(tmp_path, _FIXTURE)
    sites = control_sites([src], _NO_VOCAB, PYTHON_BOUNDARY).sites
    assert {s.sqlform for s in sites if s.kind == "early-exit"} == {"unknown"}


def test_an_empty_boundary_claims_nothing_external_or_configurational(tmp_path: Path) -> None:
    """AUTHORED: only `sys.exit` stays external; `if p.returncode` falls through, unclassified."""
    src = _write(tmp_path, _FIXTURE)
    keys = _keys(control_sites([src], _VOCAB, _NO_BOUNDARY).sites)
    external = {(scope, construct) for scope, construct, kind in keys if kind == "external"}
    assert (external, ("shell", "if", "unclassified") in keys) == ({("shell", "exit")}, True)


def test_an_empty_boundary_leaves_except_oserror_unclassified(tmp_path: Path) -> None:
    """AUTHORED: the exception type is the boundary's to name; an empty one names none."""
    src = _write(tmp_path, _FIXTURE)
    keys = _keys(control_sites([src], _VOCAB, _NO_BOUNDARY).sites)
    assert ("guards", "except", "unclassified") in keys


def test_a_site_carries_its_path_line_scope_and_snippet(tmp_path: Path) -> None:
    """AUTHORED: the columns of one site, read off a small source."""
    path = _write(tmp_path, "def f(a):\n    if a > 1:\n        pass\n")
    site = next(s for s in control_sites([path], _VOCAB, PYTHON_BOUNDARY).sites if s.scope == "f")
    assert (site.path, site.line, site.construct, site.scope, site.snippet) == (
        path,
        2,
        "if",
        "f",
        "a > 1",
    )


def test_the_governing_expression_of_an_if_is_its_test(tmp_path: Path) -> None:
    """AUTHORED: a fingerprint census reads `referents(site.governing)`."""
    sites = _sites(tmp_path, "def f(a, b):\n    if a.x > b:\n        pass\n")
    site = next(s for s in sites if s.construct == "if")
    assert referents(site.governing) == {"a", "x", "b"}


def test_the_governing_expression_of_a_break_is_the_enclosing_test(tmp_path: Path) -> None:
    """AUTHORED: an exit is governed by the `if` it sits under."""
    site = next(s for s in _sites(tmp_path) if s.construct == "break")
    assert referents(site.governing) == {"sym", "x"}


def test_a_break_under_no_test_has_no_governing_expression(tmp_path: Path) -> None:
    """AUTHORED: `for x in y: break` has nothing to read."""
    sites = _sites(tmp_path, "def f(y):\n    for x in y:\n        break\n")
    site = next(s for s in sites if s.construct == "break")
    assert site.governing == ()


def test_an_external_except_keeps_its_real_type_as_governing(tmp_path: Path) -> None:
    """AUTHORED: the verdict is forced external, the recorded expression is the handler's type."""
    site = next(s for s in _sites(tmp_path) if s.construct == "except")
    assert (site.kind, referents(site.governing)) == ("external", {"OSError"})


def test_the_governing_expression_does_not_enter_a_sites_equality(tmp_path: Path) -> None:
    """AUTHORED: parsing the same source twice gives equal sites, though the nodes differ."""
    first = _sites(tmp_path)
    second = _sites(tmp_path)
    assert first == second


def test_a_trailing_return_is_not_control_flow(tmp_path: Path) -> None:
    """AUTHORED: the function's last statement is excluded; an earlier return is a guard."""
    sites = _sites(tmp_path, "def f(a):\n    if a:\n        return 1\n    return 2\n")
    assert [(s.line, s.construct) for s in sites if s.construct.startswith("return")] == [
        (3, "return-guard")
    ]


def test_an_else_is_reported_at_its_first_statement(tmp_path: Path) -> None:
    """AUTHORED: an `else:` has no node of its own, so the line is the first statement's."""
    sites = _sites(tmp_path, "def f(a):\n    if a:\n        pass\n    else:\n        b = 1\n")
    assert [s.line for s in sites if s.construct == "else"] == [5]


def test_an_elif_is_named_as_an_elif(tmp_path: Path) -> None:
    """AUTHORED: the chained `if` is an `elif`, not a second `if`."""
    sites = _sites(tmp_path, "def f(a, b):\n    if a:\n        pass\n    elif b:\n        pass\n")
    assert [s.construct for s in sites if s.scope == "f"] == ["if", "elif"]


def test_sites_come_back_in_path_order_then_line_order(tmp_path: Path) -> None:
    """AUTHORED: two files give the first file's sites first, each ordered by line."""
    one = _write(tmp_path, "if x:\n    pass\nif y:\n    pass\n", "one.py")
    two = _write(tmp_path, "if z:\n    pass\n", "two.py")
    sites = control_sites([one, two], _VOCAB, PYTHON_BOUNDARY).sites
    assert [(s.path, s.line) for s in sites] == [(one, 1), (one, 3), (two, 1)]
