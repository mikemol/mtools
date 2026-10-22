# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-worktree-reap REPO`: classify a repository's scratch worktrees, read-only (W1382).

Scratch worktrees (`mikemol-scratch`, W1378) pile up: this repository's own `git worktree list`
holds seventeen, fourteen of them `prunable` (their directory is gone) and the rest unaccounted for.
Removing the wrong one loses work, so the first step only CLASSIFIES, and removes, saves and prunes
nothing:

    held             a process has this directory as its working directory (never touched)
    new              an existing worktree no earlier run listed (never a candidate)
    dirty            uncommitted changes in the tree
    unmerged         commits on the branch that `git cherry main BRANCH` says main lacks (or a
                     detached head, which cannot be judged)
    gone             the directory is missing, git calls it prunable, and its branch holds nothing
                     main lacks: only the record is left
    clean-equivalent a clean tree and every commit already in main

⚑ THE ORDER IS THE SAFETY: held first (a live session's checkout is never a candidate), then a
missing directory's branch is judged by its commits alone, then a dirty tree, then unmerged commits;
only a worktree that is none of those is clean-equivalent. A class that could not be established is
never read as clean: a detached head is unmerged, and a git command that failed gives None, which
reads as unmerged for `cherry` and as dirty for `status`, never as an empty answer.

⚑ `/proc/<pid>/cwd` IS A LINK, AND IT IS READ AS ONE: `Path.readlink` returns the path and follows
nothing, which is the only way to ask a process where it is. No repository link is read.

⚑ TWO READS OVER TIME, ONE RUN APART (W1809): a worktree whose directory exists and which an
earlier run did not list is `new`, and is never a candidate, because a checkout made a minute
ago is clean and merged-looking and its owner has not started. The earlier run's listing is
kept in `<git common dir>/mtools/worktree-reap.seen`, the only thing this command writes (the
worktrees themselves are never touched). The first run has nothing remembered, so it reports
every present worktree as new and says so on standard error; a second run is the second read.

The `refs/stash-reap` save and the removal by exact path are later steps (W1382).

CONSUMED BY: the `mikemol-worktree-reap` console script.
"""

import sys
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from mikemol.hooks.commit_kata import run_git_in

HELD = "held"
DIRTY = "dirty"
UNMERGED = "unmerged"
GONE = "gone"
NEW = "new"
SAVE_FLAG = "--save"
REMOVE_FLAG = "--remove"
CLEAN = "clean-equivalent"
EXIT_OK = 0
EXIT_USAGE = 2
BRANCH_PREFIX = "refs/heads/"
USAGE = (
    "usage: mikemol-worktree-reap REPO [--save] [--remove]   (classifies; --save keeps dirty and\n"
    "unmerged work under refs/stash-reap/; --remove removes gone and clean-equivalent worktrees)\n"
)
FIRST_RUN = (
    "mikemol-worktree-reap: first run for this repository, so every present worktree is `new`; "
    "run it again later and the second read classifies them\n"
)
Readlink = Callable[[Path], str | None]


@dataclass(frozen=True, slots=True)
class Worktree:
    """One registered worktree: its path, its branch ('' when detached), and whether it is gone."""

    path: str
    branch: str
    prunable: bool


def parse_worktrees(text: str) -> list[Worktree]:
    """Read `git worktree list --porcelain`, one blank-line-separated block per worktree.

    Returns:
        every worktree in the order printed (the main one first).

    """
    found: list[Worktree] = []
    for block in text.split("\n\n"):
        path = branch = ""
        prunable = False
        for line in block.splitlines():
            if line.startswith("worktree "):
                path = line[len("worktree ") :]
            elif line.startswith("branch "):
                branch = line[len("branch ") :].removeprefix(BRANCH_PREFIX)
            elif line.startswith("prunable"):
                prunable = True
        if path:
            found.append(Worktree(path, branch, prunable))
    return found


def readlink_of(path: Path) -> str | None:
    """Read where a link points without following it.

    Returns:
        the target string, or None when it cannot be read (the process exited, or no access).

    """
    try:
        return str(path.readlink())
    except OSError:
        return None


def holders(path: str, proc: Path = Path("/proc"), read: Readlink = readlink_of) -> list[int]:
    """List the processes whose working directory is `path` or inside it.

    Returns:
        their pids, in pid order; empty when /proc cannot be listed.

    """
    try:
        names = sorted(int(entry.name) for entry in proc.iterdir() if entry.name.isdecimal())
    except OSError:
        return []
    inside = path.rstrip("/") + "/"
    found: list[int] = []
    for pid in names:
        cwd = read(proc / str(pid) / "cwd")
        if cwd is not None and (cwd + "/").startswith(inside):
            found.append(pid)
    return found


def unmerged_commits(cherry: str) -> bool:
    """Say whether `git cherry` lists a commit the upstream lacks (a line beginning `+`).

    Returns:
        True when one is listed.

    """
    return any(line.startswith("+") for line in cherry.splitlines())


def classify(
    wt: Worktree, cherry: str | None, status: str | None, *, held: bool, new: bool = False
) -> str:
    """Classify one worktree from what was read about it; None means the read failed.

    Returns:
        `HELD`, `NEW`, `UNMERGED`, `GONE`, `DIRTY` or `CLEAN`, in that order of precedence.

    """
    if held:
        return HELD
    if new:
        return NEW
    risky = not wt.branch or cherry is None or unmerged_commits(cherry)
    if wt.prunable:
        return UNMERGED if risky else GONE
    if status is None or status.strip():
        return DIRTY
    return UNMERGED if risky else CLEAN


def _out(root: Path, argv: Sequence[str]) -> str | None:
    # Run git in `root` and return its stdout, None when it failed.
    done = run_git_in(["-C", str(root), *argv], {}, None)
    return done.stdout if done.returncode == 0 else None


def seen_file(root: Path) -> Path | None:
    """Name the file that remembers the worktrees an earlier run listed.

    Returns:
        `<git common dir>/mtools/worktree-reap.seen`, or None when git cannot say.

    """
    common = _out(root, ["rev-parse", "--git-common-dir"])
    if common is None:
        return None
    return (root / common.strip()).resolve() / "mtools" / "worktree-reap.seen"


def load_seen(path: Path | None) -> set[str] | None:
    """Read the remembered worktree paths.

    Returns:
        the paths, or None when there is no file (a first run) or it cannot be read.

    """
    if path is None:
        return None
    try:
        return set(path.read_text(encoding="utf-8").splitlines())
    except OSError:
        return None


def save_seen(path: Path | None, listed: Sequence[Worktree]) -> None:
    """Remember this run's worktrees for the next one; a failed write remembers nothing."""
    if path is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(f"{wt.path}\n" for wt in listed), encoding="utf-8")
    except OSError:
        return


