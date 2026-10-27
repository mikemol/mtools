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
    embargoes: [{path, rel, reason}]: the queue's `embargoes` field (W511, rule 6), each path
            made absolute against the project; [] when the queue holds none, absent when the
            queue or the field cannot be read.
"""

import json
import os
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import cast

from mikemol.hooks.payload import as_record, text_of

# The project's queue, relative to CLAUDE_PROJECT_DIR.
QUEUE = Path(".claude") / "paths-forward.json"

# The ratchet baseline's file name (rule 4), and the file that declares a rise it may take.
BASELINE = "ratchet-preview.txt"
REBASELINES = "rebaselines.json"


def declared_rises(project: Path) -> list[dict[str, object]] | None:
    """Return the baseline rises `rebaselines.json` declares, each as {ratchet, old, new}.

    ⚑ THE DOOR IS A DECLARATION, NOT AN EXEMPTION (W1977 option 2, operator-chosen 2026-10-26): rule
    4 still refuses a rise, except one an entry names by the file's current size and its resulting
    size. The entry's warrant is checked by `mikemol-ratchet rebaselines`, not here.

    Returns:
        the declared rises; [] when the file is absent or holds none; None when it cannot be read.

    """
    try:
        doc: object = json.loads((project / REBASELINES).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except Exception as caught:
        if not isinstance(caught, (OSError, ValueError)):
            raise
        return None
    raw = as_record(doc).get("rebaselines") if isinstance(doc, dict) else None
    if not isinstance(raw, list):
        return None
    rises: list[dict[str, object]] = []
    for item in cast("list[object]", raw):
        entry = as_record(item)
        ratchet, old, new = entry.get("ratchet"), entry.get("old"), entry.get("new")
        if isinstance(ratchet, str) and isinstance(old, int) and isinstance(new, int):
            rises.append({"ratchet": ratchet, "old": old, "new": new})
    return rises


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
    except Exception as caught:
        if not isinstance(caught, (OSError, subprocess.TimeoutExpired)):
            raise
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


def queue_doc(state: Path) -> dict[str, object] | None:
    """Return a queue file's top-level record, or None when it cannot be read as JSON.

    Public so host_facts reads the queue the same way (a read-only parse: the one-writer rule is
    about writes).

    Returns:
        the record; None for a missing or malformed file.

    """
    try:
        with state.open(encoding="utf-8") as handle:
            raw: object = json.load(handle)
    except Exception as caught:
        if not isinstance(caught, (OSError, ValueError)):
            raise
        return None
    return as_record(raw)


def held_symbols(
    state: Path,
    lifts: Callable[[Mapping[str, object]], bool] | None = None,
) -> list[str] | None:
    """Return the symbols blocked on a human in a queue file, or None when it cannot be read.

    ⚑ A HOLD THE OPERATOR HAS LIFTED IN THEIR OWN VERIFIED WORDS IS NOT HELD (W1525): a card whose
    warrant verifies now as origin human and names it is left out, so the policy lets the writer
    change it. The signed lift still works as it did.

    Returns:
        the held symbols, sorted; None for a missing or malformed queue.

    """
    doc = queue_doc(state)
    if doc is None:
        return None
    rows = doc.get("waypoints")
    if not isinstance(rows, list):
        return None

    def check(row: Mapping[str, object]) -> bool:
        if lifts is not None:
            return lifts(row)
        # Imported here, not at the top: a built hook venv links the modules that existed when it
        # was built, and a module-level import of a newer one stops the gate's own bazel wrapper
        # from starting, so no bazel call could ever rebuild the venv that lacks it.
        from mikemol.hooks import hold_lift

        return hold_lift.lifted(row)

    held: list[str] = []
    for item in rows:
        row = as_record(item)
        if row.get("status") == "blocked" and row.get("blocked_kind") == "human" and not check(row):
            held.append(text_of(row.get("symbol")))
    return sorted(held)


def embargoes(state: Path, project: Path) -> list[dict[str, str]] | None:
    """Return the queue's embargo records with absolute paths (W511, rule 6).

    ⚑ ONE MALFORMED RECORD VOIDS THE FACT: dropping it would read as "that path is free", the
    very reading that did not happen, so a field that is not a list of {path, reason} is None.

    Returns:
        [{path, rel, reason}] in stored order; [] when the field is absent; None when the queue or
        the field cannot be read.

    """
    doc = queue_doc(state)
    if doc is None:
        return None
    raw = doc.get("embargoes", [])
    if not isinstance(raw, list):
        return None
    found: list[dict[str, str]] = []
    for item in raw:
        row = as_record(item)
        rel = text_of(row.get("path"))
        if not rel:
            return None
        found.append({"path": str(project / rel), "rel": rel, "reason": text_of(row.get("reason"))})
    return found


def baseline_lines(path: Path) -> int | None:
    """Return a baseline file's non-blank line count: 0 when absent, None when unreadable.

    Returns:
        the count, 0 for a file not yet written, or None when it exists but cannot be read.

    """
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return 0
    except Exception as caught:
        if not isinstance(caught, (OSError, ValueError)):
            raise
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
    embargoed = embargoes(state, project)
    if embargoed is not None:
        facts["embargoes"] = embargoed
    target = text_of(as_record(payload.get("tool_input")).get("file_path"))
    if payload.get("tool_name") in {"Write", "Edit"} and Path(target).name == BASELINE:
        lines = baseline_lines(Path(cwd) / target)
        if lines is not None:
            facts["target_lines"] = lines
        rises = declared_rises(project)
        if rises is not None:
            facts["rebaselines"] = rises
        facts["target_rel"] = os.path.relpath(Path(cwd) / target, project)
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
