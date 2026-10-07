# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W832: `mikemol-commit`, the commit kata graduated, ending in ONE line that says what happened.

The host's commit kata printed git's output (the `[main <sha>] subject` line first, then the hook's
stderr, last) and its exit code, so a commit's outcome read as "completed, exit 0" and was checked
by hand against `git log` every time (operator, 2026-10-06: "why do we have to keep asking whether
the commit landed?"). A gate that passes and a commit that lands are different facts: a hook can
exit 0 over a commit git did not make. This compares HEAD before and after and prints, last:

    COMMITTED <repo> <sha7> <subject>
    REFUSED <repo> (rc=N): the cause is above; HEAD is still <sha7>
    NOT COMMITTED <repo>: <why>

⚑ GRADUATED FROM `.claude/katas/katas.py` (mtools:W796): standing rule 16 keeps executable code
out of `.claude/`, so the kata could not even be edited to say this. Ported with its two pieces of
hard-won behaviour: a modified tracked `MODULE.bazel.lock` rides along (a bazel gate rewrites its
own lock, and paperkit's hook-index refuses a commit while any tracked file differs from the
index), and only tracked paths are pathspecs (an ignored file would make the whole commit refuse).

⚑ NO TRACKED PATH IS NOT A COMMIT OF EVERYTHING STAGED: the kata built `git commit --` with an
empty pathspec in that case, which commits whatever is staged. This returns NOT COMMITTED and runs
nothing.

CONSUMED BY: the `mikemol-commit` console script.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import TextIO

QUEUE_PATHS = (
    ".claude/paths-forward.json",
    ".claude/paths-forward.ledger",
    ".claude/paths-forward.md",
)
LOCK = "MODULE.bazel.lock"
ROOT_ENV = "MIKEMOL_GITHUB_ROOT"
TRAILER_ENV = "COMMIT_TRAILER"
DEFAULT_TRAILER = "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
COMMIT_TIMEOUT_S = 10800  # a cold-cache paperkit gate outlasted 3000 s twice (2026-10-07)
SHORT = 7
EXIT_NOT_COMMITTED = 1
TIMED_OUT = 124
EXIT_USAGE = 2
USAGE = (
    "usage: mikemol-commit REPO --waypoint W --subject S [--body B] [PATH ...]\n"
    "  REPO is a path, or a directory name under the host root; PATH defaults to the queue files\n"
)

Runner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]
"""Run one git command: the arguments after `git` in, the finished process out."""


@dataclass(frozen=True)
class Request:
    """One commit asked for: which waypoint, what it says, and which paths it takes."""

    waypoint: str
    subject: str
    body: str = ""
    paths: tuple[str, ...] = ()
    trailer: str = DEFAULT_TRAILER


