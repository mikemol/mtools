# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Page order for a two-pass ADF scan: the backs arrive last-page-first (W1422).

⚑⚑ AN ADF THAT DOES NOT DO DUPLEX NEEDS THE STACK FED TWICE. Pass one scans the fronts in page
order: f1, f2, ..., fn. The operator flips the stack over and feeds it again, and the stack goes in
back-first (luthen-observability:W1210, measured on the Brother over eSCL): the first sheet through
carries the back of page n. So pass two yields bn, ..., b2, b1, and the document is f1 b1 f2 b2 ...
fn bn. This module is that interleave and nothing else: no scanner, no file is read, so it is tested
with planted file names.

⚑ A COUNT THAT DOES NOT MATCH IS REFUSED, NOT PADDED. A jam or a double feed leaves fronts and backs
unequal, and interleaving them anyway would shift every later back onto the wrong page and read as a
complete document. The error names both counts so the operator knows which pass lost a sheet.
"""

from collections.abc import Sequence
from pathlib import Path


class PageCountError(ValueError):
    """The two passes produced different numbers of sheets."""


def order(fronts: Sequence[Path], backs: Sequence[Path]) -> list[Path]:
    """Interleave fronts with the reversed backs into page order.

    Returns:
        f1, b1, f2, b2, ..., where b1 is the LAST file of the second pass.

    Raises:
        PageCountError: when the passes hold different numbers of files.

    """
    if len(fronts) != len(backs):
        msg = f"{len(fronts)} front(s) but {len(backs)} back(s): a sheet was lost or double-fed"
        raise PageCountError(msg)
    pages: list[Path] = []
    for front, back in zip(fronts, reversed(backs), strict=True):
        pages.extend((front, back))
    return pages
