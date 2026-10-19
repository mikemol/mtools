# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A follower reads the verdict the train leader left for it, prints it and exits (W1671).

⚑ THE LEADER LANDED OR REFUSED THIS STACK FOR IT (W1670): when a lease holder joined the stacks
behind it into one run, each of those stacks is already decided by the time its own process gets
its turn. The leader leaves each follower a file, `<git dir>/mtools/stack-<key>.verdict`, holding
the exit code and the lines `run_stack` would have printed; the follower finds it when its turn
comes, prints the text, forgets its snapshot and returns the code. It never takes the lease, never
gates and never commits, so the gate that already judged its tree is not run again.

⚑ A TORN FILE IS NO VERDICT: the write goes to a temp name and is replaced into place, and a file
that is missing, unreadable, not an object, or without an integer code and a text is read as none,
so a follower whose verdict never arrived runs on its own turn as before and loses nothing.

⚑ A VERDICT IS TAKEN ONCE: `take` clears the file it read, so a process re-executed by the claim
cannot print it twice.

CONSUMED BY: `commit_kata.main` (the follower's turn) and the train leader (W1654).
"""

import json
from pathlib import Path
from typing import cast

from mikemol.hooks.traindrive import Verdict


def verdict_path(ledger: Path, key: str) -> Path:
    """Name the file a leader leaves for the stack with this submit key.

    Returns:
        `<ledger>/stack-<key>.verdict`.

    """
    return ledger / f"stack-{key}.verdict"


def write(ledger: Path, verdict: Verdict) -> bool:
    """Leave a follower its verdict, atomically.

    Returns:
        True when the file was replaced into place; False when the ledger could not be written.

    """
    path = verdict_path(ledger, verdict.key)
    staging = path.with_name(f"{path.name}.tmp")
    payload: dict[str, object] = {"code": verdict.code, "text": verdict.text}
    try:
        ledger.mkdir(parents=True, exist_ok=True)
        staging.write_text(json.dumps(payload), encoding="utf-8")
        staging.replace(path)
    except OSError:
        return False
    return True


def read(ledger: Path, key: str) -> Verdict | None:
    """Read the verdict left for a key.

    Returns:
        the verdict, or None when the file is missing or is not a code and a text.

    """
    try:
        raw = cast("object", json.loads(verdict_path(ledger, key).read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return None
    if not isinstance(raw, dict):
        return None
    fields = cast("dict[str, object]", raw)
    code, text = fields.get("code"), fields.get("text")
    if isinstance(code, int) and not isinstance(code, bool) and isinstance(text, str):
        return Verdict(key, code, text)
    return None


def take(ledger: Path, key: str) -> Verdict | None:
    """Read the verdict left for a key and clear it.

    Returns:
        the verdict, or None when there is none.

    """
    found = read(ledger, key)
    if found is not None:
        verdict_path(ledger, key).unlink(missing_ok=True)
    return found
