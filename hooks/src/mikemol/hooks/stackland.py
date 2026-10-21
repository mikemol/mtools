# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Build a stack of commits without running a hook, so one gate can judge the tip (mtools:W1160).

`git commit` runs the repository's hooks, and the gate is a hook, so N commits cost N gate runs.
`git commit-tree` runs none. This builds the chain with plumbing and moves nothing: no ref, no real
index. The caller gates the tip once (W1161) and moves HEAD only if it passed.

    1. a PRIVATE index (`<git dir>/mtools/stack.index`): `read-tree <head>`.
    2. for each entry, in order: `add` its named paths into that same index, `write-tree`, then
       `commit-tree <tree> -p <parent> -m <message>`. Each commit therefore holds only its own paths
       on top of the one before, so `git blame` and `git show` stay per card.

⚑ THE INDEX ACCUMULATES: entry k's tree is entry k-1's tree plus entry k's paths, never the working
tree's other edits, so a peer's unstaged file cannot ride into any commit (the rule `isolated`
already keeps for one commit).

⚑ THE TIP NAMES THE TREE THE GATE JUDGED, THE OTHERS NAME THE TIP (W1745, nemik:W703): a stack gates
only its tip, so the last commit carries `Gated-Tree: <its tree>` (as a single commit does, W1666)
and every earlier one carries `Gated-by: <the tip's waypoint>`, the commit whose gate covered it.
The tip's tree is known when its commit is made and the tip's waypoint is known from the start, so
one pass still suffices.

⚑ A FAILURE IS RETURNED, NOT RAISED, WITH THE COMMITS BUILT BEFORE IT: they are unreachable objects
and harmless, and the caller reports that nothing landed.

See `.claude/design/stack-land.md`. CONSUMED BY: the stack mode of `mikemol-commit` (W1161).
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from mikemol.hooks.isolated import Done, EnvRunner, add_argv_list
from mikemol.hooks.stacksnap import Frozen, apply_argv

_WAYPOINT = re.compile(r"^Waypoint: (W\d+)\b|\A(W\d+)\b", re.MULTILINE)
NO_TIP = "-"


@dataclass(frozen=True)
class Entry:
    """One commit of the stack: its full message (trailer included) and the paths it carries.

    `files`, when given, are the bytes frozen at submit (W1447): they are placed into the index
    instead of re-reading `paths` from the working tree, which a queued peer may have changed.
    """

    message: str
    paths: tuple[str, ...]
    files: tuple[Frozen, ...] | None = None


@dataclass
class Stack:
    """The chain built so far, oldest first, and the git step that stopped it (None when whole)."""

    commits: list[str] = field(default_factory=list)
    trees: list[str] = field(default_factory=list)
    failed: Done | None = None


def _stopped(done: Done) -> bool:
    return done.returncode != 0


def tip_name(message: str) -> str:
    """Name the waypoint a stack's tip commit belongs to.

    Returns:
        the message's `Waypoint:` trailer, else its leading `W<n>`, or `-` when it has neither.

    """
    found = _WAYPOINT.search(message)
    return (found.group(1) or found.group(2)) if found else NO_TIP


def stamped(message: str, tree: str, tip: str, *, is_tip: bool) -> str:
    """Add the gate trailer a commit of a stack carries.

    Returns:
        the message with `Gated-Tree: <tree>` when it is the tip, else `Gated-by: <tip>`.

    """
    trailer = f"Gated-Tree: {tree}" if is_tip else f"Gated-by: {tip}"
    return f"{message.rstrip()}\n{trailer}\n"


def build(root: Path, entries: Sequence[Entry], run: EnvRunner, head: str) -> Stack:
    """Create one commit per entry on top of `head`, running no hook and moving no ref.

    Returns:
        the chain; `failed` holds the first git step that did not succeed, and `commits` the ones
        built before it.

    """
    stack = Stack()
    gitdir = run(["rev-parse", "--absolute-git-dir"], {}, root)
    if _stopped(gitdir):
        stack.failed = gitdir
        return stack
    git_dir = Path(gitdir.stdout.strip())
    index = git_dir / "mtools" / "stack.index"
    index.parent.mkdir(parents=True, exist_ok=True)
    index.unlink(missing_ok=True)
    scope = {"GIT_DIR": str(git_dir), "GIT_INDEX_FILE": str(index)}
    tracked_tree = {**scope, "GIT_WORK_TREE": str(root)}
    read = run(["read-tree", head], scope, root)
    if _stopped(read):
        stack.failed = read
        return stack
    parent = head
    tip = tip_name(entries[-1].message) if entries else NO_TIP
    for place, entry in enumerate(entries):
        frozen = entry.files is not None
        plan = (
            apply_argv(entry.files) if entry.files is not None else add_argv_list(root, entry.paths)
        )
        for argv in plan:
            added = run(argv, scope if frozen else tracked_tree, root)
            if _stopped(added):
                stack.failed = added
                return stack
        tree = run(["write-tree"], scope, root)
        if _stopped(tree):
            stack.failed = tree
            return stack
        message = stamped(entry.message, tree.stdout.strip(), tip, is_tip=place == len(entries) - 1)
        made = run(["commit-tree", tree.stdout.strip(), "-p", parent, "-m", message], scope, root)
        if _stopped(made):
            stack.failed = made
            return stack
        parent = made.stdout.strip()
        stack.trees.append(tree.stdout.strip())
        stack.commits.append(parent)
    return stack