_AUTHOR = {
    "GIT_AUTHOR_NAME": "mikemol-worktree-reap",
    "GIT_AUTHOR_EMAIL": "noreply@mikemol.invalid",
    "GIT_COMMITTER_NAME": "mikemol-worktree-reap",
    "GIT_COMMITTER_EMAIL": "noreply@mikemol.invalid",
    # ⚑ A FIXED DATE, SO THE SAME WORK IS THE SAME COMMIT: a commit's sha includes its timestamps,
    # and a ref named by that sha would differ between two saves a second apart, which broke the
    # idempotence the name promises (the gate refused W1810's first stack on exactly that).
    "GIT_AUTHOR_DATE": "1970-01-01T00:00:00Z",
    "GIT_COMMITTER_DATE": "1970-01-01T00:00:00Z",
}
STASH_REF = "refs/stash-reap/"
SHORT = 7


def _in(folder: Path, argv: Sequence[str], env: dict[str, str]) -> str | None:
    # Run git in `folder` with added environment and return its stripped stdout, None on failure.
    done = run_git_in(list(argv), env, folder)
    return done.stdout.strip() if done.returncode == 0 else None


def snapshot_commit(wt: Worktree) -> str | None:
    """Commit everything a worktree holds (tracked changes and untracked files) without touching it.

    ⚑ A TEMPORARY INDEX, NEVER THE WORKTREE'S OWN: `git stash create` leaves untracked files out,
    and an untracked file is exactly the work a scratch checkout loses. With `GIT_INDEX_FILE`
    pointing at a scratch file, `read-tree HEAD` and `add -A` build the whole state, `write-tree`
    names it and `commit-tree` makes a commit on top of HEAD (so the branch's own unmerged commits
    ride along). The worktree's own index and files are not written or changed.

    Returns:
        the commit's sha, or None when any step failed.

    """
    folder = Path(wt.path)
    with tempfile.TemporaryDirectory() as scratch:
        env = {**_AUTHOR, "GIT_INDEX_FILE": str(Path(scratch) / "index")}
        for argv in (["read-tree", "HEAD"], ["add", "-A"]):
            if _in(folder, argv, env) is None:
                return None
        tree = _in(folder, ["write-tree"], env)
        if not tree:
            return None
        return _in(folder, ["commit-tree", tree, "-p", "HEAD", "-m", f"stash-reap {wt.path}"], env)


