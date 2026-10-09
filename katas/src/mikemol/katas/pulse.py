# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""One view of the fleet: commits and pending paths, nemik's warnings, the top of the ranking.

Ported from the host katas.py `pulse` (mtools:W796, W877). It composes `fleet.status` with two
nemik tools run through `procrun.capture`; it reads, it writes nothing.

⚑ THE STANDING WARNINGS ARE THE CALLER'S. A warning nemik prints every time (no working card, an
adopted-writer notice, a long title) is noise to the operator who has already accepted it, so the
caller names the substrings to hide; they change with the operator's rulings, not with this code.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.procrun.proc import capture

from mikemol.katas import fleet

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

CHECK_TIMEOUT_S = 1800.0
"""How long nemik-check or nemik-rank may take: they read every queue."""

RANK_ROWS = 12
"""How many of the ranking's first lines the pulse shows."""

NONE_SHOWN = "(none)"
_MARKS = ("VIOLATES", "Warning")


def warning_lines(output: str, standing: Sequence[str] = ()) -> list[str]:
    """Pick the lines of nemik-check output that page the operator.

    Returns:
        every line naming a VIOLATES or a Warning, minus those that carry a standing substring.

    """
    return [
        line
        for line in output.splitlines()
        if any(mark in line for mark in _MARKS) and not any(skip in line for skip in standing)
    ]


def pulse(host: fleet.Fleet, nemik: Path, standing: Sequence[str] = ()) -> list[str]:
    """Render the fleet view: status rows, then nemik-check's warnings, then the top ranking.

    `nemik` is the directory holding `nemik-check` and `nemik-rank`.

    Returns:
        the lines to print, section headings included.

    """
    checked = capture((str(nemik / "nemik-check"),), timeout=CHECK_TIMEOUT_S).stdout
    ranked = capture((str(nemik / "nemik-rank"), "--all"), timeout=CHECK_TIMEOUT_S).stdout
    shown = warning_lines(checked, standing)
    return [
        *fleet.status(host),
        "-- nemik-check (warnings other than the standing ones)",
        *(shown or [NONE_SHOWN]),
        f"-- nemik-rank --all, top {RANK_ROWS}",
        *ranked.splitlines()[:RANK_ROWS],
    ]
