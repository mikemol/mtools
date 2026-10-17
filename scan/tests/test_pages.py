# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for two-pass page order: backs reversed, interleaved, mismatches refused (W1422).

⚑ NO SCANNER: the pages are planted file names. The controls are the three ways the order goes
wrong: the backs used as they arrived (so every back lands on the wrong page), a one-sheet document
(where reversing changes nothing and must not break), and unequal passes, which are refused with
both counts rather than padded.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mikemol.scan import pages


def _names(count: int, prefix: str) -> list[Path]:
    return [Path(f"{prefix}{n}.pgm") for n in range(1, count + 1)]


def test_the_backs_are_reversed_then_interleaved_into_page_order() -> None:
    """Three sheets: the second pass yields b3 b2 b1, and the document is f1 b1 f2 b2 f3 b3."""
    fronts = _names(3, "f")
    arrival = [Path("b3.pgm"), Path("b2.pgm"), Path("b1.pgm")]
    got = pages.order(fronts, arrival)
    assert [p.name for p in got] == ["f1.pgm", "b1.pgm", "f2.pgm", "b2.pgm", "f3.pgm", "b3.pgm"]


def test_the_backs_in_arrival_order_would_misplace_every_page() -> None:
    """The control: interleaving without the reversal gives b3 after f1, which is the bug."""
    fronts = _names(3, "f")
    arrival = [Path("b3.pgm"), Path("b2.pgm"), Path("b1.pgm")]
    naive = [p.name for pair in zip(fronts, arrival, strict=True) for p in pair]
    assert naive[1] == "b3.pgm"
    assert pages.order(fronts, arrival)[1].name == "b1.pgm"


def test_a_single_sheet_and_an_empty_document_are_fine() -> None:
    """One sheet is f1 b1; nothing at all is an empty list, not an error."""
    assert [p.name for p in pages.order([Path("f1.pgm")], [Path("b1.pgm")])] == ["f1.pgm", "b1.pgm"]
    assert pages.order([], []) == []


def test_unequal_passes_are_refused_naming_both_counts() -> None:
    """A lost or double-fed sheet raises, with the counts, and builds nothing."""
    with pytest.raises(pages.PageCountError, match=r"3 front\(s\) but 2 back\(s\)"):
        pages.order(_names(3, "f"), _names(2, "b"))
