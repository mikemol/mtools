# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""What a corpus actually imports, graded against what its manifest declares.

Cleanroomed from substrate's `scratch/_pycodemod_census.py` (`imports`, `_declared_deps`; W43). A
hand-listed dependency set is only as current as its last edit; the set is discoverable from the
source. Each top-level import gets one verdict, never present/absent:

    FIRST-PARTY  a module or package of the corpus itself (a file of that name is in it)
    VENDORED     first-party on disk, but under a path the caller names as vendored
    STDLIB       the standard library: no declaration owed
    DECLARED     third-party, importable, and in the manifest
    UNDECLARED   importable but in NO manifest: works today, breaks on a fresh clone
    MISSING      imported and not importable here

⚑⚑ THE VERDICT IS ABOUT THIS INTERPRETER: importable and MISSING are asked of the running import
system, as in the origin. Run it in the environment the corpus is meant to run in.

⚑ A DISTRIBUTION NAME IS NOT AN IMPORT NAME (`persist-queue` imports as `persistqueue`): the
installed metadata is asked which top-level names a declared distribution provides.

What moved and what did not:

⚑⚑⚑ AN UNREADABLE MANIFEST REFUSES; IT IS NEVER AN EMPTY DECLARATION. The origin read
ROOT/pyproject.toml and returned an empty set on any failure, so every third-party import read
UNDECLARED: a finding manufactured by the probe. The manifest is now an operand, and one that
cannot be read or parsed raises `ManifestError`.

⚑⚑ THE DECLARED MATCH IS CASE-INSENSITIVE ON BOTH SIDES. The origin lowercased the declared names
and compared the import name as written, so `import PIL` could never match the `pil` a declared
`pillow` provides (read at source: `top in declared` against lowercased entries).

⚑⚑ STDLIB IS `sys.stdlib_module_names`, EXACT, before any path heuristic. The origin classified by
where `find_spec` pointed (`site-packages` in the path, the stdlib directory prefix).

⚑ VENDORED IS THE CALLER'S PATH FRAGMENTS; the origin hard-coded `/vendor/` and its own `/eliza/`.
⚑ AN UNREAD FILE IS REPORTED: the origin read with `errors="replace"` and skipped a SyntaxError.
"""

from __future__ import annotations

import ast
import importlib.metadata
import importlib.util
import re
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.pycodemod.sites import Skip

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

FIRST_PARTY = "FIRST-PARTY"
VENDORED = "VENDORED"
STDLIB = "STDLIB"
DECLARED = "DECLARED"
UNDECLARED = "UNDECLARED"
MISSING = "MISSING"
_INIT = "__init__.py"
_SPECIFIER = re.compile(r"[<>=!~\[; @]")
_DIST_INFO = ".dist-info"


class ManifestError(ValueError):
    """The manifest could not be read as a pyproject; nothing is graded against a guess."""


@dataclass(frozen=True, slots=True, order=True)
class ImportUse:
    """One top-level module the corpus imports: its verdict, how many files, and one of them."""

    module: str
    verdict: str
    files: int
    example: str


@dataclass(frozen=True, slots=True)
class ImportUses:
    """The graded top-level imports, and the files that could not be read."""

    rows: list[ImportUse] = field(default_factory=list)
    skipped: list[Skip] = field(default_factory=list)


def _record(value: object) -> dict[str, object]:
    """Rebuild `value` as a string-keyed record with `object` values (hooks' `as_record`).

    Returns:
        the record, or an empty one when `value` is not a mapping.

    """
    if not isinstance(value, dict):
        return {}
    return {str(k): v for k, v in value.items()}


def _strings(value: object) -> list[str]:
    return [v for v in value if isinstance(v, str)] if isinstance(value, list) else []


def _dist_name(requirement: str) -> str:
    return _SPECIFIER.split(requirement.strip(), maxsplit=1)[0]


def _provides(dist: str) -> set[str]:
    """Ask the installed metadata which top-level import names a distribution provides.

    Returns:
        the names, lowercased; none when the distribution is not installed.

    """
    try:
        files = importlib.metadata.files(dist) or []
    except importlib.metadata.PackageNotFoundError:
        return set()
    out: set[str] = set()
    for f in files:
        parts = f.parts
        if len(parts) > 1 and parts[0] not in {"..", ""} and not parts[0].endswith(_DIST_INFO):
            out.add(parts[0].lower())
    return out


def declared_imports(manifest: Path) -> frozenset[str]:
    """Return every import name a pyproject declares, base and extras, lowercased.

    Returns:
        the normalised distribution names and the top-level names each installed one provides.

    Raises:
        ManifestError: when the manifest cannot be read or parsed.

    """
    try:
        doc: object = tomllib.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        msg = f"cannot read {manifest} as a pyproject: {type(exc).__name__}"
        raise ManifestError(msg) from exc
    project = _record(_record(doc).get("project"))
    reqs = _strings(project.get("dependencies"))
    for extra in _record(project.get("optional-dependencies")).values():
        reqs.extend(_strings(extra))
    out: set[str] = set()
    for req in reqs:
        dist = _dist_name(req)
        if dist:
            out.add(dist.replace("-", "_").lower())
            out |= _provides(dist)
    return frozenset(out)


def _tops(tree: ast.Module) -> set[str]:
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
            out.add(node.module.split(".")[0])
    return out


def _parse(path: str) -> ast.Module | Skip:
    try:
        return ast.parse(Path(path).read_text(encoding="utf-8"), filename=path)
    except UnicodeDecodeError as exc:
        return Skip(path, "undecodable", type(exc).__name__)
    except OSError as exc:
        return Skip(path, "unreadable", type(exc).__name__)
    except SyntaxError as exc:
        return Skip(path, "unparseable", type(exc).__name__)


def _ours(paths: Sequence[str]) -> set[str]:
    return {p.parent.name if p.name == _INIT else p.stem for p in map(Path, paths)}


def _verdict(top: str, declared: frozenset[str]) -> str:
    if top in sys.stdlib_module_names or top in sys.builtin_module_names:
        return STDLIB
    try:
        spec = importlib.util.find_spec(top)
    except (ImportError, ValueError):
        spec = None
    if spec is None:
        return MISSING
    return DECLARED if top.lower() in declared else UNDECLARED


def import_census(paths: Sequence[str], manifest: Path, vendored: Iterable[str] = ()) -> ImportUses:
    """Return every top-level module `paths` import, graded against `manifest`.

    ⚑ AN UNREADABLE MANIFEST RAISES `ManifestError` (from `declared_imports`) before any file is
    read: nothing is graded against a guess.

    Returns:
        one row per top-level module, with the skipped files.

    """
    declared = declared_imports(manifest)
    fragments = tuple(vendored)
    out = ImportUses()
    seen: dict[str, list[str]] = {}
    for path in paths:
        tree = _parse(path)
        if isinstance(tree, Skip):
            out.skipped.append(tree)
            continue
        for top in _tops(tree):
            seen.setdefault(top, []).append(path)
    ours = _ours(paths)
    for top, where in sorted(seen.items()):
        if top in ours:
            vend = any(frag in w for w in where for frag in fragments)
            verdict = VENDORED if vend else FIRST_PARTY
        else:
            verdict = _verdict(top, declared)
        out.rows.append(ImportUse(top, verdict, len(where), min(where)))
    return out
