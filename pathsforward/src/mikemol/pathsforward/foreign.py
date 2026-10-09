# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Resolve a foreign `repo:W<n>` blocker by READING that repo's queue, never writing it (W538).

⚑ A DORMANT REPO'S SESSION NEVER RUNS (luthen-observability, 2026-10-04): el-openglo:W154 stayed
blocked on luthen-observability:W328, done since 2026-10-03, because only the owner's own session
could prune it. Here the BLOCKED repo prunes its own card, from a read of the peer's state file:
a symbol that is done in the peer's waypoints, or sits in its residue, has landed.

⚑ READ-ONLY, AND LOCK-FREE ON THE PEER. The peer file goes through `store.load` (never `save`,
never `exclusive`): `save` writes atomically by replace, so a read sees the old or the new file.
A repo name carrying a path separator or `..` would escape the root and is refused by name; a
link in the path is data to refuse, never to read through.

⚑ NOTHING IS SKIPPED IN SILENCE. A foreign blocker that stays is returned with the reason it
stays, one line each, so the caller prints it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.pathsforward import store
from mikemol.pathsforward.model import strlist, symbol_number, text

if TYPE_CHECKING:
    from mikemol.pathsforward.model import State

QUEUE = (".claude", "paths-forward.json")
_SEP = ":"
_ESCAPES = ("\\", "..")
_DONE = "done"


@dataclass
class Pruned:
    """What one foreign prune did: the cards freed, and a line for each blocker kept."""

    freed: list[str] = field(default_factory=list[str])
    kept: list[str] = field(default_factory=list[str])


def default_root() -> Path:
    """Name the directory that holds the repos, from the user's home at runtime.

    Returns:
        `~/github`.

    """
    return Path.home() / "github"


def split(ref: str) -> tuple[str, str] | None:
    """Split `repo:W<n>` into its two halves.

    Returns:
        (repo, symbol), or None when `ref` is not shaped like a foreign symbol.

    """
    repo, sep, sym = ref.partition(_SEP)
    if not sep or not repo or symbol_number(sym) is None:
        return None
    return repo, sym


def _escapes(repo: str) -> bool:
    """Say whether a workstream name would leave the root.

    ⚑ A NAME MAY NOW BE A PATH (`parent/child`, mtools:W882, nemik:W224), so a separator is no
    longer the refusal; each SEGMENT is judged instead. An empty one (a leading, trailing or
    doubled `/`), one that starts with a dot (`.`, `..`, a hidden directory), one with a
    backslash, or one containing `..` is a way out of the root, or not a name.

    Returns:
        True when any segment is empty, dot-led, holds a backslash, or holds `..`.

    """
    return any(
        not segment or segment.startswith(".") or any(bad in segment for bad in _ESCAPES)
        for segment in repo.split("/")
    )


def _link_in(root: Path, repo: str) -> bool:
    """Say whether any directory from the root down to the workstream is a link.

    Returns:
        True when a link lies on the way, whose target would be read through.

    """
    parts = repo.split("/")
    return any(root.joinpath(*parts[: i + 1]).is_symlink() for i in range(len(parts)))


def peer(root: Path, repo: str) -> tuple[State | None, Path, str]:
    """Read a peer's queue, or say why it cannot be.

    Returns:
        (state, path, "") on success; (None, path, why) when refused or unreadable.

    """
    repo_dir = root / repo
    path = repo_dir.joinpath(*QUEUE)
    if _escapes(repo):
        return None, path, f"repo name {repo!r} has an empty, dot-led or escaping segment; refused"
    if _link_in(root, repo) or path.parent.is_symlink() or path.is_symlink():
        return None, path, f"{path} is a link; refused as data"
    if not path.is_file():
        return None, path, f"{repo} has no queue file at {path}"
    try:
        return store.load(path), path, ""
    except store.UnreadableStateError as exc:
        return None, path, f"queue file unreadable: {exc}"


def landed(root: Path, repo: str, sym: str) -> tuple[bool, str]:
    """Judge one foreign symbol against the owner's queue, read-only.

    Returns:
        (True, why) when it is done or in residue; (False, why-kept) otherwise.

    """
    theirs, path, why = peer(root, repo)
    if theirs is None:
        return False, why
    for w in theirs.waypoints:
        if text(w, "symbol") == sym:
            status = text(w, "status")
            return status == _DONE, f"{sym} is {status} in {path}"
    if any(text(r, "symbol") == sym for r in theirs.residue):
        return True, f"{sym} is residue in {path}"
    return False, f"{sym} is not in {path}"


def prune_foreign(state: State, root: Path) -> Pruned:
    """Drop foreign blockers that have landed, by the same rule as `ops.prune_done`.

    A list that empties returns the card to ready; one that only shrinks restarts its ticks.
    Every foreign blocker that stays is named in `kept` with its reason.

    Returns:
        the freed symbols and the kept-blocker lines, in queue order.

    """
    out = Pruned()
    seen: dict[str, tuple[bool, str]] = {}
    for w in state.waypoints:
        on = strlist(w, "blocked_on")
        if text(w, "status") != "blocked":
            continue
        kept: list[str] = []
        for b in on:
            parts = split(b)
            if parts is None:
                kept.append(b)
                continue
            if b not in seen:
                seen[b] = landed(root, *parts)
            ok, why = seen[b]
            if not ok:
                kept.append(b)
                out.kept.append(f"KEPT {text(w, 'symbol')} blocked on {b}: {why}")
        if kept == on:
            continue
        w["blocked_on"], w["ticks_blocked"] = kept, 0
        if not kept:
            w["status"], w["blocked_kind"] = "ready", None
            out.freed.append(text(w, "symbol"))
    return out
