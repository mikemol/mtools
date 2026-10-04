# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Collect whatever cell peaks EXIST and fold them into a project's observation store.

Ported from paperkit's `tools/mem_harvest.py` (paperkit:W142), behaviour unchanged.

WHY THIS IS NOT A BAZEL ACTION. Having `mem_learn` depend on every cell whose peak it wants
inverts the economics: a def grid of tens of thousands of pk_eval cells would first require
running the sweep UNSIZED. A measurement must not cost what it is meant to save. So the cells
write their peaks as a SIDE EFFECT of work that runs anyway, and this is a reading over the output
tree afterwards. The measurement WARMS UP: pass 1 runs on the cold-start floor and deposits peaks,
the harvest folds them in, pass 2 is sized from measurement.

MERGE, NEVER REPLACE. A harvest sees only the cells that happened to run. Each key is only ever
raised into place, never removed by absence; the store's monotone-max upsert enforces it.

    mikemol-mem-harvest <project-dir> [--db FILE] [--bazel-out DIR] [--run ID]
"""

from __future__ import annotations

import sys
from contextlib import closing
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.memres import mem_db
from mikemol.memres.mem_learn import BYTES_PER_MB, resolution

if TYPE_CHECKING:
    from collections.abc import Sequence

type Measured = dict[tuple[str, str, str], float]


def _read_peak(path: Path) -> str | None:
    """Read one peak file.

    Returns:
        The stripped text, or None when it cannot be read (a directory, a permission error).

    """
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return None


def peaks_for(project: str, tree: Path) -> Measured:
    """Find the readable `.peak` files under `tree` that belong to `project`.

    MAX, not mean: a grid's cells run concurrently and each must fit, so the reservation a claim
    needs is its worst cell, not its typical one. The result is keyed by CELL (a def claim has
    many), so the store can recompute a manifest for a different bucket ladder without
    re-measuring.

    Returns:
        `{(resolution, claim, cell): max_mb}`; unreadable files, `unavailable:*` files and
        zero readings carry no measurement and are absent.

    """
    out: Measured = {}
    for path in tree.rglob("*.peak"):
        if f"paperkit_{project}" not in str(path) and f"/{project}/" not in str(path):
            continue
        res, claim = resolution(path.stem)
        raw = _read_peak(path)
        if res is None or raw is None or not raw.isdigit():
            continue
        mb = int(raw) / BYTES_PER_MB
        if mb <= 0:
            continue
        key = (res, claim, path.stem)
        out[key] = max(out.get(key, 0), mb)
    return out


def deposit(db: Path, project: str, measured: Measured, run: str = "") -> int:
    """Record observations in the store; MONOTONICITY IS THE DATABASE'S JOB.

    A hand-written merge over `mem.json` once lowered a manifest from 512 with 41 overrides to
    256 with 2 on a narrow pass. `bytes = max(bytes, excluded.bytes)` is the same rule as one
    clause the database enforces.

    Returns:
        The number of observations offered to the store.

    """
    rows = [
        (project, res, claim, cell, int(mb * BYTES_PER_MB))
        for (res, claim, cell), mb in measured.items()
    ]
    with closing(mem_db.connect(db)) as conn:
        return mem_db.record(conn, rows, run=run)


def _opt(argv: Sequence[str], name: str, default: str | None = None) -> str | None:
    """Find the value after `name` in `argv`.

    Returns:
        The following argument, or `default` when `name` is absent or the last argument.

    """
    if name in argv and argv.index(name) + 1 < len(argv):
        return argv[argv.index(name) + 1]
    return default


def main(argv: Sequence[str] | None = None) -> int:
    """Harvest the peaks under the output tree of `<project-dir>` into the store.

    The project is `root` when the directory is named `paperkit`, else the directory's name; an
    absent tree or an absent measurement is not an error.

    Returns:
        0 on success or when there is nothing to harvest; 2 when no project dir was given.

    """
    args = sys.argv[1:] if argv is None else argv
    if not args:
        sys.stderr.write(
            "usage: mikemol-mem-harvest <project-dir> [--db FILE] [--bazel-out DIR] [--run ID]\n",
        )
        return 2
    proj_dir = Path(args[0])
    project = "root" if proj_dir.resolve().name == "paperkit" else proj_dir.name
    repo = proj_dir.resolve() if project == "root" else proj_dir.resolve().parent
    tree = Path(_opt(args, "--bazel-out") or (repo / "bazel-out"))
    db = Path(_opt(args, "--db") or (repo / "mem.sqlite"))
    if not tree.exists():
        sys.stderr.write(f"mem-harvest: no output tree at {tree} - nothing to harvest\n")
        return 0
    measured = peaks_for(project, tree)
    if not measured:
        sys.stderr.write(
            f"mem-harvest: {project}: no readable peaks (run under --config=memobserve first)\n",
        )
        return 0
    count = deposit(db, project, measured, run=_opt(args, "--run", "") or "")
    resolutions = sorted({res for res, _, _ in measured})
    sys.stderr.write(f"mem-harvest: {project}: {count} observation(s) over {resolutions} -> {db}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
