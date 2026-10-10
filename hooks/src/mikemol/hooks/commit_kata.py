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
FENCE_ENV = "MIKEMOL_FENCE_BIN"
HELD_ENV = "MIKEMOL_COMMIT_LOCK_HELD"
TIMEOUT_ENV = "MIKEMOL_COMMIT_LOCK_TIMEOUT"
DEFAULT_LOCK_TIMEOUT_S = "3600"
BUDGET = (
    "MEMBUDGET_FILE",
    "MEMBUDGET_MAXLOAD",
    "MEMBUDGET_ZRAM_MAX",
    "MEMBUDGET_TIMEOUT",
    "MEMBUDGET_NOBLOCK",
    "MEMBUDGET_PARENT",
)
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

    ⚑ A STAGED DELETION IS STILL TRACKED (W855, luthen-observability:W256). `git rm` takes the path
    out of the index, so `ls-files` alone dropped it from the pathspec, the `--only` commit rebuilt
    its temporary index from HEAD with the file back in it, and the gate's index-matches-tree arm
    refused with a remedy (`git add`) that did not apply. A path HEAD holds is tracked, whether or
    not the index or the tree still has it.

    Returns:
        True when `path` is in the index or in HEAD.

    """
    in_index = run(["-C", str(root), "ls-files", "--error-unmatch", "--", path]).returncode == 0
    return in_index or run(["-C", str(root), "cat-file", "-e", f"HEAD:{path}"]).returncode == 0


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


def published(root: Path, sha: str, run: Runner = run_git) -> str:
    """Say whether `sha` is on the remote main (W924), so nobody asks 'is my sha published?'.

    ⚑ READ AFTER THE COMMIT RETURNS: the post-commit hook pushes inside `git commit`, so by the time
    the verdict is built the push has succeeded or been refused. The remote-tracking ref is what the
    push last updated, which is the fact a pin needs ("can only pin a published sha").

    Returns:
        `PUSHED`, `LOCAL: not on origin/main`, or `no origin/main` when the repository has no
        such ref.

    """
    ref = run(["-C", str(root), "rev-parse", "--verify", "--quiet", "origin/main"])
    if ref.returncode != 0:
        return "no origin/main"
    ancestor = run(["-C", str(root), "merge-base", "--is-ancestor", sha, "origin/main"])
    return "PUSHED" if ancestor.returncode == 0 else "LOCAL: not on origin/main"


def verdict(root: Path, before: str, after: str, rc: int, run: Runner = run_git) -> str:
    """Say what a commit did, from HEAD and not from the gate's last stage.

    Returns:
        the COMMITTED, REFUSED or NOT COMMITTED line.

    """
    name = root.name
    if after and after != before:
        subject = run(["-C", str(root), "log", "-1", "--format=%s", after]).stdout.strip()
        return f"COMMITTED {name} {after[:SHORT]} {subject} [{published(root, after, run)}]"
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


@dataclass(frozen=True)
class Claim:
    """What to exec so this commit runs under the repository's fence claim."""

    argv: list[str]
    env: dict[str, str]


def claim_of(
    root: Path, env: Mapping[str, str], own: Sequence[str], run: Runner = run_git
) -> Claim | str:
    """Plan the re-exec of this commit under a blocking per-repository fence claim (W886, W910).

    ⚑ THE CLAIM IS KEYED ON THE REPOSITORY BEING COMMITTED, NOT ON WHERE THE LAUNCHER LIVES. It was
    keyed on the launcher's checkout, so a paperkit gate (minutes long) held every mtools commit
    behind it, and the reverse. The repository is resolved here, once, by `resolve_root`.

    ⚑ `hold 0 claim:path:<git dir>/mtools/commit` is fence's zero-capacity claim: it waits, names
    the holder, and is reaped when its owner dies. The ledger is per repository under the git
    directory with the load and zram gates off, so a busy host cannot stall a commit, and the wait
    is bounded by MIKEMOL_COMMIT_LOCK_TIMEOUT (an hour by default).

    ⚑⚑ NOTHING OF THAT CONFIGURATION REACHES THE COMMAND. `hold` hands its environment to what it
    runs, and the gate beneath leases from the HOST ledger with the HOST's ceilings, so each
    budget variable is put back as it was (or removed if it was unset) by the `env` between the
    hold and the commit.

    Returns:
        the Claim to exec; or the reason there is none ("" when this process already holds it, so
        a nested call does not wait on its own parent).

    """
    if env.get(HELD_ENV):
        return ""
    fence = env.get(FENCE_ENV, "")
    if not fence or not os.access(fence, os.X_OK):
        return "the fence venv is not built ('bazel build //fence:.venv')"
    gitdir = run(["-C", str(root), "rev-parse", "--absolute-git-dir"])
    if gitdir.returncode != 0:
        return f"{root} is not a git checkout"
    ledger = Path(gitdir.stdout.strip()) / "mtools"
    ledger.mkdir(parents=True, exist_ok=True)
    removals = [part for name in BUDGET if name not in env for part in ("-u", name)]
    restore = [f"{HELD_ENV}=1", *(f"{name}={env[name]}" for name in BUDGET if name in env)]
    argv = [
        fence,
        "hold",
        "0",
        f"claim:path:{ledger / 'commit'}",
        "--",
        "env",
        *removals,
        *restore,
        *own,
    ]
    held = {k: v for k, v in env.items() if k not in {"MEMBUDGET_NOBLOCK", "MEMBUDGET_PARENT"}}
    held["MEMBUDGET_FILE"] = str(ledger / "commit.ledger")
    held["MEMBUDGET_MAXLOAD"] = "0"
    held["MEMBUDGET_ZRAM_MAX"] = "0"
    held["MEMBUDGET_TIMEOUT"] = env.get(TIMEOUT_ENV) or DEFAULT_LOCK_TIMEOUT_S
    return Claim(argv, held)


def main(argv: Sequence[str] | None = None) -> int:
    """Run `mikemol-commit`.

    Returns:
        the exit code from `commit`, or EXIT_USAGE for a bad command line. A commit that must wait
        for the repository's claim is re-exec'd under it and never returns here.

    """
    env = dict(os.environ)
    args = list(sys.argv[1:] if argv is None else argv)
    parsed = parse(args, env)
    if parsed is None:
        sys.stderr.write(USAGE)
        return EXIT_USAGE
    root, request = parsed
    claim = claim_of(root, env, [sys.executable, sys.argv[0], *args])
    if isinstance(claim, Claim):
        os.execve(claim.argv[0], claim.argv, claim.env)
    if claim:
        sys.stderr.write(f"mikemol-commit: no commit lock ({claim}); committing unlocked\n")
    return commit(root, request, sys.stdout)
