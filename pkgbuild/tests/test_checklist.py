# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that the adopter's checklist is filled in from the wheel, and nothing is invented.

W1136. ⚑ THE VALUES ARE READ: the name from the wheel's file name (normalized, underscores
and dots become hyphens), the hash from its bytes, the path absolute. ⚑ THE CONTROLS: a file
that is not a wheel by name, a wheel that is not there, a flag with no value and an extra operand
each exit 2 and print nothing to standard output.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from mikemol.pkgbuild import checklist

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_USAGE = 2
_NAME = "mikemol_demo_tool-0.1.0+gabc1234-py3-none-any.whl"


def _wheel(tmp_path: Path) -> Path:
    path = tmp_path / _NAME
    path.write_bytes(b"wheel bytes")
    return path


def test_the_name_is_normalized_from_the_file_name(tmp_path: Path) -> None:
    """Underscores become hyphens and the case is folded; a name that is no wheel's is None."""
    folded = checklist.dist_of(tmp_path / "Mikemol_Demo.Tool-0.1.0-py3-none-any.whl")
    assert folded == "mikemol-demo-tool"
    assert checklist.dist_of(tmp_path / "mikemol_demo-0.1.0.tar.gz") is None
    assert checklist.dist_of(tmp_path / "mikemol_demo-0.1.0.whl") is None


def test_the_three_steps_carry_the_real_hash_the_absolute_path_and_the_hub(tmp_path: Path) -> None:
    """The requirement line, the lock hash and command, and the underscored pip target."""
    wheel = _wheel(tmp_path)
    lines = checklist.checklist(wheel, dict(checklist.DEFAULTS, **{"--hub": "checks_pip"}))
    text = "\n".join(lines)
    assert f"mikemol-demo-tool @ file://{wheel.absolute()}" in text
    assert f"--hash=sha256:{hashlib.sha256(b'wheel bytes').hexdigest()}" in text
    assert "uv pip compile --offline --generate-hashes --python-version 3.13" in text
    assert '"@checks_pip//mikemol_demo_tool"' in text


def test_the_command_prints_the_steps_with_the_given_flags(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Flags change the file names and the Python version in the printed command."""
    wheel = _wheel(tmp_path)
    flags = ["--in", "a.in", "--out", "a.lock", "--python", "3.14"]
    assert checklist.run([str(wheel), *flags]) == 0
    out = capsys.readouterr().out
    assert "add to a.in:" in out
    assert "--python-version 3.14 a.in -o a.lock" in out


def test_a_non_wheel_a_missing_file_a_dangling_flag_and_an_extra_operand_are_usage_errors(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Each exits 2 and writes nothing to standard output."""
    wheel = _wheel(tmp_path)
    assert checklist.run([str(tmp_path / "pkg-0.1.0.tar.gz")]) == _USAGE
    assert checklist.run([str(tmp_path / "mikemol_x-0.1.0-py3-none-any.whl")]) == _USAGE
    assert checklist.run([str(wheel), "--hub"]) == _USAGE
    assert checklist.run([str(wheel), str(wheel)]) == _USAGE
    assert checklist.run([]) == _USAGE
    assert not capsys.readouterr().out
