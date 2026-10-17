# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""An isolated checkout for the next card, opened and closed by symbol (mtools:W1378).

⚑⚑ THE RACE THIS ENDS: editing a dist in the main tree while a commit touching it is queued lets the
gate snapshot a half-edited tree (a queued stack was refused for exactly that, 2026-10-17: new code
against an old test). A scratch worktree gives each card its own tree, so the main tree stands
still under whatever is queued and the next card is built beside it. `open` makes the worktree and
a branch named for the card; `close` removes the worktree. LANDING a finished change into the main
tree is the other half (W1379), not this module.

⚑ THE ROOT IS DECLARED, NEVER GUESSED: worktrees live under `MIKEMOL_SCRATCH_ROOT`, one directory
per repo and card (`<root>/<repo>-W<n>`). With no root there is no default, so a worktree never
lands inside the repo it was cut from or in a directory nobody named. A symbol that is not `W<n>`,
a path that already exists and a repo that is not a git checkout are refused before git is run.

⚑ GIT IS REACHED ONLY THROUGH `Run`, a plain function the tests replace; the real one runs git with
the environment's GIT_* variables dropped, as `worktree_venv` does, so a hook's own git context
never leaks into the new checkout. `close` uses plain `git worktree remove`, which itself refuses a
dirty tree, so uncommitted work is never destroyed by it.

⚑ TO TEST THE WORKTREE'S CODE, NOT THE MAIN TREE'S: a dist's editable install points at the main
tree, so pytest in the worktree would import the main tree's source. `PYTHONPATH=<dist>/src` comes
before the editable path, which is the recipe `hint` prints. That ordering is stated from how the
interpreter builds `sys.path` and has not been run end to end here.
"""

import os
import re
import shutil
import subprocess
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

ROOT_ENV = "MIKEMOL_SCRATCH_ROOT"
_SYMBOL = re.compile(r"W\d+")
Run = Callable[[Sequence[str]], tuple[int, str]]


class ScratchError(RuntimeError):
    """A worktree could not be opened or closed, with the reason."""


def root_of(environ: Mapping[str, str]) -> Path:
    """Read the declared scratch root.

    Returns:
        the root as a Path.

    Raises:
        ScratchError: when `MIKEMOL_SCRATCH_ROOT` is unset or empty (there is no default).

    """
    named = environ.get(ROOT_ENV, "")
    if not named:
        msg = f"{ROOT_ENV} is not set: there is no default scratch root"
        raise ScratchError(msg)
    return Path(named)


def path_for(root: Path, repo: Path, symbol: str) -> Path:
    """Name the worktree of one card of one repo.

    Returns:
        `<root>/<repo name>-<symbol>`.

    Raises:
        ScratchError: when the symbol is not `W<n>`.

    """
    if _SYMBOL.fullmatch(symbol) is None:
        msg = f"{symbol!r} is not a waypoint symbol (W<n>)"
        raise ScratchError(msg)
    return root / f"{repo.resolve().name}-{symbol}"


def add_argv(repo: Path, where: Path, symbol: str) -> list[str]:
    """Build the git argv that cuts a worktree and a branch named for the card from HEAD.

    Returns:
        the argv.

    """
    return [
        "git",
        "-C",
        str(repo),
        "worktree",
        "add",
        "-b",
        f"scratch/{symbol}",
        str(where),
        "HEAD",
    ]


def remove_argv(repo: Path, where: Path) -> list[str]:
    """Build the git argv that removes the worktree (refused by git when it is dirty).

    Returns:
        the argv.

    """
    return ["git", "-C", str(repo), "worktree", "remove", str(where)]


def hint(where: Path, dist: str, main_python: Path) -> str:
    """Say how to run a dist's tests against the worktree's source, not the main tree's.

    Returns:
        a one-line shell recipe.

    """
    return f"PYTHONPATH={where / dist / 'src'} {main_python} -m pytest {where / dist / 'tests'}"


def open_worktree(repo: Path, root: Path, symbol: str, run: Run) -> Path:
    """Cut a scratch worktree for `symbol` from the repo's HEAD.

    Returns:
        the new worktree's path.

    Raises:
        ScratchError: when the repo is not a checkout, the path exists, or git refuses.

    """
    if not (repo / ".git").exists():
        msg = f"{repo} is not a git checkout"
        raise ScratchError(msg)
    where = path_for(root, repo, symbol)
    if where.exists():
        msg = f"{where} already exists: close {symbol} first"
        raise ScratchError(msg)
    root.mkdir(parents=True, exist_ok=True)
    code, said = run(add_argv(repo, where, symbol))
    if code != 0:
        msg = f"git worktree add exited {code}: {said.strip()[:300]}"
        raise ScratchError(msg)
    return where


def close_worktree(repo: Path, root: Path, symbol: str, run: Run) -> Path:
    """Remove the scratch worktree for `symbol`; git refuses when it holds uncommitted work.

    Returns:
        the path that was removed.

    Raises:
        ScratchError: when there is no such worktree or git refuses.

    """
    where = path_for(root, repo, symbol)
    if not where.is_dir():
        msg = f"no scratch worktree for {symbol} at {where}"
        raise ScratchError(msg)
    code, said = run(remove_argv(repo, where))
    if code != 0:
        msg = f"git worktree remove exited {code}: {said.strip()[:300]}"
        raise ScratchError(msg)
    return where


def run_git(argv: Sequence[str]) -> tuple[int, str]:
    """Run git with the caller's GIT_* variables dropped and capture its exit code and stderr.

    Returns:
        (exit code, stderr text).

    """
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    git = shutil.which("git") or "git"
    proc = subprocess.run([git, *argv[1:]], capture_output=True, text=True, check=False, env=env)
    code: int = proc.returncode
    err: str = proc.stderr
    return code, err
