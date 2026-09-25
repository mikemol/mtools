# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.ledger.finding_mode`: substrate's suite, and the letter's §3.2.

⚑⚑⚑ THE ONE-GREEN-PATH PROPERTY IS ASSERTED AS A PROPERTY: every reachable state is driven and
exactly one is CLOSED. A case checking only the documented path would pass against a reader
returning CLOSED for everything.

⚑⚑ THE DELETED CASE IS THE LOAD-BEARING ONE: a GONE mode is OPEN, and distinguishable by message
from one that still dispatches.

⚑ THE LENSES ARE INJECTED, NEVER PATCHED, so nothing survives from one case into the next.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Protocol, cast

import pytest

from mikemol.ledger import finding_kinds, finding_mode
from mikemol.ledger.finding_kinds import CLOSED, OPEN, UNRUNNABLE

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from mikemol.ledger.finding_kinds import Verdict

Lens = tuple[int | None, str]

# ⚑ COLUMN-ALIGNED ON PURPOSE: a variable run of spaces is what defeated the original substring.
_DIVERGENCE_ROWS = """\
── scratch/mdstruct.py
  UNDOCUMENTED     --rows        dispatched on argv
  UNDOCUMENTED  --spans   dispatched on argv
── scratch/toolmodes.py
  UNDOCUMENTED   --sync    dispatched on argv
"""

# ⚑ THE `NOT on:` LINE IS THIS FIXTURE'S WHOLE VALUE: a name-only test matches the negative list.
_FIND_DECLARED = """\
  --budget  on scratch/mdstruct.py  [usage]  the per-section byte budget
  ⚑ NOT on: scratch/toolmodes.py, scratch/pycodemod.py
"""
_FIND_BARE = "  --budget  on scratch/mdstruct.py\n"
_FIND_ELSEWHERE = """\
  --budget  on scratch/pycodemod.py  [usage]  a different tool entirely
  ⚑ NOT on: scratch/mdstruct.py
"""
_FIND_NONE = "  --nosuch is declared by NO tool\n"
_DIVERGENCE_BUDGET = _DIVERGENCE_ROWS.replace("--rows", "--budget")

_TOOL = "scratch/mdstruct.py"
_STEM = "mdstruct.py"
_DIVERGENCE = ("lens", "--divergence")
_FIND = ("lens", "--find")

# A real lens: prints the declared find rows when asked to find, and nothing when asked to diverge.
_LENS_SCRIPT = f"import sys\nprint({_FIND_DECLARED!r} if '--find' in sys.argv else '')\n"


class _ModeWithoutLenses(Protocol):
    """`mode_undocumented` as a caller who supplied no lenses would call it."""

    def __call__(self, tool: str, mode: str) -> Verdict: ...


def _drive(divergence: Lens, find: Lens) -> Verdict:
    """Run the verdict against two stubbed lenses, injected rather than patched.

    Returns:
        the verdict.

    """

    def lens(cmd: Sequence[str]) -> Lens:
        return find if "--find" in cmd else divergence

    return finding_mode.mode_undocumented(
        _TOOL, "--budget", divergence=_DIVERGENCE, find=_FIND, runner=lens
    )


def test_the_divergence_reader_finds_rows_however_they_are_spaced() -> None:
    """Widely and narrowly spaced UNDOCUMENTED rows are found; a mode in no row is absent."""
    assert finding_mode.diverges(_DIVERGENCE_ROWS, _STEM, "--rows")
    assert finding_mode.diverges(_DIVERGENCE_ROWS, _STEM, "--spans")
    assert not finding_mode.diverges(_DIVERGENCE_ROWS, _STEM, "--budget")


def test_a_row_under_another_tool_does_not_answer_for_this_one() -> None:
    """The block structure is load-bearing: `--sync` belongs to toolmodes.py, not mdstruct.py."""
    assert not finding_mode.diverges(_DIVERGENCE_ROWS, _STEM, "--sync")
    assert finding_mode.diverges(_DIVERGENCE_ROWS, "toolmodes.py", "--sync")


