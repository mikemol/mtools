# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""What iterating to a fixpoint hands back — the sequence, and the converged text.

⚑⚑ THE READING IS THE SEQUENCE, NOT THE VERDICT. `[686, 571, 312, …]` says approach; `[56, 56,
56]` says plateau; a growing sequence says divergence. A boolean discards the only thing that
separates those three — which is precisely how both historical stopping rules were adopted (see
`test_roundtrip_stopping.py`).

⚑ AND THE TEXT MUST COME BACK. A function that ran a document all the way to its fixpoint and
returned only deltas let a census report *"48 rows → 0 after one pass"* while nothing could write
that result. **A census with no apply trains a reader to dismiss it as pre-existing.**
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.mdstruct import roundtrip

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.needs_pandoc


def test_convergence_reports_the_whole_sequence(doc: Path) -> None:
    """Check the per-round deltas are returned, not only the verdict."""
    doc.write_text("# H\n\nsome text\n", encoding="utf-8")
    result = roundtrip.fixpoint(doc)
    assert result.deltas, "no per-round deltas were reported"
    assert result.converged
    assert result.deltas[-1] == 0, "converged without a zero delta"


def test_the_converged_text_is_returned(doc: Path) -> None:
    """Check the fixpoint's TEXT comes back, not only the fact that one exists."""
    doc.write_text("Heading\n=======\n\ntext\n", encoding="utf-8")
    result = roundtrip.fixpoint(doc)
    assert result.text
    assert result.text != "", "the converged text was discarded"
