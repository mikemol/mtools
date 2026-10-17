# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A card's manifest: the exact repo-relative files it will create or edit, plus a size (W1426).

⚑⚑ EXACT FILES, NEVER A GLOB, NEVER A DIRECTORY. The manifest exists so a reader can compute, by
plain set intersection, whether two cards can be stacked (nemik:W613, the decision relayed by
github-8f 2026-10-17). A directory entry that "means everything under it" is a glob by another
name and would make every overlap a guess, so a directory, a glob character, an absolute path, a
`..` step, a link and a duplicate are each refused at write time, naming the path.

⚑ THE SIZE CLASS IS A CLOSED ENUM: `small` (about 50 changed lines or fewer), `medium` (about 300
or fewer), `large` (atomize instead: nemik warns on it like a missing manifest). It is a claim the
card makes before the work, which `mikemol-commit --stack` compares to the real diff (W1427).

THE PATHS MAY NOT EXIST YET: a card that will CREATE a file lists it, so existence is not
required; only a path that exists and is a directory or a link is refused.
"""

from collections.abc import Sequence
from pathlib import Path, PurePosixPath

from mikemol.pathsforward.ops import RefusedError

SIZES = ("small", "medium", "large")
_GLOB_CHARS = frozenset("*?[]{}")


def _fault(path: str, root: Path) -> str:
    """Name what is wrong with one manifest path, or nothing when it is acceptable.

    Returns:
        the first reason, or the empty string.

    """
    pure = PurePosixPath(path)
    actual = root / path
    checks = (
        (not path or path != path.strip(), "is empty or has surrounding spaces"),
        (pure.is_absolute(), "is absolute: a manifest holds repo-relative paths"),
        (".." in pure.parts, "steps outside the repo with '..'"),
        (path.endswith("/"), "ends in '/': a directory is not a file"),
        (bool(_GLOB_CHARS & set(path)), "holds a glob character: name exact files"),
        (actual.is_symlink(), "is a link: a link is never followed"),
        (actual.is_dir(), "is a directory: name the files in it"),
    )
    return next((why for bad, why in checks if bad), "")


def check(paths: Sequence[str], root: Path) -> None:
    """Refuse a manifest that is not a list of distinct exact repo-relative files.

    Raises:
        RefusedError: naming every bad path with its reason, or the first duplicate.

    """
    faults = [f"{path!r} {why}" for path in paths if (why := _fault(path, root))]
    if faults:
        msg = "manifest: " + "; ".join(faults)
        raise RefusedError(msg)
    seen: set[str] = set()
    for path in paths:
        if path in seen:
            msg = f"manifest: {path!r} is listed twice"
            raise RefusedError(msg)
        seen.add(path)
