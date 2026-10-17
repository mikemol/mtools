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

import io
import os
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from mikemol.hooks.commit_body import refusal as _body_refusal
from mikemol.hooks.commit_counts import INFLIGHT, QUEUED
from mikemol.hooks.commit_gauge import note as _note_counts
from mikemol.hooks.commit_span import SUBMIT_ENV, Moments
from mikemol.hooks.commit_span import emit as _emit_spans
from mikemol.hooks.commit_span import emit_stack as _emit_stack
from mikemol.hooks.commit_turn import wait_turn as _wait_turn
from mikemol.hooks.gateenv import child_env
from mikemol.hooks.isolated import Done, commit_isolated
from mikemol.hooks.isolated import add_argv_list as _add_argv_list
from mikemol.hooks.loadwait import wait_for_load as _wait_for_load
from mikemol.hooks.snapshot import DEFAULT_NAMESPACE, NAMESPACE_ENV
from mikemol.hooks.stackdrift import QUEUE as _QUEUE
from mikemol.hooks.stackdrift import report as _drift_report
from mikemol.hooks.stackfreeze import SNAP_ENV, at_submit, forget, with_files
from mikemol.hooks.stackrun import Item as _Item
from mikemol.hooks.stackrun import Seams as _Seams
from mikemol.hooks.stackrun import items_of as _items_of
from mikemol.hooks.stackrun import run_stack as _run_stack
from mikemol.hooks.verdictlog import ship_text as _ship_text

body_refusal = _body_refusal
wait_for_load = _wait_for_load
add_argv_list = _add_argv_list
StackItem = _Item
StackSeams = _Seams
stack_items = _items_of
stack_run = _run_stack
ship_text = _ship_text
new_buffer = io.StringIO
SHIP_FLAG = "--ship"

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
LOCAL_MARKS = ("[LOCAL:", "[REMOTE-MISMATCH")  # a COMMITTED line whose push did not land (W1097)
MISMATCH_MARK = "REMOTE-MISMATCH"  # the tracking ref says pushed and the remote disagrees (W1082)
EXIT_NOT_COMMITTED = 1
TIMED_OUT = 124
EXIT_USAGE = 2
EXIT_RACED = 5
FENCE_ENV = "MIKEMOL_FENCE_BIN"
HELD_ENV = "MIKEMOL_COMMIT_LOCK_HELD"
COMMIT_LIMIT_ENV = "MIKEMOL_COMMIT_TIMEOUT_S"
TIMEOUT_ENV = "MIKEMOL_COMMIT_LOCK_TIMEOUT"
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
    "       mikemol-commit REPO --waypoint W --subject S --ship [PATH ...]   (verdicts to vlog)\n"
    "       mikemol-commit REPO --stack FILE\n"
    "  FILE is a JSON list of waypoint, subject, body, paths: several commits, ONE gate run on\n"
    "  the tip, one verdict each; a refusal lands nothing\n"
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
            env=child_env(argv, extra),
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
    present = [target for target in wanted if (root / target).exists()]
    for argv in add_argv_list(root, present):
        run(["-C", str(root), *argv])
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
    tracked = ancestor.returncode == 0
    remote = remote_head(root, run)
    if remote is None:
        word = "PUSHED" if tracked else "LOCAL: not on origin/main"
        return f"{word}; UNVERIFIED: git ls-remote origin failed"
    if remote == sha or on_remote(root, sha, remote, run):
        return "PUSHED"
    return f"{MISMATCH_MARK} remote={remote[:SHORT]}" if tracked else "LOCAL: not on origin/main"


def remote_head(root: Path, run: Runner = run_git) -> str | None:
    """Ask the remote itself where its main is (W1082), not the tracking ref a push last wrote.

    ⚑ THE TRACKING REF IS A CLAIM, THE REMOTE IS THE FACT. `origin/main` moves when a push or a
    fetch moves it, so a ref that was updated by hand, or left by a push that a hook later undid,
    reads PUSHED over a remote that never held the commit.

    Returns:
        the remote's full sha for `refs/heads/main`, or None when `git ls-remote` failed or said
        nothing (offline, no such remote, no such branch).

    """
    asked = run(["-C", str(root), "ls-remote", "origin", "refs/heads/main"])
    words = asked.stdout.split()
    return words[0] if asked.returncode == 0 and words else None


