# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A waypoint's attachments: files in the repo it cites, each pinned by a hash (nemik:W276).

    "attachments": [{"path": ".claude/letters/x.md", "sha256": "<64 hex digits>"}]

⚑ A PEER READING THE REPO AT A COMMIT RESOLVES AN ATTACHMENT THE SAME WAY, so a path is relative to
the queue's project root and never absolute or climbing out of it. The record is plain data in the
waypoint, so it rides in the state digest and in `--show` without either learning about it.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, cast

from mikemol.pathsforward.model import text

if TYPE_CHECKING:
    from mikemol.pathsforward.model import Json, State

KEY = "attachments"
_SHA256 = re.compile(r"[0-9a-f]{64}")


def path_fault(path: str) -> str | None:
    """Say why a path cannot be an attachment's.

    Returns:
        the fault, or None when it is a repo-relative path with no `..` segment.

    """
    if not path.strip():
        return "path is empty"
    if path.startswith("/") or "\\" in path:
        return f"path {path!r} is not repo-relative"
    if ".." in PurePosixPath(path).parts:
        return f"path {path!r} climbs out of the repo with .."
    return None


def _fields(entry: object) -> dict[object, object]:
    """Read an entry as a map.

    Returns:
        the entry's fields; {} when it is not an object.

    """
    return cast("dict[object, object]", entry) if isinstance(entry, dict) else {}


def fault(entry: object) -> str | None:
    """Say why one attachment entry is malformed.

    Returns:
        the fault, or None when it is `{path, sha256}` with a clean path and 64 hex digits.

    """
    if not isinstance(entry, dict):
        return f"entry {entry!r} is not an object"
    path, digest = _fields(entry).get("path"), _fields(entry).get("sha256")
    if not isinstance(path, str):
        return "entry has no path"
    if not isinstance(digest, str) or _SHA256.fullmatch(digest) is None:
        return f"entry {path!r}: sha256 is not 64 lowercase hex digits"
    return path_fault(path)


def entries(rec: Json) -> list[tuple[str, str]]:
    """Read a waypoint's well-formed attachments.

    Returns:
        the (path, sha256) pairs; a malformed entry is left to `findings`.

    """
    value = rec.get(KEY)
    if not isinstance(value, list):
        return []
    return [
        (str(_fields(e)["path"]), str(_fields(e)["sha256"]))
        for e in cast("list[object]", value)
        if fault(e) is None
    ]


def findings(state: State) -> list[str]:
    """Report an `attachments` field that is not a list of well-formed entries.

    Returns:
        one finding per malformed field or entry; an absent field is fine.

    """
    found: list[str] = []
    for w in state.waypoints:
        value = w.get(KEY)
        if value is None:
            continue
        if not isinstance(value, list):
            found.append(f"{text(w, 'symbol')}: {KEY} is {type(value).__name__}, not a list")
            continue
        found.extend(
            f"{text(w, 'symbol')}: {KEY}: {why}"
            for why in (fault(e) for e in cast("list[object]", value))
            if why is not None
        )
    return found
