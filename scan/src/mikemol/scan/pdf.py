# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Ordered page files to one searchable PDF, behind a seam (W1424).

⚑⚑ TWO PROGRAMS, BECAUSE ocrmypdf TAKES ONE INPUT. It reads a single image or PDF, not a list, so
the ordered pages are first joined into one PDF (`img2pdf`, which reads TIFF; the ADF pass writes
TIFF for this reason) and that PDF is then made searchable (`ocrmypdf`). `commands` builds both
argvs and `build` runs them in order through `Run`, so tests plant nothing and start nothing.

⚑ THE ORDER IS THE CALLER'S: the page list is already in document order (`pages.order`), and it
reaches `img2pdf` as given, one argv word per file. An empty list is refused rather than turned
into an empty PDF, and a nonzero exit from either program raises with that program's own words,
naming which step failed.

⚑ NOT YET RUN AGAINST THE REAL PROGRAMS: only the positional input/output of ocrmypdf and the `-o`
output of img2pdf are used, on the strength of their usage lines. Their presence in the scanner
image is luthen-observability:W1209's to land; the first real scan is the check.
"""

from collections.abc import Callable, Sequence
from pathlib import Path

Run = Callable[[Sequence[str]], tuple[int, str]]
JOINED = "joined.pdf"


class PdfError(RuntimeError):
    """A page list could not become a searchable PDF, naming the step that failed."""


def commands(pages: Sequence[Path], work: Path, out: Path) -> tuple[list[str], list[str]]:
    """Build the join command and the OCR command.

    Returns:
        (img2pdf argv writing `<work>/joined.pdf`, ocrmypdf argv reading it and writing `out`).

    """
    joined = work / JOINED
    return (
        ["img2pdf", *map(str, pages), "-o", str(joined)],
        ["ocrmypdf", str(joined), str(out)],
    )


def build(pages: Sequence[Path], work: Path, out: Path, run: Run) -> Path:
    """Join the pages and make the result searchable.

    Returns:
        the output path.

    Raises:
        PdfError: when there are no pages, or either program exits nonzero.

    """
    if not pages:
        msg = "no pages to make a PDF from"
        raise PdfError(msg)
    work.mkdir(parents=True, exist_ok=True)
    join, ocr = commands(pages, work, out)
    for step, argv in (("img2pdf", join), ("ocrmypdf", ocr)):
        code, said = run(argv)
        if code != 0:
            msg = f"{step} exited {code}: {said.strip()[:300]}"
            raise PdfError(msg)
    return out