def on_remote(root: Path, sha: str, remote: str, run: Runner = run_git) -> bool:
    """Say whether the remote's main is at or above `sha`.

    A remote that moved past the commit (a peer pushed on top) names a sha this clone may not hold
    yet; one fetch of main brings it, then the ancestry is asked once more.

    Returns:
        True when `sha` is `remote` or an ancestor of it.

    """
    asked = ["-C", str(root), "merge-base", "--is-ancestor", sha, remote]
    if run(asked).returncode == 0:
        return True
    if run(["-C", str(root), "cat-file", "-e", f"{remote}^{{commit}}"]).returncode == 0:
        return False
    run(["-C", str(root), "fetch", "-q", "origin", "main"])
    return run(asked).returncode == 0


def made_by(root: Path, request: Request, span: str, run: Runner = run_git) -> bool:
    """Say whether a commit in `span` (a rev range) is the one `request` asked for (nemik:W428).

    ⚑ HEAD MOVING IS NOT THIS RUN'S COMMIT LANDING. While an isolated gate ran, the host flush
    committed `Queue: state sync` (Waypoint: none) and the old verdict read HEAD, saw it had moved,
    and printed COMMITTED for the sweep's commit; the waypoint it was gating never landed. A commit
    is this run's when its subject is the request's and it carries the request's Waypoint trailer.

    Returns:
        True when some commit in the range carries both.

    """
    listed = run(["-C", str(root), "rev-list", span]).stdout.split()
    for sha in listed:
        lines = run(["-C", str(root), "log", "-1", "--format=%B", sha]).stdout.splitlines()
        if lines[:1] == [request.subject] and f"Waypoint: {request.waypoint}" in lines:
            return True
    return False


def raced(root: Path, before: str, after: str, run: Runner = run_git) -> str:
    """Say that HEAD moved to a commit this run did not make (nemik:W428).

    Returns:
        the RACED line, naming HEAD's sha and subject.

    """
    subject = run(["-C", str(root), "log", "-1", "--format=%s", after]).stdout.strip()
    return (
        f"RACED {root.name}: HEAD moved to {after[:SHORT]} {subject}, which this run did not make; "
        f"its own commit did not land (HEAD was {before[:SHORT]})"
    )


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
    root: Path, request: Request, out: TextIO, run: Runner = run_git, isolated: bool = False
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
    moved = bool(after) and after != before
    span = f"{before}..{after}" if before else after
    mine = made_by(root, request, span, run) if moved else True
    if mine:
        line = verdict(root, before, after, done.returncode, run)
        if any(mark in line for mark in LOCAL_MARKS):
            out.write(f"push not completed: run  git -C {root} push origin HEAD:main\n")
        out.write(f"{line}\n")
    else:
        out.write(f"{raced(root, before, after, run)}\n")
    if moved:
        return 0 if mine else EXIT_RACED
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
    # ⚑ THE TRAILERS ARE THE TOOL'S (W1273): a body carrying `Waypoint:` or `Co-Authored-By:` would
    # have it twice, so it is refused here with the reason, as a usage error.
    reason = body_refusal(values["--body"])
    if reason is not None:
        sys.stderr.write(f"mikemol-commit: {reason}\n")
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


# From `bazel-bin/hooks/.venv/bin`, `bazel-bin` is the parent two levels above `.venv`.
BAZEL_BIN_DEPTH = 2


def fence_of(env: Mapping[str, str], python: str) -> str:
    """Name the fence to claim with: the one the launcher named, else one found near `python`.

    ⚑ A REPO THAT INSTALLS THE HOOKS AND FENCE WHEELS INTO ONE VENV HAS NO LAUNCHER, so nothing set
    `MIKEMOL_FENCE_BIN` and its commits ran unlocked with a note, though `mikemol-membudget` sat in
    the same `bin/` (linux-sources, 2026-10-11, github-8f). The venv's own script is the fallback.

    ⚑ MTOOLS' OWN BAZEL BUILD KEEPS THE FENCE IN A VENV BESIDE THE HOOKS VENV, not inside it:
    `bazel-bin/hooks/.venv/bin/python3` and `bazel-bin/fence/.venv/bin/mikemol-membudget`. A commit
    run straight from that build (linux-sources, after its repin to f04f0a2) found neither the
    variable nor a script in `bin/`, so that sibling build is the second fallback.

    Returns:
        the named path when set and non-empty, else the first of `<python's directory>/
        mikemol-membudget` and the sibling bazel venv's script that is executable, else the first.

    """
    named = env.get(FENCE_ENV, "")
    if named:
        return named
    here = Path(python).parent
    beside = here / "mikemol-membudget"
    found = [beside]
    if len(here.parents) > BAZEL_BIN_DEPTH:
        found.append(
            here.parents[BAZEL_BIN_DEPTH] / "fence" / ".venv" / "bin" / "mikemol-membudget"
        )
    return str(next((c for c in found if os.access(c, os.X_OK)), beside))


