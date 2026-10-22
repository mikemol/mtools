# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-worktree-reap REPO`: classify a repository's scratch worktrees, read-only (W1382).

Scratch worktrees (`mikemol-scratch`, W1378) pile up: this repository's own `git worktree list`
holds seventeen, fourteen of them `prunable` (their directory is gone) and the rest unaccounted for.
Removing the wrong one loses work, so the first step only CLASSIFIES, and removes, saves and prunes
nothing:

    held             a process has this directory as its working directory (never touched)
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

The two reads over time that tell a live worktree from a just-created one, the `refs/stash-reap`
save and the removal by exact path are later steps (W1382).

CONSUMED BY: the `mikemol-worktree-reap` console script.
"""

import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from mikemol.hooks.commit_kata import run_git_in

HELD = "held"
DIRTY = "dirty"
UNMERGED = "unmerged"
GONE = "gone"
CLEAN = "clean-equivalent"
EXIT_OK = 0
EXIT_USAGE = 2
BRANCH_PREFIX = "refs/heads/"
USAGE = "usage: mikemol-worktree-reap REPO   (read-only: classifies, changes nothing)\n"
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


def classify(wt: Worktree, cherry: str | None, status: str | None, *, held: bool) -> str:
    """Classify one worktree from what was read about it; None means the read failed.

    Returns:
        `HELD`, `UNMERGED`, `GONE`, `DIRTY` or `CLEAN`, in that order of precedence.

    """
    if held:
        return HELD
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


def report(root: Path, upstream: str = "main") -> list[str]:
    """Classify every scratch worktree of the repository at `root`.

    Returns:
        one `CLASS<TAB>PATH<TAB>BRANCH` line per worktree other than the main one.

    """
    listed = parse_worktrees(_out(root, ["worktree", "list", "--porcelain"]) or "")[1:]
    lines: list[str] = []
    for wt in listed:
        cherry = _out(root, ["cherry", upstream, wt.branch]) if wt.branch else ""
        status = "" if wt.prunable else _out(Path(wt.path), ["status", "--porcelain"])
        kind = classify(wt, cherry, status, held=bool(holders(wt.path)))
        lines.append(f"{kind}\t{wt.path}\t{wt.branch or '(detached)'}")
    return lines


def main(argv: Sequence[str] | None = None) -> int:
    """Print the classification of a repository's scratch worktrees.

    Returns:
        `EXIT_OK` with the lines printed, `EXIT_USAGE` when the one argument (REPO) is missing.

    """
    args = sys.argv[1:] if argv is None else list(argv)
    if len(args) != 1:
        sys.stderr.write(USAGE)
        return EXIT_USAGE
    sys.stdout.writelines(f"{line}\n" for line in report(Path(args[0])))
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
