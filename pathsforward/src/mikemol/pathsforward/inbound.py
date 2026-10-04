# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The inbound census: which peer cards wait on THIS repo, and which of them nobody has claimed.

⚑ MIRRORS nemik's `inbound(g)` (src/nemik/blocks.py, the function behind `nemik-inbound`) and the
two adapter rules it reads (src/nemik/adapter.py: `resolve_blocker`, `queue_graph`), restated over
queue files instead of an RDF graph. nemik reads queues and pathsforward writes them, so the
dependency may not run the other way: nothing here imports or runs nemik, and the agreement is a
measured acceptance (the UNCLAIMED sets are diffed against `nemik-inbound`), not a shared import.

⚑ THE RULE, EXACTLY AS NEMIK HAS IT (read from its source 2026-10-04, not guessed):
  - A peer card COUNTS when its status is anything but `done`. A ready card still carrying a
    `blocked_on` counts. A card in the peer's residue never counts (it has no blockers).
  - Each `blocked_on` entry is resolved against the set of repos that have a queue: a bare `W<n>`
    is the peer's own card and is skipped; `<repo>:W<n>` names a card of that repo; otherwise the
    first word, less a trailing colon, comma or possessive, is a repo name or a `<repo>-<2 hex>`
    session name and names the repo as a whole. Anything else (the operator) is not a peer block.
  - A named `<this-repo>:W<n>` counts only when `W<n>` exists here as a waypoint or as residue; a
    name that points at nothing is skipped by nemik and so is skipped here.
  - A row is CLAIMED by every local waypoint, in any status, whose `enables` cites the peer card
    as `<peer>:W<n>` or whose `caused_by` is that same reference; and a named target is itself a
    claim. UNCLAIMED is the empty set of claims. So a block on the repo as a whole is unclaimed
    until a local card `enables` or is `caused_by` the peer card.
  - One row per (peer card, target): two entries naming the same target collapse into one.

⚑ READ-ONLY, REUSING `foreign.peer` (store.load only; a repo name holding a separator or `..` and
a link at the repo directory or the queue are refused as data). A peer that cannot be read is
returned by name with the reason, never dropped. The repo name is the state file's directory
name (`<repo>/.claude/paths-forward.json`), as nemik derives it from the directory listing.
Dot-named directories (git worktrees) are not repos, as in nemik's `workstream_files`.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from mikemol.pathsforward import foreign
from mikemol.pathsforward.model import foreign_symbol, strlist, symbol_number, text
from mikemol.pathsforward.payload import PROG

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from mikemol.pathsforward.model import State

_DONE = "done"
_QUEUE_GLOB = "*/.claude/paths-forward.json"
_SESSION = re.compile(r"^(?P<repo>.+)-[0-9a-f]{2}$")
_TRAILING = re.compile("(['" + chr(0x2019) + "]s|[:,])$")
TITLE_CLIP = 80


@dataclass(frozen=True)
class Ask:
    """One peer card waiting on this repo: who, which card, on what, and who claims it.

    `named` is the local symbol the peer cited (`W153`), or empty when it waits on the repo.
    """

    peer: str
    symbol: str
    title: str
    named: str
    claimed_by: tuple[str, ...] = ()


@dataclass(frozen=True)
class Census:
    """What a scan found: every ask, and a line for each peer queue that could not be read."""

    asks: tuple[Ask, ...]
    unreadable: tuple[str, ...]


def repo_name(state_path: Path) -> str:
    """Name the repo a state file belongs to: the directory two levels above it.

    Returns:
        the directory name of `<repo>/.claude/paths-forward.json`.

    """
    return state_path.parent.parent.name


def known_repos(root: Path) -> list[str]:
    """List the repos under `root` that carry a queue, dot-named directories left out.

    Returns:
        the repo names, sorted.

    """
    names = (path.parents[1].name for path in root.glob(_QUEUE_GLOB))
    return sorted(name for name in names if not name.startswith("."))


def ref(peer: str, symbol: str) -> str:
    """Spell a peer card as the citable `<repo>:W<n>`.

    Returns:
        the reference.

    """
    return f"{peer}:{symbol}"


def resolve(who: str, known: frozenset[str]) -> tuple[str, str] | None:
    """Read one `blocked_on` entry as the repo it waits on and the card it names there.

    Returns:
        (repo, symbol) for `repo:W<n>`, (repo, "") for a repo or session name, else None.

    """
    entry = who.strip()
    if symbol_number(entry) is not None:
        return None
    named = foreign_symbol(entry)
    if named and named[0] in known:
        return named[0], f"W{named[1]}"
    words = entry.split()
    head = _TRAILING.sub("", words[0]) if words else ""
    session = _SESSION.match(head)
    for candidate in (head, str(session.group("repo")) if session else ""):
        if candidate in known:
            return candidate, ""
    return None


