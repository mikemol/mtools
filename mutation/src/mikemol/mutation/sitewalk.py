# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The one finder of a module's def-sites, for the mutation grid and the declared specs (W1761).

⚑ TWO PROGRAMS FOUND SITES AND THEY DRIFTED. `mutate.def_sites` (the declared-spec scope) and the
runner's `_owned` (the dist grid) were separate walks, and the 2026-10-20 Protocol fix (github-8f,
after a docstring-bodied stub survived four times in webpage) had to land in both. They differ on
four points and each is now a named field of `Policy`, so a difference is a choice a caller makes
and not a fork nobody decided:

    locals_marker  a def inside a def is `outer.<locals>.inner` (Python's own `__qualname__`, what
                   the grid addresses by) rather than `outer.inner`.
    repeat_labels  the n-th repeat of a path (a property getter and setter, the two arms of an
                   `if TYPE_CHECKING:`) carries `#n`, so every site has its own address.
    async_sites    an `async def` is a site; otherwise it is only walked, so a def nested in one
                   still gets the path Python would give it.
    one_liners     `def f(): return 1` is a site; otherwise it is skipped, because its body shares
                   a line with its signature and a line-span replacement cannot isolate it.

⚑ A PROTOCOL'S METHODS ARE NEVER SITES, whatever the policy: a Protocol states a shape and
implements none of it, so no test can exercise a body there, and a perturbed stub changes no
verdict. `is_protocol` is the one reading of that rule. It accepts a bare, qualified
(`typing.Protocol`, `typing_extensions.Protocol`) or subscripted base; the grid's own copy accepted
only the first two spellings of the name, and the wider reading is the intended one.

⚑ NOT FOLDED IN HERE, ON PURPOSE: `mikemol.mutantcell.def_sites` is a third walk, ported from
paperkit, whose output keys every claim's sensitivity fingerprint, so a change to what it emits
re-keys a whole grid. It still lacks the Protocol rule. That is carried as a finding on W1761, not
repaired here.
"""

import ast
from dataclasses import dataclass

type FuncNode = ast.FunctionDef | ast.AsyncFunctionDef


@dataclass(frozen=True, slots=True)
class Policy:
    """How one caller names and chooses sites: the four points the two finders differed on."""

    locals_marker: bool
    repeat_labels: bool
    async_sites: bool
    one_liners: bool


@dataclass(frozen=True, slots=True)
class Site:
    """A def-site: its address, its node, and the class that owns it (None for a nested def)."""

    path: str
    node: FuncNode
    owner: ast.ClassDef | None


DEFINITION = Policy(locals_marker=False, repeat_labels=False, async_sites=True, one_liners=False)
GRID = Policy(locals_marker=True, repeat_labels=True, async_sites=False, one_liners=True)


def _names_protocol(base: ast.expr) -> bool:
    """Say whether a class base is `Protocol`, bare, qualified (`typing.Protocol`) or subscripted.

    Returns:
        True for `Protocol`, `typing.Protocol`, `Protocol[T]` and `typing.Protocol[T]`.

    """
    node = base.value if isinstance(base, ast.Subscript) else base
    if isinstance(node, ast.Attribute):
        return node.attr == "Protocol"
    return isinstance(node, ast.Name) and node.id == "Protocol"


def is_protocol(node: ast.ClassDef) -> bool:
    """Say whether a class declares a `typing.Protocol`.

    Returns:
        True when any base names `Protocol`.

    """
    return any(_names_protocol(base) for base in node.bases)


def walk(tree: ast.AST, policy: Policy) -> list[Site]:
    """Walk a parsed module in source order, naming each def-site by its path under `policy`.

    Returns:
        The sites in source order; every path is distinct when `policy.repeat_labels` is set.

    """
    found: list[Site] = []
    seen: dict[str, int] = {}
    nested = ".<locals>." if policy.locals_marker else "."

    def visit(body: ast.AST, prefix: str, owner: ast.ClassDef | None) -> None:
        for child in ast.iter_child_nodes(body):
            if isinstance(child, ast.FunctionDef) or (
                policy.async_sites and isinstance(child, ast.AsyncFunctionDef)
            ):
                path = f"{prefix}{child.name}"
                seen[path] = seen.get(path, 0) + 1
                label = f"{path}#{seen[path]}" if policy.repeat_labels and seen[path] > 1 else path
                if policy.one_liners or child.body[0].lineno > child.lineno:
                    found.append(Site(label, child, owner))
                visit(child, f"{path}{nested}", None)
            elif policy.locals_marker and isinstance(child, ast.AsyncFunctionDef | ast.Lambda):
                name = child.name if isinstance(child, ast.AsyncFunctionDef) else "<lambda>"
                visit(child, f"{prefix}{name}{nested}", None)
            elif isinstance(child, ast.ClassDef):
                if not is_protocol(child):
                    visit(child, f"{prefix}{child.name}.", child)
            else:
                visit(child, prefix, owner)

    visit(tree, "", None)
    return found
