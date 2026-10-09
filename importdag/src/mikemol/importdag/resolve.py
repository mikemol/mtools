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

⚑⚑ AN AMBIGUOUS ABSOLUTE NAME IS NEVER GUESSED, ONLY REPORTED, WITH ITS CANDIDATES. Two files can
answer one name (`scripts/a.py` and `tools/a.py` both answer `a`; a package `gcalc/` and a module
`gcalc.py` both answer `gcalc`). A name with several candidates resolves to the one beside the
importing file (Python's own reading of a bare sibling import) when exactly one is there, and
otherwise is returned as `Unsettled(name, candidates)` with no edge: the NAME is the dotted prefix
that is ambiguous, so one decision settles every importer, and the candidates say what to choose
between. The caller owns what an unsettled name means (a blocker to be resolved, not a skipped
edge to be forgotten). A decision is data: `declared` maps a name to the file it is declared to
mean, and it is honoured ONLY when that file is one of the candidates, so a stale declaration
cannot pin a name to a file that no longer answers it.

⚑⚑ IMPORTING A MODULE ALSO IMPORTS ITS PACKAGES' `__init__.py` (W792). `import a.b.c` runs
`a/__init__.py` and `a/b/__init__.py` before `c`, so each resolved file carries an edge to the
`__init__.py` of every package directory above it, outermost first. Measured: debtplan called
nemik's `adapter.py` ready while mypy's closure of it also reported `src/nemik/__init__.py`, because
that implicit import was not an edge. ⚑ ONLY THE DIRECTORIES THE NAME ITSELF SPANS COUNT for an
absolute import (`import b.c` found at `src/a/b/c.py` runs `b/__init__.py`, never `src/` or `a/`,
whose roles this suffix index cannot know), and a relative one counts from its base directory. A
directory with no `__init__.py` is a namespace package and contributes nothing, and a file is never
its own import, so a package's `__init__.py` importing its own submodule adds no edge to itself.

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
class Unsettled:
    """A dotted name several files could answer, none beside the importer: not guessed."""

    name: str
    candidates: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Resolution:
    """The indexed files one module imports, and the names it could not settle."""

    files: frozenset[str]
    ambiguous: tuple[Unsettled, ...]


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
    path: str, name: str, idx: Index, declared: Mapping[str, str]
) -> tuple[frozenset[str], Unsettled | None, int]:
    """Resolve one absolute name at its longest dotted prefix that any file answers.

    Returns:
        The files the name means, the `Unsettled` prefix when several files answer it and none
        is beside `path` or declared, and how many dotted parts the matched prefix spans (0 when
        nothing matched). A declaration is honoured only when it names one of the candidates. A
        file is never its own import.

    """
    parts = name.split(".")
    for cut in range(len(parts), 0, -1):
        prefix = ".".join(parts[:cut])
        hits = idx.names.get(prefix, frozenset()) - {path}
        if not hits:
            continue
        settled = _settle(path, hits)
        if settled is not None:
            return settled, None, cut
        pinned = declared.get(prefix)
        if pinned in hits:
            return frozenset({pinned}), None, cut
        return frozenset(), Unsettled(prefix, tuple(sorted(hits))), cut
    return frozenset(), None, 0


def _initializers(path: str, target: str, start: int, files: frozenset[str]) -> frozenset[str]:
    """Name the package `__init__.py` files that importing `target` also runs.

    Returns:
        For each directory of `target`'s parent from index `start` on, cumulative from the
        outermost, that directory's `__init__.py` when the tree has one. The importer itself is
        left out: a file is never its own import.

    """
    parts = PurePosixPath(target).parent.parts
    first = max(start, 0)
    markers = (
        "/".join((*parts[: first + cut], PACKAGE_FILE)) for cut in range(1, len(parts) - first + 1)
    )
    return frozenset(m for m in markers if m in files and m != path)


def _spanned(target: str, depth: int) -> int:
    """Count the leading parent directories an absolute name of `depth` parts does NOT span.

    Returns:
        How many directories above the ones the name spans: a module `y/c.py` named `y.c` spans one
        directory (`y`), and a package `y/__init__.py` named `y` spans one too.

    """
    parts = PurePosixPath(target).parent.parts
    named = depth if PurePosixPath(target).name == PACKAGE_FILE else depth - 1
    return len(parts) - named


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


def resolve(
    path: str,
    refs: Iterable[Reference],
    idx: Index,
    declared: Mapping[str, str] | None = None,
) -> Resolution:
    """Resolve the references of the file `path` against an index.

    An absolute name is tried at its longest dotted prefix first, so `import a.b.c` finds
    `a/b/c.py` and not `a.py`, and an attribute (`a.b.thing`) falls back to the module that holds
    it. A relative reference is a direct lookup from the importer's directory.

    Returns:
        The indexed files the references mean, and the absolute names left unsettled, once each,
        sorted by name. `declared` maps an ambiguous name to the candidate it is declared to mean.

    """
    pins = declared or {}
    files: set[str] = set()
    unsettled: dict[str, Unsettled] = {}
    for ref in refs:
        if ref.level:
            base = len(PurePosixPath(path).parent.parts) - (ref.level - 1)
            for target in _relative(path, ref, idx.files):
                files |= {target, *_initializers(path, target, base - 1, idx.files)}
            continue
        found, left, depth = _absolute(path, ref.name, idx, pins)
        for target in found:
            files |= {target, *_initializers(path, target, _spanned(target, depth), idx.files)}
        if left is not None:
            unsettled[left.name] = left
    return Resolution(frozenset(files), tuple(unsettled[name] for name in sorted(unsettled)))


def derive(
    root: Path, paths: Sequence[str], declared: Mapping[str, str] | None = None
) -> dict[str, Resolution]:
    """Derive every file's imports among `paths`, each path relative to `root`.

    A file that cannot be read raises from `read_text` (`OSError`, or `UnicodeDecodeError` for a
    file that is not UTF-8) and is not skipped, because a missing row reads as a module that
    imports nothing.

    Returns:
        One `Resolution` per path, in `paths` order.

    """
    table = index(paths)
    return {
        path: resolve(path, references((root / path).read_text(encoding="utf-8")), table, declared)
        for path in paths
    }
