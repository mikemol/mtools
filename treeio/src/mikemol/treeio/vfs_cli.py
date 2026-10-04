# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The `mikemol-vfs` command line: read, list, census and compare over a working tree or a revision.

Ported from the `__main__` half of paperkit's `tools/vfs.py`. The `--selftest` mode is gone: the
suite that mode ran is now this distribution's pytest suite.

Exit codes carry the three-valuedness of a read, and the first cut of paperkit's CLI got this wrong
in exactly the way the library exists to prevent: `0 if r else 1` collapsed ABSENT and BROKEN into
one failure, re-creating the old at_revision defect at the CLI boundary after removing it from the
library.

    0  PRESENT: the read happened
    1  ABSENT:  a legitimate answer, not an error
    2  BROKEN:  the read did NOT happen (also a census that met a broken member)
    3  AMBIGUOUS: the question was ill-posed; the message names the pattern to use instead

A shell `if` still treats every non-zero as "no content", so the common case is unaffected, and a
caller that needs the distinction can have it. An ambiguous pattern is a VERDICT, not a crash: the
message already names the replacement and a traceback would bury it.
"""

from __future__ import annotations

import argparse
import sys
from typing import TYPE_CHECKING

from mikemol.treeio.census import Comparison, census, compare
from mikemol.treeio.listing import AmbiguousPatternError, listdir, suffixed
from mikemol.treeio.presence import Presence
from mikemol.treeio.read import read
from mikemol.treeio.sources import Rev, WorkingTree

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mikemol.treeio.sources import Source

_SHOWN = 12  # how many missed or extra paths a comparison names per side
_EXIT_BROKEN = 2
_EXIT_AMBIGUOUS = 3
_EXIT_OF = {Presence.PRESENT: 0, Presence.ABSENT: 1, Presence.BROKEN: _EXIT_BROKEN}


class _Parsed(argparse.Namespace):
    """The typed shape `argparse` fills in."""

    read: str | None
    at: str | None
    list: str | None
    states: bool
    census: str | None
    suffix: str
    compare: str | None


def _say(text: str) -> None:
    """Write one line to stdout."""
    sys.stdout.write(text + "\n")


def _parser() -> argparse.ArgumentParser:
    """Build the argument parser.

    Returns:
        The parser for every mode.

    """
    ap = argparse.ArgumentParser(
        prog="mikemol-vfs",
        description="one read/write seam over a working tree and git history",
    )
    ap.add_argument("--read", metavar="PATH", help="read a path and report its Presence")
    ap.add_argument(
        "--at",
        metavar="REV",
        default=None,
        help="read from a git revision instead of the working tree",
    )
    ap.add_argument("--list", metavar="GLOB", help="list paths matching a glob")
    ap.add_argument("--states", action="store_true", help="the Presence roster and what each means")
    ap.add_argument(
        "--census",
        metavar="GLOB",
        help="Presence census over a glob, splitting PRESENT into empty (0 bytes) vs nonempty",
    )
    ap.add_argument(
        "--suffix",
        metavar="EXT",
        default="",
        help=(
            "restrict --list and --census to paths ending in EXT (for example .agda). "
            "NOT expressible as a glob: the WorkingTree and Rev matchers disagree on `**/*.ext`"
        ),
    )
    ap.add_argument(
        "--compare",
        metavar="GLOB",
        help=(
            "what this pattern selects at each source against the depth-agnostic `<dir>/**` "
            "control, and which paths each branch DROPS. Bypasses the AmbiguousPattern "
            "refusal: ambiguous patterns are its subject."
        ),
    )
    return ap


def _show_compare(found: Comparison) -> None:
    """Print one comparison: a header, then each source's counts and its missed and extra paths."""
    _say(f"compare {found.pattern}   control {found.control}   rev {found.rev}")
    for tag, side in (("wt", found.wt), ("head", found.head)):
        _say(
            f"  {tag:<5} {side.n:5d}   control {side.control_n:5d}"
            f"   missed {len(side.missed)}   extra {len(side.extra)}"
        )
        for path in side.missed[:_SHOWN]:
            _say(f"        MISSED  {path}")
        for path in side.extra[:_SHOWN]:
            _say(f"        EXTRA   {path}")


def _show_states() -> None:
    """Print the roster of presences and what each means."""
    for member in Presence.all():
        _say(f"  {member!s:<8} {'(defect) ' if member.is_defect else ''}{member.gloss}")


def _run_census(pattern: str, source: Source, suffix: str) -> int:
    """Print a presence census over a glob.

    Returns:
        2 when any member was broken, otherwise 0.

    """
    found = census(pattern, source, suffix)
    tail = f"  suffix={suffix}" if suffix else ""
    _say(f"census {pattern}{tail}  ({source})")
    _say(f"  PRESENT nonempty  {found.nonempty}")
    _say(f"  PRESENT empty     {found.empty}")
    for path in found.empty_paths:
        _say(f"      {path}")
    _say(f"  ABSENT            {found.absent}")
    _say(f"  BROKEN            {found.broken}")
    for path, error in found.broken_paths:
        _say(f"      {path}  {error}")
    _say(f"  total             {found.total}")
    return _EXIT_BROKEN if found.broken else 0


def _run_read(path: str, source: Source) -> int:
    """Print one read's verdict.

    Returns:
        0 for PRESENT, 1 for ABSENT, 2 for BROKEN.

    """
    result = read(path, source)
    _say(f"{result.presence!s:<8} {path}  ({source})")
    if result.presence is Presence.PRESENT:
        _say(f"  {len(result.data or b'')} bytes")
    elif result.error:
        _say(f"  {result.error}")
    return _EXIT_OF[result.presence]


def _dispatch(a: _Parsed) -> int:
    """Run the one mode the arguments name, or print help when none is named.

    Returns:
        The exit status of the mode.

    """
    if a.compare:
        _show_compare(compare(a.compare, a.at or "HEAD", a.suffix))
        return 0
    if a.states:
        _show_states()
        return 0
    source: Source = Rev(a.at) if a.at else WorkingTree()
    if a.census:
        return _run_census(a.census, source, a.suffix)
    if a.list:
        for path in suffixed(listdir(a.list, source), a.suffix):
            _say(path)
        return 0
    if a.read:
        return _run_read(a.read, source)
    _parser().print_help()
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line.

    Returns:
        The mode's exit status, or 3 for an ambiguous pattern after naming it on stderr.

    """
    parsed = _parser().parse_args(sys.argv[1:] if argv is None else argv, namespace=_Parsed())
    try:
        return _dispatch(parsed)
    except AmbiguousPatternError as e:
        sys.stderr.write(f"AMBIGUOUS  {e}\n")
        return _EXIT_AMBIGUOUS


if __name__ == "__main__":
    raise SystemExit(main())