def ref_name(wt: Worktree, sha: str) -> str:
    """Name the ref that keeps a worktree's work: its branch (or directory) and the commit.

    ⚑ THE SHA IS IN THE NAME, so saving the same work twice is the same ref (idempotent) and saving
    different work never overwrites an earlier save.

    Returns:
        `refs/stash-reap/<branch with / as ->-<sha7>`.

    """
    slug = wt.branch.replace("/", "-") if wt.branch else f"detached-{Path(wt.path).name}"
    return f"{STASH_REF}{slug}-{sha[:SHORT]}"


def save(root: Path, wt: Worktree, kind: str) -> str | None:
    """Keep a dirty or unmerged worktree's work under `refs/stash-reap/`, and report the ref.

    Returns:
        the ref name; None for any other class, or when the work could not be committed or named.

    """
    if kind not in {DIRTY, UNMERGED}:
        return None
    folder = root if wt.prunable else Path(wt.path)
    if kind == DIRTY:
        sha = snapshot_commit(wt)
    else:
        sha = _in(folder, ["rev-parse", wt.branch or "HEAD"], {})
    if not sha:
        return None
    ref = ref_name(wt, sha)
    return ref if _in(root, ["update-ref", ref, sha], {}) is not None else None


def remove(root: Path, wt: Worktree, kind: str) -> bool:
    """Remove one worktree by its exact path, only when it is gone or clean-equivalent and unheld.

    ⚑ GIT'S OWN REFUSAL IS THE LAST GATE: `git worktree remove PATH` is run WITHOUT `--force`, so a
    tree that turned dirty or locked since the classification is refused by git and stays. MEASURED
    2026-10-22 on a scratch repository: the same command, without force, cleanly removes the record
    of a worktree whose directory is already gone. Held is read again just before, so a session that
    entered the directory after the classification keeps it. The branch is not touched: the card is
    the worktree, and a branch holding commits is what `--save` keeps.

    Returns:
        True when git removed it; False for any other class, a held directory, or git's refusal.

    """
    if kind not in {GONE, CLEAN} or holders(wt.path):
        return False
    return _in(root, ["worktree", "remove", wt.path], {}) is not None


def _kind_of(root: Path, wt: Worktree, upstream: str, seen: set[str] | None) -> str:
    # Read what is needed about one worktree and classify it.
    cherry = _out(root, ["cherry", upstream, wt.branch]) if wt.branch else ""
    status = "" if wt.prunable else _out(Path(wt.path), ["status", "--porcelain"])
    fresh = not wt.prunable and (seen is None or wt.path not in seen)
    return classify(wt, cherry, status, held=bool(holders(wt.path)), new=fresh)


def report(
    root: Path, upstream: str = "main", *, saving: bool = False, removing: bool = False
) -> list[str]:
    """Classify every scratch worktree of the repository at `root`.

    With `saving`, a dirty or unmerged worktree's work is also kept under `refs/stash-reap/` and
    the ref is a fourth field on its line. With `removing`, a gone or clean-equivalent worktree
    is removed by its exact path (`remove`) and its line ends in `removed`.

    Returns:
        one `CLASS<TAB>PATH<TAB>BRANCH[<TAB>REF][<TAB>removed]` line per worktree other than
        the main one.

    """
    listed = parse_worktrees(_out(root, ["worktree", "list", "--porcelain"]) or "")[1:]
    where = seen_file(root)
    seen = load_seen(where)
    lines: list[str] = []
    for wt in listed:
        kind = _kind_of(root, wt, upstream, seen)
        line = f"{kind}\t{wt.path}\t{wt.branch or '(detached)'}"
        ref = save(root, wt, kind) if saving else None
        if ref:
            line += f"\t{ref}"
        if removing and remove(root, wt, kind):
            line += "\tremoved"
        lines.append(line)
    save_seen(where, listed)
    return lines


def main(argv: Sequence[str] | None = None) -> int:
    """Print the classification of a repository's scratch worktrees.

    Returns:
        `EXIT_OK` with the lines printed, `EXIT_USAGE` when the one argument (REPO) is missing.

    """
    given = sys.argv[1:] if argv is None else list(argv)
    args = [word for word in given if word not in {SAVE_FLAG, REMOVE_FLAG}]
    if len(args) != 1:
        sys.stderr.write(USAGE)
        return EXIT_USAGE
    root = Path(args[0])
    first = load_seen(seen_file(root)) is None
    lines = report(root, saving=SAVE_FLAG in given, removing=REMOVE_FLAG in given)
    sys.stdout.writelines(f"{line}\n" for line in lines)
    if first and lines:
        sys.stderr.write(FIRST_RUN)
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
