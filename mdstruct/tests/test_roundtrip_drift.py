# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""One round: what a single round-trip reports about what changed.

⚑⚑ PANDOC NORMALIZES BY DESIGN, SO IDENTITY IS THE UNUSUAL CASE. That makes a bare pass/fail the
wrong shape for this reader: the caller almost always gets "not identical" and needs the SIZE and
SHAPE of the difference to decide whether it matters. A count alone sends them to re-derive what
the tool already computed.

⚑ THIS FILE IS ONE ROUND ONLY. Iteration to a fixpoint is a different subject with a different
failure mode, and its cases live in `test_roundtrip_fixpoint.py` and
`test_roundtrip_stopping.py`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.mdstruct import roundtrip

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.needs_pandoc


def test_a_normalized_document_round_trips_identically(doc: Path) -> None:
    """Check a document already at its fixpoint reports no drift.

    ⚑ THE POSITIVE CONTROL FOR THE WHOLE READER. Without it, a drift detector that reported a
    difference unconditionally would satisfy every other case in this file.
    """
    doc.write_text("# Heading\n\nA plain paragraph.\n", encoding="utf-8")
    normalized = roundtrip.fixpoint(doc)
    doc.write_text(normalized.text, encoding="utf-8")
    assert roundtrip.roundtrip(doc).identical


def test_drift_carries_its_sample_not_just_a_count(doc: Path) -> None:
    """Check a non-identical round-trip reports WHAT changed.

    ⚑ NOT A PASS/FAIL. The SIZE and SHAPE of the drift is what a caller needs; a bare count is a
    number they cannot act on without reading the two documents themselves.
    """
    doc.write_text("Heading\n=======\n\n*  loose  bullet\n", encoding="utf-8")
    drift = roundtrip.roundtrip(doc)
    if not drift.identical:
        assert drift.changed > 0
        assert drift.sample, "a drift reported a count with no sample"
