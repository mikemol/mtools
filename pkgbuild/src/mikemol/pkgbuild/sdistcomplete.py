# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Name the files under a dist's `tests/` that its sdist does not carry (W1230).

⚑ AN SDIST OF A DIST'S TESTS IS WHAT AN INDEX USER RUNS THEM FROM. setuptools adds only
`tests/test*.py` to an sdist by default, so `conftest.py`, fixtures and data files silently drop out
and the suite fails to collect for whoever unpacks it (measured on six dists, W1228). This compares
the files the commit tracks under `tests/` with the members of the built sdist, so the omission is
a named finding at release time instead of a failure a user finds.

⚑ ONLY WHAT THE COMMIT CARRIES IS COUNTED: caches are not files of the commit, and a file under
`tests/` the sdist has but the tree lacks is not a finding.

CONSUMED BY: `relcheck.row_of`, the publish preflight (W1151).
"""

from __future__ import annotations

import tarfile
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

JUNK = frozenset({"__pycache__", ".pytest_cache"})
SHOWN = 8


def tracked_tests(dist: Path) -> list[str]:
    """List the files under the dist's `tests/`, relative to the dist.

    Returns:
        the paths in name order; empty when there is no `tests/` directory.

    """
    root = dist / "tests"
    if not root.is_dir():
        return []
    found = (p for p in root.rglob("*") if p.is_file() and not JUNK & set(p.parts))
    return sorted(p.relative_to(dist).as_posix() for p in found)


def sdist_members(sdist: Path) -> set[str]:
    """List the files of an sdist, relative to its single top directory.

    Returns:
        the member paths with the leading `<name>-<version>/` removed.

    """
    with tarfile.open(sdist) as archive:
        names = [m.name for m in archive.getmembers() if m.isfile()]
    return {name.split("/", 1)[1] for name in names if "/" in name}


def missing(dist: Path, sdist: Path) -> list[str]:
    """Find the tracked test files the sdist lacks.

    Returns:
        their paths relative to the dist, in name order.

    """
    carried = sdist_members(sdist)
    return [path for path in tracked_tests(dist) if path not in carried]


def verdict(dist: Path, sdist: Path) -> tuple[str, str]:
    """Judge one dist's sdist.

    Returns:
        `("ok", "")`, or `("failed", why)` naming the first few missing files and the fix.

    """
    lost = missing(dist, sdist)
    if not lost:
        return "ok", ""
    shown = ", ".join(lost[:SHOWN]) + (" ..." if len(lost) > SHOWN else "")
    fix = "add `graft tests` to MANIFEST.in"
    return "failed", f"{len(lost)} test file(s) not in the sdist: {shown} ({fix})"
