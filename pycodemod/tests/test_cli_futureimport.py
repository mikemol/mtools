# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `future-import`: a file goes only when the import went and none was left bare.

⚑ THE CONTROL IS THE PLANNER'S MISS: a name in base position is left unquoted by the planner, ruff
reads it as an undefined name at run time, and the judge refuses the file. mypy would have passed
it, which is why the measure is ruff's and not mypy's.
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from mikemol.pycodemod.cli_futureimport import IMPORT_LINE, measure, print_future_import
from mikemol.pycodemod.cli_typedargs import PROBE_PREFIX, TypedArgsFlags

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path

    import pytest

    type Runner = Callable[[Sequence[str], Path], tuple[int, str, str]]

_TAIL = "\n\nclass Later:\n    pass\n"
QUOTABLE = "from __future__ import annotations\n\ndef f(x: Later) -> int:\n    return 1\n" + _TAIL
BASE = 'from __future__ import annotations\n\ndef f(x: Lit["a"] | Later) -> int:\n    return 1\n'
BASE += _TAIL
NAME = "mod.py"
_UNQUOTED = (": Later)", "| Later)")


def _ruff(argv: Sequence[str], cwd: Path) -> tuple[int, str, str]:
    # A stand-in for the project's ruff: the run-time check reports an undefined name for an
    # unquoted forward reference once the future import is gone; sorting and formatting pass.
    if "--select" not in argv or "F821,TC004" not in argv:
        return 0, "", ""
    text = (cwd / argv[-1]).read_text(encoding="utf-8")
    bare = IMPORT_LINE not in text and any(mark in text for mark in _UNQUOTED)
    found = '[{"message": "Undefined name `Later`"}]' if bare else "[]"
    return (1, found, "") if bare else (0, found, "")


def _flags(root: Path, *, write: bool) -> TypedArgsFlags:
    return TypedArgsFlags(root=str(root), write=write)


def test_a_dry_run_names_the_write_and_changes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The import goes and `Later` is quoted, so the judge accepts; the dry run leaves the file."""
    target = tmp_path / NAME
    target.write_text(QUOTABLE, encoding="utf-8")
    assert print_future_import([str(target)], _flags(tmp_path, write=False), _ruff) == 0
    assert target.read_text(encoding="utf-8") == QUOTABLE
    assert "would-write" in capsys.readouterr().out
    assert not list(tmp_path.glob(f"{PROBE_PREFIX}*"))


def test_write_removes_the_import_and_quotes_the_forward_name(tmp_path: Path) -> None:
    """`--write` lands the candidate: no future import, `Later` as a string."""
    target = tmp_path / NAME
    target.write_text(QUOTABLE, encoding="utf-8")
    assert print_future_import([str(target)], _flags(tmp_path, write=True), _ruff) == 0
    written = target.read_text(encoding="utf-8")
    assert "__future__" not in written
    assert 'x: "Later"' in written


def test_a_name_the_planner_cannot_quote_is_refused_and_listed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Base position stays unquoted; ruff's undefined name makes the judge refuse the file."""
    target = tmp_path / NAME
    target.write_text(BASE, encoding="utf-8")
    assert print_future_import([str(target)], _flags(tmp_path, write=True), _ruff) == 1
    assert target.read_text(encoding="utf-8") == BASE
    out = capsys.readouterr().out
    assert f'{target}:3 Lit["a"] | Later: an annotation holding a quote' in out


def test_the_measure_counts_the_import_line_as_a_finding(tmp_path: Path) -> None:
    """With the import present the measure holds one finding."""
    (tmp_path / NAME).write_text(QUOTABLE, encoding="utf-8")
    counted = measure(tmp_path, tmp_path.joinpath(NAME).relative_to(tmp_path), _ruff)
    assert counted == Counter({IMPORT_LINE: 1})
