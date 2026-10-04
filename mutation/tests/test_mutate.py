# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mutate`: each spec perturbs exactly its site of a planted source."""

from __future__ import annotations

import ast
import re
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

from mikemol.mutation import mutate

if TYPE_CHECKING:
    from pathlib import Path

USAGE_EXIT = 2
RAISE = "raise BaseException('PAPERKIT_MUT')\n"

SITES_SRC = """\
import os


def classify(x):
    if x > 0:
        return 'pos'
    elif x < 0:
        return 'neg'
    else:
        return 'zero'


def one(x): return x


class K:
    def m(self):
        for i in range(3):
            self.n = i
        while self.go:
            self.go = False
        try:
            f()
        except ValueError:
            g()
        else:
            e()
        finally:
            h()
        with ctx():
            pass

    def inner(self):
        def deep():
            if q:
                return 1
            return 2
        return deep


async def co():
    await z()
    async with a:
        pass
    async for i in b:
        pass
"""

GUARD_SRC = """\
def f():
    try:
        a()
    except BaseException:
        b()
    try:
        c()
    except:
        d()
    try:
        e()
    except (ValueError, KeyError):
        g()
"""

DATA_SRC = """\
SCOPE = {'1.1': ('full', 'a'), '1.2': ('fragment', 'b'), '1.3': ('full', 'c')}
COLORS = ['red', 'green', 'blue']
ONE = ('only',)
TAGS = {'x', 'y'}
LONE = {'z'}
TYPED: dict[str, int] = {'a': 1, 'b': 2}
MERGED = {**SCOPE, 'k': 'v'}
NOT_LITERAL = make()
a, b = [1, 2]
"""

SWALLOW_SRC = """\
A = {'k': 1}
B = {'k': 2}
C = {'k': 3}
D = {'k': 4}
E = {'k': 5}
F = {'k': 6}


def f():
    x = A.get('k', 0)
    y = B.get('k')
    try:
        z = C['k']
    except KeyError:
        z = 0
    try:
        w = D['k']
    except (KeyError, ValueError):
        w = 0
    try:
        v = E['k']
    except mod.Err:
        v = 0
    try:
        u = F['k']
    except:
        u = 0
"""

IMPORT_SRC = """\
'''doc'''
from __future__ import annotations

import os
import sys, re
from pathlib import Path
from os import (
    path,
)

x = 1
"""


@dataclass
class Arm:
    """A branch arm presented to `mutate_lines` with a def node's interface."""

    body: list[ast.stmt]
    end_lineno: int | None


def _no_segment(_source: str, _node: ast.AST) -> None:
    """Stand in for `ast.get_source_segment` when it finds no span."""


def _span(node: ast.stmt) -> tuple[int, int]:
    """Return the first and last line of a statement.

    Returns:
        The (first, last) pair.

    """
    return node.lineno, node.end_lineno or 0


def test_def_sites_name_every_multiline_def_in_source_order() -> None:
    """Methods, closures and async defs are named by qualname; a one-liner is skipped."""
    names = [qn for qn, _ in mutate.def_sites(SITES_SRC)]
    assert names == ["classify", "K.m", "K.inner", "K.inner.deep", "co"]
    assert mutate.def_sites("def (") == []


def test_branch_sites_number_every_arm_per_def_in_source_order() -> None:
    """Each arm of if/elif/else, for, while, try, with and async forms gets a per-def index."""
    got = [
        (qn, n, *_span(first), last.end_lineno)
        for qn, n, (first, last) in mutate.branch_sites(SITES_SRC)
    ]
    assert got == [
        ("classify", 0, 6, 6, 6),
        ("classify", 1, 7, 10, 10),
        ("classify", 2, 8, 8, 8),
        ("classify", 3, 10, 10, 10),
        ("K.m", 0, 19, 19, 19),
        ("K.m", 1, 21, 21, 21),
        ("K.m", 2, 23, 23, 23),
        ("K.m", 3, 25, 25, 25),
        ("K.m", 4, 27, 27, 27),
        ("K.m", 5, 29, 29, 29),
        ("K.m", 6, 31, 31, 31),
        ("K.inner.deep", 0, 36, 36, 36),
        ("co", 0, 44, 44, 44),
        ("co", 1, 46, 46, 46),
    ]
    assert mutate.branch_sites("def (") == []