def test_the_declaration_reader_resolves_this_tools_source() -> None:
    """A declaration by THIS tool resolves to its source; a sourceless row says so."""
    assert finding_mode.declared_by(_FIND_DECLARED, _STEM, "--budget") == "[usage]"
    assert finding_mode.declared_by(_FIND_BARE, _STEM, "--budget") == finding_mode.UNSTATED
    assert finding_mode.declared_by(_FIND_NONE, _STEM, "--nosuch") is None


def test_a_tool_named_only_in_the_not_on_line_is_not_a_declarer() -> None:
    """THE NEGATIVE-LIST ARM: `mdstruct.py` in `NOT on:` is not a declaration by it."""
    assert finding_mode.declared_by(_FIND_ELSEWHERE, _STEM, "--budget") is None
    assert finding_mode.declared_by(_FIND_ELSEWHERE, "pycodemod.py", "--budget") is not None


def test_each_outcome_and_exactly_one_green_path() -> None:
    """Dispatching and GONE are OPEN and distinct; declared is CLOSED; a dead lens is UNRUNNABLE.

    ⚑⚑⚑ EXACTLY ONE DRIVEN OUTCOME IS CLOSED — the property the polarity probe rests on.
    """
    dispatches = _drive((0, _DIVERGENCE_BUDGET), (0, _FIND_NONE))
    documented = _drive((0, ""), (0, _FIND_DECLARED))
    deleted = _drive((0, ""), (0, _FIND_NONE))
    no_divergence = _drive((None, "boom"), (0, _FIND_DECLARED))
    no_find = _drive((0, ""), (None, "boom"))
    assert dispatches[0] == OPEN
    assert "no self-description" in dispatches[1]
    assert documented == (CLOSED, f"{_STEM} --budget is DOCUMENTED — declared [usage]")
    assert deleted[0] == OPEN
    assert "GONE" in deleted[1]
    assert deleted[1] != dispatches[1]
    assert no_divergence[0] == UNRUNNABLE
    assert no_find[0] == UNRUNNABLE
    assert "cannot be distinguished" in no_find[1]
    every = [dispatches, documented, deleted, no_divergence, no_find]
    assert [code for code, _ in every].count(CLOSED) == 1


def test_the_lenses_are_the_callers_with_no_default() -> None:
    """No substrate lens remains, and a call without lenses is a TypeError: THE LETTER'S §3.2."""
    assert not hasattr(finding_mode, "DIVERGENCE")
    assert not hasattr(finding_mode, "FIND")
    unsupplied = cast("_ModeWithoutLenses", finding_mode.mode_undocumented)
    with pytest.raises(TypeError, match="divergence"):
        unsupplied(_TOOL, "--budget")


def test_the_callers_lens_argvs_are_what_run() -> None:
    """The divergence argv runs as given, and the find argv runs with the mode appended."""
    ran: list[tuple[str, ...]] = []

    def lens(cmd: Sequence[str]) -> Lens:
        ran.append(tuple(cmd))
        return 0, ""

    finding_mode.mode_undocumented(
        _TOOL, "--budget", divergence=_DIVERGENCE, find=_FIND, runner=lens
    )
    assert ran == [_DIVERGENCE, (*_FIND, "--budget")]


def test_the_ledgers_own_runner_composes_with_a_real_lens(tmp_path: Path) -> None:
    """`finding_kinds.runner_in(cwd)` drives a real lens script to a DOCUMENTED verdict."""
    (tmp_path / "lens.py").write_text(_LENS_SCRIPT, encoding="utf-8")
    code, _ = finding_mode.mode_undocumented(
        _TOOL,
        "--budget",
        divergence=(sys.executable, "lens.py", "--divergence"),
        find=(sys.executable, "lens.py", "--find"),
        runner=finding_kinds.runner_in(tmp_path),
    )
    assert code == CLOSED
