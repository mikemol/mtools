# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The population: which `.py` files are a tree's corpus, and how a caller's root resolves.

Moved from substrate's `substrate/corpus.py` (N-a row 2). Its suite, `corpus_selftest`, is ported
to `tests/test_corpus.py`.

⚑⚑⚑ THE ROOT IS THE CALLER'S, ALWAYS, AND HAS NO DEFAULT. substrate defined
`ROOT = Path(__file__).absolute().parent.parent`: its repo root in place, and the virtualenv's
lib directory once installed. Every importer that leaned on the default — 173 of them — would
then have censused site-packages, and nothing would have failed; a well-formed answer about the
wrong tree. So `roots`, `resolve_root` and `py_files` take `root` as a REQUIRED keyword. Calling
without it is a TypeError at the call site, which is the refusal the letter asked for, made
unconstructible rather than detected.

⚑⚑ THE SKIP POLICY IS SPLIT. `GENERIC_SKIP_DIRS` (virtualenvs, caches, VCS, editor snapshots) is
true of every tree and travels. substrate's `agda` and `docs` are substrate's own trees, so they
are the caller's `skip` argument, not a constant here.

⚑ `absolute()`, NEVER `resolve()`: `resolve()` follows symlinks, and bazel's convenience links
are symlinks whose NAMES are how they are excluded.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Collection

# Top-level directories that are never a tree's own source, whatever the tree.
GENERIC_SKIP_DIRS = frozenset({"node_modules", "__pycache__", ".venv", ".git", ".edit-snapshots"})

# ⚑ GENERATED OUTPUT TREES ARE NOT THE CORPUS: a machine-derived copy of a source file reads
# exactly like the source. Measured in substrate: mutation-testing copies under `bazel-bin/`
# buried the one real definition under 135KB of hits. Matched as whole PATH COMPONENTS, so
# `rebuild/` and `buildtools/` are unaffected.
GENERATED_DIRS = frozenset(
    {
        "bazel-bin",
        "bazel-out",
        "bazel-testlogs",
        "bazel-genfiles",
        "build",
        "dist",
        "_build",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".nox",
        ".eggs",
    }
)

# Matched as whole path COMPONENTS, like GENERATED_DIRS.
_SKIP_PARTS = frozenset(
    {".edit-snapshots", "__pycache__", ".venv", "site-packages", "node_modules", "_build", ".git"}
)

# bazel's convenience symlinks are `bazel-<workspace>`: a set cannot enumerate them.
_BAZEL_LINK = "bazel-"


class PopulationError(Exception):
    """A requested root resolved to nothing — raised rather than silently emptied.

    ⚑ The message names BOTH trees searched, because the defect it reports is a caller believing
    one was consulted when the other answered.
    """

    def __init__(self, requested: str, root: Path) -> None:
        """Name what was asked for and both trees that were searched."""
        super().__init__(f"no such path in the current directory or in {root}: {requested}")


def excluded(rel: Path) -> bool:
    """Report whether a root-relative directory is outside the corpus.

    ⚑ Public, because the exclusion rule is the contract several tools must agree with. It
    matches path COMPONENTS, never substrings, and is relative to the requested root: a caller
    who NAMES a tree under site-packages still reaches it.

    Returns:
        True when any component is a skipped, generated or bazel-link directory.

    """
    parts = set(rel.parts)
    return (
        bool(parts & _SKIP_PARTS)
        or bool(parts & GENERATED_DIRS)
        or any(p.startswith(_BAZEL_LINK) for p in parts)
    )


def roots(*, root: Path, skip: Collection[str] = ()) -> tuple[str, ...]:
    """Discover the top-level directories that make up the corpus of `root`.

    ⚑ The skip vocabulary applies at the ROOT level too: a generated tree that is a top-level
    entry becomes its own root, and the component check below it would never see its name.

    Returns:
        the sorted names of `root`'s corpus directories.

    """
    skipped = GENERIC_SKIP_DIRS | frozenset(skip)
    return tuple(
        sorted(
            d.name
            for d in root.iterdir()
            if d.is_dir()
            and not d.name.startswith(".")
            and d.name not in skipped
            and d.name not in GENERATED_DIRS
            and not d.name.startswith(_BAZEL_LINK)
        )
    )


def resolve_root(requested: str, *, root: Path) -> Path:
    """Resolve one caller-supplied path: the current directory FIRST, then `root`.

    ⚑ The caller's shell is what they meant, so CWD wins; `root` is a fallback that can only
    widen what a caller reaches, never redirect it. Neither answering is a fact about the query.

    Returns:
        the absolute path the request names.

    Raises:
        PopulationError: when neither the current directory nor `root` has the path.

    """
    path = Path(requested)
    if path.is_absolute():
        return path
    here = (Path.cwd() / requested).absolute()
    if here.exists():
        return here
    there = root / requested
    if there.exists():
        return there
    raise PopulationError(requested, root)


def py_files(*requested: str, root: Path, skip: Collection[str] = ()) -> list[str]:
    """Return every `.py` file under the requested paths, or under all of `root`'s corpus.

    Returns:
        the sorted file paths.

    """
    out: list[str] = []
    for name in requested or roots(root=root, skip=skip):
        base = resolve_root(name, root=root)
        if base.is_file():
            out.append(str(base))
            continue
        for directory, _sub, files in os.walk(base):
            if excluded(Path(directory).relative_to(base)):
                continue
            out.extend(str(Path(directory) / f) for f in files if f.endswith(".py"))
    return sorted(out)
