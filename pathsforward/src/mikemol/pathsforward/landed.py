# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Name the cards a landed commit carries since a time (mtools:W1377, github-8f).

⚑ A CARD IS ADVANCED WHEN A LANDED COMMIT CARRIES ITS SYMBOL, not when a queue edit stamped it:
`last_worked` is stamped on every update, so one bulk call that unblocked 130 cards read as 165
cards advanced by a tick that landed nothing of the kind. Every commit `mikemol-commit` writes ends
in a `Waypoint: W<n>` trailer, so the trailers of the commits since a time name what landed.

⚑ NO ANSWER IS NOT ZERO: with no git or an unreadable log the caller gets None and keeps the old
count, because a tick that could not look must not report that nothing landed.
CONSUMED BY: `closegate.judge`.
"""

import re
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import cast

_TRAILER = re.compile(r"^Waypoint: (W[0-9]+)[ \t]*$", re.MULTILINE)
_GIT_TIMEOUT_S = 60

Reader = Callable[[Path, str], str | None]


def trailer_cards(log: str) -> set[str]:
    """Read the symbols named by `Waypoint:` trailers in a log of commit messages.

    Returns:
        the distinct symbols.

    """
    return set(cast("list[str]", _TRAILER.findall(log)))


def read_log(root: Path, since: str) -> str | None:
    """Read the messages of the commits made since a time.

    Returns:
        the messages, or None when git is absent or refused.

    """
    git = shutil.which("git")
    if git is None:
        return None
    try:
        done = subprocess.run(
            [git, "-C", str(root), "log", f"--since={since}", "--format=%B"],
            capture_output=True,
            text=True,
            check=False,
            timeout=_GIT_TIMEOUT_S,
        )
    except Exception as caught:
        if not isinstance(caught, (OSError, subprocess.TimeoutExpired)):
            raise
        return None
    return done.stdout if done.returncode == 0 else None


def landed_since(root: Path, since: str, reader: Reader = read_log) -> set[str] | None:
    """Name the cards a commit carries since `since`.

    Returns:
        the symbols, or None when `since` is empty or the log could not be read.

    """
    if not since:
        return None
    log = reader(root, since)
    return None if log is None else trailer_cards(log)
