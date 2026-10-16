# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The fleet's EXIT_ constants agree with the exit table, or are listed in the shrinking baseline.

W1298 (of W1295). The sibling dists' sources arrive as this target's runfiles, through its deps on
their libraries, so the census reads the same files a commit would ship. Every arm needs a
positive control: an empty runfiles tree would otherwise read as "no violations".
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from mikemol.corpus import exitcensus

_ROOT = Path(__file__).parents[2]
_DISTS = ("fence", "pathsforward", "hooks", "katas", "waldo")
_TABLE = _ROOT / "corpus" / "exit-table.json"
_BASELINE = _ROOT / "corpus" / "exit-baseline.txt"
_MINIMUM = 40


def _args() -> list[str]:
    return [str(_TABLE), *(str(_ROOT / dist) for dist in _DISTS)]


def test_the_runfiles_hold_enough_constants_to_make_a_pass_mean_something() -> None:
    """The positive control: the census sees dozens of constants, so a pass is not empty."""
    doc = cast("object", json.loads(_TABLE.read_text(encoding="utf-8")))
    rows = exitcensus.census([_ROOT / dist for dist in _DISTS], exitcensus.table_of(doc))
    assert len(rows) >= _MINIMUM


def test_no_new_disagreement_with_the_exit_table_and_no_fixed_one_left_listed() -> None:
    """The gate: the baseline equals today's violations, so it can only shrink."""
    assert exitcensus.main(["--baseline", str(_BASELINE), *_args()]) == 0
