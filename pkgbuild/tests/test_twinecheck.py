# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the three states of `twinecheck.check` (W1189).

⚑ THE INTERPRETER IS A PARAMETER, so each state is reached by a stub that stands in for the
interpreter: one that exits 0, one that exits 1 with twine's complaint, one that says twine is not
installed, and a path that is no program at all. The real twine against real artifacts is the
integration test in `test_relcheck`.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from mikemol.pkgbuild import twinecheck

if TYPE_CHECKING:
    from pathlib import Path

_OWNER_ONLY = 0o700


def _stub(tmp_path: Path, body: str) -> str:
    """Write an executable Python script that stands in for the interpreter.

    Returns:
        its path.

    """
    script = tmp_path / "stub-python"
    script.write_text(f"#!{sys.executable}\nimport sys\n{body}\n", encoding="utf-8")
    script.chmod(_OWNER_ONLY)
    return str(script)


def test_an_interpreter_that_passes_is_ok_and_gets_the_strict_check_over_every_path(
    tmp_path: Path,
) -> None:
    """Exit 0 is `ok`, and the command is `-m twine check --strict` then the paths in order."""
    stub = _stub(tmp_path, "print(' '.join(sys.argv[1:]))")
    state, text = twinecheck.check([tmp_path / "a.tar.gz", tmp_path / "b.whl"], python=stub)
    assert state == "ok"
    assert text == f"-m twine check --strict {tmp_path / 'a.tar.gz'} {tmp_path / 'b.whl'}"


def test_an_interpreter_that_refuses_is_failed_with_its_output(tmp_path: Path) -> None:
    """Exit 1 is `failed`, and both streams are in the detail so the reason reaches the row."""
    body = "print('out line')\nsys.stderr.write('syntax errors in markup\\n')\nsys.exit(1)"
    state, text = twinecheck.check([tmp_path / "a.whl"], python=_stub(tmp_path, body))
    assert state == "failed"
    assert "out line" in text
    assert "syntax errors" in text


def test_an_interpreter_without_twine_is_unavailable_not_failed_and_not_ok(tmp_path: Path) -> None:
    """The control: absence is its own state, so the caller cannot read it as a pass."""
    stub = _stub(tmp_path, "sys.stderr.write('No module named twine\\n')\nsys.exit(1)")
    state, text = twinecheck.check([tmp_path / "a.whl"], python=stub)
    assert state == "unavailable"
    assert twinecheck.NOT_INSTALLED in text


def test_a_missing_interpreter_is_unavailable(tmp_path: Path) -> None:
    """A path that is no program is an OSError, and also `unavailable`."""
    state, text = twinecheck.check([tmp_path / "a.whl"], python=str(tmp_path / "absent"))
    assert state == "unavailable"
    assert "absent" in text