def test_branch_sites_refuse_an_arm_a_base_exception_handler_would_swallow() -> None:
    """A try body under `except BaseException` or a bare `except:` is refused; handlers are not."""
    got = [(qn, n, first.lineno) for qn, n, (first, _) in mutate.branch_sites(GUARD_SRC)]
    assert got == [("f", 0, 5), ("f", 1, 9), ("f", 2, 11), ("f", 3, 13)]


def test_flip_sites_number_every_if_and_while_condition_per_def() -> None:
    """The test expression of each if and while, in source order, per def."""
    got = [
        (qn, n, ast.get_source_segment(SITES_SRC, t)) for qn, n, t in mutate.flip_sites(SITES_SRC)
    ]
    assert got == [
        ("classify", 0, "x > 0"),
        ("classify", 1, "x < 0"),
        ("K.m", 0, "self.go"),
        ("K.inner.deep", 0, "q"),
    ]
    assert mutate.flip_sites("def (") == []


def test_data_sites_name_every_entry_of_a_module_level_literal() -> None:
    """Dict, list, tuple and set literals yield their entries; spreads and unpacks are skipped."""
    got = [
        (
            qn,
            n,
            kind,
            None if k is None else ast.get_source_segment(DATA_SRC, k),
            ast.get_source_segment(DATA_SRC, v),
        )
        for qn, n, kind, k, v in mutate.data_sites(DATA_SRC)
    ]
    assert got == [
        ("SCOPE", 0, "dict", "'1.1'", "('full', 'a')"),
        ("SCOPE", 1, "dict", "'1.2'", "('fragment', 'b')"),
        ("SCOPE", 2, "dict", "'1.3'", "('full', 'c')"),
        ("COLORS", 0, "List", None, "'red'"),
        ("COLORS", 1, "List", None, "'green'"),
        ("COLORS", 2, "List", None, "'blue'"),
        ("ONE", 0, "Tuple", None, "'only'"),
        ("TAGS", 0, "Set", None, "'x'"),
        ("TAGS", 1, "Set", None, "'y'"),
        ("LONE", 0, "Set", None, "'z'"),
        ("TYPED", 0, "dict", "'a'", "1"),
        ("TYPED", 1, "dict", "'b'", "2"),
        ("MERGED", 1, "dict", "'k'", "'v'"),
    ]
    assert mutate.data_sites("def (") == []


def test_data_sites_refuse_a_dict_whose_reads_swallow_a_dropped_key() -> None:
    """`.get(k, default)` and `except KeyError` hide a drop; a one-argument get does not."""
    assert {site[0] for site in mutate.data_sites(SWALLOW_SRC)} == {"B", "E", "F"}


def test_the_empty_spec_is_the_identity() -> None:
    """The baseline point of the mutation set is the source, byte for byte."""
    assert mutate.emit_mutant(SITES_SRC, "") == SITES_SRC


def test_a_def_spec_replaces_the_whole_body_with_an_uncatchable_raise() -> None:
    """`def:`, a bare qualname and the method and async forms all drop a body."""
    lines = SITES_SRC.splitlines(keepends=True)
    want = "".join([*lines[:4], "    " + RAISE, *lines[10:]])
    assert mutate.emit_mutant(SITES_SRC, "classify") == want
    assert mutate.emit_mutant(SITES_SRC, "def:classify") == want
    method = mutate.emit_mutant(SITES_SRC, "def:K.m")
    assert method == "".join([*lines[:17], "        " + RAISE, *lines[31:]])
    asynchronous = mutate.emit_mutant(SITES_SRC, "co")
    assert asynchronous == "".join([*lines[:41], "    " + RAISE])
    with pytest.raises(KeyError, match=re.escape("mutant: 'one' is not a def-site in the module")):
        mutate.emit_mutant(SITES_SRC, "one")


