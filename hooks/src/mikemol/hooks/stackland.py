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
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from mikemol.hooks.isolated import Done, EnvRunner, add_argv_list
from mikemol.hooks.runproc import Result
from mikemol.hooks.stacksnap import QUEUE_FILES, Frozen, apply_argv, live_paths

_WAYPOINT = re.compile(r"^Waypoint: (W\d+)\b|\A(W\d+)\b", re.MULTILINE)
# ⚑ AN ADMISSION IS AN EXACT LINE (W2301): `Admission: <row id>` and nothing else on the line, so a
# body cannot forge one inside prose.
_ADMISSION = re.compile(r"^Admission: (\S+)$", re.MULTILINE)
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


def admissions(message: str) -> list[str]:
    """List the admission rows a message names, one per exact `Admission: <row id>` line.

    Returns:
        the row ids, in message order; a line with anything else on it names none.

    """
    return [found.group(1) for found in _ADMISSION.finditer(message)]


def stamped(message: str, tree: str, tip: str, *, is_tip: bool) -> str:
    """Add the gate trailer a commit of a stack carries.

    Returns:
        the message with `Gated-Tree: <tree>` when it is the tip, else `Gated-by: <tip>`.

    """
    trailer = f"Gated-Tree: {tree}" if is_tip else f"Gated-by: {tip}"
    return f"{message.rstrip()}\n{trailer}\n"


def _place(
    root: Path,
    entry: Entry,
    run: EnvRunner,
    scope: Mapping[str, str],
    tracked_tree: Mapping[str, str],
) -> Done | None:
    # Put one entry's files into the private index; the first git step that fails, else None.
    #
    # ⚑ FROZEN BYTES GO IN BY CACHE INFO, QUEUE FILES ARE READ FROM THE TREE NOW (W1464): see
    # `stacksnap.live_paths`. An entry never frozen reads all of its paths from the tree.
    if entry.files is None:
        steps = [(argv, tracked_tree) for argv in add_argv_list(root, entry.paths)]
    else:
        steps = [(argv, scope) for argv in apply_argv(entry.files)]
        steps += [(argv, tracked_tree) for argv in add_argv_list(root, live_paths(entry.paths))]
    for argv, env in steps:
        added = run(argv, env, root)
        if _stopped(added):
            return added
    return None


def _spent(root: Path, run: EnvRunner, scope: Mapping[str, str], head: str, row: str) -> str | None:
    # Why the row cannot be admitted: spent in the history reachable from `head`, or the history
    # cannot be read in full. ⚑ A HISTORY THAT CANNOT BE READ IS NEVER READ AS "NOT SPENT": a failed
    # `git log`, or a shallow clone that has cut the commit off, would admit a spent row.
    shallow = run(["rev-parse", "--is-shallow-repository"], scope, root)
    if shallow.returncode != 0 or shallow.stdout.strip() != "false":
        return f"the history is shallow or unreadable, so the admission {row} cannot be checked"
    pattern = f"^Admission: {re.escape(row)}$"
    argv = ["log", head, "--max-count=1", "--format=%H", "--extended-regexp", f"--grep={pattern}"]
    found = run(argv, scope, root)
    if found.returncode != 0:
        return f"the history could not be read to check the admission {row}"
    return f"the admission {row} is already spent" if found.stdout.strip() else None


@dataclass
class _Chain:
    """The git environment and the position of the chain being built."""

    root: Path
    run: EnvRunner
    scope: Mapping[str, str]
    tracked_tree: Mapping[str, str]
    head: str
    parent: str
    parent_tree: str
    tip: str
    last: int
    taken: set[str] = field(default_factory=set)


def _replay(chain: _Chain, entry: Entry, tree: str) -> str | None:
    # ⚑ ONLY AN ADMITTED ENTRY IS REFUSED FOR CHANGING NOTHING (the host's narrowing of v5, via
    # github-14): an honest follower that carries the same blob as a stack ahead, or a stack that
    # re-names an earlier entry's path, has an empty entry and must still land. An admitted entry
    # that carries a non-queue file and changes no non-queue file is a replay: its change is
    # already there. ⚑ THE QUEUE FILES ARE LEFT OUT OF THE COMPARISON, because `queuecarry` adds a
    # changed queue file to a stack's last entry, which would otherwise make a replay look new.
    if not admissions(entry.message) or all(p in QUEUE_FILES for p in entry.paths):
        return None
    diff = chain.run(
        ["diff-tree", "-r", "-z", "--name-only", "--no-renames", chain.parent_tree, tree],
        chain.scope,
        chain.root,
    )
    if diff.returncode != 0:
        return "the entry could not be compared with its parent, so it is not admitted"
    if any(name not in QUEUE_FILES for name in diff.stdout.split("\0") if name):
        return None
    return "this entry changes nothing: its change is already there"


