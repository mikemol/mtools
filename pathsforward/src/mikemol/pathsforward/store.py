# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The effectful edge: reading, atomically writing, and exclusively holding a state file.

⚑⚑ EVERY WRITE IS A TEMP FILE THEN A REPLACE. el-openglo truncated the live file and wrote into
it, so a concurrent reader crashed with `JSONDecodeError: Expecting value: line 1 column 1`
(measured in the survey's lock race). A reader here sees the old bytes or the new ones.

⚑⚑ EVERY READ-MODIFY-WRITE HOLDS `flock` ON A SIDECAR. The sidecar and not the state file,
because the replace swaps the state file's inode and a lock on the old inode protects nothing.

⚑ THE SIBLINGS FOLLOW THE STATE PATH. `paths-forward.json` has `paths-forward.md`,
`paths-forward.ledger` and `paths-forward.flock` beside it, so a copy under test never reaches
the live ones. There is no default root: the caller names the file.
"""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, cast

from mikemol.pathsforward.model import MalformedStateError, State, validate

if TYPE_CHECKING:
    from collections.abc import Iterator

MIRROR = ".md"
LEDGER = ".ledger"
FLOCK = ".flock"


class UnreadableStateError(ValueError):
    """The state file is missing, unreadable, unparseable or malformed; it is refused."""


def sibling(state_path: Path, suffix: str) -> Path:
    """Name a file beside the state file.

    Returns:
        the state path with its suffix replaced.

    """
    return state_path.with_suffix(suffix)


def load(path: Path) -> State:
    """Read and validate a state file.

    Returns:
        the state.

    Raises:
        UnreadableStateError: naming the path and the cause.

    """
    try:
        return validate(cast("object", json.loads(path.read_text(encoding="utf-8"))))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, MalformedStateError) as exc:
        msg = f"REFUSED: {path}: {exc}"
        raise UnreadableStateError(msg) from exc


def write_atomic(path: Path, body: str) -> None:
    """Write `body` to a temp file beside `path`, fsync it, and replace `path` with it."""
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
    ) as fh:
        fh.write(body)
        fh.flush()
        os.fsync(fh.fileno())
    Path(fh.name).replace(path)


def save(path: Path, state: State) -> None:
    """Write the state atomically, two-space indented, UTF-8, newline-terminated."""
    write_atomic(path, json.dumps(state.doc, indent=2, ensure_ascii=False) + "\n")


@contextlib.contextmanager
def exclusive(path: Path) -> Iterator[None]:
    """Hold an exclusive flock on the state file's sidecar for the duration.

    Yields:
        nothing; the lock is held while the block runs, and released on every exit path.

    """
    with sibling(path, FLOCK).open("a", encoding="utf-8") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
