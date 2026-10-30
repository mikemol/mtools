# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Name the imports of an edited live module that the built venv copy does not hold (W2092).

⚑ THE CLASS: a hook module's source is live (the built venv imports the working tree's file) while
its MODULE LIST is whatever the last `bazel build //hooks:.venv` staged, so an edit that imports a
module the venv has not seen kills the next commit at import, before any gate runs (commit_kata
gained imports of flakemetric and later stackahead that way; the repair each time was `bazel build
//hooks:.venv` between the new module and the importing edit). The launcher already refuses a stale
venv at RUN time with the repair named (W1183); this names the cause at EDIT time.

⚑ PURE, ON TEXT: `source` is the edited file's text and `built` is the set of module names the
built venv holds, read by the caller (a listing of its `site-packages/mikemol/hooks`). Nothing here
touches disk, the venv or the network, so a PreToolUse hook (W2093) can call it on an edit it has
not applied yet.

⚑ ONLY `mikemol.hooks.<module>` IS JUDGED: an import of anything else is the venv's own business.
`from mikemol.hooks import x` names the module `mikemol.hooks.x`; the package itself is always
held. A relative import cannot be resolved without the file's own module name, so it is NAMED as
unreadable, never guessed at (`unreadable`).

CONSUMED BY: nothing yet (W2093, the PreToolUse hook that refuses the edit).
"""

import ast
from collections.abc import Collection

PREFIX = "mikemol.hooks"


def _in_hooks(name: str) -> bool:
    return name.startswith(PREFIX + ".")


def _hooks_modules(tree: ast.AST) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names if _in_hooks(alias.name))
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            if node.module == PREFIX:
                found.update(f"{PREFIX}.{a.name}" for a in node.names if a.name != "*")
            elif _in_hooks(node.module):
                found.add(node.module)
    return found


def unbuilt_imports(source: str, built: Collection[str]) -> list[str]:
    """Name the `mikemol.hooks` modules `source` imports that `built` does not hold.

    Returns:
        the missing module names, sorted; empty when every import is held, when there are none,
        and when the source does not parse (the edit's own lint refuses a syntax error).

    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    return sorted(_hooks_modules(tree) - set(built))


def unreadable(source: str) -> list[str]:
    """Name the relative imports in `source`, which this check cannot resolve.

    Returns:
        each relative import as its dots and module (`.x`, `..pkg.y`, `.` for `from . import z`),
        sorted and distinct; empty when there are none or the source does not parse.

    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    found = {
        "." * node.level + (node.module or "")
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.level > 0
    }
    return sorted(found)
