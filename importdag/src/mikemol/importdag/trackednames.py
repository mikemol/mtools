# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Name the files git tracks in a distribution, so the graph is checked over what a gate sees.

The sandbox a gate builds holds only tracked files, so a module that exists on disk and is not
tracked cannot fail it, and a tracked module the committed graph does not name fails it only after
the gate has queued (W2011). `graph --check --files` takes the names from `git ls-files` instead of
walking the directory, so a new tracked module fails first, by name, with the `--write` to run
(agreed with github-8f, 2026-10-25, option a: no glob survives).

⚑ NO ANSWER IS NOT AN EMPTY LIST: with no git or a git that refuses, the caller gets None and says
so; an empty answer would read as "the distribution tracks nothing" and every module as missing.

CONSUMED BY: `graph.main` (`--files`).
"""

import shutil
import subprocess
from pathlib import Path

_GIT_TIMEOUT_S = 60


def of(dist: Path) -> list[str] | None:
    """List the distribution's tracked files, relative to the distribution.

    Returns:
        the paths git lists for the directory (index entries, so a staged new file counts), sorted;
        None when git is absent or refuses.

    """
    git = shutil.which("git")
    if git is None:
        return None
    try:
        done = subprocess.run(
            [git, "-C", str(dist), "ls-files", "-z", "--", "."],
            capture_output=True,
            text=True,
            check=False,
            timeout=_GIT_TIMEOUT_S,
        )
    except Exception as caught:
        if not isinstance(caught, (OSError, subprocess.TimeoutExpired)):
            raise
        return None
    if done.returncode != 0:
        return None
    return sorted(name for name in done.stdout.split("\0") if name)