def _start(root: Path, entries: Sequence[Entry], run: EnvRunner, head: str) -> _Chain | Done:
    # The private index read from `head`, or the first git step that failed.
    gitdir = run(["rev-parse", "--absolute-git-dir"], {}, root)
    if _stopped(gitdir):
        return gitdir
    git_dir = Path(gitdir.stdout.strip())
    index = git_dir / "mtools" / "stack.index"
    index.parent.mkdir(parents=True, exist_ok=True)
    index.unlink(missing_ok=True)
    scope = {"GIT_DIR": str(git_dir), "GIT_INDEX_FILE": str(index)}
    read = run(["read-tree", head], scope, root)
    if _stopped(read):
        return read
    parent_tree = run(["rev-parse", f"{head}^{{tree}}"], scope, root)
    if _stopped(parent_tree):
        return parent_tree
    tip = tip_name(entries[-1].message) if entries else NO_TIP
    tracked = {**scope, "GIT_WORK_TREE": str(root)}
    return _Chain(
        root, run, scope, tracked, head, head, parent_tree.stdout.strip(), tip, len(entries) - 1
    )


def _vet(chain: _Chain, entry: Entry) -> Done | None:
    # The admission rows the entry names, each spent never and at most once in this chain.
    for row in admissions(entry.message):
        if row in chain.taken:
            return Result(1, "", f"the admission {row} is already spent")
        why = _spent(chain.root, chain.run, chain.scope, chain.head, row)
        if why is not None:
            return Result(1, "", why)
        chain.taken.add(row)
    return None


def _link(chain: _Chain, stack: Stack, place: int, entry: Entry) -> Done | None:
    # Add one entry's commit to the chain; the first step that failed, else None.
    refused = _vet(chain, entry) or _place(
        chain.root, entry, chain.run, chain.scope, chain.tracked_tree
    )
    if refused is not None:
        return refused
    tree = chain.run(["write-tree"], chain.scope, chain.root)
    if _stopped(tree):
        return tree
    name = tree.stdout.strip()
    replay = _replay(chain, entry, name)
    if replay is not None:
        return Result(1, "", replay)
    message = stamped(entry.message, name, chain.tip, is_tip=place == chain.last)
    made = chain.run(
        ["commit-tree", name, "-p", chain.parent, "-m", message], chain.scope, chain.root
    )
    if _stopped(made):
        return made
    chain.parent, chain.parent_tree = made.stdout.strip(), name
    stack.trees.append(name)
    stack.commits.append(chain.parent)
    return None


def build(root: Path, entries: Sequence[Entry], run: EnvRunner, head: str) -> Stack:
    """Create one commit per entry on top of `head`, running no hook and moving no ref.

    ⚑ AN ADMISSION IS SPENT ONCE, HERE, BEFORE `commit-tree` (W2301): an entry whose message names
    `Admission: <row>` fails the chain when a commit reachable from `head` already carries that line
    or an earlier entry of this chain does, so two stacks in one train cannot both be admitted. A
    history that is shallow or cannot be read fails it too, never reads as unspent. ONLY AN ADMITTED
    entry that carries a non-queue file and changes nothing fails for that (its change is already
    there); an honest follower, or a stack re-naming an earlier path, still lands.

    Returns:
        the chain; `failed` holds the first git step that did not succeed, and `commits` the ones
        built before it.

    """
    stack = Stack()
    chain = _start(root, entries, run, head)
    if not isinstance(chain, _Chain):
        stack.failed = chain
        return stack
    for place, entry in enumerate(entries):
        failed = _link(chain, stack, place, entry)
        if failed is not None:
            stack.failed = failed
            break
    return stack
