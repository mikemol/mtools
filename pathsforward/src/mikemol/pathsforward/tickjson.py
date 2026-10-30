# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The `--tick-open --json` document: what the open printed, and each hook's own record (W2169).

⚑ ONE DOCUMENT, NOT TEXT A READER PARSES. A reader of `--tick-open` (nemik:W1276's class emitter,
the host's tick-open hook) had lines to scrape and no time it could trust: a reflog stamp in local
time from the previous local date read as today's. With `--json` the open runs as it always does,
its output is captured, and one JSON object comes out: the holder, the exit status, the lines the
open printed, and `hooks`, a record per tick hook with the UTC time THAT hook was read.

⚑ THE TEXT IS KEPT WHOLE IN `lines`, and `hooks` repeats the hook results structurally. Nothing is
parsed out of the text and nothing is dropped from it.

CONSUMED BY: `cli._tick_open` when `--json` is given.
"""

import contextlib
import io
import json
from collections.abc import Callable
from datetime import UTC, datetime


def utc_stamp() -> str:
    """Read the clock in UTC, to the second.

    Returns:
        the time as `YYYY-MM-DDTHH:MM:SSZ`.

    """
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def capture(run: Callable[[], int]) -> tuple[int, list[str]]:
    """Run a step that prints, and keep what it printed instead of showing it.

    Returns:
        the step's status, and its stdout split into lines.

    """
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = run()
    return code, buffer.getvalue().splitlines()


def document(holder: str, code: int, lines: list[str], hooks: list[dict[str, object]]) -> str:
    """Build the one JSON document for an open.

    Returns:
        the object as text: `holder`, `exit`, `hooks` (each `{command, exit, read_at, output}`) and
        `lines`, the open's printed text.

    """
    body = {"holder": holder, "exit": code, "hooks": hooks, "lines": lines}
    return json.dumps(body, indent=2, ensure_ascii=False)
