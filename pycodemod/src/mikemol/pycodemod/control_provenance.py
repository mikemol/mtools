# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""Where a control-flow site's governing value came from: the boundary, configuration, the scope.

Cleanroomed from substrate's `scratch/_pycodemod_control.py` (W606, commit 2 of 4): `ext_names`,
`external_expr`, `mode_expr`, `scopes`, `own_walk`, `module_consts` and `params`. The origin read
module globals for what counts as outside the program; here every classifier takes the
`control_roster.Boundary` as an explicit operand, so an empty boundary claims nothing external and
nothing configurational. Row provenance is not here: `storeflow` owns it, through a `StoreVocab`.

⚑⚑ THE ORDER OF THE MODE TEST AND THE ROOT TEST IS THE WHOLE DISTINCTION. `os` is an external root,
so a naive root test files `os.environ.get("X")` under the irreducible half, putting the program's
own configuration reads beside reading a file off the disk. `external_expr` therefore skips a
dotted name the boundary lists as configuration before it asks whether the root is external.

⚑⚑ THE HOP IS THE POINT. `p = subprocess.run(cmd)` then `if p.returncode:` names no external module
in the branch's own expression, so a test reading only the governing expression sees a plain
attribute test. `ext_names` carries the boundary one assignment forward, to a fixpoint of five
rounds, because `blob = fh.read()` then `blob = blob or b""` chains two hops.

⚑ THE MODULE SCOPE IS WHY `own_walk` EXISTS. `ast.walk(module)` reaches every function-local name in
the file, so a module-level census would inherit every local and report the `__main__` guard as
something it is not. `own_walk` stops at a nested def or class. ⚑ `scopes`, `own_walk`, `params`
and `module_consts` read no boundary table, so they take no `Boundary`: an operand a function never
reads is a claim it depends on something.
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from mikemol.pycodemod.storeflow import touches

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Iterator

    from mikemol.pycodemod.control_roster import Boundary

_DEFS = (ast.FunctionDef, ast.AsyncFunctionDef)
_ROUNDS = 5


def _as_list(governing: ast.AST | list[ast.AST] | None) -> list[ast.AST]:
    """Normalise a governing expression, which is a node, a list of nodes, or nothing.

    Returns:
        the nodes as a list; empty for no expression.

    """
    if governing is None:
        return []
    return list(governing) if isinstance(governing, list) else [governing]


def _attr_root(node: ast.AST) -> str | None:
    """Find the name an attribute chain starts from.

    Returns:
        the root name, or None when the chain does not start at a bare name.

    """
    while isinstance(node, ast.Attribute):
        node = node.value
    return node.id if isinstance(node, ast.Name) else None


def _dotted_has(node: ast.AST, attr: str) -> bool:
    """Report whether any link of an attribute chain is `attr`.

    Returns:
        True when some attribute along the chain has that name.

    """
    while isinstance(node, ast.Attribute):
        if node.attr == attr:
            return True
        node = node.value
    return False


def _is_mode_dotted(node: ast.AST, boundary: Boundary) -> bool:
    """Report whether a node is a dotted configuration read of `boundary`.

    Returns:
        True for `sys.argv`, `os.environ` and anything chained off them.

    """
    if not isinstance(node, ast.Attribute):
        return False
    root = _attr_root(node)
    return (root, node.attr) in boundary.mode_dotted or any(
        root == r and _dotted_has(node, a) for r, a in boundary.mode_dotted
    )


def external_expr(governing: ast.AST | list[ast.AST] | None, boundary: Boundary) -> bool:
    """Report whether an expression reaches the boundary - the classifier's first test.

    Returns:
        True when a name, method or module root in the expression is external by `boundary`;
        a dotted name `boundary` lists as configuration does not count.

    """
    for top in _as_list(governing):
        for n in ast.walk(top):
            if isinstance(n, ast.Name) and n.id in boundary.names:
                return True
            if (
                isinstance(n, ast.Attribute)
                and not _is_mode_dotted(n, boundary)
                and (n.attr in boundary.attrs or _attr_root(n) in boundary.roots)
            ):
                return True
    return False


def mode_expr(
    governing: ast.AST | list[ast.AST] | None,
    params_: Collection[str],
    consts: Collection[str],
    boundary: Boundary,
) -> bool:
    """Report whether an expression branches on configuration.

    Returns:
        True when it names a parameter, a module constant, a bare mode name of `boundary` or a
        dotted configuration read of it (`sys.argv`, `os.environ`).

    """
    for top in _as_list(governing):
        for n in ast.walk(top):
            if isinstance(n, ast.Name) and (
                n.id in params_ or n.id in consts or n.id in boundary.mode_names
            ):
                return True
            if _is_mode_dotted(n, boundary):
                return True
    return False