def run_git(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
    """Run a git command, capturing its output.

    Returns:
        the finished process; a missing git is a 127 with the reason on stderr.

    """
    git = shutil.which("git")
    if git is None:
        return subprocess.CompletedProcess(list(argv), 127, "", "git is not installed")
    try:
        return subprocess.run(
            [git, *argv],
            capture_output=True,
            text=True,
            check=False,
            timeout=COMMIT_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        # ⚑ A GATE THAT RUNS PAST THE LIMIT IS A VERDICT, NOT A CRASH (mtools:W844). This raised, so
        # the caller read a traceback where the one line it reads should have been.
        return subprocess.CompletedProcess(
            list(argv), TIMED_OUT, "", f"git timed out after {COMMIT_TIMEOUT_S} s"
        )


def head_of(root: Path, run: Runner = run_git) -> str:
    """Name the commit `root`'s HEAD points at.

    Returns:
        the full sha, or "" for a repository with no commit yet.

    """
    return run(["-C", str(root), "rev-parse", "HEAD"]).stdout.strip()


def tracked(root: Path, path: str, run: Runner) -> bool:
    """Say whether git tracks `path` (only a tracked path can be a commit pathspec).

    Returns:
        True when `path` is in the index.

    """
    return run(["-C", str(root), "ls-files", "--error-unmatch", "--", path]).returncode == 0


def message_of(request: Request) -> str:
    """Build the commit message: subject, body, the waypoint trailer, the co-author trailer.

    Returns:
        the message text.

    """
    head = f"{request.subject}\n\n{request.body}\n\n" if request.body else f"{request.subject}\n\n"
    return f"{head}Waypoint: {request.waypoint}\n\n{request.trailer}\n"


def prepare(root: Path, request: Request, run: Runner = run_git) -> list[str] | None:
    """Stage what is new among the paths and build the `git commit` arguments.

    Returns:
        the arguments after `git`, or None when no requested path is tracked.

    """
    wanted = list(request.paths) or list(QUEUE_PATHS)
    lock_dirty = run(["-C", str(root), "diff", "--quiet", "--", LOCK]).returncode == 1
    if LOCK not in wanted and lock_dirty:
        wanted.append(LOCK)
    for target in wanted:
        if (root / target).exists():
            run(["-C", str(root), "add", "-A", "--", target])
    pathspecs = [target for target in wanted if tracked(root, target, run)]
    if not pathspecs:
        return None
    return ["-C", str(root), "commit", "-m", message_of(request), "--", *pathspecs]


def verdict(root: Path, before: str, after: str, rc: int, run: Runner = run_git) -> str:
    """Say what a commit did, from HEAD and not from the gate's last stage.

    Returns:
        the COMMITTED, REFUSED or NOT COMMITTED line.

    """
    name = root.name
    if after and after != before:
        subject = run(["-C", str(root), "log", "-1", "--format=%s", after]).stdout.strip()
        return f"COMMITTED {name} {after[:SHORT]} {subject}"
    if rc == TIMED_OUT:
        return (
            f"NOT COMMITTED {name}: timed out after {COMMIT_TIMEOUT_S} s (no verdict); "
            f"HEAD is still {before[:SHORT]}"
        )
    if rc != 0:
        return f"REFUSED {name} (rc={rc}): the cause is above; HEAD is still {before[:SHORT]}"
    return f"NOT COMMITTED {name}: exit 0 but HEAD did not move from {before[:SHORT]}"


def commit(root: Path, request: Request, out: TextIO, run: Runner = run_git) -> int:
    """Commit the request's paths, print git's and the hook's output, then the verdict.

    Returns:
        0 when HEAD moved; otherwise git's own status, or EXIT_NOT_COMMITTED when that was 0.

    """
    argv = prepare(root, request, run)
    if argv is None:
        out.write(f"NOT COMMITTED {root.name}: none of the requested paths is tracked by git\n")
        return EXIT_NOT_COMMITTED
    before = head_of(root, run)
    done = run(argv)
    shown = (done.stdout + done.stderr).strip()
    if shown:
        out.write(f"{shown}\n")
    after = head_of(root, run)
    out.write(f"{verdict(root, before, after, done.returncode, run)}\n")
    if after and after != before:
        return 0
    return done.returncode or EXIT_NOT_COMMITTED


def resolve_root(given: str, env: Mapping[str, str]) -> Path:
    """Resolve a repository named by path, or by directory name under the host root.

    Returns:
        the repository's directory.

    """
    if "/" in given or given.startswith("."):
        return Path(given).resolve()
    return Path(env.get(ROOT_ENV) or Path.home() / "github") / given


def parse(args: Sequence[str], env: Mapping[str, str]) -> tuple[Path, Request] | None:
    """Read `REPO --waypoint W --subject S [--body B] [PATH ...]`.

    Returns:
        the repository and the request, or None for a usage error (a missing value or flag).

    """
    values = {"--waypoint": "", "--subject": "", "--body": ""}
    positional: list[str] = []
    index = 0
    while index < len(args):
        word = args[index]
        if word in values:
            if index + 1 >= len(args):
                return None
            values[word] = args[index + 1]
            index += 2
        else:
            positional.append(word)
            index += 1
    if not positional or not values["--waypoint"] or not values["--subject"]:
        return None
    request = Request(
        waypoint=values["--waypoint"],
        subject=values["--subject"],
        body=values["--body"],
        paths=tuple(positional[1:]),
        trailer=env.get(TRAILER_ENV) or DEFAULT_TRAILER,
    )
    return resolve_root(positional[0], env), request


def main(argv: Sequence[str] | None = None) -> int:
    """Run `mikemol-commit`.

    Returns:
        the exit code from `commit`, or EXIT_USAGE for a bad command line.

    """
    env = dict(os.environ)
    parsed = parse(sys.argv[1:] if argv is None else argv, env)
    if parsed is None:
        sys.stderr.write(USAGE)
        return EXIT_USAGE
    root, request = parsed
    return commit(root, request, sys.stdout)