def claim_of(
    root: Path,
    env: Mapping[str, str],
    own: Sequence[str],
    run: Runner = run_git,
    python: str = sys.executable,
) -> Claim | str:
    """Plan the re-exec of this commit under a blocking per-repository fence claim (W886, W910).

    ⚑ THE CLAIM IS KEYED ON THE REPOSITORY BEING COMMITTED, NOT ON WHERE THE LAUNCHER LIVES. It was
    keyed on the launcher's checkout, so a paperkit gate (minutes long) held every mtools commit
    behind it, and the reverse. The repository is resolved here, once, by `resolve_root`.

    ⚑ `hold 0 claim:path:<git dir>/mtools/commit` is fence's zero-capacity claim: it waits, names
    the holder, and is reaped when its owner dies. The ledger is per repository under the git
    directory with the load and zram gates off, so a busy host cannot stall a commit.

    ⚑ THE WAIT HAS NO DEADLINE (W1463, github-8f 2026-10-17): it ended after an hour, and with
    35-minute gates a stack three back in the queue expired with no verdict, three of them in one
    day. A wall-clock give-up is what the fleet rule forbids. The wait ends when the holder does,
    and the fence reaps a holder that died; only a caller that sets MIKEMOL_COMMIT_LOCK_TIMEOUT
    gets a bound, and that is its own choice.

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
    fence = fence_of(env, python)
    if not os.access(fence, os.X_OK):
        return "the fence venv is not built (add the mikemol-fence dist to this repo's pins)"
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
    if env.get(TIMEOUT_ENV):
        held["MEMBUDGET_TIMEOUT"] = env[TIMEOUT_ENV]
    else:
        held.pop("MEMBUDGET_TIMEOUT", None)
    return Claim(argv, held)


def isolation_reason(root: Path, env: Mapping[str, str]) -> str:
    """Say why `isolation_wanted` answered as it did.

    Returns:
        the cause: the forcing or opting-out variable, or what the repository's pre-commit says.

    """
    flag = env.get(ISOLATED_ENV)
    if flag == "1":
        return f"forced by {ISOLATED_ENV}=1"
    if flag == "0":
        return f"opted out by {ISOLATED_ENV}=0"
    if supports_isolation(root):
        return "the repository's pre-commit names MIKEMOL_REAL_ROOT"
    return "the repository's pre-commit does not name MIKEMOL_REAL_ROOT"


def lock_state(claim: str) -> str:
    """Say whether the commit holds the repository's claim.

    Returns:
        "held" when the claim is already taken above this process, else "none" and the reason.

    """
    return f"none ({claim})" if claim else "held"


def routing_line(isolated: bool, reason: str, lock: str) -> str:
    """Name the path this commit took and its lock, so a repo can tell a fallback from a choice.

    ⚑ A HOOK THAT DOES NOT NAME MIKEMOL_REAL_ROOT FALLS TO THE PLAIN PATH WITHOUT A WORD (the
    linux-sources trial, 2026-10-11, mtools:W1015): the commit printed COMMITTED and nothing said
    which path ran or whether it held the lock.

    Returns:
        one line, before the verdict.

    """
    path = "isolated" if isolated else "plain"
    return f"mikemol-commit: path: {path} ({reason}); lock: {lock}"


def stack_target(args: Sequence[str], env: Mapping[str, str]) -> tuple[Path, Path] | None:
    """Read `REPO --stack FILE`, the form that lands several commits under one gate (W1164).

    Returns:
        the repository and the stack file, or None when the arguments are not exactly that form.

    """
    if len(args) == len(("REPO", "--stack", "FILE")) and args[1] == "--stack":
        return resolve_root(args[0], env), Path(args[2])
    return None


class TeeBuffer(io.StringIO):
    """A buffer that also writes everything to standard output as it arrives (W1442).

    ⚑ THE STACK'S OUTPUT STAYS LIVE: the span starter needs the verdict lines after the run, and
    holding them back until then would change when the caller sees them. This keeps the exact
    stream and remembers a copy.
    """

    def write(self, text: str, /) -> int:
        """Pass `text` to standard output, then keep it.

        Returns:
            the number of characters kept.

        """
        sys.stdout.write(text)
        return super().write(text)


def run_stack_mode(
    root: Path,
    stack_file: Path,
    env: Mapping[str, str],
    isolated: bool,
    started: tuple[int, int],
) -> int:
    """Land the stack in `stack_file`: build, gate the tip once, move HEAD, one verdict each.

    ⚑ A STACK NEEDS THE ISOLATED PATH: the gate runs on a snapshot of the tip, which only a
    repository whose pre-commit knows `MIKEMOL_REAL_ROOT` can do. A plain-path repository is
    refused, not run some other way.

    ⚑ THE RUN IS ONE TRACE (W1442): `started` is (submitted, lease held) in epoch ns, and the spans
    `commit.stack`, `commit.stack.queued` and `commit.stack.gating` start after the last verdict.

    Returns:
        the stack's exit code; EXIT_USAGE for an unreadable file; EXIT_NOT_COMMITTED when the
        repository cannot isolate.

    """
    if not isolated:
        sys.stdout.write(
            f"NOT COMMITTED {root.name}: a stack needs the isolated commit path "
            f"({isolation_reason(root, env)})\n"
        )
        return EXIT_NOT_COMMITTED
    items = stack_items(stack_file)
    if isinstance(items, str):
        sys.stderr.write(f"mikemol-commit: {items}\n")
        return EXIT_USAGE
    items = with_files(items, root, env, run_git_in)
    for line in _drift_report(items, root / _QUEUE):
        sys.stdout.write(line + "\n")
    trailer = env.get(TRAILER_ENV) or DEFAULT_TRAILER
    seams = StackSeams(
        run=run_git_in,
        namespace=Path(env.get(NAMESPACE_ENV, DEFAULT_NAMESPACE)),
        message_of=lambda item: message_of(
            Request(item.waypoint, item.subject, item.body, (), trailer)
        ),
        published=lambda sha: published(root, sha),
    )
    tee = TeeBuffer()
    try:
        code = stack_run(root, items, tee, seams)
    finally:
        forget(env)
    moments = Moments(started[0], started[1], time.time_ns())
    _emit_stack(tee.getvalue(), moments, [item.waypoint for item in items], env)
    return code


def commit_buffered(
    root: Path, request: Request, isolated: bool, after: Callable[[str], None]
) -> int:
    """Commit, print the output as ever, then hand its text to `after` (W1168, W1441).

    ⚑ THE OUTPUT IS NOT CHANGED: `commit` already writes after the commit has finished, so holding
    it in a buffer and printing it at once is the same bytes at the same moment. Whatever `after`
    does (shipping verdict lines, starting spans) comes AFTER the print and can fail only
    silently, so a logging fault never alters a verdict.

    Returns:
        the same exit code `commit` returned.

    """
    out = new_buffer()
    code = commit(root, request, out, isolated=isolated)
    sys.stdout.write(out.getvalue())
    after(out.getvalue())
    return code


def submitted_ns(env: Mapping[str, str]) -> int:
    """Read when this commit was first submitted, else now.

    ⚑ THE SUBMISSION TIME SURVIVES THE CLAIM RE-EXEC through the environment (`SUBMIT_ENV`): the
    process that waits for the lease is replaced by the one that holds it, so the queued span can
    only be measured from a time the first process left behind. A malformed value reads as now.

    Returns:
        epoch nanoseconds.

    """
    given = env.get(SUBMIT_ENV, "")
    return int(given) if given.isdigit() else time.time_ns()


def after_of(
    shipping: bool, env: Mapping[str, str], waypoint: str, started: tuple[int, int]
) -> Callable[[str], None]:
    """Build what runs on a finished commit's output: ship the verdict lines, start the spans.

    Returns:
        a function of the output text; `started` is (submitted, lease held) in epoch ns.

    """

    def after(text: str) -> None:
        if shipping:
            ship_text(text)
        _emit_spans(text, Moments(started[0], started[1], time.time_ns()), waypoint, env)

    return after


def _take_turn(ledger: Path, key: str) -> None:
    """Wait for every commit submitted before this one to finish, then go on (W1463).

    ⚑ BEFORE THE CLAIM, NOT INSIDE IT: the fence woke whichever waiting run it chose, so a stack
    built on an earlier queued stack could gate first and be refused for files not yet in HEAD. The
    queue's own map already orders the live commits by submission time, so a run waits here until
    none is ahead and only then asks for the lease.
    """
    waited = _wait_turn(ledger / "commit.counts", key)
    if waited:
        sys.stdout.write(f"commit: waited for {waited} earlier submission(s) to finish\n")


def main(argv: Sequence[str] | None = None) -> int:
    """Run `mikemol-commit`.

    Returns:
        the exit code from `commit`, or EXIT_USAGE for a bad command line. A commit that must wait
        for the repository's claim is re-exec'd under it and never returns here.

    """
    env = dict(os.environ)
    args = list(sys.argv[1:] if argv is None else argv)
    shipping = SHIP_FLAG in args
    bare = [a for a in args if a != SHIP_FLAG]
    stacked = stack_target(bare, env)
    parsed = parse(bare, env) if stacked is None else None
    if stacked is not None:
        root = stacked[0]
    elif parsed is not None:
        root = parsed[0]
    else:
        sys.stderr.write(USAGE)
        return EXIT_USAGE
    submitted = submitted_ns(env)
    env[SUBMIT_ENV] = str(submitted)
    ledger = ledger_of(root)
    key = str(submitted)
    if not env.get(HELD_ENV):
        track(ledger, key, QUEUED, env)
    if stacked is not None and not env.get(HELD_ENV):
        env[SNAP_ENV] = at_submit(root, stacked[1], ledger, key, run_git_in)
    if ledger is not None and not env.get(HELD_ENV):
        _take_turn(ledger, key)
    claim = claim_of(root, env, [sys.executable, sys.argv[0], *args])
    if isinstance(claim, Claim):
        os.execve(claim.argv[0], claim.argv, claim.env)
    if claim:
        sys.stderr.write(f"mikemol-commit: no commit lock ({claim}); committing unlocked\n")
    held = Held(env, submitted, time.time_ns(), claim, shipping)
    track(ledger, key, INFLIGHT, env)
    try:
        return run_held(root, (stacked, parsed), held)
    finally:
        track(ledger, key, None, env)


@dataclass(frozen=True)
class Held:
    """What a commit knows once it holds the lease (or went without it)."""

    env: Mapping[str, str]
    submitted: int
    lease: int
    claim: str
    shipping: bool


def ledger_of(root: Path) -> Path | None:
    """Name the repository's commit ledger directory, `<git dir>/mtools`, where the counts live.

    Returns:
        the directory path, or None when git cannot name the git directory.

    """
    found = run_git(["-C", str(root), "rev-parse", "--absolute-git-dir"])
    return Path(found.stdout.strip()) / "mtools" if found.returncode == 0 else None


def track(ledger: Path | None, key: str, state: str | None, env: Mapping[str, str]) -> None:
    """Move this commit to `state` in the live counts, None ending it; never raises."""
    if ledger is not None:
        _note_counts(ledger, key, state, env)


def run_held(
    root: Path,
    which: tuple[tuple[Path, Path] | None, tuple[Path, Request] | None],
    held: Held,
) -> int:
    """Run the stack or the single commit once the lease is held.

    Returns:
        the exit code of the stack or the commit; EXIT_USAGE when neither was parsed.

    """
    stacked, parsed = which
    waited = wait_for_load(held.env)
    if waited:
        sys.stdout.write(waited + "\n")
    isolated = isolation_wanted(root, held.env)
    reason = isolation_reason(root, held.env)
    lock = lock_state(held.claim)
    sys.stdout.write(routing_line(isolated=isolated, reason=reason, lock=lock) + "\n")
    started = (held.submitted, held.lease)
    if stacked is not None:
        return run_stack_mode(root, stacked[1], held.env, isolated, started)
    if parsed is None:
        return EXIT_USAGE
    after = after_of(held.shipping, held.env, parsed[1].waypoint, started)
    return commit_buffered(root, parsed[1], isolated, after)
