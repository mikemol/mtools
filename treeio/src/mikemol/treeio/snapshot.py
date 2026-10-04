# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Take a recoverable snapshot before a tool rewrites tree files, and say how to get back.

Ported from paperkit's `tools/edit_snapshot.py`. THE FAILURE MODE WAS NOT HYPOTHETICAL: an ad-hoc
dead-import regex, written by hand instead of routed through the import module, matched an import
statement plus its indented continuation lines, and where an import sat above a PARAMETERIZED module
header it swallowed the header and its whole parameter list. Thirty-three files were damaged and
one was reduced from forty-one lines to three. The damage was found by the build, not by the tool.
The discipline had been recorded as PROSE: "the decision was made and the damage written before any
verification could run", and "a stash, not a revert, is the way back; this tool never touches git".
This module is that prose mechanized: the tool takes the snapshot itself, so recovery does not
depend on the operator having thought of it first.

WHY NOT `git stash`. A stash is worktree-global and pops as a unit. A pipeline that runs its
per-file passes in parallel would interleave pushes and pop each other's state, turning one tool's
rollback into another tool's corruption. `git stash create` instead builds a commit OBJECT and
prints its sha without touching the worktree or the stash stack, so every run gets its own
immutable snapshot identified by its sha, concurrent runs cannot interfere, nothing is staged,
nothing is reverted, and recovery is an explicit per-path `git checkout <sha> -- <paths>` the
operator runs deliberately, never something this package does on its own.

THIS PACKAGE NEVER RESTORES ON ITS OWN. It records how to. An automatic rollback would be a
revert-in-disguise, and reverting is the thing that costs a day's work.

