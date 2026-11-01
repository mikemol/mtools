# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Refuse a recursive delete whose target the session did not create, and say what to do instead.

W1919's hook, its pure core (W1995). The decision is a function of three plain values: the command,
the paths the session is known to have created, and the working directory the command runs in. It
reads no filesystem and no environment, so what a session created is the CALLER's record (W1993)
and this module is correct for any record.

⚑ A TARGET IS ALLOWED ONLY INSIDE A CREATED PATH. Each target is made absolute against the working
directory and normalised (`..` and `.` resolved as text); it passes when it equals a created path
or lies under one. A target that cannot be shown to lie there is refused, including `/`, `~` (the
shell has not expanded it by the time the hook reads the text) and a relative path that climbs out.

⚑ AN UNREADABLE COMMAND IS REFUSED, NEVER ALLOWED: a delete whose target is built by expansion
cannot be judged (`deletecmd.UnreadableError`), and the refusal carries that reader's own words.

⚑ THE REMEDY IS PART OF THE REFUSAL, because a refusal that names no way forward is retried with
the same command in other spelling: list the target first, then delete the entries by name.

CONSUMED BY: the PreToolUse Bash hook (W1919), not yet wired.
"""

import posixpath
from collections.abc import Iterable

from mikemol.hooks import deletecmd

REMEDY = (
    "list the target first (ls -la), then delete the entries the session created by name; "
    "a path the session did not create is not this session's to delete"
)
_SEP = "/"
_HOME = "~"


def _absolute(target: str, cwd: str) -> str:
    return posixpath.normpath(posixpath.join(cwd, target))


def _inside(path: str, root: str) -> bool:
    return path == root or path.startswith(root.rstrip(_SEP) + _SEP)


def _stray(found: list[deletecmd.Delete], roots: list[str], cwd: str) -> tuple[str, str] | None:
    # The first (form, target) whose absolute path lies under none of the created roots.
    for delete in found:
        for target in delete.targets:
            path = _absolute(target, cwd)
            if target.startswith(_HOME) or not any(_inside(path, root) for root in roots):
                return delete.form, target
    return None


def refusal(command: str, created: Iterable[str], cwd: str) -> str | None:
    """Judge a shell command's recursive deletes against the paths the session created.

    Returns:
        the refusal, with its remedy, when a target is outside every created path or the command
        cannot be read; None when the command holds no recursive delete or all targets are inside.

    """
    roots = [posixpath.normpath(path) for path in created]
    try:
        found = deletecmd.deletes(command)
    except deletecmd.UnreadableError as caught:
        return f"recursive delete refused: {caught}; {REMEDY}"
    stray = _stray(found, roots, cwd)
    if stray is None:
        return None
    form, target = stray
    where = f"the {form} target {target!r} is not under a path this session created"
    return f"recursive delete refused: {where}; {REMEDY}"
