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

import contextlib
import fcntl
import json
import os
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import cast

from mikemol.pathsforward import export, ownership
from mikemol.pathsforward.model import MalformedStateError, State, text, validate

MIRROR = ".md"
LEDGER = ".ledger"
FLOCK = ".flock"
EXPORT = ".export.json"


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
    except Exception as exc:
        if not isinstance(
            exc, (OSError, UnicodeDecodeError, json.JSONDecodeError, MalformedStateError)
        ):
            raise
        msg = f"REFUSED: {path}: {exc}"
        raise UnreadableStateError(msg) from exc


def write_atomic(path: Path, body: str) -> None:
    """Write `body` to a temp file beside `path`, fsync it, and replace `path` with it.

    ⚑ THE REPLACEMENT KEEPS WHAT IT REPLACES (mtools:W955): the existing file's mode, and its owner
    and group when the process may give them (a new file takes its directory's owner and group), so
    a root run changes nothing visible.
    """
    ref, mode = ownership.reference(path), ownership.mode_of(path)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
    ) as fh:
        fh.write(body)
        fh.flush()
        os.fsync(fh.fileno())
    ownership.adopt(Path(fh.name), ref, mode=mode)
    Path(fh.name).replace(path)


def write_export(path: Path, state: State) -> dict[str, object]:
    """Write the repo's version-2 export beside the state file, only when its bytes differ.

    ⚑ AN UNCHANGED EXPORT KEEPS ITS MTIME (nemik:W636): the pod decides whether the exports
    changed by file mtime, so the file is replaced only when the new bytes differ.

    Returns:
        the export that was built, written or not.

    """
    repo = Path(text(state.doc, "project_root") or str(path.parent.parent)).name
    cards = [*state.waypoints, *state.residue]
    built = export.build(repo, export.stamp_of(cards), cards)
    target = path.with_suffix(EXPORT)
    body = json.dumps(built, indent=2, ensure_ascii=False) + "\n"
    if not target.is_file() or target.read_text(encoding="utf-8") != body:
        write_atomic(target, body)
    return built


def refresh_export(path: Path, state: State) -> None:
    """Rewrite an export that already exists, so a flag is never waiting on a stale file (W1841).

    ⚑ OPT-IN BY HAVING EXPORTED ONCE (nemik:W873): nemik uses a repo's export only when it is no
    older than the state, so a writer that does not re-export after a change is always stale and
    falls back to a list that does not know the withheld flag. A repo that never ran `--export`
    gets no new file.
    """
    if path.with_suffix(EXPORT).is_file():
        write_export(path, state)


def save(path: Path, state: State) -> None:
    """Write the state atomically, two-space indented, UTF-8, newline-terminated.

    ⚑ AN EXISTING EXPORT FOLLOWS THE STATE (W1841): every write through here refreshes it.
    """
    write_atomic(path, json.dumps(state.doc, indent=2, ensure_ascii=False) + "\n")
    refresh_export(path, state)


@contextlib.contextmanager
def exclusive(path: Path) -> Iterator[None]:
    """Hold an exclusive flock on the state file's sidecar for the duration.

    Yields:
        nothing; the lock is held while the block runs, and released on every exit path.

    """
    with ownership.open_append(sibling(path, FLOCK)) as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
