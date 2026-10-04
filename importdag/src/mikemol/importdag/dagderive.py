# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Derive an engine's import DAG with both sides of every edge in one namespace.

An edge used to be recorded as a path-shaped key against a bare-stem value, so a build had to
translate one namespace into the other before it could name a target. That translation was a
dict comprehension keyed on the bare stem, which is silently last-wins: a second module with an
existing stem, in another directory, would replace the first and its bytecode would never be
staged for anything importing it. Build targets are already path-shaped, so an edge is recorded
here as the importing module's path and the imported module's path, and the translation becomes
the identity.

Resolution is still by stem, because sources may still say a flat `import bib`. What changed is
what an edge is recorded as, and an ambiguous stem now refuses instead of silently picking one.

Imports are read from the syntax tree, never by text search: a text search matches the name in
comments and strings and reports phantom edges.
"""

from __future__ import annotations

import ast
from pathlib import Path


def imports(text: str, names: set[str], pkg: str = "paperkit") -> set[str]:
    """Collect the engine-internal module names `text` imports, restricted to `names`.

    Both spellings of an import record the same edge, and reading only the flat one erases the
    DAG: `import bibparse` and `from paperkit import bibparse` are one dependency written two
    ways. `pkg` names the engine's own package so a subpackage import resolves to the same stem
    the flat form yields; callers key on stems, so a dotted name here would silently drop the
    edge instead.

    Four forms are read: `import bibparse` yields `bibparse`; `from paperkit import bibparse`
    yields `bibparse`; `from paperkit.tools import vfs` yields `vfs`; and a flat from-import of
    an engine stem such as `from _fixture_model import fx` yields `_fixture_model`.

    Returns:
        The stems in `names` that `text` imports. A text that does not parse yields the empty
        set.

    """
    out: set[str] = set()
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return out
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out |= {a.name for a in node.names if a.name in names}
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod in names:
                out.add(mod)
            elif mod == pkg or mod.startswith(pkg + "."):
                out |= {a.name for a in node.names if a.name in names}
    return out


def stem_index(paths: list[str]) -> dict[str, str]:
    """Map each module's bare stem to its engine-relative path, refusing an ambiguous stem.

    A package marker is exempt, and that is a property of the language rather than a waiver:
    `__init__.py` is never the target of an `import __init__`, it is reached as the package's own
    name, one per directory by construction. So it cannot be the ambiguous referent of an import
    edge, and excluding it narrows the index to exactly the names an edge can name. Every other
    duplicate stem is a hard error.

    Returns:
        The path of each stem.

    Raises:
        ValueError: Two paths share one bare stem.

    """
    by_stem: dict[str, list[str]] = {}
    for p in paths:
        stem = Path(p).stem
        if stem == "__init__":
            continue
        by_stem.setdefault(stem, []).append(p)
    dupes = {s: ms for s, ms in by_stem.items() if len(ms) > 1}
    if dupes:
        msg = (
            f"two engine modules share a bare stem, so an import naming it is ambiguous: "
            f"{dupes}. A flat map silently keeps one; this refuses instead."
        )
        raise ValueError(msg)
    return {s: ms[0] for s, ms in by_stem.items()}


def edges(eng: Path, paths: list[str]) -> list[tuple[str, str]]:
    """Return every engine-internal import edge as importer path and imported path.

    Returns:
        The edges in `paths` order, each importer's imports sorted by stem. A module's import of
        its own stem is not an edge.

    """
    index = stem_index(paths)
    out: list[tuple[str, str]] = []
    for p in paths:
        stem = Path(p).stem
        found = imports((eng / p).read_text(encoding="utf-8"), set(index)) - {stem}
        out.extend((p, index[imp]) for imp in sorted(found))
    return out


def cone(start: str, edges_by_mod: dict[str, list[str]]) -> set[str]:
    """Return the transitive import closure of one module, as engine-relative paths.

    The walk is owned here because every consumer that wrote its own walk also wrote its own
    translation between the key namespace and the value namespace, and one of those silently
    stopped after a single hop and under-derived the expected set. `start` is an
    engine-relative path and so is every element of the result, including `start` itself. A
    consumer that wants stems takes them; one that wants targets strips the suffix. Nothing
    reconstructs a key from a value.

    Returns:
        Every path reachable from `start` along `edges_by_mod`, and `start`.

    """
    seen: set[str] = set()
    todo = [start]
    while todo:
        m = todo.pop()
        if m in seen:
            continue
        seen.add(m)
        todo.extend(edges_by_mod.get(m, []))
    return seen
