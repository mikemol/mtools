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
import sys
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


def _run(argv: list[str], env: dict[str, str] | None = None) -> str | None:
    # The output of a child that exited 0, or None when it is absent, failed or timed out.
    try:
        done = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            check=False,
            timeout=_GIT_TIMEOUT_S,
            env=env,
        )
    except Exception as caught:
        if not isinstance(caught, (OSError, subprocess.TimeoutExpired)):
            raise
        return None
    return done.stdout if done.returncode == 0 else None


def read_commits(root: Path) -> str | None:
    """Read the last 500 commits as `sha US UTC-stamp US message RS` records (W1639).

    Returns:
        the text `reconcilecmd.parse_log` reads, or None when git is absent or refused.

    """
    git = shutil.which("git")
    if git is None:
        return None
    fmt = "--format=%H%x1f%cd%x1f%B%x1e"
    date = "--date=format-local:%Y-%m-%dT%H:%M:%SZ"
    env = {"TZ": "UTC", "PATH": "/usr/bin:/bin"}
    return _run([git, "-C", str(root), "log", "-n500", date, fmt], env)


def read_head_files(root: Path) -> frozenset[str] | None:
    """Name every file HEAD holds, relative to the root (W1717).

    Returns:
        the paths, or None when git is absent or refused: no answer is not an empty tree.

    """
    git = shutil.which("git")
    if git is None:
        return None
    listing = _run([git, "-C", str(root), "ls-tree", "-r", "--name-only", "HEAD"])
    return None if listing is None else frozenset(listing.splitlines())


def gate_tool(root: Path, beside: Path, on_path: str | None) -> str | None:
    """Find `mikemol-commit`: beside the running interpreter, then on PATH, then the repo's own.

    ⚑ A FULL-PATH LAUNCH HAS NO .venv/bin ON PATH (luthen-observability:W1541, W1862): the writer
    and `mikemol-commit` are installed into one environment, so the directory of the
    interpreter running the writer is the sibling's home whatever PATH says.

    Returns:
        the tool's path, or None when none of the three has it.

    """
    sibling = beside / "mikemol-commit"
    if sibling.is_file():
        return str(sibling)
    own = root / "hooks" / ".venv" / "bin" / "mikemol-commit"
    return on_path or (str(own) if own.is_file() else None)


def read_gate(root: Path) -> str | None:
    """Read the live-commit map as JSON from `mikemol-commit --in-gate --json` (W1587).

    Returns:
        the JSON text, or None when the tool is absent or refused.

    """
    tool = gate_tool(root, Path(sys.executable).parent, shutil.which("mikemol-commit"))
    if tool is None:
        return None
    return _run([tool, root.name, "--in-gate", "--json"])


def landed_since(root: Path, since: str, reader: Reader = read_log) -> set[str] | None:
    """Name the cards a commit carries since `since`.

    Returns:
        the symbols, or None when `since` is empty or the log could not be read.

    """
    if not since:
        return None
    log = reader(root, since)
    return None if log is None else trailer_cards(log)
