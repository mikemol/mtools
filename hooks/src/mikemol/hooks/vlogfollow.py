# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-vlog --from-file F --follow`: ship from the saved offset, then wait for more (W1817).

luthen-observability:W1492, under the operator's rule of 2026-10-21 that every log reaches
VictoriaLogs STREAMED by its source's most native path, never in timer batches: a oneshot unit on a
60 s timer left VictoriaLogs about ten packages behind a live emerge. The batch form already keeps
the right state, `(inode, offset)`, so following is the batch form repeated whenever the file
changes, run as a `Type=simple`, `Restart=always` unit.

⚑ THE LOOP IS WHAT THE BATCH FORM LACKED, AND NOTHING ELSE CHANGES: each pass is `vlogcli`'s own
pass (read from the saved offset, spool, commit the consumed prefix, start the drainer), so rotation
(a new inode, or a file shorter than the offset, restarts at 0), the at-least-once commit and the
spool's `hold` policy are the batch form's, unchanged and tested there.

⚑ A CHANGE IS READ FROM THE FILE'S OWN SIGNATURE, `(inode, size)`, TAKEN BEFORE THE PASS: anything
appended while the pass ran makes the signature differ afterwards, so the next pass runs at once and
nothing waits for a second append. A signature that cannot be read (the file is missing, as it is
between a rotation's rename and its recreation) is a signature too: it differs from any real one,
so the loop passes again when the file returns.

⚑ HELD IS NOT UNCHANGED: under `on_full = hold` a spool at its ceiling takes only part of a chunk
and the tail stays in the file, so the file may not change again for as long as the endpoint is
down. When a pass left lines behind the loop does not wait for growth; it pauses and passes again,
which finds room once the drainer has made some.

⚑ THE PAUSE IS A SAMPLING PERIOD, NOT A DEADLINE: it is how often the signature is read while the
file is quiet. inotify is not in the standard library, so a stat poll is the base, and it covers the
cases inotify cannot (a btrfs reflink tree, a bind mount). Nothing here ends the loop on elapsed
time; it ends when the unit is stopped.

CONSUMED BY: `vlogcli.main` with `--follow`.
"""

from collections.abc import Callable
from pathlib import Path

Signature = tuple[int, int] | None
Step = Callable[[], bool]
Pause = Callable[[], None]
Stop = Callable[[], bool]


def signature(path: Path) -> Signature:
    """Read the file's identity and size.

    Returns:
        (inode, size), or None when the file cannot be read.

    """
    try:
        stat = path.stat()
    except OSError:
        return None
    return stat.st_ino, stat.st_size


def never() -> bool:
    """Say that the loop is not to stop.

    Returns:
        False.

    """
    return False


def follow(step: Step, path: Path, pause: Pause, stop: Stop = never) -> int:
    """Run `step` whenever `path` changes, until `stop` says so.

    `step()` is one pass of the batch form and returns True when it left lines in the file (the
    spool was at its ceiling).

    Returns:
        the number of passes made.

    """
    passes = 0
    while not stop():
        seen = signature(path)
        held = step()
        passes += 1
        if held:
            pause()
            continue
        while signature(path) == seen and not stop():
            pause()
    return passes
