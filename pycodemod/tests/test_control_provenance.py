# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.pycodemod.control_provenance`: the boundary, configuration, the scope.

⚑⚑ WHAT IS TRANSCRIBED AND WHAT IS AUTHORED. Transcribed from the origin's `--control` selftest
arms, restated on synthetic source because those arms ran the census (a later commit) over a file:
a branch on a value one hop from a subprocess is external (`ext_names`), `with open` is external,
a parameter or constant read is configuration, and a module scope does not inherit function-local
names (`own_walk`). Arms marked AUTHORED have no origin: the empty-boundary arms, the multi-hop
fixpoint, `os.environ` ahead of the `os` root, the scope labels, the parameter kinds and the
constant spellings. ⚑ NO FUNCTION HERE READS A FILE, so the skipped-file arm belongs to the census.
"""

from __future__ import annotations

import ast

from mikemol.pycodemod import control_provenance as cp
from mikemol.pycodemod.control_roster import PYTHON_BOUNDARY, Boundary

_EMPTY = Boundary(
    roots=frozenset(),
    names=frozenset(),
    attrs=frozenset(),
    exceptions=frozenset(),
    mode_dotted=frozenset(),
    mode_names=frozenset(),
)
_DB = Boundary(
    roots=frozenset({"db"}),
    names=frozenset(),
    attrs=frozenset(),
    exceptions=frozenset(),
    mode_dotted=frozenset(),
    mode_names=frozenset(),
)


def _expr(src: str) -> ast.expr:
    return ast.parse(src, mode="eval").body


def _mod(src: str) -> ast.Module:
    return ast.parse(src)


def test_a_subprocess_hop_makes_the_result_external() -> None:
    """`p = subprocess.run(cmd)` carries the boundary into `p`; `p.returncode` alone does not."""
    tree = _mod("p = subprocess.run(cmd)\nif p.returncode:\n    pass\n")
    assert cp.ext_names(tree.body, PYTHON_BOUNDARY) == {"p"}
    assert not cp.external_expr(_expr("p.returncode"), PYTHON_BOUNDARY)


def test_the_hop_is_iterated_to_a_fixpoint() -> None:
    """AUTHORED: `fh = open()`, `blob = fh.read()`, `blob2 = blob or b""`, `c = blob2` chain."""
    tree = _mod("fh = open(p)\nblob = fh.read()\nblob2 = blob or b''\nc = blob2\n")
    assert cp.ext_names(tree.body, PYTHON_BOUNDARY) == {"fh", "blob", "blob2", "c"}


def test_ext_names_reads_with_for_and_annotated_targets() -> None:
    """AUTHORED: `with open() as fh`, `for x in os.listdir()` and `y: int = input()` all bind."""
    src = "with open(p) as fh:\n    pass\nfor x in os.listdir(d):\n    pass\ny: int = input()\n"
    assert cp.ext_names(_mod(src).body, PYTHON_BOUNDARY) == {"fh", "x", "y"}


def test_a_pure_assignment_binds_no_external_name() -> None:
    """AUTHORED: arithmetic on locals reaches no boundary."""
    assert cp.ext_names(_mod("a = 1\nb = a + 2\n").body, PYTHON_BOUNDARY) == set()


def test_open_and_attribute_calls_reach_the_boundary() -> None:
    """A bare `open`, a module root and a reading method are each external."""
    assert cp.external_expr(_expr("open(path, 'rb')"), PYTHON_BOUNDARY)
    assert cp.external_expr(_expr("os.path.exists(path)"), PYTHON_BOUNDARY)
    assert cp.external_expr(_expr("fh.read()"), PYTHON_BOUNDARY)


def test_a_pure_expression_is_not_external() -> None:
    """`len(xs) + 1` names nothing outside the program, and no expression at all is not either."""
    assert not cp.external_expr(_expr("len(xs) + 1"), PYTHON_BOUNDARY)
    assert not cp.external_expr(None, PYTHON_BOUNDARY)


def test_external_expr_takes_a_list_of_nodes() -> None:
    """A governing expression may be several nodes; one external member suffices."""
    nodes: list[ast.AST] = [_expr("a + 1"), _expr("open(p)")]
    assert cp.external_expr(nodes, PYTHON_BOUNDARY)


def test_os_environ_is_configuration_not_external() -> None:
    """The mode test runs before the root test: `os` is a root yet `os.environ` is configuration."""
    assert not cp.external_expr(_expr("os.environ"), PYTHON_BOUNDARY)
    assert cp.mode_expr(_expr("os.environ"), set(), set(), PYTHON_BOUNDARY)
    assert cp.mode_expr(_expr("sys.argv[1]"), set(), set(), PYTHON_BOUNDARY)
    assert cp.external_expr(_expr("os.getcwd()"), PYTHON_BOUNDARY)


def test_mode_expr_reads_parameters_constants_and_the_main_guard() -> None:
    """A parameter, an ALL-CAPS constant and `__name__` each make an expression a mode test."""
    assert cp.mode_expr(_expr("additive"), {"additive"}, set(), PYTHON_BOUNDARY)
    assert cp.mode_expr(_expr("VERBOSE"), set(), {"VERBOSE"}, PYTHON_BOUNDARY)
    assert cp.mode_expr(_expr("__name__ == '__main__'"), set(), set(), PYTHON_BOUNDARY)
    assert not cp.mode_expr(_expr("sym == 'x'"), {"additive"}, {"VERBOSE"}, PYTHON_BOUNDARY)
    assert not cp.mode_expr(None, {"a"}, set(), PYTHON_BOUNDARY)


def test_an_empty_boundary_claims_nothing() -> None:
    """AUTHORED: with no tables, nothing is external and no bare mode name is configuration."""
    assert not cp.external_expr(_expr("open(p).read()"), _EMPTY)
    assert not cp.external_expr(_expr("subprocess.run(c)"), _EMPTY)
    assert not cp.mode_expr(_expr("__name__ == sys.argv"), set(), set(), _EMPTY)
    assert cp.ext_names(_mod("p = subprocess.run(c)\n").body, _EMPTY) == set()


def test_an_empty_boundary_still_reads_parameters() -> None:
    """AUTHORED: parameters and constants are operands of the call, not boundary data."""
    assert cp.mode_expr(_expr("flag"), {"flag"}, set(), _EMPTY)
    assert cp.mode_expr(_expr("LIMIT"), set(), {"LIMIT"}, _EMPTY)


def test_a_custom_boundary_replaces_the_python_one() -> None:
    """AUTHORED: a boundary naming `db` as a root makes `db.fetch()` external, `os` no longer."""
    assert cp.external_expr(_expr("db.fetch()"), _DB)
    assert not cp.external_expr(_expr("os.getcwd()"), _DB)


def test_scopes_labels_module_defs_and_classes() -> None:
    """AUTHORED: the module, every def (nested too) and every class is its own scope."""
    tree = _mod("def f():\n    def g():\n        pass\nclass C:\n    def m(self):\n        pass\n")
    assert sorted(label for _node, label in cp.scopes(tree)) == [
        "<module>",
        "class C",
        "f",
        "g",
        "m",
    ]


def test_a_module_scope_does_not_inherit_function_locals() -> None:
    """The module walk stops at a def, so a function-local assignment is not a module one."""
    tree = _mod("def f():\n    rows = con.execute('q')\nif __name__ == '__main__':\n    pass\n")
    module_kinds = {type(n).__name__ for n in cp.own_walk(tree)}
    assert {"If", "FunctionDef"} <= module_kinds
    assert "Assign" not in module_kinds
    assert "Assign" in {type(n).__name__ for n in cp.own_walk(tree.body[0])}


def test_own_walk_of_a_def_includes_defaults_and_decorators() -> None:
    """AUTHORED: a def's defaults and decorators are walked with the def."""
    fn = _mod("@deco\ndef f(a=helper()):\n    return a\n").body[0]
    names = {n.id for n in cp.own_walk(fn) if isinstance(n, ast.Name)}
    assert {"deco", "helper", "a"} <= names


def test_params_cover_every_parameter_kind() -> None:
    """AUTHORED: positional-only, positional, keyword-only, `*args` and `**kwargs`."""
    fn = _mod("def f(a, /, b, *args, c, **kw):\n    pass\n").body[0]
    assert cp.params(fn) == {"a", "b", "args", "c", "kw"}


def test_params_of_a_module_or_class_is_empty() -> None:
    """AUTHORED: only a def has parameters."""
    assert cp.params(_mod("x = 1\n")) == set()
    assert cp.params(_mod("class C:\n    pass\n").body[0]) == set()


def test_module_consts_are_all_caps_bindings_only() -> None:
    """AUTHORED: `VERBOSE = 1` and `LIMIT: int = 2` count; `name`, `Mixed` and tuples do not."""
    tree = _mod("VERBOSE = 1\nLIMIT: int = 2\nname = 3\nMixed = 4\nA, B = 1, 2\n")
    assert cp.module_consts(tree) == {"VERBOSE", "LIMIT"}
