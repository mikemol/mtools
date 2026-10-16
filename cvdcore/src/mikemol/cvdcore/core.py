# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The pure core of the CVD distinctness gate: numpy and colorspacious, no repo import (W1315).

Ported from el-openglo's `cvd_core.py` at commit 9a4be98 (el-openglo:W544, for nemik:W438), typed
under the bar. Semantic ambiguity of a colour pair is its minimum CAM02-UCS distance across four
views of colour vision: trichromat identity plus simulated protanomaly, deuteranomaly and
tritanomaly (Machado model, severity 100, via colorspacious). The floor is not hand-picked: it is
the tightest worst-view separation inside the Okabe-Ito colour-universal-design palette itself.

⚑ WHAT CHANGED IN THE PORT, said so a pin can be read against it: `VIEWS` is a tuple, not a list
(nothing mutates it); the floor's initial sentinel carries empty strings, not None, so the result
type is one shape; the two `functools.cache` memos are explicit dicts (the decorator's type is Any
under the bar); the module has no `__main__` selftest (the seven arms are pytest tests); and the
WCAG and APCA contrast code (also pure) is not here, it stays with the caller.

WEAKNESS, STATED. The Okabe-Ito table is the 2008 chromatic set, seven colours; the floor is
recomputed once and cached, never stored.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from colorspacious import cspace_convert

if TYPE_CHECKING:
    from collections.abc import Sequence

    from numpy import ndarray

VIEWS: tuple[str | None, ...] = (None, "protanomaly", "deuteranomaly", "tritanomaly")
"""The four views: trichromat (None) and the three simulated deficiencies."""

SEVERITY = 100
"""The simulated deficiency's severity: full."""

OKABE_ITO: dict[str, tuple[int, int, int]] = {
    "orange": (230, 159, 0),
    "sky": (86, 180, 233),
    "bluegreen": (0, 158, 115),
    "yellow": (240, 228, 66),
    "blue": (0, 114, 178),
    "vermillion": (213, 94, 0),
    "purple": (204, 121, 167),
}
"""Okabe and Ito (2008) Color Universal Design palette, the chromatic members."""

_BYTE = 255.0
_TRIPLE = (3,)
_FAR = 1e9
_TRICHROMAT = "trichromat"
_SPACE = "CAM02-UCS"
_UCS_MEMO: dict[tuple[tuple[float, float, float], str | None], ndarray] = {}
_FLOOR_MEMO: dict[str, tuple[float, str, str, str]] = {}


def _source(cvd: str | None) -> str | dict[str, object]:
    """Name the colorspacious source space for a view.

    Returns:
        plain sRGB1 for the trichromat view, else the CVD simulation spec at full severity.

    """
    if cvd is None:
        return "sRGB1"
    return {"name": "sRGB1+CVD", "cvd_type": cvd, "severity": SEVERITY}


def _ucs_one(rgb255: tuple[float, float, float], cvd: str | None) -> ndarray:
    """Convert one colour to CAM02-UCS, memoised on the exact float triple.

    ⚑ RENDER-SPEED (el-openglo #3b): a pure conversion; the palette re-asks the same few colours
    thousands of times (11,616 conversions per main_qml before this memo).

    Returns:
        the colour in CAM02-UCS under the view; `_ucs` hands callers a copy.

    """
    key = (rgb255, cvd)
    known = _UCS_MEMO.get(key)
    if known is not None:
        return known
    made = cspace_convert(np.asarray(rgb255, dtype=float) / _BYTE, _source(cvd), _SPACE)
    _UCS_MEMO[key] = made
    return made


def _ucs(rgb255: Sequence[float] | ndarray, cvd: str | None) -> ndarray:
    """Convert a colour, or an array of colours, to CAM02-UCS under a view.

    Returns:
        the converted colour; a single triple is served from the memo as a COPY, so a caller that
        mutates the result cannot poison it.

    """
    colour = np.asarray(rgb255, dtype=float)
    if colour.shape == _TRIPLE:
        red, green, blue = colour.tolist()
        return _ucs_one((red, green, blue), cvd).copy()
    return cspace_convert(colour / _BYTE, _source(cvd), _SPACE)


def worst_view_dE(a: Sequence[float], b: Sequence[float]) -> tuple[float, str]:
    """Measure the minimum CAM02-UCS distance between two colours over the four views.

    Returns:
        (distance, view): the smallest distance and the view that collapses the pair.

    """
    best = (_FAR, "none")
    for view in VIEWS:
        distance = float(np.linalg.norm(_ucs(a, view) - _ucs(b, view)))
        if distance < best[0]:
            best = (distance, view or _TRICHROMAT)
    return best


def reference_floor() -> tuple[float, str, str, str]:
    """Find the tightest worst-view separation inside the Okabe-Ito palette.

    Memoised: a constant of the module-level `OKABE_ITO` table, recomputed per call before (168
    conversions each).

    Returns:
        (distance, first name, second name, collapsing view).

    """
    known = _FLOOR_MEMO.get("floor")
    if known is not None:
        return known
    names = list(OKABE_ITO)
    floor = (_FAR, "", "", "")
    for i, first in enumerate(names):
        for second in names[i + 1 :]:
            distance, view = worst_view_dE(OKABE_ITO[first], OKABE_ITO[second])
            if distance < floor[0]:
                floor = (distance, first, second, view)
    _FLOOR_MEMO["floor"] = floor
    return floor


def reference_floors() -> dict[str, float]:
    """Give the Okabe-Ito floor keyed by pair class.

    ⚑ Consumers want the floor keyed by class, not as one scalar: `reference_floor()` returns the
    single tightest pair, this returns the floor each class is judged against. They are NOT
    interchangeable: an earlier repair rewrote a caller of this into `reference_floor()[0]` and so
    silently changed which number the gate used.

    Returns:
        {class: floor}, both classes at the one number.

    """
    floor = reference_floor()[0]
    return {"enforced": floor, "surfaced": floor}


def rgb(text: str) -> tuple[int, ...]:
    """Parse a comma-separated colour.

    Returns:
        the integers of `text`, e.g. `"1,2,3"` is `(1, 2, 3)`.

    """
    return tuple(int(part) for part in text.split(","))
