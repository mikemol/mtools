# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The interpreter a linked git worktree borrows from its checkout's main tree (W553).

⚑⚑⚑ `.venv` IS UNTRACKED, SO A FRESH WORKTREE NEVER HAS ONE, and the armed pycheck hook refused
every `.py` edit made in one ("has no .venv/bin/python3"), which drove agents to `sed` and `cp`
(no hook sees those) or to a venv of their own. The fallback here is for the CHECKERS ONLY: when
the distribution holding the file has no interpreter of its own, the SAME distribution's `.venv`
in the checkout's main tree supplies the tools.

⚑⚑ ONLY THE INTERPRETER MOVES. The caller still stages the file, picks the config and sets the
working directory in the WORKTREE's distribution, so ruff reads the worktree's `pyproject.toml`
and mypy's `mypy_path = "src"` (relative to that directory, searched before site-packages)
resolves imports from the worktree's source, not from the main tree's editable install.

⚑ THE MAIN TREE IS ASKED OF GIT (`rev-parse --git-common-dir`), never named by a path. A path
git did not report is never followed, no link is created, and a refusal stays a refusal: a
non-worktree, a worktree whose main tree has no venv for that distribution, a missing git, or
anything odd in git's answer all return None, so the caller keeps its existing deny.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path, PurePosixPath

_GIT_TIMEOUT_S = 10
_ANSWER_LINES = 3
_VENV_PY = Path(".venv") / "bin" / "python3"
_MAIN_GIT_DIR = ".git"


def _clean_env() -> dict[str, str]:
    """Return this process's environment minus every GIT_* variable, with git's config off.

    Returns:
        the environment git is run under.

    """
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    return env


def _ask_git(root: Path) -> list[str] | None:
    """Return git's [common dir, toplevel, prefix] for `root`, or None when git cannot say.

    Returns:
        the three answers, or None.

    """
    git = shutil.which("git")
    if git is None or not root.is_dir():
        return None
    try:
        proc = subprocess.run(
            [
                git,
                "-C",
                str(root),
                "rev-parse",
                "--path-format=absolute",
                "--git-common-dir",
                "--show-toplevel",
                "--show-prefix",
            ],
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_S,
            check=False,
            env=_clean_env(),
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    lines = proc.stdout.split("\n")
    return lines if len(lines) >= _ANSWER_LINES else None


def main_tree_venv_python(root: Path) -> Path | None:
    """Return the main tree's interpreter for the distribution at `root` (a linked worktree's).

    Returns:
        `<main tree>/<root's path inside its tree>/.venv/bin/python3` when `root` lies in a linked
        worktree and that file exists; None otherwise (not a worktree, nothing there, git unsure).

    """
    answer = _ask_git(root)
    if answer is None:
        return None
    common, toplevel, prefix = answer[0], answer[1], answer[2]
    if not common or Path(common).name != _MAIN_GIT_DIR:
        return None
    main_tree = Path(common).parent
    if Path(toplevel) == main_tree:
        return None
    parts = PurePosixPath(prefix).parts
    if PurePosixPath(prefix).is_absolute() or ".." in parts:
        return None
    candidate = main_tree.joinpath(*parts) / _VENV_PY
    return candidate if candidate.exists() else None