def test_a_branch_spec_replaces_one_arm_and_names_a_miss() -> None:
    """The arm's span becomes the raise at the arm's own indentation."""
    lines = SITES_SRC.splitlines(keepends=True)
    simple = mutate.emit_mutant(SITES_SRC, "branch:classify#0")
    assert simple == "".join([*lines[:5], "        " + RAISE, *lines[6:]])
    elif_arm = mutate.emit_mutant(SITES_SRC, "branch:classify#1")
    assert elif_arm == "".join([*lines[:6], "    " + RAISE, *lines[10:]])
    handler = mutate.emit_mutant(SITES_SRC, "branch:K.m#3")
    assert handler == "".join([*lines[:24], "            " + RAISE, *lines[25:]])
    miss = "mutant: 'branch:classify#9' is not a branch-arm site in the module"
    with pytest.raises(KeyError, match=re.escape(miss)):
        mutate.emit_mutant(SITES_SRC, "branch:classify#9")


def test_a_flip_spec_inverts_one_condition_and_names_a_miss() -> None:
    """`if C` becomes `if not (C)`, across lines too; a miss and a lost span are loud."""
    flipped = mutate.emit_mutant(SITES_SRC, "flip:classify#0")
    assert flipped == SITES_SRC.replace("    if x > 0:", "    if not (x > 0):")
    loop = mutate.emit_mutant(SITES_SRC, "flip:K.m#0")
    assert loop == SITES_SRC.replace("while self.go:", "while not (self.go):")
    spread = "def g(a, b):\n    if (a and\n            b):\n        return 1\n"
    assert mutate.flip_condition(spread, "g", 0) == (
        "def g(a, b):\n    if (not (a and\n            b)):\n        return 1\n"
    )
    miss = "mutant: 'flip:classify#9' is not a condition site in the module"
    with pytest.raises(KeyError, match=re.escape(miss)):
        mutate.emit_mutant(SITES_SRC, "flip:classify#9")


def test_a_flip_whose_source_span_is_lost_is_loud(monkeypatch: pytest.MonkeyPatch) -> None:
    """With no recoverable segment the flip refuses rather than guess."""
    monkeypatch.setattr(ast, "get_source_segment", _no_segment)
    lost = "mutant: 'flip:classify#0' has no recoverable source span"
    with pytest.raises(KeyError, match=re.escape(lost)):
        mutate.emit_mutant(SITES_SRC, "flip:classify#0")


def test_a_data_drop_rebuilds_only_the_affected_literal() -> None:
    """Each container keeps its type; the rest of the module is byte-identical."""
    want = {
        "SCOPE#1": (
            "SCOPE = {'1.1': ('full', 'a'), '1.2': ('fragment', 'b'), '1.3': ('full', 'c')}",
            "SCOPE = {'1.1': ('full', 'a'), '1.3': ('full', 'c')}",
        ),
        "COLORS#2": ("COLORS = ['red', 'green', 'blue']", "COLORS = ['red', 'green']"),
        "ONE#0": ("ONE = ('only',)", "ONE = ()"),
        "TAGS#0": ("TAGS = {'x', 'y'}", "TAGS = {'y'}"),
        "LONE#0": ("LONE = {'z'}", "LONE = set()"),
        "TYPED#0": ("TYPED: dict[str, int] = {'a': 1, 'b': 2}", "TYPED: dict[str, int] = {'b': 2}"),
        "MERGED#1": ("MERGED = {**SCOPE, 'k': 'v'}", "MERGED = {**SCOPE}"),
    }
    for arg, (old, new) in want.items():
        assert mutate.emit_mutant(DATA_SRC, "data-:" + arg) == DATA_SRC.replace(old, new)
    miss = "mutant: 'data-:NOPE#0' is not a data site in the module"
    with pytest.raises(KeyError, match=re.escape(miss)):
        mutate.emit_mutant(DATA_SRC, "data-:NOPE#0")


