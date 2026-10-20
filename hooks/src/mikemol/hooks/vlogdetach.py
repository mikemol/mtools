# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Start the drainer detached, so a stalled endpoint never holds the caller (W1179).

⚑ THE DRAINER IS STARTED AND NOT WAITED FOR: its own session, no standard streams, no timeout. If
the endpoint stalls, this process sits in a socket call and the SPOOL grows; the caller has long
since returned. Only one drainer works a spool at a time (`vlogspool` takes a non-blocking lock),
so a stalled one makes later ones report busy and leave the files alone.

⚑ THE DRAINER SEES THE SAME SETTINGS: its argv is built from the shipper config, so it needs no
file the caller did not have.

⚑ A CHILD THAT CANNOT DELIVER SAYS SO WHERE IT OUTLIVES IT (W1744, github-8f 2026-10-19): a detached
telemetry child used to write its stderr to /dev/null, so a store that refused it left no trace at
all. When `systemd-cat` exists the child runs under it, so whatever it prints reaches the journal,
which luthen already ships to VictoriaLogs; it needs no trace store to be heard. With no
`systemd-cat` the child runs bare as before. Metric samples stay the guaranteed channel.

CONSUMED BY: `vlogcli`, and every module that starts a detached telemetry child.
"""

import os
import shutil
import subprocess
import sys
from collections.abc import Sequence

from mikemol.hooks import vlogship

JOURNAL = "systemd-cat"
TAG = "mikemol-telemetry"


def drain_argv(config: vlogship.Config) -> list[str]:
    """Build the argv of a detached drainer that sees the same config.

    Returns:
        the command, `python -m mikemol.hooks.vlogcli --drain ...`.

    """
    argv = [sys.executable, "-m", "mikemol.hooks.vlogcli", "--drain"]
    argv += ["--spool-dir", str(config.spool_dir), "--max-lines", str(config.max_lines)]
    argv += ["--max-bytes", str(config.max_bytes)]
    if config.service:
        argv += ["--service", config.service]
    for part in config.resolver:
        argv += ["--resolver-arg", part]
    return argv


def journaled(argv: Sequence[str]) -> list[str]:
    """Wrap a child's argv so its output reaches the journal, when `systemd-cat` exists.

    Returns:
        `systemd-cat -t mikemol-telemetry -p warning` followed by `argv`; `argv` unchanged when
        there is no `systemd-cat` on the PATH.

    """
    program = shutil.which(JOURNAL)
    if program is None:
        return list(argv)
    return [program, "-t", TAG, "-p", "warning", *argv]


def spawn_detached(argv: Sequence[str]) -> None:
    """Start `argv` in its own session, its output to the journal, and do not wait for it."""
    subprocess.Popen(
        journaled(argv),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def spawn_with_stdin(argv: Sequence[str], text: str) -> None:
    """Start `argv` detached, give it `text` on stdin, and do not wait for it (W1783).

    ⚑ AN OS PIPE, NOT POPEN'S STDIN OBJECT: `text` is a bounded batch (the caller chunks it well
    under the pipe buffer), so writing it before the child reads can never block this process.
    """
    read_end, write_end = os.pipe()
    try:
        subprocess.Popen(
            journaled(argv),
            stdin=read_end,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        os.write(write_end, text.encode("utf-8"))
    finally:
        os.close(read_end)
        os.close(write_end)