def asks_of(peer: str, state: State, me: str, known: frozenset[str]) -> list[Ask]:
    """List the open cards of one peer queue that wait on `me`, claims not yet looked up.

    Returns:
        one Ask per (card, target), in queue order.

    """
    out: list[Ask] = []
    seen: set[tuple[str, str]] = set()
    for w in state.waypoints:
        if text(w, "status") == _DONE:
            continue
        for who in strlist(w, "blocked_on"):
            target = resolve(who, known)
            if target is None or target[0] != me or (text(w, "symbol"), target[1]) in seen:
                continue
            seen.add((text(w, "symbol"), target[1]))
            out.append(Ask(peer, text(w, "symbol"), text(w, "title"), target[1]))
    return out


def claims(local: State, me: str, ask: Ask) -> tuple[str, ...] | None:
    """Find the local cards that claim an ask, and the named target when it exists.

    Returns:
        the claiming references, sorted; None when the ask names a local card that does not
        exist, which nemik leaves out of its census.

    """
    wanted = (ask.peer, symbol_number(ask.symbol))
    found = {
        ref(me, text(w, "symbol"))
        for w in local.waypoints
        if wanted in {foreign_symbol(c) for c in (*strlist(w, "enables"), text(w, "caused_by"))}
    }
    if ask.named:
        live = {text(w, "symbol") for w in (*local.waypoints, *local.residue)}
        if ask.named not in live:
            return None
        found.add(ref(me, ask.named))
    return tuple(sorted(found))


def census(root: Path, me: str, local: State, repos: Sequence[str] | None = None) -> Census:
    """Scan the sibling queues under `root` for cards waiting on `me`.

    `repos` replaces the directory listing (a test, or a caller that already listed it).

    Returns:
        every ask with its claims, sorted by peer and card, and the unreadable peers.

    """
    names = known_repos(root) if repos is None else list(repos)
    known = frozenset([*names, me])
    found: list[Ask] = []
    unreadable: list[str] = []
    for repo in sorted(names):
        if repo == me:
            continue
        theirs, _, why = foreign.peer(root, repo)
        if theirs is None:
            unreadable.append(f"{repo}: {why}")
            continue
        for ask in asks_of(repo, theirs, me, known):
            claimed = claims(local, me, ask)
            if claimed is not None:
                found.append(replace(ask, claimed_by=claimed))
    found.sort(key=lambda a: (a.peer, symbol_number(a.symbol) or 0, a.named))
    return Census(tuple(found), tuple(unreadable))


def unclaimed(found: Census) -> list[Ask]:
    """Pick the asks nobody has claimed.

    Returns:
        the asks with no claiming reference.

    """
    return [ask for ask in found.asks if not ask.claimed_by]


def clip(title: str) -> str:
    """Shorten a title to one greppable line.

    Returns:
        the title's first line, cut to TITLE_CLIP characters.

    """
    lines = title.splitlines()
    return lines[0][:TITLE_CLIP] if lines else ""


def claim_command(state_path: Path, ask: Ask) -> str:
    """Spell the command that claims an ask, with a title to edit.

    Returns:
        the `--add` invocation citing the peer card in both `--enables` and `--caused-by`.

    """
    cite = ref(ask.peer, ask.symbol)
    title = f"Answer {cite}: {clip(ask.title)}"
    return (
        f"{PROG} --state {shlex.quote(str(state_path))} --add {shlex.quote(title)} "
        f"--enables {cite} --caused-by {cite}"
    )


def ask_line(state_path: Path, ask: Ask) -> str:
    """Render one ask for `--inbound`: UNCLAIMED with its claim command, or CLAIMED with by whom.

    Returns:
        a line starting with the token UNCLAIMED or CLAIMED, then the peer card.

    """
    cite = ref(ask.peer, ask.symbol)
    if ask.claimed_by:
        return f"CLAIMED {cite} by {','.join(ask.claimed_by)} :: {clip(ask.title)}"
    return f"UNCLAIMED {cite} :: {clip(ask.title)} :: {claim_command(state_path, ask)}"


def payload_lines(found: Census) -> tuple[str, ...]:
    """Render the payload's inbound section: the unclaimed asks, then each unreadable peer.

    Returns:
        the lines, a heading first; empty when there is nothing to say, so a quiet repo's
        payload is unchanged.

    """
    rows = unclaimed(found)
    if not rows and not found.unreadable:
        return ()
    head = (
        f"inbound: {len(rows)} peer ask(s) wait on this repo with no claiming waypoint "
        f"({PROG} --state <state_path> --inbound prints each claim command):"
    )
    return (
        head,
        *(f"  {ref(a.peer, a.symbol)} :: {clip(a.title)}" for a in rows),
        *(f"  unreadable: {entry}" for entry in found.unreadable),
    )
