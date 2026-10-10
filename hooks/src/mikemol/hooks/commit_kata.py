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
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.hooks.isolated import commit_isolated
from mikemol.hooks.snapshot import DEFAULT_NAMESPACE, NAMESPACE_ENV

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import TextIO

    from mikemol.hooks.isolated import Done

QUEUE_PATHS = (
    ".claude/paths-forward.json",
    ".claude/paths-forward.ledger",
    ".claude/paths-forward.md",
)
LOCK = "MODULE.bazel.lock"
ROOT_ENV = "MIKEMOL_GITHUB_ROOT"
ISOLATED_ENV = "MIKEMOL_COMMIT_ISOLATED"
TRAILER_ENV = "COMMIT_TRAILER"
DEFAULT_TRAILER = "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
COMMIT_TIMEOUT_S = 10800  # a cold-cache paperkit gate outlasted 3000 s twice (2026-10-07)
SHORT = 7
EXIT_NOT_COMMITTED = 1
TIMED_OUT = 124
EXIT_USAGE = 2
FENCE_ENV = "MIKEMOL_FENCE_BIN"
HELD_ENV = "MIKEMOL_COMMIT_LOCK_HELD"
COMMIT_LIMIT_ENV = "MIKEMOL_COMMIT_TIMEOUT_S"
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
    "  commits go through a private index over a snapshot where the repo's pre-commit reads\n"
    f"  MIKEMOL_REAL_ROOT (mtools:W891); {ISOLATED_ENV}=0 opts out, =1 forces\n"
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


def isolated_commit(root: Path, request: Request, paths: Sequence[str]) -> Done:
    """Commit `paths` through a private index and a snapshot of the tree that lands (W891, W902).

    ⚑ OPT-IN BY `MIKEMOL_COMMIT_ISOLATED=1` until a soak says otherwise (W904). The snapshot lives
    at its fixed namespaced path (`MIKEMOL_SNAPSHOT_ROOT`, else `snapshot.DEFAULT_NAMESPACE`).

    Returns:
        the finished `git commit`, or the step that failed before it.

    """
    namespace = Path(os.environ.get(NAMESPACE_ENV, DEFAULT_NAMESPACE))
    return commit_isolated(root, paths, message_of(request), run_git_in, namespace)


def commit_limit(env: Mapping[str, str]) -> int:
    """Say how long a commit may run, in seconds (paperkit:W299).

    A cold engine sweep outlasts the default, so `MIKEMOL_COMMIT_TIMEOUT_S` raises it; anything
    that is not a positive integer is ignored rather than read as no limit.

    Returns:
        the override when it is a positive integer, else `COMMIT_TIMEOUT_S`.

    """
    raw = env.get(COMMIT_LIMIT_ENV, "")
    return int(raw) if raw.isdecimal() and int(raw) > 0 else COMMIT_TIMEOUT_S


