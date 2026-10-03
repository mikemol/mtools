# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W511: the freeze/embargo record — repo paths no session may edit while a freeze holds.

The operator ruled (2026-10-03) that a paperkit freeze's embargo is a QUEUE FIELD written with
this tool, not a repo file. The hooks package's standing rule 6 reads it: an Edit or Write to an
embargoed path is denied while the record stands, so the rule lifts the moment the record does.

⚑ ONE RECORD PER PATH, AND THE PATH IS THE WHOLE PREDICATE. A freeze's prose ("the paperkit-use
freeze is HELD") gives a policy nothing to match; the embargoed paths are what it forbids, so the
field holds exactly those, each with the reason a reader is shown. A path is project-relative
(the hook resolves it against CLAUDE_PROJECT_DIR); an absolute or `..` path is refused, since it
would name something outside the project the queue governs.

Shape: `embargoes: [{path, reason, since}]`, absent when empty (never `[]`).
"""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import TYPE_CHECKING, cast

from mikemol.pathsforward.model import RefusedError, text

if TYPE_CHECKING:
    from mikemol.pathsforward.model import Json, State

FIELD = "embargoes"


def records(state: State) -> list[Json]:
    """Return the stored embargo records, malformed entries skipped.

    Returns:
        each record that is a mapping, in stored order.

    """
    raw = state.doc.get(FIELD)
    if not isinstance(raw, list):
        return []
    return [cast("Json", r) for r in cast("list[object]", raw) if isinstance(r, dict)]


def _checked(path: str) -> str:
    """Return a project-relative path in normal form, or refuse it.

    Returns:
        the path, normalized.

    Raises:
        RefusedError: on an empty, absolute or escaping path.

    """
    pure = PurePosixPath(path.strip())
    if not path.strip() or pure.is_absolute() or ".." in pure.parts:
        msg = f"embargo path {path!r} must be project-relative, without '..'"
        raise RefusedError(msg)
    return str(pure)


def embargo(state: State, path: str, reason: str, now: str) -> str:
    """Record one embargoed path.

    Returns:
        the stored path.

    Raises:
        RefusedError: on a bad path, a blank or multiline reason, or a path already embargoed.

    """
    rel = _checked(path)
    if not reason.strip() or "\n" in reason or "\r" in reason:
        msg = "embargo reason must be one non-blank line"
        raise RefusedError(msg)
    rows = records(state)
    if any(text(r, "path") == rel for r in rows):
        msg = f"{rel} is already embargoed; --lift-embargo it first"
        raise RefusedError(msg)
    rows.append({"path": rel, "reason": reason.strip(), "since": now})
    state.doc[FIELD] = rows
    return rel


def lift(state: State, path: str) -> str:
    """Remove one embargo record; the field goes with the last one.

    Returns:
        the lifted path.

    Raises:
        RefusedError: when the path is not embargoed.

    """
    rel = _checked(path)
    rows = records(state)
    kept = [r for r in rows if text(r, "path") != rel]
    if len(kept) == len(rows):
        msg = f"{rel} is not embargoed"
        raise RefusedError(msg)
    if kept:
        state.doc[FIELD] = kept
    else:
        state.doc.pop(FIELD, None)
    return rel
