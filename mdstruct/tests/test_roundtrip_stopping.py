# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The two stopping rules that were both wrong, in opposite directions.

⚑⚑⚑ EACH FIX CAUSED THE NEXT DEFECT, WHICH IS WHY THEY SHARE A FILE. A round cap read `[1340,
899, 561]` as divergence — the exact opposite, since a DECREASING delta is the signature of
approach; run to convergence it reaches zero in seven. The fix for that, "stop unless the delta
strictly decreases", then read a PLATEAU as a stall: `[…, 92, 56, 56, 56, 34, 34, 34, 0]`
converges in 12, descending in plateaus, because pandoc re-emits a block group at a time.

⚑⚑ BOTH WERE ADOPTED BY READING A VERDICT WITHOUT ITS SEQUENCE. Kept together so a future reader
meets the pair, not one of them: fixing either in isolation is what produced the other.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.mdstruct import roundtrip

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.needs_pandoc

# ⚑ THE WORST PLATEAU MEASURED IS THREE REPEATS, so a budget of 4 leaves margin. Named because a
# budget of 1 reproduces the second wrong rule exactly — stopping on the first repeat — and a
# bare `4` beside the assertion cannot say which side of that line it is defending.
_MIN_BUDGET_FOR_MEASURED_PLATEAU = 4

# A document pandoc rewrites over several rounds: setext headings, loose bullets, ragged spacing.
_MULTI_ROUND = """Heading
=======

*   a  loose   bullet
*   another one

Some   text with  *emphasis*  and  ragged   spacing.

Sub
---

more    text
"""


def test_a_plateau_is_not_treated_as_a_stall() -> None:
    """Check the flat budget admits repeats — a TERMINATION bound, not a capability one.

    ⚑ THE SECOND WRONG RULE, PINNED AS A CONSTANT. A budget of 1 would reproduce the defect,
    stopping on the first repeat, so this asserts room for the measured worst plateau with
    margin.
    """
    assert roundtrip.FLAT_BUDGET >= _MIN_BUDGET_FOR_MEASURED_PLATEAU


def test_a_round_cap_is_not_the_default(doc: Path) -> None:
    """Check a document needing several rounds converges when none is requested.

    ⚑ THE FIRST WRONG RULE. A default cap turns a document needing one more round than the cap
    into a reported divergence — a CAPABILITY bound dressed as a termination bound.

    ⚑⚑ ASSERTED AS BEHAVIOUR, NOT BY INTROSPECTING THE SIGNATURE. `inspect.Parameter.default` is
    typed `Any` by design — it holds whatever was declared — so every read of it carries an
    unchecked value into the assertion, leaving the test untyped at exactly the point it made
    its claim. **And the signature was never the property that mattered:** a `rounds=None`
    default with a cap applied inside the body satisfies that check and still has the defect.
    Running a genuinely multi-round document to convergence with no `rounds` argument tests the
    thing the defect broke.
    """
    doc.write_text(_MULTI_ROUND, encoding="utf-8")
    result = roundtrip.fixpoint(doc)
    assert result.converged, f"did not converge without a round argument: {result.deltas}"
    assert result.deltas[-1] == 0
