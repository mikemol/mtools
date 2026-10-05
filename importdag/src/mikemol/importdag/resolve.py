# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Resolve the imports of a set of module files against each other, whatever the layout.

`dagderive` reads an engine whose modules are flat stems under one package name. A set of files
from another repository is not that: modules sit under `src/` namespace roots, several packages
share one tree, and a script says `import sibling` bare. A dotted import name there is a SUFFIX of
a path, not a stem, so each file is indexed by every dotted suffix of its own path and an import
is resolved against that index.

⚑⚑ AN AMBIGUOUS NAME IS REPORTED, NEVER PICKED. Two files can answer one name (`scripts/a.py` and
`tools/a.py` both answer `a`). `dagderive.stem_index` refuses that outright, which is right for an
engine that must stage every module; a census over a foreign tree must go on. So a name with
several candidates resolves to the one beside the importing file (Python's own reading of a bare
sibling import) when exactly one is there, and otherwise lands in `Resolution.ambiguous` with no
edge. The caller sees what was left unsettled and decides; a skipped edge loosens an order and can
never make a cycle.

⚑ THE TRANSITIVE CLOSURE IS `dagderive.cone`, NOT A SECOND WALK. This module derives edges only.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

INIT = "__init__"
"""A package marker is named by its package, so its own stem is dropped from the module path."""


@dataclass(frozen=True, slots=True)
class Resolution:
    """The indexed files one module imports, and the import names it could not settle."""

    files: frozenset[str]
    ambiguous: tuple[str, ...]


def _from_names(node: ast.ImportFrom) -> set[str]:
    """Name the modules one `from` statement can mean.

    Returns:
        The module and each `module.name`, or just the names for a relative `from . import x`,
        whose module is a sibling of the importing file.

    """
    if node.module:
        return {node.module, *(f"{node.module}.{alias.name}" for alias in node.names)}
    return {alias.name for alias in node.names}


def import_names(text: str) -> frozenset[str]:
    """Collect every dotted module name `text` imports, read from the syntax tree.

    Returns:
        The names `import a.b` and `from a import b` can mean (`a.b`, and `a` with `a.b`), and the
        bare names of a relative `from . import x`. A text that does not parse yields none.

    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return frozenset()
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            found.update(_from_names(node))
    return frozenset(found)


def module_names(path: str) -> tuple[str, ...]:
    """Name a file by every dotted suffix of its own path.

    Returns:
        `pkg/src/m/x.py` as `pkg.src.m.x`, `src.m.x`, `m.x` and `x`, longest first. A package
        marker `pkg/sub/__init__.py` is named by its package, `pkg.sub` and `sub`.

    """
    parts = list(Path(path).parts)
    if parts:
        parts[-1] = Path(parts[-1]).stem
    if parts and parts[-1] == INIT:
        parts.pop()
    return tuple(".".join(parts[i:]) for i in range(len(parts)))


def index(paths: Iterable[str]) -> dict[str, frozenset[str]]:
    """Index files by the dotted names they could be imported as.

    Returns:
        Each dotted suffix, and every file of `paths` it could name.

    """
    found: dict[str, set[str]] = {}
    for path in paths:
        for name in module_names(path):
            found.setdefault(name, set()).add(path)
    return {name: frozenset(files) for name, files in found.items()}


def _settle(path: str, hits: frozenset[str]) -> frozenset[str] | None:
    """Narrow the files a name could mean to the ones it does mean.

    Returns:
        The hits when there are one or none, else the one hit beside `path`, else None.

    """
    if len(hits) <= 1:
        return hits
    here = str(Path(path).parent)
    near = frozenset(hit for hit in hits if str(Path(hit).parent) == here)
    return near or None


def resolve(path: str, names: Iterable[str], table: Mapping[str, frozenset[str]]) -> Resolution:
    """Resolve the import `names` of the file `path` against an index.

    A name is tried at its longest dotted prefix first, so `import a.b.c` finds `a/b/c.py` and not
    `a.py`, and an attribute (`a.b.thing`) falls back to the module that holds it. A file never
    imports itself.

    Returns:
        The indexed files the names mean, and the names that could mean several with none beside
        `path`, sorted.

    """
    files: set[str] = set()
    ambiguous: set[str] = set()
    for name in names:
        parts = name.split(".")
        for cut in range(len(parts), 0, -1):
            hits = table.get(".".join(parts[:cut]), frozenset()) - {path}
            if not hits:
                continue
            settled = _settle(path, hits)
            if settled is None:
                ambiguous.add(name)
            else:
                files |= settled
            break
    return Resolution(frozenset(files), tuple(sorted(ambiguous)))


def derive(root: Path, paths: Sequence[str]) -> dict[str, Resolution]:
    """Derive every file's imports among `paths`, each path relative to `root`.

    A file that cannot be read raises from `read_text` (`OSError`, or `UnicodeDecodeError` for a
    file that is not UTF-8) and is not skipped, because a missing row reads as a module that
    imports nothing.

    Returns:
        One `Resolution` per path, in `paths` order.

    """
    table = index(paths)
    return {
        path: resolve(path, import_names((root / path).read_text(encoding="utf-8")), table)
        for path in paths
    }
