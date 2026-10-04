# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Project `mem.sqlite` to `mem.json`, the Starlark-readable build input.

Ported from paperkit's `tools/mem_project.py` (paperkit:W142). Behaviour unchanged except the
staleness message, which names the console script instead of `python3 tools/mem_project.py`.

WHY TWO ARTIFACTS. The store keeps one row per observation so a bucket can say what it rests on;
the generator reads a repo-rule input at FETCH time and only ever wants the number. A new cell
changes the DB's bytes but not the manifest it projects to, so watching the DB would re-fetch the
rule once per deposited observation to regenerate a BUILD file whose content never moved. Watching
the projection invalidates exactly when a RESERVATION changes.

GENERATED, never authored: `mem.json` is derived state, and the freshness check is `--check`:
regenerate and byte-compare, so a drifted projection is named rather than silently trusted.

    mikemol-mem-project <db> <project> <out.json>          write the projection
    mikemol-mem-project <db> <project> <out.json> --check  exit 1 if it would change
"""

from __future__ import annotations

import json
import sys
from contextlib import closing
from pathlib import Path
from typing import TYPE_CHECKING, cast

from mikemol.memres import mem_db

if TYPE_CHECKING:
    from collections.abc import Sequence

_ARGC = 3


def render(db: Path, project: str) -> str:
    """Render the manifest of `project` in `db` as the text of its `mem.json`.

    Returns:
        The JSON text with a trailing newline, or "" when there are no observations (nothing is
        emitted rather than a false `{}`).

    """
    with closing(mem_db.connect(db)) as conn:
        manifest = mem_db.manifest(conn, project)
    if not manifest.get("claims") and len(manifest) == 1:
        return ""
    return json.dumps(manifest, indent=2, sort_keys=True) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    """Write (or with `--check`, verify) the projection of one project into `<out.json>`.

    Returns:
        0 on success or when there is nothing to project; 1 when `--check` finds `<out.json>`
        stale; 2 when fewer than `<db> <project> <out.json>` were given.

    """
    args = sys.argv[1:] if argv is None else argv
    if len(args) < _ARGC:
        sys.stderr.write("usage: mikemol-mem-project <db> <project> <out.json> [--check]\n")
        return 2
    db, project, out = Path(args[0]), args[1], Path(args[2])
    text = render(db, project)
    if not text:
        sys.stderr.write(
            f"mem-project: {project}: no observations in {db} - leaving {out} alone\n",
        )
        return 0
    if "--check" in args:
        current = out.read_text(encoding="utf-8") if out.exists() else ""
        if current != text:
            sys.stderr.write(
                f"mem-project: {out} is STALE against {db} - regenerate with:\n"
                f"  mikemol-mem-project {db} {project} {out}\n",
            )
            return 1
        return 0
    out.write_text(text, encoding="utf-8")
    summary = {
        key: value
        for key, value in cast("dict[str, object]", json.loads(text)).items()
        if key != "claims"
    }
    sys.stderr.write(f"mem-project: {project} -> {out} ({summary})\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