def _bound(target: ast.AST) -> set[str]:
    """Collect the names an assignment target binds.

    Returns:
        every Name under the target.

    """
    return {x.id for x in ast.walk(target) if isinstance(x, ast.Name)}


def _flow(node: ast.AST) -> tuple[list[ast.expr], ast.expr | None]:
    """Split a statement into the targets it binds and the value that flows into them.

    Returns:
        `(targets, value)` for an assignment, annotated assignment or `for`; `([], None)` else.

    """
    if isinstance(node, ast.Assign):
        return node.targets, node.value
    if isinstance(node, ast.AnnAssign) and node.value is not None:
        return [node.target], node.value
    if isinstance(node, (ast.For, ast.AsyncFor)):
        return [node.target], node.iter
    return [], None


def _with_bound(node: ast.AST, boundary: Boundary) -> set[str]:
    """Collect the names a `with ... as` binds from an external context manager.

    Returns:
        the bound names; empty for a node that is not a `with`.

    """
    out: set[str] = set()
    if isinstance(node, (ast.With, ast.AsyncWith)):
        for it in node.items:
            if it.optional_vars is not None and external_expr(it.context_expr, boundary):
                out |= _bound(it.optional_vars)
    return out


def ext_names(nodes: Iterable[ast.AST], boundary: Boundary) -> set[str]:
    """Return the names carrying a value that CAME FROM the boundary, to a five-round fixpoint.

    Returns:
        names bound by an assignment, annotated assignment, loop target or `with ... as` whose
        value is external by `boundary` or touches a name already in the set.

    """
    seq = list(nodes)
    out: set[str] = set()
    for _round in range(_ROUNDS):
        before = len(out)
        for n in seq:
            out |= _with_bound(n, boundary)
            targets, val = _flow(n)
            if val is not None and (external_expr(val, boundary) or touches(val, out)):
                for t in targets:
                    out |= _bound(t)
        if len(out) == before:
            break
    return out


def _children(scope: ast.AST) -> list[ast.AST]:
    """List the direct members of a scope.

    Returns:
        the body, plus a def's argument defaults and decorators.

    """
    if isinstance(scope, _DEFS):
        return [*scope.body, *scope.args.defaults, *scope.decorator_list]
    if isinstance(scope, (ast.Module, ast.ClassDef)):
        return list(scope.body)
    return []


def own_walk(scope: ast.AST) -> Iterator[ast.AST]:
    """Yield every node in one scope, without descending into a nested def or class.

    Yields:
        each node of the scope's body (and a def's defaults and decorators); a nested def or class
        is yielded itself but its body is not.

    """
    stack = _children(scope)
    while stack:
        n = stack.pop()
        yield n
        if isinstance(n, (*_DEFS, ast.ClassDef)):
            continue
        stack.extend(ast.iter_child_nodes(n))


def scopes(tree: ast.AST) -> list[tuple[ast.AST, str]]:
    """Return the module and every def and class in it, each its own scope.

    Returns:
        `(node, label)` pairs: `<module>`, the def's name, or `class <name>`.

    """
    out: list[tuple[ast.AST, str]] = [(tree, "<module>")]
    for n in ast.walk(tree):
        if isinstance(n, _DEFS):
            out.append((n, n.name))
        elif isinstance(n, ast.ClassDef):
            out.append((n, "class " + n.name))
    return out


def params(scope: ast.AST) -> set[str]:
    """Return a def's parameter names, every kind; empty for the module or a class.

    Returns:
        positional-only, positional, keyword-only, `*args` and `**kwargs` names.

    """
    if not isinstance(scope, _DEFS):
        return set()
    a = scope.args
    names = {x.arg for x in (*a.posonlyargs, *a.args, *a.kwonlyargs)}
    names.update(extra.arg for extra in (a.vararg, a.kwarg) if extra is not None)
    return names


def module_consts(tree: ast.Module) -> set[str]:
    """Return the ALL-CAPS module-level bindings - the configuration a branch can read.

    Returns:
        names assigned at module scope whose spelling is upper case.

    """
    out: set[str] = set()
    for s in tree.body:
        targets: list[ast.expr] = []
        if isinstance(s, ast.Assign):
            targets = s.targets
        elif isinstance(s, ast.AnnAssign):
            targets = [s.target]
        out.update(t.id for t in targets if isinstance(t, ast.Name) and t.id.isupper())
    return out
