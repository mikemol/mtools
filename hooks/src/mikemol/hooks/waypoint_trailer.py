# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W491: every commit message names the waypoint it lands, as a `Waypoint:` trailer line.

The accepted forms are `Waypoint: W<n>` and `Waypoint: none`. Anything else on a `Waypoint:`
line (`Waypoint: 174`, `Waypoint: w174`) is refused rather than ignored: a malformed trailer
reads like a citation and points nowhere.

⚑ Lines starting with `#` are skipped, because git strips them from the message it records;
a trailer that exists only there is absent from the commit.

CONSUMED BY: `.githooks/commit-msg`, as `hooks/.venv/bin/python3 -m mikemol.hooks.waypoint_trailer`.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_PREFIX = "Waypoint:"
_VALID = re.compile(r"Waypoint: (W[1-9][0-9]*|none)")


def trailer_problem(message: str) -> str | None:
    """Judge the `Waypoint:` trailer of a commit message.

    Returns:
        None when a valid trailer is present, else the reason for refusing.

    """
    lines = [ln.rstrip() for ln in message.splitlines() if not ln.startswith("#")]
    found = [ln for ln in lines if ln.startswith(_PREFIX)]
    if not found:
        return "no `Waypoint: W<n>` or `Waypoint: none` trailer line"
    bad = [ln for ln in found if _VALID.fullmatch(ln) is None]
    if bad:
        return f"malformed trailer {bad[0]!r}; expected `Waypoint: W<n>` or `Waypoint: none`"
    return None


def main(argv: list[str] | None = None) -> int:
    """Check the commit-message file named by the first argument.

    Returns:
        0 when the trailer is valid, 1 when it is absent or malformed, 2 on bad usage.

    """
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        sys.stderr.write("usage: waypoint_trailer COMMIT_MSG_FILE\n")
        return 2
    problem = trailer_problem(Path(args[0]).read_text(encoding="utf-8"))
    if problem is None:
        return 0
    sys.stderr.write(f"commit-msg: REFUSED — {problem}\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
