# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Say whether the reservation loop has CONVERGED, or is silently running on the floor.

Ported from paperkit's `tools/mem_converge.py` (paperkit:W142). Behaviour unchanged except the
no-argument usage line (paperkit printed the last line of its own docstring).

The learning loop (observe, harvest, project, size) warms up: a first pass runs unsized and
deposits peaks, a later pass is sized from them. Nothing said when that warm-up was DONE, so a
project could sit at the cold-start floor indefinitely and every board stayed green.

CONVERGENCE, as a property of the artifacts rather than a feeling: a project that HAS a grid
(pk_eval cells in its generated BUILD) must have a `def` bucket in its manifest, and every one of
its cells must carry a reservation > 0. ELIGIBILITY FIRST: a project with no grid needs no `def`
bucket, and `mem = 0` is not "sized", it is the floor sentinel.

    python -m mikemol.memres.mem_converge <bazel-external-dir> [<root>] [--check]

Prints one line per project with a grid; exits 1 if any has not converged.

    INSTRUMENT, NOT A GATE. Nothing in paperkit runs this; re-verify its output at each use.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Sequence

# ONE CELL PER LINE, not a paren-bounded scan: a site string can CONTAIN a `)`, so
# `pk_eval\(name[^)]*` would stop inside the site and never reach the `mem` attr.
_EVAL = re.compile(r"^pk_eval\(name.*$", re.MULTILINE)
_MEM = re.compile(r"mem = (\d+)")
_PROJECT = re.compile(r"bib\.project\(([^)]*)\)")
_NAME = re.compile(r'name\s*=\s*"paperkit_([^"]+)"')
_PATH = re.compile(r'project\s*=\s*"([^"]+)"')

type Survey = list[tuple[str, int, int, int | None]]


def _group(match: re.Match[str], index: int) -> str:
    """Take one group of a match.

    Returns:
        The group's text, typed `str` (the standard library types it `str | Any`).

    """
    return cast("str", match.group(index))


def _read(path: Path) -> str | None:
    """Read a text file.

    Returns:
        Its text, or None when it cannot be read.

    """
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def _declared_path(module: Path, proj: str) -> str | None:
    """Read the project path MODULE.bazel declares for `proj` (its own name-to-path mapping).

    Returns:
        The declared `project = "..."`, or None when `module` is unreadable or does not declare
        `proj`.

    """
    text = _read(module)
    if text is None:
        return None
    for match in _PROJECT.finditer(text):
        body = _group(match, 1)
        name = _NAME.search(body)
        path = _PATH.search(body)
        if name is not None and path is not None and _group(name, 1) == proj:
            return _group(path, 1)
    return None


def _manifest_rel(root: Path, proj: str) -> str:
    """Resolve `<project path>/mem.json` through MODULE.bazel's own name-to-path declaration.

    A project's NAME is not its PATH, and MODULE.bazel owns the mapping. An undeclared project is
    a finding about the OWNER: it is named on stderr, never silently guessed.

    Returns:
        `mem.json` for the root project (`project = "."`), else `<path>/mem.json`; the path
        falls back to the project's name when it is undeclared.

    """
    module = root / "MODULE.bazel"
    path = _declared_path(module, proj) if module.is_file() else None
    if path is None:
        sys.stderr.write(
            f"mem-converge: {proj} is not declared in MODULE.bazel - falling back to its name as "
            "a path, which is the very conflation this function exists to avoid\n",
        )
        path = proj
    return "mem.json" if path == "." else f"{path}/mem.json"


def _def_bucket(manifest: Path) -> int | None:
    """Read the `def` bucket of a manifest file.

    Returns:
        The `def` value when it is an int; None when the file is absent, unreadable, not JSON,
        or has no int `def`.

    """
    text = _read(manifest) if manifest.is_file() else None
    if text is None:
        return None
    try:
        data = cast("dict[str, object]", json.loads(text))
    except ValueError:
        return None
    bucket = data.get("def")
    return bucket if isinstance(bucket, int) else None


def survey(external: Path, root: Path) -> Survey:
    """Survey every external `*paperkit_*` repo that has a grid.

    A cell is AT THE FLOOR when it has no `mem` attr at all or `mem = 0` (the unmeasured
    sentinel); only a positive value is a learned reservation.

    Returns:
        `[(project, cells, floor_cells, def_bucket)]` for every project with a grid.

    """
    out: Survey = []
    for repo in sorted(external.glob("*paperkit_*")):
        text = _read(repo / "BUILD.bazel") if (repo / "BUILD.bazel").is_file() else None
        cells = cast("list[str]", _EVAL.findall(text)) if text is not None else []
        if not cells:
            continue
        proj = repo.name.split("paperkit_")[-1]
        floor = 0
        for cell in cells:
            mem = _MEM.search(cell)
            if mem is None or _group(mem, 1) == "0":
                floor += 1
        bucket = _def_bucket(root / _manifest_rel(root, proj))
        out.append((proj, len(cells), floor, bucket))
    return out


def main(argv: Sequence[str] | None = None) -> int:
    """Print one convergence line per grid project; exit 1 if any has not converged.

    Returns:
        0 when all converged; 1 when some have not; 2 when no directory was given or no project
        has a grid.

    """
    args = [arg for arg in (sys.argv[1:] if argv is None else argv) if not arg.startswith("--")]
    if not args:
        sys.stderr.write("usage: mem_converge.py <bazel-external-dir> [<root>] [--check]\n")
        return 2
    rows = survey(Path(args[0]), Path(args[1]) if len(args) > 1 else Path.cwd())
    if not rows:
        sys.stderr.write("mem-converge: no project has a grid - nothing to converge\n")
        return 2
    bad: list[str] = []
    for proj, cells, floor, bucket in rows:
        ok = bucket is not None and floor == 0
        shown = bucket if bucket is not None else "MISSING"
        verdict = "converged" if ok else "NOT CONVERGED"
        sys.stdout.write(
            f"  {proj:<11} cells={cells:<7} at-floor={floor:<7} def={shown!s:<6} {verdict}\n",
        )
        if not ok:
            bad.append(proj)
    if bad:
        sys.stderr.write(
            f"mem-converge: {len(bad)} of {len(rows)} project(s) have NOT converged: "
            f"{', '.join(bad)} - run an observe pass (--config=memobserve), then "
            "mikemol-mem-harvest + mikemol-mem-project, then refetch\n",
        )
        return 1
    sys.stdout.write(f"mem-converge: all {len(rows)} grid project(s) converged\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
