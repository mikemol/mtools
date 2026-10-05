# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""One shared incomplete-scan banner every driver printer calls, so no mode decides it alone.

Measured by linux-sources against substrate's origin (inbox/archive/2026-09-26-linux-sources-
pycodemod-literal-silent-skip.md, W46): `--calls` named a skip and called the whole query broken
when every file failed to parse; `--literal` and `--source`, over the SAME failure, printed a bare
`0 … in 0 of N file(s)` with no banner and no skip reason — a false negative that reads exactly like
an honest empty result. Each origin mode re-decided its own reporting, and one of three decided
silently.

⚑ THE FIX IS ONE FUNCTION, NOT A CONVENTION EVERY MODE MUST REMEMBER. `incomplete()` takes the
skip reasons and the population size and returns the banner lines plus the exit code the driver
should use — zero when reads happened, non-zero when every file in the population was skipped,
because a result with no readable input is a broken query, not an empty one.

⚑ TAKES `(why, error)` PAIRS, NOT `Skip` OBJECTS: `core.Skip` and `exit.Skip` are two distinct
dataclasses (never unified — W46 is one shared reporter, not a skip-type merger), and a structural
`Protocol` over their shared shape leaves `why`/`error` as accessor stubs no caller ever reaches,
which the mutation grid rightly reports as SURVIVED — code nothing exercises. A plain tuple has no
such stub.

⚑ AN EMPTY RESULT SAYS WHAT IT SEARCHED (W643, W648). summit measured `importers` on a module
nobody imports: exit 0 and only skip counters, so a capability check could not fail on an empty
result and a zero read as an absence. `Tally` counts the ROW lines a handler writes, with no edit
to any handler's loop; `note()` writes a line that is NOT a row (a banner, a summary count), so a
mode that always prints a summary still counts as empty when it found nothing.
"""

from __future__ import annotations

import io
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import TextIO

_BANNER = "\N{WARNING SIGN} INCOMPLETE SCAN"
_BROKEN = (
    "\N{WARNING SIGN}\N{WARNING SIGN} EVERY file was skipped"
    " — this is a BROKEN QUERY, not an empty result."
)


def incomplete(skipped: Sequence[tuple[str, str]], population: int) -> tuple[list[str], int]:
    """Return the incomplete-scan banner and the exit code, or `([], 0)` when nothing was skipped.

    `skipped` is a sequence of `(why, error)` pairs — a caller with `Skip` objects passes
    `[(s.why, s.error) for s in skips]`.

    ⚑ GROUPED BY REASON, NOT BY (REASON, ERROR): the letter's own example counted `unparseable` once
    with `AttributeError` shown because only one error type occurred; a reason with two distinct
    error types shows both, comma-joined, rather than splitting into two skip-count lines a reader
    would have to re-add.

    Returns:
        the banner lines (empty when nothing was skipped) and the exit code.

    """
    if not skipped:
        return [], 0
    read = population - len(skipped)
    by_reason: dict[str, list[str]] = {}
    for why, error in skipped:
        by_reason.setdefault(why, []).append(error)
    lines = [f"{_BANNER} — read {read} of {population} file(s); {len(skipped)} skipped:"]
    for why in sorted(by_reason):
        errors = by_reason[why]
        kinds = ", ".join(sorted(set(errors)))
        lines.append(f"  {why}: {len(errors)} ({kinds})")
    if read == 0:
        lines.append(_BROKEN)
    return lines, (1 if read == 0 else 0)


class Tally(io.TextIOBase):
    """A stdout stand-in that forwards every write and counts the lines as rows.

    `inner` receives the text unchanged; `rows` is the number of newline-terminated lines written
    through `write`, so a handler's own `sys.stdout.write` of a line is counted without any edit.
    """

    def __init__(self, inner: TextIO) -> None:
        """Wrap `inner`, with no rows counted yet."""
        super().__init__()
        self.inner = inner
        self.rows = 0

    def write(self, text: str, /) -> int:
        """Forward `text` and count its lines as rows.

        Returns:
            the number of characters written.

        """
        self.rows += text.count("\n")
        return self.inner.write(text)

    def flush(self) -> None:
        """Flush the wrapped stream."""
        self.inner.flush()


def note(text: str) -> None:
    """Write `text` to stdout as a line that is not a row (a banner or a summary count)."""
    out = sys.stdout
    if isinstance(out, Tally):
        out.inner.write(text)
    else:
        out.write(text)


def found_none(mode: str, searched: int) -> str:
    """Return the line an empty census prints: what it searched, and that it found none.

    Returns:
        `<mode>: searched N file(s), found none`.

    """
    return f"{mode}: searched {searched} file(s), found none"