def run_git(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
    """Run a git command in the current directory (see `run_git_in`).

    Returns:
        the finished process.

    """
    return run_git_in(argv, {}, None)


def run_git_in(
    argv: Sequence[str], extra: Mapping[str, str], cwd: Path | None
) -> subprocess.CompletedProcess[str]:
    """Run a git command with added environment in a directory, output going to files (W928).

    ⚑ A PIPE LETS AN ORPHAN WEDGE THE WAIT. `subprocess.run(capture_output=True)` reads the pipes to
    EOF, and a gate's descendant that outlives a killed git (a bazel client, a background census)
    keeps the write end open, so the commit never returned and held the repository's claim for
    hours (paperkit-f5 measured 2h51m with git a zombie). A file has no write end to hold open:
    this waits on the git process itself, and reads the files once it is gone.

    Returns:
        the finished process; a missing git is a 127 with the reason on stderr; a git still
        running past the limit is killed and read as TIMED_OUT.

    """
    git = shutil.which("git")
    if git is None:
        return subprocess.CompletedProcess(list(argv), 127, "", "git is not installed")
    with (
        tempfile.TemporaryFile("w+", encoding="utf-8") as out,
        tempfile.TemporaryFile("w+", encoding="utf-8") as err,
    ):
        child = subprocess.Popen(
            [git, *argv],
            stdin=subprocess.DEVNULL,
            stdout=out,
            stderr=err,
            cwd=cwd,
            env={**os.environ, **extra} if extra else None,
        )
        limit = commit_limit({**os.environ, **extra})
        try:
            code = child.wait(timeout=limit)
        except subprocess.TimeoutExpired:
            # ⚑ A GATE THAT RUNS PAST THE LIMIT IS A VERDICT, NOT A CRASH (mtools:W844).
            child.kill()
            child.wait()
            return subprocess.CompletedProcess(
                list(argv), TIMED_OUT, "", f"git timed out after {limit} s"
            )
        out.seek(0)
        err.seek(0)
        return subprocess.CompletedProcess(list(argv), code, out.read(), err.read())


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


def supports_isolation(root: Path) -> bool:
    """Say whether a repository's own pre-commit knows how to run from a snapshot (W904).

    ⚑ THE PROBE IS THE HOOK'S OWN TEXT, NOT A LIST OF REPOSITORIES. A gate that finds its tools
    beside the checkout is blind in a snapshot (W939: seven refused attempts, each a lookup that
    assumed the checkout). A hook that reads `MIKEMOL_REAL_ROOT` says it was written for one, and a
    repository that has not adopted that keeps today's mode with nothing to configure.

    Returns:
        True when `<root>/.githooks/pre-commit` mentions MIKEMOL_REAL_ROOT.

    """
    hook = root / ".githooks" / "pre-commit"
    try:
        return "MIKEMOL_REAL_ROOT" in hook.read_text(encoding="utf-8")
    except OSError:
        return False


def isolation_wanted(root: Path, env: Mapping[str, str]) -> bool:
    """Decide whether this commit runs isolated: on by default where the hook supports it.

    ⚑ `MIKEMOL_COMMIT_ISOLATED=0` OPTS OUT and `=1` FORCES (the soak's spelling, kept); unset, the
    repository's own pre-commit decides (`supports_isolation`). Adopted after five clean isolated
    commits in a row (W904: a000194, 9fa2d89, ba7fd0e, bc3797e, 3bdc47a).

    Returns:
        True to commit through a private index over a snapshot.

    """
    flag = env.get(ISOLATED_ENV)
    if flag in {"0", "1"}:
        return flag == "1"
    return supports_isolation(root)


def wanted_of(root: Path, request: Request, run: Runner = run_git) -> list[str]:
    """Name the paths a request takes: its own, or the queue files, and a dirty bazel lock.

    Returns:
        the paths, in the order asked.

    """
    wanted = list(request.paths) or list(QUEUE_PATHS)
    lock_dirty = run(["-C", str(root), "diff", "--quiet", "--", LOCK]).returncode == 1
    if LOCK not in wanted and lock_dirty:
        wanted.append(LOCK)
    return wanted


def isolated_paths(root: Path, request: Request, run: Runner = run_git) -> list[str]:
    """Name the pathspecs an isolated commit takes: each wanted path that exists or is tracked.

    ⚑ NOTHING IS STAGED IN THE REAL INDEX, so a new file is not "tracked" yet; it counts when it
    is on disk, and a deleted path counts when HEAD or the index still holds it.

    Returns:
        the pathspecs; empty when nothing asked for exists or is tracked.

    """
    wanted = wanted_of(root, request, run)
    return [t for t in wanted if (root / t).exists() or tracked(root, t, run)]


def prepare(root: Path, request: Request, run: Runner = run_git) -> list[str] | None:
    """Stage what is new among the paths and build the `git commit` arguments.

    Returns:
        the arguments after `git`, or None when no requested path is tracked.

    """
    wanted = wanted_of(root, request, run)
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
            f"NOT COMMITTED {name}: timed out after {commit_limit(os.environ)} s (no verdict); "
            f"HEAD is still {before[:SHORT]}"
        )
    if rc != 0:
        return f"REFUSED {name} (rc={rc}): the cause is above; HEAD is still {before[:SHORT]}"
    return f"NOT COMMITTED {name}: exit 0 but HEAD did not move from {before[:SHORT]}"


def commit(
    root: Path, request: Request, out: TextIO, run: Runner = run_git, *, isolated: bool = False
) -> int:
    """Commit the request's paths, print git's and the hook's output, then the verdict.

    With `isolated`, the commit goes through a private index over a snapshot (W902), so the real
    index is not locked for the gate's run and a peer's unstaged file does not refuse it.

    Returns:
        0 when HEAD moved; otherwise git's own status, or EXIT_NOT_COMMITTED when that was 0.

    """
    paths = isolated_paths(root, request, run) if isolated else []
    argv = None if isolated else prepare(root, request, run)
    if argv is None and not paths:
        out.write(f"NOT COMMITTED {root.name}: none of the requested paths is tracked by git\n")
        return EXIT_NOT_COMMITTED
    before = head_of(root, run)
    done = isolated_commit(root, request, paths) if argv is None else run(argv)
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
    # ⚑ THE RUN-TIME GUARD LAUNCHER SITS BETWEEN THE CLAIM AND THE COMMIT (W921; the ask is
    # luthen-observability:W710): it reads the host's guard policy and, if it declares any, watches
    # beside the commit and interrupts the bazel client beneath it on a trip. It runs in the fence
    # venv's interpreter, so a host without that interpreter simply has no guard layer.
    interpreter = Path(fence).parent / "python3"
    guard = [str(interpreter), "-m", "mikemol.fence.guard_cli", "--"]
    argv = [
        fence,
        "hold",
        "0",
        f"claim:path:{ledger / 'commit'}",
        "--",
        "env",
        *removals,
        *restore,
        *(guard if os.access(interpreter, os.X_OK) else []),
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
    return commit(root, request, sys.stdout, isolated=isolation_wanted(root, env))