def test_a_data_drop_keeps_a_two_tuple_a_tuple() -> None:
    """Dropping from a 2-tuple leaves `('x',)`, never the parenthesised scalar."""
    assert mutate.emit_mutant("P = ('a', 'b')\n", "data-:P#1") == "P = ('a',)\n"


def test_drop_data_multi_applies_every_index_against_the_original_numbering() -> None:
    """Several indices of one literal, and several literals, land in one pass."""
    got = mutate.drop_data_multi(
        DATA_SRC, ["data-:COLORS#0", "data-:COLORS#2", "data-:SCOPE#0", "LONE#0"]
    )
    want = (
        DATA_SRC.replace("COLORS = ['red', 'green', 'blue']", "COLORS = ['green']")
        .replace("SCOPE = {'1.1': ('full', 'a'), ", "SCOPE = {")
        .replace("LONE = {'z'}", "LONE = set()")
    )
    assert got == want
    nothing = "mutant: 'data-:NOPE' is not a data literal in the module"
    with pytest.raises(KeyError, match=re.escape(nothing)):
        mutate.drop_data_multi(DATA_SRC, ["data-:NOPE#0"])
    beyond = "mutant: 'data-:COLORS#3' index out of range"
    with pytest.raises(KeyError, match=re.escape(beyond)):
        mutate.drop_data_multi(DATA_SRC, ["data-:COLORS#3"])


def test_a_data_perturb_swaps_one_value_for_a_counterfactual() -> None:
    """A string takes a same-position sibling, else a marker; other scalars shift or flip."""
    want = {
        "SCOPE#0": ("'1.1': ('full', 'a')", "'1.1': ('fragment', 'a')"),
        "COLORS#0": ("COLORS = ['red', 'green', 'blue']", "COLORS = ['blue', 'green', 'blue']"),
        "ONE#0": ("ONE = ('only',)", "ONE = ('only·PAPERKIT_PERTURB',)"),
        "TYPED#1": ("{'a': 1, 'b': 2}", "{'a': 1, 'b': 3}"),
    }
    for arg, (old, new) in want.items():
        assert mutate.emit_mutant(DATA_SRC, "dflip:" + arg) == DATA_SRC.replace(old, new)
    others = {
        "B = {'a': True, 'b': False}\n": ("dflip:B#0", "B = {'a': False, 'b': False}\n"),
        "N = [1.5]\n": ("dflip:N#0", "N = [2.5]\n"),
        "Z = [None]\n": ("dflip:Z#0", "Z = ['PAPERKIT_PERTURB']\n"),
        "Y = [b'x']\n": ("dflip:Y#0", 'Y = ["PAPERKIT_PERTURB"]\n'),
        "P = [f(), g()]\n": ("dflip:P#0", 'P = ["PAPERKIT_PERTURB", g()]\n'),
        "M = {'a': ('x', 1), 'b': 'plain', 'c': ('y',), 'd': ()}\n": (
            "dflip:M#0",
            "M = {'a': ('y', 1), 'b': 'plain', 'c': ('y',), 'd': ()}\n",
        ),
        "Q = {'a': {'q': 'r'}}\n": (
            "dflip:Q#0",
            "Q = {'a': {'q·PAPERKIT_PERTURB': 'r'}}\n",
        ),
    }
    for src, (spec, new) in others.items():
        assert mutate.emit_mutant(src, spec) == new
    miss = "mutant: 'dflip:NOPE#0' is not a data site in the module"
    with pytest.raises(KeyError, match=re.escape(miss)):
        mutate.emit_mutant(DATA_SRC, "dflip:NOPE#0")


