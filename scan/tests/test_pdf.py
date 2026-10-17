# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the PDF step: join in order, then OCR, naming the step that fails (W1424).

⚑ NO PROGRAMS ARE RUN: `Run` records the argvs. The controls are the three ways it goes wrong: the
pages reaching img2pdf in any order but the one given, an empty page list quietly becoming an empty
PDF, and a failed first step letting the OCR step run on a PDF that was never written.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from mikemol.scan import pdf

if TYPE_CHECKING:
    from collections.abc import Sequence

_FAILED = 1
_TWO = 2


def _recorder(codes: Sequence[int] = (0, 0)) -> tuple[pdf.Run, list[list[str]]]:
    asked: list[list[str]] = []

    def run(argv: Sequence[str]) -> tuple[int, str]:
        asked.append(list(argv))
        return codes[len(asked) - 1], "tool said this"

    return run, asked


def test_the_pages_reach_img2pdf_in_the_order_given_then_ocrmypdf_reads_the_joined_pdf(
    tmp_path: Path,
) -> None:
    """f1 b1 f2 b2 stays f1 b1 f2 b2, one word each; the OCR step reads what the join wrote."""
    pages = [Path(f"{name}.tif") for name in ("f1", "b1", "f2", "b2")]
    run, asked = _recorder()
    out = pdf.build(pages, tmp_path / "work", tmp_path / "out.pdf", run)
    assert out == tmp_path / "out.pdf"
    assert asked[0][:5] == ["img2pdf", "f1.tif", "b1.tif", "f2.tif", "b2.tif"]
    joined = str(tmp_path / "work" / pdf.JOINED)
    assert asked[0][-2:] == ["-o", joined]
    assert asked[1] == ["ocrmypdf", joined, str(tmp_path / "out.pdf")]


def test_no_pages_is_refused_and_nothing_runs(tmp_path: Path) -> None:
    """The control: an empty list never becomes an empty PDF."""
    run, asked = _recorder()
    with pytest.raises(pdf.PdfError, match="no pages"):
        pdf.build([], tmp_path / "w", tmp_path / "o.pdf", run)
    assert not asked


def test_a_failed_join_stops_before_ocr_and_names_the_step(tmp_path: Path) -> None:
    """img2pdf exits 1: the error says so, with its words, and ocrmypdf is never run."""
    run, asked = _recorder((_FAILED, 0))
    with pytest.raises(pdf.PdfError, match=r"img2pdf exited 1: tool said this"):
        pdf.build([Path("a.tif")], tmp_path / "w", tmp_path / "o.pdf", run)
    assert len(asked) == 1


def test_a_failed_ocr_names_ocrmypdf(tmp_path: Path) -> None:
    """The second step failing is reported as the second step."""
    run, asked = _recorder((0, _FAILED))
    with pytest.raises(pdf.PdfError, match=r"ocrmypdf exited 1"):
        pdf.build([Path("a.tif")], tmp_path / "w", tmp_path / "o.pdf", run)
    assert len(asked) == _TWO
