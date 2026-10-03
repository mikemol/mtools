# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W238: gather the facts the standing policy's (b) rules read, before opa runs.

The launcher (`hooks/bin/mikemol-hook-standing`) pipes the harness payload through this module,
which adds `input.facts`, and hands the result to `opa eval`. Rego cannot run git or read the
queue, so a rule that depends on repository or queue state reads a fact gathered here.

⚑ A FACT THAT CANNOT BE GATHERED IS ABSENT, NEVER EMPTY. An empty `staged` list would assert
"nothing is staged" and let rule 9 pass on a reading that did not happen; an absent one leaves the
rule undefined, and that residue is stated rather than hidden. A payload that is not JSON raises,
and the launcher refuses on any nonzero exit (fail closed).

Facts:
    staged: absolute paths of the files in the index of the repository holding the payload's cwd.
    queue:  {path, held}: the project's queue file and the symbols blocked on a human there.
    target_lines: for a Write to the ratchet baseline, its current non-blank line count (0 when
            it does not exist yet); rule 4 compares the Write's content against it.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from mikemol.hooks.payload import as_record, text_of

# The project's queue, relative to CLAUDE_PROJECT_DIR.
QUEUE = Path(".claude") / "paths-forward.json"

# The ratchet baseline's file name (rule 4).
BASELINE = "ratchet-preview.txt"


def _git(cwd: Path, *args: str) -> str | None:
    git = shutil.which("git")
    if git is None:
        return None
    try:
        proc = subprocess.run(
            [git, "-C", str(cwd), *args],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return proc.stdout if proc.returncode == 0 else None


def staged_paths(cwd: Path) -> list[str] | None:
    """Return the index's files as absolute paths, or None outside a readable repository.

    Returns:
        the staged files' absolute paths, sorted; None when git cannot answer.

    """
    top = _git(cwd, "rev-parse", "--show-toplevel")
    names = _git(cwd, "diff", "--cached", "--name-only", "-z")
    if top is None or names is None:
        return None
    root = top.strip()
    return sorted(f"{root}/{name}" for name in names.split("\0") if name)


def held_symbols(state: Path) -> list[str] | None:
    """Return the symbols blocked on a human in a queue file, or None when it cannot be read.

    Returns:
        the held symbols, sorted; None for a missing or malformed queue.

    """
    try:
        with state.open(encoding="utf-8") as handle:
            raw: object = json.load(handle)
    except (OSError, ValueError):
        return None
    rows = as_record(raw).get("waypoints")
    if not isinstance(rows, list):
        return None
    held: list[str] = []
    for item in rows:
        row = as_record(item)
        if row.get("status") == "blocked" and row.get("blocked_kind") == "human":
            held.append(text_of(row.get("symbol")))
    return sorted(held)


def baseline_lines(path: Path) -> int | None:
    """Return a baseline file's non-blank line count: 0 when absent, None when unreadable.

    Returns:
        the count, 0 for a file not yet written, or None when it exists but cannot be read.

    """
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return 0
    except (OSError, ValueError):
        return None
    return sum(1 for line in text.splitlines() if line.strip())


def gather(payload: dict[str, object], project: Path) -> dict[str, object]:
    """Return the facts for one payload; a fact that cannot be gathered is left out.

    Returns:
        the facts record placed at `input.facts`.

    """
    facts: dict[str, object] = {}
    cwd = text_of(payload.get("cwd")) or str(project)
    staged = staged_paths(Path(cwd))
    if staged is not None:
        facts["staged"] = staged
    state = project / QUEUE
    held = held_symbols(state)
    if held is not None:
        facts["queue"] = {"path": str(state), "held": held}
    target = text_of(as_record(payload.get("tool_input")).get("file_path"))
    if payload.get("tool_name") == "Write" and Path(target).name == BASELINE:
        lines = baseline_lines(Path(cwd) / target)
        if lines is not None:
            facts["target_lines"] = lines
    return facts


def main() -> int:
    """Read the payload on stdin and print it with `facts` added.

    Returns:
        0; a payload that is not JSON raises, which the launcher refuses on.

    """
    raw: object = json.load(sys.stdin)
    payload = as_record(raw)
    project = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path.cwd())
    payload["facts"] = gather(payload, project)
    sys.stdout.write(json.dumps(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