def test_a_data_perturb_with_no_locatable_segment_marks_the_whole_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the source segment cannot be found the value itself is replaced by the marker."""
    monkeypatch.setattr(ast, "get_source_segment", _no_segment)
    assert mutate.emit_mutant("X = [1]\n", "dflip:X#0") == 'X = ["PAPERKIT_PERTURB"]\n'


def test_mutate_lines_collapses_nested_nodes_and_replaces_several_at_once() -> None:
    """An inner def inside an outer one is already gone; two disjoint defs both drop."""
    sites = dict(mutate.def_sites(SITES_SRC))
    nested = mutate.mutate_lines(SITES_SRC, [sites["K.inner"], sites["K.inner.deep"]])
    assert nested == mutate.emit_mutant(SITES_SRC, "K.inner")
    both = mutate.mutate_lines(SITES_SRC, [sites["classify"], sites["K.m"]])
    assert both == mutate.emit_mutant(mutate.emit_mutant(SITES_SRC, "K.m"), "classify")
    assert mutate.mutate_lines(SITES_SRC, []) == SITES_SRC


def test_mutate_lines_takes_any_node_with_a_body_and_an_end_line() -> None:
    """A branch arm presented as a pseudo-node replaces its span like a def body."""
    ((_, _, (first, last)), *_) = mutate.branch_sites(SITES_SRC)
    arm = Arm(body=[first], end_lineno=last.end_lineno)
    assert mutate.mutate_lines(SITES_SRC, [arm]) == mutate.emit_mutant(
        SITES_SRC, "branch:classify#0"
    )


def test_an_import_drop_removes_every_matching_top_level_import() -> None:
    """Plain, aliased-list and from-forms of one module all go; a miss is loud."""
    lines = IMPORT_SRC.splitlines(keepends=True)
    no_os = mutate.emit_mutant(IMPORT_SRC, "import-:os")
    assert no_os == "".join([*lines[:3], *lines[4:6], *lines[9:]])
    no_sys = mutate.emit_mutant(IMPORT_SRC, "import-:sys")
    assert no_sys == "".join([*lines[:4], *lines[5:]])
    no_pathlib = mutate.emit_mutant(IMPORT_SRC, "import-:pathlib")
    assert no_pathlib == "".join([*lines[:5], *lines[6:]])
    miss = "mutant: 'path' is not a top-level import in the module"
    with pytest.raises(KeyError, match=re.escape(miss)):
        mutate.emit_mutant(IMPORT_SRC, "import-:path")


def test_an_import_injection_is_dead_code_after_the_docstring_and_future_imports() -> None:
    """`if False:` guards the import, placed after the docstring and any __future__ import."""
    guard = "if False:  # PAPERKIT_MUT\n    import json\n"
    lines = IMPORT_SRC.splitlines(keepends=True)
    assert mutate.emit_mutant(IMPORT_SRC, "import+:json") == "".join(
        [*lines[:2], guard, *lines[2:]]
    )
    assert mutate.emit_mutant("'''d'''\nx = 1\n", "import+:json") == "'''d'''\n" + guard + "x = 1\n"
    assert mutate.emit_mutant("f()\nx = 1\n", "import+:json") == guard + "f()\nx = 1\n"


def test_an_unknown_operator_and_a_malformed_index_are_loud() -> None:
    """A spec the dispatcher cannot place raises; a miss is never a silent no-op."""
    unknown = "mutant: unknown mutation op in spec 'bogus:x'"
    with pytest.raises(KeyError, match=re.escape(unknown)):
        mutate.emit_mutant(SITES_SRC, "bogus:x")
    with pytest.raises(ValueError, match="invalid literal"):
        mutate.emit_mutant(SITES_SRC, "branch:classify")
    with pytest.raises(KeyError, match=re.escape("not a def-site")):
        mutate.emit_mutant("def (", "f")


def test_the_command_line_prints_the_perturbed_module(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`main` reads the module and prints the mutant; a wrong argument count is usage, exit 2."""
    module = tmp_path / "m.py"
    module.write_text(SITES_SRC, encoding="utf-8")
    assert mutate.main([str(module), "classify"]) == 0
    assert capsys.readouterr().out == mutate.emit_mutant(SITES_SRC, "classify")
    monkeypatch.setattr(sys, "argv", ["mikemol-mutate", str(module), ""])
    assert mutate.main() == 0
    assert capsys.readouterr().out == SITES_SRC
    assert mutate.main([str(module)]) == USAGE_EXIT
    assert capsys.readouterr().err == "usage: mikemol-mutate <module.py> <spec>\n"
