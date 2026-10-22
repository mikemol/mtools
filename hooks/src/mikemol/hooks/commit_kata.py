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
from mikemol.hooks.commit_counts import WAYPOINTS_ENV as _WAYPOINTS_ENV
from mikemol.hooks.commit_counts import live as _live
from mikemol.hooks.commit_counts import live_json as _live_json
from mikemol.hooks.commit_gauge import note as _note_counts
from mikemol.hooks.commit_span import SUBMIT_ENV, Moments
from mikemol.hooks.commit_span import emit as _emit_spans
from mikemol.hooks.commit_span import emit_stack as _emit_stack
from mikemol.hooks.commit_turn import wait_turn as _wait_turn
from mikemol.hooks.commit_verdict import emit as _emit_verdict
from mikemol.hooks.commit_withdraw import clear_marker as _clear_marker
from mikemol.hooks.commit_withdraw import marker_path as _marker_path
from mikemol.hooks.commit_withdraw import withdraw as _withdraw
from mikemol.hooks.commitprogress import Probes as _Probes
from mikemol.hooks.commitprogress import gate_roots as _gate_roots
from mikemol.hooks.commitprogress import gate_servers as _gate_servers
from mikemol.hooks.commitprogress import looks_from as _looks_from
from mikemol.hooks.commitprogress import period_from as _period_from
from mikemol.hooks.commitprogress import phase_of as _phase_of
from mikemol.hooks.commitprogress import servers_of as _servers_of
from mikemol.hooks.commitprogress import stall_text as _stall_text
from mikemol.hooks.commitprogress import watch as _watch
from mikemol.hooks.gateenv import child_env
from mikemol.hooks.gatephase import stage_note as _stage_note
from mikemol.hooks.heartbeat import try_beat as _try_beat
from mikemol.hooks.historyfetch import fetch as _fetch_history
from mikemol.hooks.isolated import Done, commit_isolated
from mikemol.hooks.isolated import add_argv_list as _add_argv_list
from mikemol.hooks.launcher import announce as _announce_launcher
from mikemol.hooks.loadwait import wait_for_load as _wait_for_load
from mikemol.hooks.rootdrop import drop as _drop
from mikemol.hooks.rootdrop import invoker_home as _invoker_home
from mikemol.hooks.rootdrop import owner_of as _owner_of
from mikemol.hooks.shardgate import refusal as _shard_refusal
from mikemol.hooks.snapshot import DEFAULT_NAMESPACE, NAMESPACE_ENV
from mikemol.hooks.stackbuildfiles import refusal as _build_refusal
from mikemol.hooks.stackdrift import QUEUE as _QUEUE
from mikemol.hooks.stackdrift import report as _drift_report
from mikemol.hooks.stackfreeze import SNAP_ENV, at_submit, forget, with_files
from mikemol.hooks.stackimports import refusal as _stack_refusal
from mikemol.hooks.stackpin import pin as _pin_trees
from mikemol.hooks.stackpin import release as _release_trees
from mikemol.hooks.stackrun import Item as _Item
from mikemol.hooks.stackrun import Seams as _Seams
from mikemol.hooks.stackrun import items_of as _items_of
from mikemol.hooks.stackrun import run_stack as _run_stack
from mikemol.hooks.tool_path import find as _find_tool
from mikemol.hooks.trainjoin import Follower as _Follower
from mikemol.hooks.trainlead import lead as _train_lead
from mikemol.hooks.trainverdict import take as _take_verdict
from mikemol.hooks.verdictlog import ship_text as _ship_text

stack_build_refusal = _build_refusal
take_verdict = _take_verdict
train_lead = _train_lead
TrainGroup = _Follower
pin_trees = _pin_trees
release_trees = _release_trees
WAYPOINTS_ENV = _WAYPOINTS_ENV
live_commits = _live
live_text = _live_json
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
IN_GATE_FLAG = "--in-gate"
WITHDRAW_FLAG = "--withdraw"
MARKER_ENV = "MIKEMOL_COMMIT_WITHDRAW_MARKER"
BEAT_TOOL = "mikemol-commit"
"""The tool name a submit leaves in the session heartbeat (W1482)."""

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
SHORT = 7
LOCAL_MARKS = ("[LOCAL:", "[REMOTE-MISMATCH")  # a COMMITTED line whose push did not land (W1097)
MISMATCH_MARK = "REMOTE-MISMATCH"  # the tracking ref says pushed and the remote disagrees (W1082)
EXIT_NOT_COMMITTED = 1
TIMED_OUT = 124
STALLED = "stalled, no CPU and no output"
EXIT_USAGE = 2
EXIT_RACED = 5
FENCE_ENV = "MIKEMOL_FENCE_BIN"
FENCE_PIN = (
    'uv add "mikemol-fence @ git+https://github.com/mikemol/mtools.git@<sha>#subdirectory=fence"'
)
HELD_ENV = "MIKEMOL_COMMIT_LOCK_HELD"
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
    "       mikemol-commit REPO --withdraw KEY   (a queued submission leaves the queue)\n"
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


