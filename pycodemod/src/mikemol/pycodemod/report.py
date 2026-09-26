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

⚑ TAKES `(why, error)` PAIRS, NOT `Skip` OBJECTS: `sites.Skip` and `exit.Skip` are two distinct
dataclasses (never unified — W46 is one shared reporter, not a skip-type merger), and a structural
`Protocol` over their shared shape leaves `why`/`error` as accessor stubs no caller ever reaches,
which the mutation grid rightly reports as SURVIVED — code nothing exercises. A plain tuple has no
such stub.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

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
