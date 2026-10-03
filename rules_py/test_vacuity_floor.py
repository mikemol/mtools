# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""vacuity_floor over hand-built test modules: a count at the floor passes, one below it fails."""

from __future__ import annotations

from typing import TYPE_CHECKING

import vacuity_floor

if TYPE_CHECKING:
    from pathlib import Path

_TWO_NEGATIVES = (
    "def test_x() -> None:\n"
    "    swept = list(range(3))\n"
    "    offenders = [p for p in swept if p > 5]\n"
    "    assert not offenders\n"
    "    strays = sorted(swept)\n"
    "    assert not strays\n"
    "    assert swept\n"
)
_VERDICT_ONLY = "def test_y() -> None:\n    fired = analyze('ls')\n    assert not fired\n"
_COUNT = 2


def _modules(root: Path) -> list[Path]:
    a = root / "a" / "tests" / "test_a.py"
    b = root / "b" / "tests" / "test_b.py"
    for path, text in ((a, _TWO_NEGATIVES), (b, _VERDICT_ONLY)):
        path.parent.mkdir(parents=True)
        path.write_text(text, encoding="utf-8")
    return [a, b]


def test_negatives_are_counted_over_the_union(tmp_path: Path) -> None:
    """Every module is swept and each member is named; a verdict call is not one."""
    members = vacuity_floor.negatives(_modules(tmp_path))
    assert len(members) == _COUNT
    assert all("test_a.py" in m for m in members)


def test_floor_at_the_count_passes_and_above_it_fails(tmp_path: Path) -> None:
    """0 when the union clears the floor, 1 below it, 2 on a usage error."""
    modules = [str(m) for m in _modules(tmp_path)]
    codes = [
        vacuity_floor.main([str(_COUNT), *modules]),
        vacuity_floor.main([str(_COUNT + 1), *modules]),
        vacuity_floor.main([str(_COUNT)]),
        vacuity_floor.main(["x", *modules]),
    ]
    assert codes == [0, 1, 2, 2]