def waiter(child: subprocess.Popen[bytes]) -> Callable[[float], int | None]:
    """Wrap a child's wait so a slice that runs on reads as None, not as an exception.

    Returns:
        a function from seconds to the exit code, or None while the child is still running.

    """

    def wait(seconds: float) -> int | None:
        try:
            return child.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            return None

    return wait


def sized(handle: TextIO) -> int:
    """Say how many bytes a commit's output file holds so far.

    Returns:
        the file's size.

    """
    return os.fstat(handle.fileno()).st_size


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
        merged = {**os.environ, **extra}
        pace = (_looks_from(merged), _period_from(merged))
        roots = _gate_roots(Path(merged.get("MIKEMOL_REAL_ROOT", "")).name, merged)
        probes = _Probes(
            size=lambda: sized(out) + sized(err),
            extra=lambda: _gate_servers(_servers_of(), roots),
        )
        code = _watch(waiter(child), child.pid, probes, pace)
        if code is None:
            # ⚑ A GATE THAT MAKES NO PROGRESS IS A VERDICT, NOT A CRASH (mtools:W844, W1804): no
            # CPU in its process tree and no new output for a run of looks, never a wall limit.
            child.kill()
            child.wait()
            err.seek(0)
            return subprocess.CompletedProcess(
                list(argv), TIMED_OUT, "", _stall_text(err.read(), *pace)
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
    return f"{head}Waypoint: {request.waypoint}\n{request.trailer}\n"


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


def with_stage(line: str, shown: str) -> str:
    """Say which stage refused on a REFUSED line, from the phase marks in the gate's output.

    Returns:
        the line with 'refused in stage <name>; ' before its cause; the line as it was when it
        is not a REFUSED line or the output carries no marks.

    """
    marker = "): the cause is above"
    note = _stage_note(shown)
    if not note or not line.startswith("REFUSED ") or marker not in line:
        return line
    return line.replace(marker, f"): {note}the cause is above", 1)


def with_phase(line: str, shown: str) -> str:
    """Name the gate phase a stalled commit had reached, in its NOT COMMITTED line.

    Returns:
        the line with `stalled` followed by the last phase mark in `shown`; any other line
        unchanged.

    """
    return line.replace(
        STALLED, f"stalled in gate phase {_phase_of(shown)}, no CPU and no output", 1
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
        return f"NOT COMMITTED {name}: {STALLED} (no verdict); HEAD is still {before[:SHORT]}"
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
        line = with_stage(
            with_phase(verdict(root, before, after, done.returncode, run), shown), shown
        )
        if any(mark in line for mark in LOCAL_MARKS):
            out.write(f"push not completed: run  git -C {root} push origin HEAD:main\n")
        out.write(f"{line}\n")
        _emit_verdict(root.name, (line, done.returncode, shown), os.environ)
    else:
        out.write(f"{raced(root, before, after, run)}\n")
    if moved:
        return 0 if mine else EXIT_RACED
    return done.returncode or EXIT_NOT_COMMITTED


def fleet_root(given: str, env: Mapping[str, str]) -> Path:
    """Find the directory a bare repository name lives under, whatever HOME says (W1752).

    Returns:
        `ROOT_ENV` when set, else the invoking user's own fleet root when they ran this through
        sudo and it holds the name, else the effective user's.

    """
    named = env.get(ROOT_ENV)
    if named:
        return Path(named)
    invoker = _invoker_home(env)
    if invoker is not None and (invoker / "github" / given).is_dir():
        return invoker / "github"
    return Path.home() / "github"


def become_owner(root: Path) -> None:
    """Drop to the repository's owner when run as root, before anything is touched (W1752).

    A root-owned repository, or a process that is not root, changes nothing; the operator's rule
    is that a user-level tool run as root neither refuses nor leaves root-owned files behind.
    """
    owner = _owner_of(root, os.geteuid())
    if owner is not None:
        os.environ.update(_drop(owner, os.environ))


def resolve_root(given: str, env: Mapping[str, str]) -> Path:
    """Resolve a repository named by path, or by directory name under the host root.

    Returns:
        the repository's directory; a root process has become its owner by then.

    """
    if "/" in given or given.startswith("."):
        root = Path(given).resolve()
    else:
        root = fleet_root(given, env) / given
    become_owner(root)
    _announce_launcher(sys.prefix, root, env, sys.stderr)
    return root


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
        top = here.parents[BAZEL_BIN_DEPTH]
        found.append(top / "fence" / ".venv" / "bin" / "mikemol-membudget")
        # ⚑ THE SHARED RESOLVER (W1714) answers for a source checkout's `bazel-bin` and the PATH,
        # so the commit lease and bazel-admit cannot disagree about where the fence is.
        shared = _find_tool("mikemol-membudget", FENCE_ENV, top, env)
        if shared is not None:
            found.append(shared)
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
        history=lambda repo: _fetch_history(repo, env),
    )
    tee = TeeBuffer()
    try:
        # ⚑ W1654: the stacks queued behind this one join its run, gated once at the joined tip;
        # each is told its own verdict, and nobody behind means the stack runs as it always did.
        group = TrainGroup(str(started[0]), tuple(items))
        joined = train_lead(root, ledger_of(root), group, (seams, env), tee)
        code = stack_run(root, items, tee, seams) if joined is None else joined
    finally:
        forget(env)
        release_trees(root, ledger_of(root), str(started[0]), run_git_in)
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


def named_waypoints(stacked: tuple[Path, Path] | None, parsed: tuple[Path, Request] | None) -> str:
    """List the waypoints this submission names, comma-separated, for the live-commit map (W1586).

    Returns:
        the stack file's waypoints in order, or the single commit's, or "" when neither is readable.

    """
    if stacked is not None:
        items = stack_items(stacked[1])
        return "" if isinstance(items, str) else ",".join(item.waypoint for item in items)
    return "" if parsed is None else parsed[1].waypoint


def in_gate(args: Sequence[str], env: Mapping[str, str], out: TextIO) -> int:
    """Print the commits the repository's gate holds now, with their waypoints, as one JSON list.

    ⚑ A READ OF THE LIVE-COMMIT MAP, NOTHING MORE (W1587, nemik:W682): it queues nothing, takes no
    lease and moves no counter, so asking cannot change what it reports. A dead entry is not listed.

    Returns:
        0; EXIT_USAGE when no repository is named; EXIT_NOT_COMMITTED when git cannot name the
        repository's directory.

    """
    named = [a for a in args if not a.startswith("--")]
    if not named:
        sys.stderr.write(USAGE)
        return EXIT_USAGE
    ledger = ledger_of(resolve_root(named[0], env))
    if ledger is None:
        sys.stderr.write(f"mikemol-commit: {named[0]}: git cannot name its directory\n")
        return EXIT_NOT_COMMITTED
    out.write(live_text(live_commits(ledger / "commit.counts")) + "\n")
    return 0


def withdraw_cmd(args: Sequence[str], env: Mapping[str, str], out: TextIO) -> int:
    """Take a queued submission out of the queue and release the trees it pinned (W1703).

    ⚑ ONLY A QUEUED SUBMISSION, through the live-commit map (`commit_withdraw`): an in-flight
    gate is refused with the reason, and a key nobody is running is said so.

    Returns:
        0 when withdrawn; 1 when no live submission has the key; EXIT_USAGE with no repository or
        no key; 2 when the submission is in flight.

    """
    at = list(args).index(WITHDRAW_FLAG)
    key = args[at + 1] if at + 1 < len(args) else ""
    named = [a for i, a in enumerate(args) if i not in {at, at + 1} and not a.startswith("--")]
    if not named or not key:
        sys.stderr.write(USAGE)
        return EXIT_USAGE
    root = resolve_root(named[0], env)
    ledger = ledger_of(root)
    if ledger is None:
        sys.stderr.write(f"mikemol-commit: {named[0]}: git cannot name its directory\n")
        return EXIT_NOT_COMMITTED
    code, text = _withdraw(ledger / "commit.counts", key)
    out.write(text + "\n")
    if code == 0:
        release_trees(root, ledger, key, run_git_in)
    return code


def admin_mode(args: Sequence[str], env: Mapping[str, str]) -> int | None:
    """Run the read or maintenance mode the arguments name, if any.

    Returns:
        the mode's exit code, or None when the arguments name no such mode.

    """
    if IN_GATE_FLAG in args:
        return in_gate([a for a in args if a != IN_GATE_FLAG], env, sys.stdout)
    if WITHDRAW_FLAG in args:
        return withdraw_cmd(args, env, sys.stdout)
    return None


def submit_problem(root: Path, stack_file: Path, env: Mapping[str, str]) -> str | None:
    """Judge a submitted stack by the refusals made before it waits for its turn.

    The first that has something to say wins: an import only a later entry adds (W1527), a build
    file naming a source no entry carries (W1604), a mutants grid already past half of its CPU
    budget (W1602).

    Returns:
        the findings, or None when the stack may wait.

    """
    snap = env[SNAP_ENV]
    return (
        _stack_refusal(root, stack_file, snap, run_git_in)
        or stack_build_refusal(root, stack_file, snap, run_git_in)
        or _shard_refusal(root, stack_file, env)
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run `mikemol-commit`.

    Returns:
        the exit code from `commit`, or EXIT_USAGE for a bad command line. A commit that must wait
        for the repository's claim is re-exec'd under it and never returns here.

    """
    env = dict(os.environ)
    args = list(sys.argv[1:] if argv is None else argv)
    mode = admin_mode(args, env)
    if mode is not None:
        return mode
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
    env.setdefault(WAYPOINTS_ENV, named_waypoints(stacked, parsed))
    ledger = ledger_of(root)
    key = str(submitted)
    env.setdefault(MARKER_ENV, marker_value(ledger, key))
    submit(ledger, key, env)
    if stacked is not None and not env.get(HELD_ENV):
        env[SNAP_ENV] = at_submit(root, stacked[1], ledger, key, run_git_in)
        # ⚑ W1604: a build file naming a Python source no entry carries is refused here, before the
        # queue turn, as an unsound import is (W1603's finding, the waiting-for-failure case).
        problem = submit_problem(root, stacked[1], env)
        if problem is not None:
            return unordered(root, ledger, key, env, problem)
        # ⚑ W1615: each entry's tree is pinned now, so a presubmit can run on it while this stack
        # waits for the lease; the run releases them. A failure pins nothing and refuses nothing.
        pin_trees(root, ledger, key, env[SNAP_ENV], run_git_in)
    if ledger is not None and not env.get(HELD_ENV):
        _take_turn(ledger, key)
        # ⚑ W1671: a train leader that joined this stack into its run left the verdict; print it
        # and return its code without taking the lease, so the gate that judged it is not rerun.
        joined = take_verdict(ledger, key)
        if joined is not None:
            sys.stdout.write(joined.text)
            forget(env)
            release_trees(root, ledger, key, run_git_in)
            track(ledger, key, None, env)
            return joined.code
    claim = claim_of(root, env, [sys.executable, sys.argv[0], *args])
    if isinstance(claim, Claim):
        os.execve(claim.argv[0], claim.argv, claim.env)
    if claim:
        # ⚑ W1696: A COMMIT THAT CANNOT TAKE THE LEASE DOES NOT RUN WITHOUT IT (operator 2026-10-09,
        # 695f3e0a line 46901: block-until-held is the model). The fence is a second pin, so no
        # correct install lacks it and "no fence" names a broken one, with the fix on the line.
        sys.stderr.write(f"mikemol-commit: REFUSED, no commit lock ({claim})\n  {FENCE_PIN}\n")
        forget(env)
        release_trees(root, ledger, key, run_git_in)
        track(ledger, key, None, env)
        return EXIT_USAGE
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


def submit(ledger: Path | None, key: str, env: Mapping[str, str]) -> None:
    """Queue a fresh submission and leave the heartbeat; a re-exec under the lease does neither."""
    if not env.get(HELD_ENV):
        beat(ledger)
        track(ledger, key, QUEUED, env)


def beat(ledger: Path | None) -> None:
    """Leave the session heartbeat (W1482): a submit is the session using a tool; never raises."""
    if ledger is not None:
        _try_beat(ledger.parent, BEAT_TOOL, time.time_ns())


def unordered(
    root: Path, ledger: Path | None, key: str, env: Mapping[str, str], problem: str
) -> int:
    """Refuse a stack at submit whose frozen files import a module only a later entry adds (W1527).

    Returns:
        EXIT_NOT_COMMITTED, after printing each finding and taking the submission out of the counts.

    """
    sys.stdout.write(
        f"NOT COMMITTED {root.name}: this stack is refused at submit, before it waits:\n"
    )
    sys.stdout.write(problem + "\n")
    forget(env)
    track(ledger, key, None, env)
    return EXIT_NOT_COMMITTED


def marker_value(ledger: Path | None, key: str) -> str:
    """Name the file that asks this submission's gate to stop (W1705), for the gate to read.

    Returns:
        the marker's path, or empty when there is no ledger to hold one.

    """
    return "" if ledger is None else str(_marker_path(ledger / "commit.counts", key))


def track(ledger: Path | None, key: str, state: str | None, env: Mapping[str, str]) -> None:
    """Move this commit to `state` in the live counts, None ending it; never raises."""
    if ledger is not None:
        _note_counts(ledger, key, state, env)
        if state is None:
            _clear_marker(ledger / "commit.counts", key)


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
