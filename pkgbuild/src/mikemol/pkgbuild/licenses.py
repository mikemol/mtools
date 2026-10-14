# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""List, and with `--write` fix, the dists that do not ship their license text (W1206, W1145).

    mikemol-wheel licenses ROOT [--write]

Every dist is a top-level directory of ROOT holding a `pyproject.toml`. A dist ships its license
when (1) it holds a `LICENSE` file equal to ROOT's own, (2) its `pyproject.toml` names it with
`license-files = ["LICENSE"]` beside the `license = ...` line, and (3) its build backend is new
enough to read that (`setuptools>=77`, PEP 639: both an SPDX `license` string and `license-files`
need it, so a dist declaring `>=68` was already wrong). The metadata check (`metacheck`, W1205) is
the judge of the built artifact; this is the writer that makes the tree pass it.

⚑ A DRY RUN BY DEFAULT: without `--write` nothing is changed, one JSON line per dist says what
would be, and the exit is 1 if any dist needs it. With `--write` the files are written and the
exit is 0 once they are.

⚑ A LINK IS NEVER READ THROUGH OR WRITTEN: a `LICENSE` that is a symlink is reported `link` and
left alone, and a directory that is a symlink is not a dist (no symlinks, operator 2026-10-02).

CONSUMED BY: `mikemol-wheel licenses` and the new-dist scaffold's check.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

LICENSE = "LICENSE"
FILES_LINE = 'license-files = ["LICENSE"]\n'
WRITE_FLAG = "--write"
MIN_SETUPTOOLS = 77
SETUPTOOLS = re.compile(r"setuptools>=(\d+)")
FLOOR = f"setuptools>={MIN_SETUPTOOLS}"
Row = dict[str, object]
States = tuple[str, str, str]
CLEAN: States = ("ok", "ok", "ok")


def dists_in(root: Path) -> list[Path]:
    """Find the dists of ROOT: the top-level directories that hold a `pyproject.toml`.

    ⚑ A DIRECTORY THAT IS A SYMLINK IS NOT A DIST: bazel's convenience link `bazel-<repo>` points
    back at the checkout, holds its `pyproject.toml`, and was the first thing the real run listed.

    Returns:
        their directories, in name order.

    """
    return sorted(p.parent for p in root.glob("*/pyproject.toml") if not p.parent.is_symlink())


def license_state(dist: Path, wanted: bytes) -> str:
    """Say whether the dist holds a LICENSE equal to the root's.

    Returns:
        `ok`, `missing`, `differs` or `link`.

    """
    target = dist / LICENSE
    if target.is_symlink():
        return "link"
    if not target.is_file():
        return "missing"
    return "ok" if target.read_bytes() == wanted else "differs"


def _license_index(lines: Sequence[str]) -> int | None:
    """Find the `license = ...` line of the project table.

    Returns:
        its index, or None when there is none.

    """
    for place, line in enumerate(lines):
        if line.startswith(("license =", "license=")):
            return place
    return None


def files_state(dist: Path) -> str:
    """Say whether the dist's pyproject names its license file.

    Returns:
        `ok`, `missing` (a license line and no `license-files`) or `no-license-line`.

    """
    lines = (dist / "pyproject.toml").read_text(encoding="utf-8").splitlines(keepends=True)
    if any(line.startswith("license-files") for line in lines):
        return "ok"
    return "missing" if _license_index(lines) is not None else "no-license-line"


def _older(found: re.Match[str]) -> bool:
    """Say whether one `setuptools>=N` is below the minimum.

    Returns:
        True when N is below the minimum.

    """
    return int(found.group(1)) < MIN_SETUPTOOLS


def backend_state(dist: Path) -> str:
    """Say whether the dist's declared setuptools is new enough for PEP 639.

    Returns:
        `ok`, or `old` when a `setuptools>=N` below the minimum is declared.

    """
    text = (dist / "pyproject.toml").read_text(encoding="utf-8")
    return "old" if any(_older(m) for m in SETUPTOOLS.finditer(text)) else "ok"


def write_files_line(dist: Path) -> None:
    """Insert `license-files = ["LICENSE"]` right after the `license = ...` line."""
    path = dist / "pyproject.toml"
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    place = _license_index(lines)
    if place is not None:
        lines.insert(place + 1, FILES_LINE)
        path.write_text("".join(lines), encoding="utf-8")


def _raised(found: re.Match[str]) -> str:
    """Replace one `setuptools>=N` by itself, or by the floor when N is below it.

    Returns:
        the text to put in its place.

    """
    return FLOOR if _older(found) else found.group(0)


def write_backend(dist: Path) -> None:
    """Raise every `setuptools>=N` below the minimum to the minimum."""
    path = dist / "pyproject.toml"
    path.write_text(SETUPTOOLS.sub(_raised, path.read_text(encoding="utf-8")), encoding="utf-8")


def states_of(dist: Path, wanted: bytes) -> States:
    """Read the three states of one dist.

    Returns:
        the license file's, the `license-files` line's and the backend's.

    """
    return license_state(dist, wanted), files_state(dist), backend_state(dist)


def fix(dist: Path, wanted: bytes, states: States) -> None:
    """Write what the states say is missing: the LICENSE copy, the line, the backend floor."""
    if states[0] in {"missing", "differs"}:
        (dist / LICENSE).write_bytes(wanted)
    if states[1] == "missing":
        write_files_line(dist)
    if states[2] == "old":
        write_backend(dist)


def run(args: Sequence[str]) -> int:
    """Run `ROOT [--write]`: one JSON line per dist.

    Returns:
        0 when every dist ships its license (after `--write`, if given), 1 when one does not, 2
        for a usage error or a root with no LICENSE.

    """
    words = [a for a in args if a != WRITE_FLAG]
    if len(words) != 1 or not (Path(words[0]) / LICENSE).is_file():
        sys.stderr.write("usage: mikemol-wheel licenses ROOT [--write]  (ROOT holds a LICENSE)\n")
        return 2
    root = Path(words[0])
    wanted = (root / LICENSE).read_bytes()
    write = WRITE_FLAG in args
    pending = 0
    for dist in dists_in(root):
        before = states_of(dist, wanted)
        if write:
            fix(dist, wanted, before)
        after = states_of(dist, wanted) if write else before
        row: Row = {
            "dist": dist.name,
            "license": before[0],
            "license-files": before[1],
            "backend": before[2],
            "written": after != before,
        }
        sys.stdout.write(json.dumps(row, sort_keys=True) + "\n")
        pending += int(after != CLEAN)
    return 1 if pending else 0
