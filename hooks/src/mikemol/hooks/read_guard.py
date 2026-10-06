# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W814: PreToolUse(Read): refuse a whole-file read of an oversized file, naming the cheaper read.

A log, a gate transcript or a task output can be hundreds of kilobytes, and a whole-file Read puts
all of it in the context at once: this session read a 1258-line paperkit gate log whole (about 42k
tokens) to learn one refusal line near its end, and dumped a 34 MB `git status` the same way. The
verdict was always a few lines at the tail or a grep for FAIL, REFUSED or `rc=`.

The rule is mechanical and bounded: a Read with NO `limit`, of a file larger than MAX_BYTES, is
denied, and the reason names the two cheaper reads (an offset and limit, or a grep for the verdict
lines through the shell). Anything that bounds the read is admitted untouched: a `limit`, or
`pages` for a PDF.

⚑ THE GUARD BOUNDS A READ, NEVER FORBIDS ONE. An agent that genuinely needs a large file whole says
so by giving `limit`, which is one parameter. A file that cannot be sized (missing, a directory,
unreadable) is admitted: the tool will report its own error, and a guard that refused on doubt
would turn every typo into a second error.

⚑ IMAGES, PDFS AND NOTEBOOKS ARE NOT TEXT TO TRUNCATE. The Read tool renders them itself (an image
is shown, a PDF is paged), so their size says nothing about the context cost of a text read, and
they are admitted by suffix.

⚑ ARMED, NOT ADVISORY, and by the same two-switch convention as its siblings: its own variable
first, then the shared one. An unarmed hook exits 0 with no decision, which the harness reads as
"allow, nothing to report", so an unarmed guard says nothing and denies nothing.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.hooks.payload import armed, as_record, text_of

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import TextIO

# The hook's own arming switch (the shared one is consulted second, by `armed`).
OWN_SWITCH = "READGUARD_HOOK_BLOCK"

# A whole-file read of more than this is refused. 200 KB is roughly 50k tokens: well past anything
# read to answer a question, and below the files that have flooded the context.
MAX_BYTES = 200_000

# The Read tool renders these itself, so a whole read is not a text dump.
RENDERED_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".ipynb")


def file_size(path: Path) -> int | None:
    """Size a file in bytes.

    Returns:
        the size; None when the path cannot be sized or is not a regular file.

    """
    try:
        return path.stat().st_size if path.is_file() else None
    except OSError:
        return None


def bounds_the_read(tool_input: dict[str, object]) -> bool:
    """Say whether the call itself bounds how much is read.

    Returns:
        True when it gives an integer `limit` (a bool is not one) or a `pages` range.

    """
    limit = tool_input.get("limit")
    if isinstance(limit, int) and not isinstance(limit, bool):
        return True
    return bool(text_of(tool_input.get("pages")))


def refusal(tool_input: dict[str, object], size_of: Callable[[Path], int | None]) -> str | None:
    """Decide whether this Read is an oversized, unbounded one.

    Returns:
        the reason to deny; None when the read is bounded, rendered by the tool, small enough, or
        of a file that cannot be sized.

    """
    name = text_of(tool_input.get("file_path"))
    if not name or bounds_the_read(tool_input):
        return None
    path = Path(name)
    if path.suffix.lower() in RENDERED_SUFFIXES:
        return None
    size = size_of(path)
    if size is None or size <= MAX_BYTES:
        return None
    return (
        f"read-guard: {path.name} is {size:,} bytes, over the {MAX_BYTES:,} a whole-file read is "
        "allowed. Read less of it: give `offset` and `limit` (the verdict of a log is usually its "
        "last 40 lines), or grep it for the verdict lines (FAIL, REFUSED, rc=) through the shell. "
        "If you truly need all of it, pass a `limit`."
    )


def run(
    payload: dict[str, object],
    size_of: Callable[[Path], int | None],
    out: TextIO,
) -> int:
    """Apply the guard to one PreToolUse(Read) payload.

    Returns:
        0 always: a denial is the decision JSON on `out`, never a nonzero exit.

    """
    reason = refusal(as_record(payload.get("tool_input")), size_of)
    if reason is None:
        return 0
    decision: dict[str, dict[str, str]] = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }
    out.write(json.dumps(decision))
    return 0


def main() -> int:
    """Read the harness payload and deny an oversized whole-file read, if armed.

    Returns:
        0 always: unarmed, unreadable and admitted all say nothing.

    """
    if not armed(OWN_SWITCH):
        return 0
    try:
        raw: object = json.load(sys.stdin)
    except ValueError:
        return 0
    return run(as_record(raw), file_size, sys.stdout)
