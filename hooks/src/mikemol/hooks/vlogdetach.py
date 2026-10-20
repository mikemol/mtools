# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Start the drainer detached, so a stalled endpoint never holds the caller (W1179).

⚑ THE DRAINER IS STARTED AND NOT WAITED FOR: its own session, no standard streams, no timeout. If
the endpoint stalls, this process sits in a socket call and the SPOOL grows; the caller has long
since returned. Only one drainer works a spool at a time (`vlogspool` takes a non-blocking lock),
so a stalled one makes later ones report busy and leave the files alone.

⚑ THE DRAINER SEES THE SAME SETTINGS: its argv is built from the shipper config, so it needs no
file the caller did not have.

CONSUMED BY: `vlogcli`.
"""

import os
import subprocess
import sys
from collections.abc import Sequence

from mikemol.hooks import vlogship


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


def spawn_detached(argv: Sequence[str]) -> None:
    """Start `argv` in its own session with no standard streams, and do not wait for it."""
    subprocess.Popen(
        list(argv),
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
            list(argv),
            stdin=read_end,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        os.write(write_end, text.encode("utf-8"))
    finally:
        os.close(read_end)
        os.close(write_end)
