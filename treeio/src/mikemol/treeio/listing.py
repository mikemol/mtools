# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""List the paths matching a glob at a source, REFUSING a pattern that means two things.

Ported from paperkit's `tools/vfs.py`. For a working tree this wraps `glob`; for a revision it
walks the git tree and applies `fnmatch`. The two matchers disagree in BOTH directions and neither
listing contains the other:

    pattern                working tree        at a revision (fnmatch)
    d/**/*.ext             EXACT               MISSES every depth-0 member
    d/*.ext                depth 0 only        EVERY depth (a star crosses a slash)
    d/**                   EXACT               EXACT: the agreeing form

The defect was never that one branch is wrong. It was that ONE CALLER'S PATTERN IS EXACT AGAINST
ONE SOURCE AND LOSSY AGAINST THE OTHER, with nothing that could tell them apart: a silent six-module
drop reads as a smaller repo, not as a broken query. So the fix is not to pick a winner. Making the
branches agree would still leave `d/**/*.ext` dropping depth 0 on BOTH, which is agreement without
correctness. Instead the ambiguity is REFUSED, and the refusal names the depth-agnostic form that
means one thing.

The refusal is source-independent on purpose: it fires on the working tree too, where the pattern
happens to be exact. A check that only fired on the lossy branch would let the trap be armed by a
caller who only ever tested against disk, which is exactly how the six-module drop shipped.

Measured against a working tree, `glob` DOES let a `**/` match zero segments, so `d/**/*.ext` finds
depth 0 on disk while `fnmatch` cannot. The refusal is right; the explanatory clause in its message
saying a `**/` cannot match zero segments "in either matcher" is not, and is kept as paperkit wrote
it because it is another item's live text.
"""

from __future__ import annotations

import fnmatch
import glob
from typing import TYPE_CHECKING

import pygit2

from mikemol.treeio.read import relpath
from mikemol.treeio.sources import Rev, WorkingTree

if TYPE_CHECKING:
    from collections.abc import Iterable

    from mikemol.treeio.sources import Source

LISTDIR_ORDER = "path-lexicographic, repo-relative, forward-slashed"
"""The order `listdir` returns, NAMED rather than discarded: a plain sorted list would pay for
the sort and then make what it bought unsayable, so no caller could state what it relies on."""


class AmbiguousPatternError(ValueError):
    """Raised by `listdir` for a pattern whose meaning depends on the source.

    THE REFUSAL NAMES ITS SUCCESSOR. A refusal that only says no re-creates the problem one layer
    up: the caller picks whichever spelling silences it. Paperkit named this `AmbiguousPattern`,
    which stays as an alias.
    """


AmbiguousPattern = AmbiguousPatternError


def _glued_double_star(segs: list[str]) -> str | None:
    """Find a segment that glues a double star to other characters.

    Returns:
        The refusal for the first such segment, or None when there is none.

    """
    for seg in segs:
        if "**" in seg and seg != "**":
            return (
                f"`{seg}` — `**` is only a segment wildcard when it is a WHOLE segment; "
                "glob reads it as a plain `*` here, fnmatch has no `**` at all"
            )
    return None


def _lossy_double_star(segs: list[str]) -> str | None:
    """Find a double star segment that is followed by more segments.

    Returns:
        The refusal naming the depth-agnostic successor, or None when the pattern has none.

    """
    if "**" in segs and segs[-1] != "**":
        successor = "/".join(segs[: segs.index("**") + 1])
        return (
            "`**/` cannot match ZERO segments in either matcher, so every depth-0 "
            "path is dropped — silently, because the drop looks like a smaller "
            f"corpus. Use the depth-agnostic `{successor}` (+ `--suffix`), which both "
            "matchers read identically."
        )
    return None


def _separator_crossing_star(pattern: str, segs: list[str]) -> str | None:
    """Find a bare star or question mark across several segments.

    A bare star is separator-RESPECTING under glob and separator-CROSSING under fnmatch. It is
    harmless only when the pattern cannot span a slash anyway, that is, when it is one segment.

    Returns:
        The refusal naming the depth-agnostic successor, or None when the pattern is safe.

    """
    if "**" not in segs and len(segs) > 1 and any("*" in s or "?" in s for s in segs):
        successor = "/".join(segs[:-1])
        return (
            "`*`/`?` crosses `/` under the Rev matcher (fnmatch) but not under "
            f"the working-tree matcher (glob), so `{pattern}` selects one depth on disk "
            f"and every depth at a revision. Use `{successor}/**` (+ `--suffix`)."
        )
    return None


def ambiguous_across_sources(pattern: str) -> str | None:
    """Give the reason `pattern` means different things at different sources, or None.

    This is a property of the PATTERN ALONE: no filesystem, no revision. That is what makes it
    checkable without a corpus, and what makes the refusal deterministic rather than a function of
    what happens to be on disk.

    Returns:
        The reason, naming the successor spelling, or None for a pattern both matchers agree on.

    """
    segs = pattern.split("/")
    return (
        _glued_double_star(segs)
        or _lossy_double_star(segs)
        or _separator_crossing_star(pattern, segs)
    )


def _walk(tree: pygit2.Tree, prefix: str, pattern: str, found: list[str]) -> None:
    """Collect every blob path under `tree` that `fnmatch` accepts, depth first."""
    for entry in tree:
        full = prefix + (entry.name or "")
        if isinstance(entry, pygit2.Tree):
            _walk(entry, full + "/", pattern, found)
        elif fnmatch.fnmatch(full, pattern):
            found.append(full)


def _list_rev(pattern: str, source: Rev) -> list[str]:
    """List the blob paths of a revision that `fnmatch` accepts.

    An empty listing from a BROKEN source would read as "the revision contains no matches", the
    same absent/broken collapse `read` exists to remove, so this RAISES instead of returning none.

    Returns:
        The matching paths, sorted.

    """
    tree, err = source.resolve()
    if tree is None:
        raise err or RuntimeError(f"cannot resolve {source.rev!r}")
    found: list[str] = []
    _walk(tree, "", pattern, found)
    return sorted(found)


def listdir(pattern: str, source: Source | None = None, *, strict: bool = True) -> list[str]:
    """List repo-relative paths matching a glob at `source`, in `LISTDIR_ORDER`.

    REFUSES (`AmbiguousPatternError`) a pattern that would mean different things at a WorkingTree
    and at a Rev. `strict=False` opts out for a caller who has ESTABLISHED it only ever reads one
    source: it is not a way to make the pattern portable. For a WorkingTree this wraps `glob`; it
    does not become a new file-discovery authority. Both sources are ordered by the SAME key, which
    is what makes a working-tree listing and a revision listing comparable at all.

    Returns:
        The matching paths, sorted.

    Raises:
        AmbiguousPatternError: when strict and the pattern is source-dependent.

    """
    chosen = WorkingTree() if source is None else source
    if strict:
        why = ambiguous_across_sources(pattern)
        if why is not None:
            msg = f"pattern {pattern!r} means different things at a WorkingTree and at a Rev: {why}"
            raise AmbiguousPatternError(msg)
    if isinstance(chosen, Rev):
        return _list_rev(pattern, chosen)
    hits = glob.glob(str(chosen.root / pattern), recursive=True)
    return sorted(relpath(p, chosen.root) for p in hits)


def suffixed(paths: Iterable[str], suffix: str) -> list[str]:
    """Filter paths to those ending in `suffix`, or keep them all when it is falsy.

    This is not sugar for a better glob: NO GLOB EXPRESSES IT, which is a measured fact about the
    two matchers. `d/**/*.ext` drops every depth-0 module on a revision and `d/*.ext` selects
    every depth there but only depth 0 on disk. The pattern to pair this with is `d/**`, which is
    depth-agnostic on BOTH matchers.

    Returns:
        The kept paths, in their given order.

    """
    return [p for p in paths if p.endswith(suffix)] if suffix else list(paths)
