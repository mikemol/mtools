# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Read a repository's recent commits in the shape `intentsio.trailers_of` reads (W1934).

⚑ THE SHAPE IS `sha US stamp US message RS`, NEWEST FIRST, WITH THE STAMP IN UTC AND ISO FORM
(`2026-10-30T18:38:11Z`): `intents.resolve` compares a stamp as text with the queue's `...Z` stamps,
so a stamp in local time or git's default form would order commits against a statement wrongly, and
silently. The child runs with `TZ=UTC` and `--date=format-local`, and a git that is absent, refuses
or times out gives None, which the caller reads as no trailers (UNCHECKED rows), never as a guess.

⚑ THE QUESTION IS BUILT APART FROM ASKING IT (`command`, `child_env`), so what is put to git is a
value a test reads; only `read` runs a child.
"""

import shutil
import subprocess
from pathlib import Path

_GIT_TIMEOUT_S = 60
_COMMITS = 2000


def command(git: str, repo: Path) -> list[str]:
    """Build the `git log` argv that prints the records `trailers_of` parses.

    Returns:
        the argv: the binary, the repository, the newest `_COMMITS` commits, ISO UTC stamps and the
        `%H US %cd US %B RS` format.

    """
    return [
        git,
        "-C",
        str(repo),
        "log",
        f"-n{_COMMITS}",
        "--date=format-local:%Y-%m-%dT%H:%M:%SZ",
        "--format=%H%x1f%cd%x1f%B%x1e",
    ]


def child_env() -> dict[str, str]:
    """Name the environment the child runs in: UTC, so `format-local` prints UTC stamps.

    Returns:
        a minimal environment holding `TZ=UTC` and a fixed `PATH`.

    """
    return {"TZ": "UTC", "PATH": "/usr/bin:/bin"}


def read(repo: Path) -> str | None:
    """Read the last commits of a repository as the records `trailers_of` parses.

    Returns:
        the log text, or None when git is absent, refuses the repository or times out.

    """
    git = shutil.which("git")
    if git is None:
        return None
    try:
        done = subprocess.run(
            command(git, repo),
            capture_output=True,
            text=True,
            check=False,
            timeout=_GIT_TIMEOUT_S,
            env=child_env(),
        )
    except Exception as caught:
        if not isinstance(caught, (OSError, subprocess.TimeoutExpired)):
            raise
        return None
    return done.stdout if done.returncode == 0 else None
