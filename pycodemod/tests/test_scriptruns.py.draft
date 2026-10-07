# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `by-path-runs`: a package script run by path becomes a module run by package."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.pycodemod import cli_scriptruns, scriptruns

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def _write(tmp_path: Path, text: str) -> str:
    path = tmp_path / "step.sh"
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_every_spelling_of_the_interpreter_is_a_run(tmp_path: Path) -> None:
    """⚑ Bare, quoted, `$(command -v …)` and a flagged interpreter all read as runs."""
    path = _write(
        tmp_path,
        'python3 tools/a.py x\n"$PY" tools/b.py\n"$(command -v python3)" tools/c.py\n'
        "python3 -u ./tools/d.py\n",
    )
    found = scriptruns.scan([path], ["tools"])
    assert [r.script for r in found.runs] == [
        "tools/a.py",
        "tools/b.py",
        "tools/c.py",
        "./tools/d.py",
    ]
    assert found.mentions == []


def test_a_mention_is_reported_and_never_rewritten(tmp_path: Path) -> None:
    """⚑⚑ A name in a comment is not a run: it is listed beside the runs and left as written."""
    path = _write(tmp_path, "# see tools/a.py for why\npython3 tools/b.py\n")
    found = scriptruns.scan([path], ["tools"])
    assert [r.script for r in found.runs] == ["tools/b.py"]
    assert [m.script for m in found.mentions] == ["tools/a.py"]
    assert found.texts[path] == "# see tools/a.py for why\npython3 -m tools.b\n"


def test_a_script_outside_the_named_packages_is_left_alone(tmp_path: Path) -> None:
    """⚑ Only the packages named are known; another directory's script is nobody's business here."""
    path = _write(tmp_path, "python3 scripts/z.py\n")
    found = scriptruns.scan([path], ["tools"])
    assert found.runs == []
    assert found.texts == {}


def test_a_write_leaves_no_run_and_says_so(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """⚑⚑ After a write the census runs again over the new text, and it must be empty."""
    path = _write(tmp_path, 'cd "$D" && python3 paperkit/gate.py --safe\n')
    flags = cli_scriptruns.RunFlags(packages=("paperkit",), write=True)
    assert cli_scriptruns.print_runs([path], flags) == 0
    assert "0 runs remain" in capsys.readouterr().out
    assert (tmp_path / "step.sh").read_text(encoding="utf-8") == (
        'cd "$D" && python3 -m paperkit.gate --safe\n'
    )
