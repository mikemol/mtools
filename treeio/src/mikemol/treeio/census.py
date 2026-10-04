# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Count what a glob selects: a presence census, and the re-derivation of the matcher asymmetry.

Ported from paperkit's `tools/vfs.py`. EMPTY IS A SUBDIVISION OF PRESENT, NOT A FOURTH PRESENCE,
and that is the point. A text view that returns an empty string for a missing file collapses ABSENT
into EMPTY, so the question "does that collapse have a POPULATION here?" is answerable only by
counting the two separately over a real corpus. A caller whose falsy branch means "no statements to
scan" is provably unaffected when the empty cell is zero.

`compare` is the derivation behind the table in `mikemol.treeio.listing`: that table is prose, and
the next reader either trusts it or re-derives it by hand, so this IS the derivation and the claim
and the check are one artefact. It bypasses the refusal by construction, since the ambiguous
patterns are precisely its subject matter.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mikemol.treeio.listing import listdir, suffixed
from mikemol.treeio.presence import Presence
from mikemol.treeio.read import read
from mikemol.treeio.sources import Rev, WorkingTree

if TYPE_CHECKING:
    from pathlib import Path

    from mikemol.treeio.sources import Source


@dataclass(frozen=True)
class Census:
    """The cells of a presence census, plus the paths worth naming."""

    nonempty: int
    empty: int
    absent: int
    broken: int
    total: int
    empty_paths: list[str]
    broken_paths: list[tuple[str, BaseException | None]]


@dataclass(frozen=True)
class Side:
    """What one pattern selected at one source, against the depth-agnostic control."""

    n: int
    control_n: int
    missed: list[str]
    extra: list[str]


@dataclass(frozen=True)
class Comparison:
    """The two matchers' answers to one pattern: the working tree, and the revision."""

    pattern: str
    control: str
    rev: str
    wt: Side
    head: Side


def census(pattern: str, source: Source, suffix: str = "") -> Census:
    """Take a presence census over a glob, splitting PRESENT into empty and nonempty.

    Returns the empty and broken paths as well as the counts, so a caller can NAME the offenders
    rather than only count them. The counting has ONE body, shared by every caller: a CLI that
    re-inlined the loop would be the one-capability-several-bodies defect in the module written to
    retire a duplicated read.

    Returns:
        The cells, with total the sum of the four.

    """
    empty: list[str] = []
    nonempty = absent = 0
    broken: list[tuple[str, BaseException | None]] = []
    for path in suffixed(listdir(pattern, source), suffix):
        result = read(path, source)
        if result.presence is Presence.PRESENT:
            if result.data:
                nonempty += 1
            else:
                empty.append(path)
        elif result.presence is Presence.ABSENT:
            absent += 1
        else:
            broken.append((path, result.error))
    return Census(
        nonempty=nonempty,
        empty=len(empty),
        absent=absent,
        broken=len(broken),
        total=nonempty + len(empty) + absent + len(broken),
        empty_paths=empty,
        broken_paths=broken,
    )


def control_of(pattern: str) -> str:
    """Derive the depth-agnostic control: the longest wildcard-free prefix plus a double star.

    It is derived from the segments, not from splitting on a double star. The first cut split on
    the double star and so emitted a control for a pattern with none in it that selects nothing,
    against which every real listing read as one hundred percent extra. A degenerate control does
    not report itself as degenerate.

    Returns:
        The control pattern.

    """
    keep: list[str] = []
    for seg in pattern.split("/"):
        if any(c in seg for c in "*?["):
            break
        keep.append(seg)
    return ("/".join(keep) or ".").rstrip("/") + "/**"


def _side(pattern: str, control: str, source: Source, suffix: str) -> Side:
    """Measure one source: what the pattern selected against what the control selected.

    Returns:
        The counts, and the paths the pattern missed or added relative to the control.

    """
    got = set(suffixed(listdir(pattern, source, strict=False), suffix))
    con = set(suffixed(listdir(control, source, strict=False), suffix))
    return Side(n=len(got), control_n=len(con), missed=sorted(con - got), extra=sorted(got - con))


def compare(pattern: str, rev: str, suffix: str = "", root: Path | None = None) -> Comparison:
    """Give the difference between the two matchers for ONE pattern.

    It compares two DIFFERENT trees (disk and a revision), so a raw difference mixes the matchers'
    disagreement with real edits. What is diagnostic is the ASYMMETRY against the depth-agnostic
    control: if the pattern were source-neutral, the pattern and the control would select the same
    subset of EACH source.

    Returns:
        The pattern, its control, and the measurement at each source.

    """
    control = control_of(pattern)
    return Comparison(
        pattern=pattern,
        control=control,
        rev=rev,
        wt=_side(pattern, control, WorkingTree(root), suffix),
        head=_side(pattern, control, Rev(rev, root), suffix),
    )
