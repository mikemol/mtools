# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the judge's measurement seam and the ruff measure that plugs into it.

W1045. ⚑ THE DEFAULT IS THE POSITIVE CONTROL: with no measure the judge still asks mypy, so the
seam is a parameter, not a replacement; the ruff measure is then checked against its own failure
(a ruff that cannot run is a reason, never an empty count) and against the shared acceptance rule
(strictly fewer, no new message).
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.pycodemod.cli_typedargs import judge
from mikemol.pycodemod.measure import ruff_measure

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mikemol.pycodemod.cli_typedargs import Verdict

_BROKEN = 2
_ORIGINAL = "orig\n"
_BETTER = "better\n"
_WORSE = "worse\n"
_NAME = "mod.py"
_D205 = {"code": "D205", "message": "1 blank line required"}
_E501 = {"code": "E501", "message": "line too long"}
_FOUND = {_ORIGINAL: [_D205, _D205], _BETTER: [_D205], _WORSE: [_D205, _E501]}


class _Tools:
    """A stand-in for ruff and mypy: a file's text decides which findings are reported."""

    def __init__(self, ruff_exit: int = 1) -> None:
        self.calls: list[list[str]] = []
        self.ruff_exit = ruff_exit

    def __call__(self, argv: Sequence[str], cwd: Path) -> tuple[int, str, str]:
        self.calls.append(list(argv))
        if argv[0].endswith("mypy"):
            return 0, "", ""
        if "--select" in argv and "--isolated" in argv:
            if self.ruff_exit not in {0, 1}:
                return self.ruff_exit, "", "ruff is broken"
            text = (cwd / argv[-1]).read_text(encoding="utf-8")
            return 1, json.dumps(_FOUND.get(text, [])), ""
        return 0, "", ""


def _judged(tmp_path: Path, tools: _Tools, candidate: str) -> Verdict:
    """Judge a candidate under the ruff measure.

    Returns:
        the judge's verdict.

    """
    return judge(tmp_path, Path(_NAME), (_ORIGINAL, candidate), tools, ruff_measure("D205,E501"))


def test_the_ruff_measure_counts_code_and_message_per_finding(tmp_path: Path) -> None:
    """Two findings of one rule are a count of two under one key."""
    (tmp_path / _NAME).write_text(_ORIGINAL, encoding="utf-8")
    counted = ruff_measure("D205")(tmp_path, Path(_NAME), _Tools())
    assert counted == Counter({"D205: 1 blank line required": 2})


def test_the_ruff_measure_asks_the_selected_rules_in_isolation(tmp_path: Path) -> None:
    """The project's own configuration cannot exempt the rule being counted."""
    (tmp_path / _NAME).write_text(_ORIGINAL, encoding="utf-8")
    tools = _Tools()
    ruff_measure("D205,D209")(tmp_path, Path(_NAME), tools)
    argv = tools.calls[0]
    assert argv[argv.index("--select") + 1] == "D205,D209"
    assert "--isolated" in argv


def test_a_ruff_that_cannot_run_is_a_reason_not_an_empty_count(tmp_path: Path) -> None:
    """Exit 2 comes back as text naming the exit and ruff's complaint."""
    (tmp_path / _NAME).write_text(_ORIGINAL, encoding="utf-8")
    counted = ruff_measure("D205")(tmp_path, Path(_NAME), _Tools(ruff_exit=_BROKEN))
    assert counted == "ruff could not run (exit 2): ruff is broken"


def test_a_clean_file_counts_as_nothing(tmp_path: Path) -> None:
    """No findings is an empty count, which is not the same thing as a failure."""
    (tmp_path / _NAME).write_text("clean\n", encoding="utf-8")
    assert ruff_measure("D205")(tmp_path, Path(_NAME), _Tools()) == Counter()


def test_the_judge_accepts_a_candidate_with_strictly_fewer_findings(tmp_path: Path) -> None:
    """Two D205 findings down to one is accepted under the ruff measure."""
    verdict = _judged(tmp_path, _Tools(), _BETTER)
    assert (verdict.ok, verdict.before, verdict.after, verdict.new) == (True, 2, 1, [])


def test_the_judge_rejects_a_fix_that_trades_for_a_new_finding(tmp_path: Path) -> None:
    """The same count of D205 plus a new E501 is refused and the new message named."""
    verdict = _judged(tmp_path, _Tools(), _WORSE)
    assert verdict.ok is False
    assert verdict.new == ["E501: line too long"]


def test_the_probe_is_removed_whatever_the_verdict(tmp_path: Path) -> None:
    """Nothing the judge wrote stays in the project."""
    _judged(tmp_path, _Tools(), _BETTER)
    assert list(tmp_path.iterdir()) == []


def test_no_measure_still_asks_mypy(tmp_path: Path) -> None:
    """The default: the seam is a parameter, so typed-args and its kin are unchanged."""
    tools = _Tools()
    judge(tmp_path, Path(_NAME), (_ORIGINAL, _BETTER), tools)
    assert any(call[0].endswith("mypy") for call in tools.calls)
