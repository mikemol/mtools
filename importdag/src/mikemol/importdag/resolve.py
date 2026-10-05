# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Resolve the imports of a set of module files against each other, whatever the layout.

`dagderive` reads an engine whose modules are flat stems under one package name. A set of files
from another repository is not that: modules sit under `src/` namespace roots, several packages
share one tree, and a script says `import sibling` bare. A dotted import name there is a SUFFIX of
a path, not a stem, so each file is indexed by every dotted suffix of its own path and an absolute
import is resolved against that index.

⚑⚑ A RELATIVE IMPORT IS EXACT, AND ITS LEVEL IS WHAT SAYS WHERE. `from .. import streams` starts at
the importer's directory, goes up one, and names `streams.py` or the package `streams/` THERE, not
any file called `streams` in the tree. Reading the dots as a bare name would answer `streams` with
every file of that name and report it ambiguous, or settle on the wrong one. A relative reference
is resolved by direct lookup, a package before a module (Python's own precedence), the longest
dotted prefix first (`from .a import b` is `a/b.py`, else `a.py`), and `from . import x` falls back
to the package's own `__init__.py` when `x` is not a module. A level that climbs above the root
resolves to nothing.

⚑⚑ AN AMBIGUOUS ABSOLUTE NAME IS REPORTED, NEVER PICKED. Two files can answer one name
(`scripts/a.py` and `tools/a.py` both answer `a`). `dagderive.stem_index` refuses that outright,
which is right for an engine that must stage every module; a census over a foreign tree must go
on. So a name with several candidates resolves to the one beside the importing file (Python's own
reading of a bare sibling import) when exactly one is there, and otherwise lands in
`Resolution.ambiguous` with no edge. The caller sees what was left unsettled and decides; a skipped
edge loosens an order and can never make a cycle.

⚑ THE TRANSITIVE CLOSURE IS `dagderive.cone`, NOT A SECOND WALK. This module derives edges only.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

INIT = "__init__"
"""A package marker is named by its package, so its own stem is dropped from the module path."""

PACKAGE_FILE = "__init__.py"
"""The file that makes a directory a package."""


@dataclass(frozen=True, slots=True)
class Reference:
    """One module an import statement can mean: its dotted name, and the dots before it.

    `level` is 0 for an absolute import and the number of leading dots for a relative one. An empty
    `name` at a positive level is the package itself, as `from . import x` also imports it.
    """

    level: int
    name: str


@dataclass(frozen=True, slots=True)
class Index:
    """The files of a tree, by every dotted suffix of their paths, and as a set of paths."""

    names: dict[str, frozenset[str]]
    files: frozenset[str]


@dataclass(frozen=True, slots=True)
class Resolution:
    """The indexed files one module imports, and the import names it could not settle."""

    files: frozenset[str]
    ambiguous: tuple[str, ...]


def _from_references(node: ast.ImportFrom) -> set[Reference]:
    """Name the modules one `from` statement can mean, keeping its level.

    Returns:
        The module and each `module.name` at the statement's level; for `from . import x` the
        package itself (an empty name) and `x`.

    """
    module = node.module or ""
    found = {Reference(node.level, module)}
    found.update(
        Reference(node.level, f"{module}.{alias.name}" if module else alias.name)
        for alias in node.names
    )
    return found


def references(text: str) -> frozenset[Reference]:
    """Collect every module `text` imports, read from the syntax tree.

    Returns:
        The names `import a.b` and `from a import b` can mean (`a.b`, and `a` with `a.b`), each at
        level 0, and the same for a relative import at its own level. A text that does not parse
        yields none.

    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return frozenset()
    found: set[Reference] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(Reference(0, alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            found.update(_from_references(node))
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


def index(paths: Iterable[str]) -> Index:
    """Index files by the dotted names they could be imported as.

    Returns:
        Each dotted suffix with every file of `paths` it could name, and the set of the paths.

    """
    listed = list(paths)
    found: dict[str, set[str]] = {}
    for path in listed:
        for name in module_names(path):
            found.setdefault(name, set()).add(path)
    return Index({name: frozenset(files) for name, files in found.items()}, frozenset(listed))


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


def _absolute(
    path: str, name: str, names: Mapping[str, frozenset[str]]
) -> tuple[frozenset[str], bool]:
    """Resolve one absolute name at its longest dotted prefix that any file answers.

    Returns:
        The files the name means, and whether it was left unsettled (several candidates, none
        beside `path`). A file is never its own import.

    """
    parts = name.split(".")
    for cut in range(len(parts), 0, -1):
        hits = names.get(".".join(parts[:cut]), frozenset()) - {path}
        if hits:
            settled = _settle(path, hits)
            return (frozenset(), True) if settled is None else (settled, False)
    return frozenset(), False


def _relative(path: str, ref: Reference, files: frozenset[str]) -> frozenset[str]:
    """Resolve one relative reference by direct lookup from the importer's directory.

    Returns:
        The file the reference names: the package `x/__init__.py` before the module `x.py`, the
        longest dotted prefix first, falling back to the package's own `__init__.py`. Nothing when
        the level climbs above the root or no file is there. A file is never its own import.

    """
    here = PurePosixPath(path).parent.parts
    up = ref.level - 1
    if up > len(here):
        return frozenset()
    base = here[: len(here) - up]
    named = tuple(ref.name.split(".")) if ref.name else ()
    for cut in range(len(named), -1, -1):
        stem = (*base, *named[:cut])
        options = ["/".join((*stem, PACKAGE_FILE))]
        if cut:
            options.append("/".join(stem) + ".py")
        for option in options:
            if option in files and option != path:
                return frozenset({option})
    return frozenset()


def resolve(path: str, refs: Iterable[Reference], idx: Index) -> Resolution:
    """Resolve the references of the file `path` against an index.

    An absolute name is tried at its longest dotted prefix first, so `import a.b.c` finds
    `a/b/c.py` and not `a.py`, and an attribute (`a.b.thing`) falls back to the module that holds
    it. A relative reference is a direct lookup from the importer's directory.

    Returns:
        The indexed files the references mean, and the absolute names that could mean several with
        none beside `path`, sorted.

    """
    files: set[str] = set()
    ambiguous: set[str] = set()
    for ref in refs:
        if ref.level:
            files |= _relative(path, ref, idx.files)
            continue
        found, unsettled = _absolute(path, ref.name, idx.names)
        files |= found
        if unsettled:
            ambiguous.add(ref.name)
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
        path: resolve(path, references((root / path).read_text(encoding="utf-8")), table)
        for path in paths
    }
