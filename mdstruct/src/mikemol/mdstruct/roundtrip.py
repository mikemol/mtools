# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Whether normalization CONVERGES, and whether the drift is one-time or a permanent tax.

⚑⚑⚑ THE FIXPOINT QUESTION IS THE ONE THAT DECIDES A WRITE PATH, AND THE FIRST READING OF IT WAS
AN EITHER/OR TRAP. The reasoning was: pandoc reflows the input, therefore a transform is
unusable — which treats PRESERVES-THE-INPUT and UNUSABLE as the only options. It is neither:

    if normalize(normalize(x)) == normalize(x)

then a ONE-TIME accepted reflow moves the document to its fixpoint and every subsequent
transform round-trips exactly. The drift measured against the ORIGINAL is then the wrong number
to judge by, because it is paid once. `roundtrip` measures that one-time cost; `fixpoint`
measures whether paying it ends.

⚑⚑⚑ AND THE TERMINATION CONDITION HAS BEEN WRONG TWICE, IN OPPOSITE DIRECTIONS. Both are kept
because each replaced the other's fix.

 1. **A ROUND CAP READ A CONVERGING SEQUENCE AS DIVERGENT.** Three rounds gave `[1340, 899,
    561]` and that was called *"diverges monotonically"* — the exact opposite of what those
    numbers say, since a DECREASING delta is the signature of approach. Run to convergence the
    same document gives `[1340, 899, 561, 400, 320, 176, 0]`: seven rounds. **A cap is a
    CAPABILITY bound dressed as a termination bound.**
 2. **THEN "STRICT DECREASE" CALLED A PLATEAU A STALL.** The fix for (1) stopped on the first
    non-strict step, so `[…, 92, 56, 56]` read as a cycle — and that misreading was written into
    a docstring and a survey built on it. MEASURED past the guard: `[686, 571, 312, 114, 92, 56,
    56, 56, 34, 34, 34, 0]` — it converges in 12, descending in PLATEAUS, because pandoc
    re-emits a block group at a time and several rounds can move the same count while different
    blocks settle. **Strictness is a stronger claim than the well-foundedness argument needs:
    no INCREASE plus eventual movement suffices.**

So the honest stopping conditions are `n == 0` (converged) or a delta that GROWS (real
divergence), with a plateau budget so a true cycle still ends.

⚑⚑ THE CONVERGED TEXT IS RETURNED, AND ITS ABSENCE IS WHY A PAYDOWN NEVER HAPPENED. This ran a
document all the way to its fixpoint and returned only the DELTAS — so a style census could
report *"48 rows → 0 after one pass"* while nothing could write that result, and the warnings
kept firing on every edit. A census with no apply trains a reader to dismiss it as pre-existing.
The answer was one return value away, not a build.
"""

from __future__ import annotations

import difflib
from typing import TYPE_CHECKING, NamedTuple

from mikemol.mdstruct import pandoc

if TYPE_CHECKING:
    from pathlib import Path

# How many changed lines to carry as a sample — enough to see the shape, bounded so a whole-file
# reflow cannot flood a caller.
_SAMPLE = 12

# ⚑ HOW MANY EQUAL DELTAS IN A ROW BEFORE CALLING IT A CYCLE. This is a TERMINATION bound — a
# repeat that never breaks is genuinely stuck — and NOT a capability bound: the measured worst
# plateau is 3, so 8 leaves room without inventing a limit the documents have to respect.
FLAT_BUDGET = 8


class Drift(NamedTuple):
    """What one normalization pass changes."""

    identical: bool
    changed: int
    sample: tuple[str, ...]


class Fixpoint(NamedTuple):
    """Whether normalization converges, the per-round deltas, and the converged text.

    ⚑ THE DELTAS ARE THE READING, NOT THE VERDICT. `[686, 571, 312, …]` says approach;
    `[56, 56, 56]` says plateau; a growing sequence says divergence. A bare boolean discards
    the only thing that distinguishes them.
    """

    converged: bool
    deltas: tuple[int, ...]
    sample: tuple[str, ...]
    text: str


def diff(before: str, after: str, limit: int = _SAMPLE) -> tuple[int, tuple[str, ...]]:
    """Return how many lines changed, and a bounded sample of them.

    Returns:
        how many lines changed, and a bounded sample of them.

    """
    lines = [line for line in difflib.unified_diff(
        before.split("\n"), after.split("\n"), lineterm="", n=0)
        if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))]
    return len(lines), tuple(lines[:limit])


def roundtrip(path: Path, opts: str | None = None) -> Drift:
    """Return what one normalization pass does to the document.

    ⚑ NOT A PASS/FAIL. Pandoc normalizes by design, so `identical` is the UNUSUAL case; what a
    caller needs is the SIZE and SHAPE of the drift, which is why the sample travels with the
    count.

    Returns:
        what one normalization pass does to the document.

    """
    src = path.read_text(encoding="utf-8")
    out = pandoc.convert(src, opts or "markdown")
    if out == src:
        return Drift(identical=True, changed=0, sample=())
    changed, sample = diff(src, out)
    return Drift(identical=False, changed=changed, sample=sample)


def fixpoint(path: Path, opts: str | None = None, rounds: int | None = None) -> Fixpoint:
    """Iterate normalization to convergence and report the sequence.

    ⚑ `rounds` DEFAULTS TO UNBOUNDED and survives only as a runaway guard for a pathological
    input. Bounding it by default is defect (1) in the module note: a cap turns a document that
    needs one more round than the cap into a reported divergence.

    Returns:
        A `Fixpoint` carrying the converged text, whether it converged, and the PER-ROUND DELTAS.
        ⚑⚑ THE SEQUENCE IS PART OF THE ANSWER, NOT DIAGNOSTIC DECORATION: a decreasing sequence
        is approach, a repeated value is a plateau and a growing one is divergence — three
        different repairs behind one boolean. Two wrong stopping rules were adopted by reading a
        verdict without its sequence, which is why this returns the deltas rather than a flag.

    """
    src = path.read_text(encoding="utf-8")
    current = pandoc.convert(src, opts or "markdown")

    deltas: list[int] = []
    sample: tuple[str, ...] = ()
    previous: int | None = None
    flat = 0

    while rounds is None or len(deltas) < rounds:
        nxt = pandoc.convert(current, opts or "markdown")
        changed, changed_sample = diff(current, nxt)
        deltas.append(changed)
        if changed and not sample:
            sample = changed_sample
        current = nxt

        if changed == 0:
            return Fixpoint(converged=True, deltas=tuple(deltas), sample=(), text=current)
        if previous is not None and changed > previous:
            # A GROWING delta is real divergence — the document is moving further each pass.
            return Fixpoint(converged=False, deltas=tuple(deltas), sample=sample, text=current)
        if previous is not None and changed == previous:
            flat += 1
            if flat >= FLAT_BUDGET:
                return Fixpoint(converged=False, deltas=tuple(deltas),
                                sample=sample, text=current)
        else:
            flat = 0
        previous = changed

    return Fixpoint(converged=False, deltas=tuple(deltas), sample=sample, text=current)