`git stash create` CANNOT capture untracked files: it ignores the include-untracked flag, which
only works on the stack-pushing form. MEASURED: a conversion damaged six untracked pipeline tools
and the recovery checkout failed with "did not match any file(s) known to git". The tools most
likely to be damaged are exactly the ones not in git, so a tracked-only snapshot protects the wrong
half. Anything untracked is copied into the snapshot directory first; recovery for those is a file
copy.
"""

from __future__ import annotations

import shutil
import sys
from typing import TYPE_CHECKING

from mikemol.treeio.context import SNAPSHOT_STATE, SnapshotState
from mikemol.treeio.gitrun import git, is_tracked
from mikemol.treeio.layout import Layout, layout

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence
    from pathlib import Path

_SHOWN = 5  # how many copied untracked files the report names before it summarizes
_JOURNAL_PATHS = 40  # how many intended paths one journal row records
_HEADER = (
    "# sha\tlabel\tn_paths\tpaths\n"
    "# restore:  git checkout <sha> -- <path>...\n"
    "# list:     git show --stat <sha>\n"
)


def _say(text: str) -> None:
    """Write one line to stdout."""
    sys.stdout.write(text + "\n")


def copy_untracked(here: Layout, paths: Iterable[str | Path]) -> list[tuple[str, Path]]:
    """Copy each untracked path into the snapshot directory.

    A stash commit holds only TRACKED content, so without this the untracked tools, which include
    every destructive one, have no recovery point at all. Best-effort: a copy failure must not
    stop the work.

    SKIP ONLY WHAT THIS INVOCATION ALREADY SAVED. The store is keyed by path and holds the
    pre-write copy; re-copying after the tool has written would overwrite the good copy with the
    damaged one, the recovery point destroying itself. So "already copied" is a genuine skip and
    "not yet seen" is a copy, which is where the per-invocation copied set earns its keep.

    Returns:
        The repository-relative path and the saved copy, for each file copied now.

    """
    saved: list[tuple[str, Path]] = []
    state = SNAPSHOT_STATE.get()
    already = state.copied if state is not None else None
    for path in paths:
        rel = here.rel(path)
        full = here.root / rel
        if not full.is_file() or is_tracked(here.root, rel):
            continue
        if already is not None and rel in already:
            continue
        dest = here.snapdir / rel
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(full, dest)
        except OSError:
            continue
        saved.append((rel, dest))
        if already is not None:
            already.add(rel)
    return saved


def record(here: Layout, sha: str, label: str, paths: Sequence[str | Path]) -> None:
    """Append one snapshot to the journal. Best-effort: it never breaks the caller."""
    new = not here.journal.exists()
    rel = [here.rel(p) for p in paths]
    row = f"{sha}\t{label}\t{len(rel)}\t{','.join(rel[:_JOURNAL_PATHS])}\n"
    try:
        here.journal.parent.mkdir(parents=True, exist_ok=True)
        with here.journal.open("a", encoding="utf-8") as fh:
            if new:
                fh.write(_HEADER)
            fh.write(row)
    except OSError:
        return


def announce(sha: str | None, label: str, out: Callable[[str], None] = _say) -> None:
    """Tell the operator how to recover. Called once, at the start of a run."""
    if sha is None:
        out(f"⚠ {label}: NO SNAPSHOT (not a git worktree?) — edits are unrecoverable")
        return
    out(f"snapshot {sha[:12]} [{label}] — recover any file with:")
    out(f"    git checkout {sha[:12]} -- <path>")


def _worktree_sha(here: Layout) -> str:
    """Name the commit that stands for the worktree.

    `git stash create` prints nothing when the worktree is clean: there is nothing to recover TO,
    so HEAD is the honest snapshot point.

    Returns:
        The stash commit, else HEAD, else an empty string when git has neither.

    """
    made = git(here.root, "stash", "create")
    sha = made.stdout.strip()
    if made.returncode == 0 and sha:
        return sha
    head = git(here.root, "rev-parse", "HEAD")
    return head.stdout.strip() if head.returncode == 0 else ""


def _report_untracked(here: Layout, untracked: list[tuple[str, Path]]) -> None:
    """Say which untracked files were copied aside, naming the first few."""
    if not untracked:
        return
    snapdir = here.rel(here.snapdir)
    _say(f"  ⚑ {len(untracked)} UNTRACKED file(s) copied to {snapdir}/ (git cannot hold them):")
    for rel, dest in untracked[:_SHOWN]:
        _say(f"      cp {here.rel(dest)} {rel}")
    if len(untracked) > _SHOWN:
        _say(f"      … and {len(untracked) - _SHOWN} more (see --list)")


def snapshot(
    label: str, paths: Sequence[str | Path] = (), root: str | Path | None = None
) -> str | None:
    """Snapshot the worktree before a tool's first write.

    `label` names the tool and target. `paths` is advisory: it is recorded in the journal so a
    reader knows which files the run intended to touch. The snapshot itself is whole-worktree,
    because a tool that damages a file it did not intend to touch is exactly the case that needs
    recovering. It never raises if this is not a git worktree or git fails: a snapshot is a safety
    net, and a missing net must not stop the work. Callers MUST NOT treat None as a reason to skip
    the edit, and must not treat a sha as permission to skip verification.

    The sha is pinned with a ref, because an unreferenced stash commit is loose and a garbage
    collection can take it: the whole point is that it is still there tomorrow.

    ESTABLISH THE PER-INVOCATION RECORD IF NOTHING ABOVE DID, so a tool that calls the snapshot or
    the guard directly still accumulates its copied set instead of re-copying, and still cannot
    overwrite a good pre-write copy with a post-write one.

    Returns:
        The sha, or None when there is no snapshot to be had.

    """
    here = layout(root)
    if SNAPSHOT_STATE.get() is None:
        SNAPSHOT_STATE.set(SnapshotState(sha=None, label=label))
    untracked = copy_untracked(here, paths)
    sha = _worktree_sha(here)
    if not sha:
        return None
    git(here.root, "update-ref", f"refs/edit-snapshots/{sha[:12]}", sha)
    record(here, sha, label, paths)
    _report_untracked(here, untracked)
    return sha
