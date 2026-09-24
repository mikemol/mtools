# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The tree a reader was GIVEN — never one it derived from its own location on disk.

Moved from substrate's `substrate/tree_root.py` (N-a row 2); its suite is ported to
`tests/test_tree_root.py`.

⚑⚑ TWO QUESTIONS, TWO AUTHORITIES. *Which tree is the caller asking about?* is an INPUT:
`from_argv` reads a required `--root` and refuses when it is absent. *Where is a package's own
code and data?* is package semantics: `package_files` asks `importlib.resources`, which is right
under a source checkout, a wheel, a zip import and a symlink alike.

⚑⚑⚑ `package_files` NOW NAMES ITS PACKAGE. substrate's asked for `files("substrate")`, which was
correct only while the module lived in substrate: moved here unchanged it would answer with THIS
distribution's files, the wrong-tree defect `corpus.ROOT` had, in a new place (the letter's §3
asked for exactly this check). The caller says whose files it means.

⚑ The labelling rule and the tree that was walked travel together as one `TreeRoot`, so a label
can never be measured against a different root than the walk (substrate's `relative_to` crash
class, gates G245/G249/G252).
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

#: The flag that names the tree. Required — see `from_argv`.
ROOT_FLAG = "--root"

#: What a caller sees when no tree was named. It states the remedy.
NO_ROOT = (
    f"no {ROOT_FLAG} given — this reader censuses the tree it is HANDED, never one it derives. "
    f"Pass {ROOT_FLAG} <dir>."
)


class RootError(ValueError):
    """No tree was named, or the named tree does not exist.

    ⚑ An unresolvable root is a fact about the query: a root that resolved to nothing walked
    nothing, and the caller fell through to a default corpus about the wrong repository.
    """


class TreeRoot(NamedTuple):
    """One tree, and the labelling that belongs to it."""

    path: Path

    def label(self, found: Path | str) -> str:
        """Return `found` relative to this tree, or whole when it lies outside.

        ⚑ Tolerant in both directions: a foreign path is returned whole rather than raising (the
        crash class), and an already-relative label passes through unchanged.

        Returns:
            the label.

        """
        text = str(found)
        prefix = str(self.path)
        prefix = prefix if prefix.endswith("/") else prefix + "/"
        return text.removeprefix(prefix)

    def holds(self, found: Path | str) -> bool:
        """Report whether `found` lies inside this tree.

        ⚑ The predicate `label` deliberately cannot express, and matched on a separator: `/repo` is
        a string prefix of `/repository`, which is not inside it.

        Returns:
            True when `found` is below this tree's path.

        """
        return str(found).startswith(str(self.path).rstrip("/") + "/")


def of(path: Path | str) -> TreeRoot:
    """Return the `TreeRoot` for `path`, refusing a tree that does not exist.

    Returns:
        the tree, absolute.

    Raises:
        RootError: when `path` is not a directory.

    """
    absolute = Path(path).absolute()
    if not absolute.is_dir():
        msg = f"{path!r} is not a directory — {NO_ROOT}"
        raise RootError(msg)
    return TreeRoot(absolute)


def from_argv(argv: Sequence[str]) -> tuple[TreeRoot, list[str]]:
    """Return the named tree and the remaining arguments, REFUSING when `--root` is absent.

    ⚑⚑ Required, with no fallback: a CWD default answers about wherever the shell was, and a
    `__file__` default about the tool's own tree. The flag and its operand are consumed, in any
    position, and a flag is never taken as the operand.

    Returns:
        the tree, and argv without the flag and its operand.

    Raises:
        RootError: when `--root` is absent, has no operand, or names no directory.

    """
    rest = list(argv)
    if ROOT_FLAG not in rest:
        raise RootError(NO_ROOT)
    at = rest.index(ROOT_FLAG)
    operand = rest[at + 1 :][:1]
    if not operand or operand[0].startswith("-"):
        msg = f"{ROOT_FLAG} needs a directory — {NO_ROOT}"
        raise RootError(msg)
    del rest[at : at + 2]
    return of(operand[0]), rest


class NotOnePackageDirError(ValueError):
    """The named package has no single directory: it is a namespace package, spread over many.

    ⚑ MEASURED WHILE PORTING: `files()` on a namespace package returns a `MultiplexedPath`, whose
    `str` is `MultiplexedPath('…')`, not a path. `Path(str(...))` turned that into a well-formed
    path that names no directory at all. substrate never met it because its package has an
    `__init__.py`; the refusal keeps the next namespace package from meeting it silently.
    """


def package_files(package: str) -> Path:
    """Return the directory holding the named PACKAGE's own files, per the runtime.

    ⚑ It is not a repo root and must never be used as one: a package's files are the package's;
    the tree a caller asks about is `from_argv`'s answer.

    Returns:
        the package's directory, as the import system resolves it.

    Raises:
        NotOnePackageDirError: when the package is not a single directory on disk.

    """
    found = files(package)
    if not isinstance(found, Path):
        msg = f"{package!r} is not one directory (a namespace package?): {found!r}"
        raise NotOnePackageDirError(msg)
    return found


def census(roots: Iterable[Path | str]) -> list[TreeRoot]:
    """Return a `TreeRoot` for each of `roots`, refusing on the first that does not exist.

    ⚑ Refusing rather than skipping: a silently dropped root shrinks a population without
    shrinking the denominator anyone reports.

    Returns:
        one tree per root, in order.

    """
    return [of(root) for root in roots]
