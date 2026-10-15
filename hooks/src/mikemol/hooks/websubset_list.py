# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The one tracked list of web-portable modules, and its reader (mtools:W1256).

⚑ ONE DECLARED LIST, NOT A MARKER IN EACH MODULE: opting a module into the web subset is a reviewed
change to one file, so what the gate guards is visible in a diff and a module cannot opt itself in
or out by an edit to its own text. The file is `hooks/websubset-portable.txt`: one repo-relative
`.py` path per line, `#` comments and blank lines ignored.

⚑ A LIST THAT CANNOT BE READ IS AN ERROR, NEVER AN EMPTY LIST. A gate whose list vanished or was
corrupted must not read as "nothing is portable, so everything passes". The reader raises one named
error for a missing file and for every malformed entry (absolute, `..`, not `.py`, listed twice),
each naming the line, so the caller prints a row and refuses.
"""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

LIST_NAME = "websubset-portable.txt"


class PortableListError(ValueError):
    """The portable list is missing or has an entry the gate cannot use."""


def _entry(raw: str, number: int) -> str | None:
    """Read one line of the list.

    Returns:
        the path, or None for a comment or blank line.

    Raises:
        PortableListError: for an absolute path, a `..` segment or a name that is not `.py`.

    """
    line = raw.split("#", 1)[0].strip()
    if not line:
        return None
    path = PurePosixPath(line)
    if path.is_absolute() or ".." in path.parts or path.suffix != ".py":
        msg = f"{LIST_NAME}:{number}: {line!r} is not a repo-relative .py path"
        raise PortableListError(msg)
    return str(path)


def portable(path: Path) -> list[str]:
    """Read the declared list of web-portable modules.

    Returns:
        the paths in file order.

    Raises:
        PortableListError: when the file is missing, or an entry is malformed or repeated.

    """
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as fault:
        msg = f"{LIST_NAME}: cannot be read ({fault.strerror})"
        raise PortableListError(msg) from fault
    found: list[str] = []
    for number, raw in enumerate(lines, start=1):
        entry = _entry(raw, number)
        if entry is None:
            continue
        if entry in found:
            msg = f"{LIST_NAME}:{number}: {entry} is listed twice"
            raise PortableListError(msg)
        found.append(entry)
    return found
