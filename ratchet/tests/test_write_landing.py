# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A write that succeeds and a write that LANDS are different claims (W670, the declared defect)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.ratchet.core import write_baseline

if TYPE_CHECKING:
    from pathlib import Path


def test_a_baseline_that_did_not_land_raises_instead_of_reading_as_written(tmp_path: Path) -> None:
    """W670: a write whose readback differs is an OSError naming the counts, never silent.

    ⚑ DECLARED DEFECT `readback-not-checked`: a key that begins with `#` is written and then read
    back as a COMMENT, so the baseline that landed is not the baseline that was asked for. Without
    the check the write reports success over a smaller set, which is how a baseline stops being
    the one nobody chose.
    """
    with pytest.raises(OSError, match="did not round-trip"):
        write_baseline(tmp_path / "b.txt", {"# not a key", "a.py:rule1"}, write=True)
