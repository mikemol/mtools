# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The two input forms of `mikemol-vlog` beyond stdin: a wrapped command, and a file from an offset.

⚑ A PIPE CANNOT SEE THE PRODUCER'S EXIT STATUS: `tool | mikemol-vlog` reports vlog's status, which
is how a failed tool reads as a passed one. The wrapper form runs the command itself, hands each
line of its standard output to the caller as it arrives, and RETURNS THE COMMAND'S OWN STATUS, so
`set -o pipefail` semantics hold without the caller having to know. Its standard error is not
touched; it still reaches the terminal, in order with the command's own writes.

⚑ THE FILE FORM READS FROM A SAVED OFFSET, ONCE, AND RETURNS (luthen's `log_ship` shape): a timer
reruns it, so nothing here loops or sleeps. The state is `(inode, offset)`. An inode that changed,
or a file shorter than the offset, means rotated or truncated: restart at 0. Only WHOLE lines are
returned, so a line being written is read next time, complete. The state is saved by `commit`
AFTER the caller has spooled the lines, so a crash re-sends (at least once) and never loses.

CONSUMED BY: the `mikemol-vlog` command (W1179).
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, TextIO, cast

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path

EXIT_NOT_STARTED = 127


@dataclass(frozen=True)
class Chunk:
    """The new whole lines of a file, where to resume, and whether it restarted at 0."""

    lines: list[str]
    inode: int
    offset: int
    restarted: bool = False


def run_wrapped(argv: Sequence[str], on_line: Callable[[str], None]) -> int:
    """Run `argv`, passing each standard-output line to `on_line`, and return its own status.

    Returns:
        the command's exit status; 127 when it cannot be started (said on standard error).

    """
    try:
        child = subprocess.Popen(list(argv), stdout=subprocess.PIPE, text=True)
    except OSError as exc:
        sys.stderr.write(f"mikemol-vlog: cannot run {argv[0]}: {exc}\n")
        return EXIT_NOT_STARTED
    stream = cast("TextIO | None", child.stdout)
    if stream is not None:
        for line in stream:
            on_line(line)
    return child.wait()


def _saved(state: Path) -> tuple[int, int]:
    """Read the saved (inode, offset).

    Returns:
        the pair, or (0, 0) when there is no usable state.

    """
    try:
        raw = cast("object", json.loads(state.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return 0, 0
    if not isinstance(raw, dict):
        return 0, 0
    fields = cast("dict[str, object]", raw)
    inode, offset = fields.get("inode"), fields.get("offset")
    if isinstance(inode, int) and isinstance(offset, int):
        return inode, offset
    return 0, 0


def read_from_offset(path: Path, state: Path) -> Chunk:
    """Read the whole lines of `path` that were not read before.

    Returns:
        the chunk; no lines and the old position when the file is missing or has nothing new.

    """
    inode, offset = _saved(state)
    try:
        stat = path.stat()
    except OSError:
        return Chunk([], inode, offset)
    restarted = bool(inode) and (inode != stat.st_ino or stat.st_size < offset)
    start = 0 if restarted or not inode else offset
    with path.open("rb") as handle:
        handle.seek(start)
        data = handle.read()
    whole = data[: data.rfind(b"\n") + 1]
    lines = whole.decode("utf-8", errors="replace").splitlines()
    return Chunk(lines, stat.st_ino, start + len(whole), restarted)


def commit(state: Path, chunk: Chunk) -> None:
    """Save the position after `chunk`'s lines were spooled."""
    position: dict[str, int] = {"inode": chunk.inode, "offset": chunk.offset}
    state.parent.mkdir(parents=True, exist_ok=True)
    scratch = state.with_name(state.name + ".new")
    scratch.write_text(json.dumps(position), encoding="utf-8")
    scratch.replace(state)
