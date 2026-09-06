# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The tool's SELF-ASSERTING CONTRACT: every heading in the source reaches the section list.

⚑⚑⚑ THIS EXISTS BECAUSE `lint` AND `roundtrip` BOTH REPORT GREEN ON A DOCUMENT THIS TOOL
SILENTLY CORRUPTS. A heading carrying an apostrophe or a link was dropped from `spans`, and the
PRECEDING section's span was extended across it — so `--replace-section` against the parent
writes INTO the missing child, with well-formed output and no error. `lint` said "no shape
findings"; `roundtrip` said "round-trips IDENTICALLY". Both were correct about the questions they
ask, and neither asks this one.

⚑⚑ THE COMPARISON MUST NOT ROUTE THROUGH THIS TOOL'S OWN PARSER. A checker that shares the
defect it checks for cannot detect it, and re-running a broken reader is not a second opinion.
So the expected set is read with a PLAIN LINE SCAN over raw bytes — deliberately the `awk` reflex
that `spans` exists to replace, used here as an INDEPENDENT witness rather than as the answer.
Its one borrowing from the parser is the fenced-code mask, because `#` inside a fence is not a
heading; that is a fact about markdown, not about this tool's section model.

⚑⚑ AND A ONE-ARMED CONTRACT CERTIFIES A GATE THAT REFUSES EVERYTHING. `--selftest` asserts BOTH
directions: that a clean document passes, AND that each known-defective fixture FIRES. A selftest
green because it is aimed at the wrong predicate is the failure this repo has now paid for twice.

⚑ THE FIXTURES ENUMERATE A SHAPE SPACE, NOT THE KNOWN BUGS. Apostrophe was found by four repos
writing possessive prose; link and image were found by enumerating heading shapes that had never
been tried. The class that bites next is one nobody has written an arm for, so the fixture list
is the standing weakness here — ADD A SHAPE BEFORE TRUSTING THIS.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, NamedTuple

from mikemol.mdstruct import spans as spans_mod

if TYPE_CHECKING:
    from pathlib import Path

_FENCE = re.compile(r"^\s*(```|~~~)")
_ATX = re.compile(r"^(#{1,6})\s+(.*?)\s*$")


class Missing(NamedTuple):
    """One heading present in the source and absent from the section list."""

    line: int
    level: int
    text: str


def source_headings(text: str) -> list[tuple[int, int, str]]:
    """Return `[(line, level, text)]` by a PLAIN SCAN of raw source.

    ⚑ NOT A PARSE. This is the independent witness, so it must not import this tool's model of a
    document. Fenced blocks are masked because a `#` inside a fence is not a heading in any
    reading; nothing else is interpreted.

    Returns:
        `[(line, level, text)]` by a PLAIN SCAN of raw source.

    """
    out: list[tuple[int, int, str]] = []
    fence: str | None = None
    for i, line in enumerate(text.split("\n"), start=1):
        marker = _FENCE.match(line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif line.strip().startswith(fence):
                fence = None
            continue
        if fence is not None:
            continue
        atx = _ATX.match(line)
        if atx:
            out.append((i, len(atx.group(1)), atx.group(2)))
    return out


def missing_headings(path: Path) -> list[Missing]:
    """Return every source heading that does NOT appear in this tool's section list.

    ⚑ KEYED ON LINE NUMBER, not on text. A heading whose text renders differently is the exact
    defect being checked for, so comparing text would ask the parser to adjudicate its own bug.

    Returns:
        every source heading that does NOT appear in this tool's section list.

    """
    reached = {span.start for span in spans_mod.spans(path)}
    body = path.read_text(encoding="utf-8")
    return [Missing(line=line, level=level, text=text)
            for line, level, text in source_headings(body)
            if line not in reached]


# ⚑⚑ THE SHAPE SPACE, not the bug list. Each entry is one heading shape and whether this tool is
# EXPECTED to reach it today. A `False` row is a KNOWN DEFECT with a standing witness: it must
# keep failing until it is fixed, and the selftest fails if it starts passing unannounced —
# because a defect that quietly resolves is a defect nobody measured resolving.
_SHAPES: tuple[tuple[str, str, bool], ...] = (
    ("plain", "B leg", True),
    ("code span", "B `c` leg", True),
    ("emphasis", "B *em* leg", True),
    ("double quote", 'B "q" leg', True),
    ("ampersand", "B & leg", True),
    ("bare parens", "B (x) leg", True),
    ("bare brackets", "B [x] leg", True),
    ("smart quote", "B \u2019s leg", True),
    ("after fence", "B leg", True),
    # ⚑ THESE THREE WERE `False` — KNOWN DEFECTS WITH STANDING WITNESSES — until the anchor
    # reconciliation stopped modelling pandoc and started asking it. The contract REFUSED to let
    # them resolve silently: it reported "expected UNREACHABLE and it was reached", which is what
    # a fixed defect is supposed to look like from inside a two-armed test.
    ("apostrophe", "B's leg", True),
    ("link", "B [x](y) leg", True),
    ("image", "B ![x](y) leg", True),
    # ⚑⚑ ADDED BY THE REPAIR ITSELF. Batching the render made the result POSITIONAL, and a line
    # beginning with `#` that is NOT a heading (`#no-space`, or a `#` inside a fence) returns no
    # heading — so a bare batch shifts every later pairing by one. The after-fence arm caught it;
    # these keep the class covered from both sides.
    ("no space after hash", "B leg", True),
    ("trailing hashes", "B leg ##", True),
    ("inline html", "B <b>x</b> leg", True),
    ("footnote ref", "B leg[^1]", True),
    ("entity", "B &amp; leg", True),
)


def selftest() -> list[str]:
    """Assert BOTH arms over the shape space; return failure lines (empty means green).

    ⚑ A P-ARM AND AN F-ARM PER SHAPE. Without the F-arms, "no shape reports missing" is
    indistinguishable from a contract that never fires; without the P-arms, a contract that
    reports EVERYTHING missing also passes. Both directions or neither.
    """
    import tempfile  # noqa: PLC0415 — a test-only dependency, not a runtime one
    from pathlib import Path  # noqa: PLC0415

    failures: list[str] = []
    for name, heading, reachable in _SHAPES:
        body = (f"# A\n\n```\n#not a heading\n```\n\n## {heading}\n\nx\n"
                if name == "after fence" else f"# A\n\n## {heading}\n\nx\n")
        path = Path(tempfile.mkdtemp()) / "fixture.md"
        path.write_text(body, encoding="utf-8")
        try:
            missing = missing_headings(path)
        finally:
            path.unlink()
            path.parent.rmdir()
        if reachable and missing:
            failures.append(f"P-arm {name!r}: expected reachable, missing {missing}")
        if not reachable and not missing:
            failures.append(
                f"F-arm {name!r}: expected UNREACHABLE and it was reached — "
                "if this was fixed, flip the row and say so")
    return failures
