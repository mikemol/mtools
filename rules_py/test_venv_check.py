# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""venv_check against hand-built venvs: a good one passes, and each defect is named.

The venvs are built in tmp_path from the interpreter running this test: `bin/python3` is an
absolute symlink into a fake toolchain repo, and the distribution's package is put on the import
path through PYTHONPATH, which the checked subprocesses inherit.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

import venv_check

_DIST = "fakedist"
_REPO = "fake_toolchain"


@pytest.fixture()
def venv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Build a venv that satisfies every check: absolute link, note, own package importable.

    Returns:
        the venv directory.

    """
    toolchain = tmp_path / _REPO / "bin"
    toolchain.mkdir(parents=True)
    (toolchain / "python3").symlink_to(sys.executable)
    root = tmp_path / "venv"
    (root / "bin").mkdir(parents=True)
    (root / "bin" / "python3").symlink_to(toolchain / "python3")
    (root / "pythonhome.runfiles").write_text(_REPO + "\n", encoding="utf-8")
    package = tmp_path / "site" / "mikemol" / _DIST
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    monkeypatch.setenv("PYTHONPATH", str(tmp_path / "site"))
    return root


def test_good_venv_has_no_findings(venv: Path) -> None:
    """The positive control: a venv with every property reports nothing."""
    assert venv_check.check(venv, _DIST) == []


def test_missing_interpreter_is_named(tmp_path: Path) -> None:
    """A venv with no bin/python3 is one finding, before anything tries to run it."""
    (tmp_path / "bin").mkdir()
    [finding] = venv_check.check(tmp_path, _DIST)
    assert "no interpreter" in finding


def test_relative_link_is_named(venv: Path) -> None:
    """A relative link is valid at one depth only, so it is a finding even where it resolves."""
    link = venv / "bin" / "python3"
    target = link.readlink()
    link.unlink()
    link.symlink_to(Path("..") / ".." / target.relative_to(target.parents[2]))
    assert any("relative link" in f for f in venv_check.check_link(venv))


def test_missing_pythonhome_note_is_named(venv: Path) -> None:
    """Without pythonhome.runfiles a sandboxed run has no PYTHONHOME, so the note is required."""
    (venv / "pythonhome.runfiles").unlink()
    [finding] = venv_check.check(venv, _DIST)
    assert "pythonhome.runfiles" in finding


def test_note_naming_another_repo_is_named(venv: Path) -> None:
    """The link and the note are two answers to one question, and they must agree."""
    (venv / "pythonhome.runfiles").write_text("other_toolchain\n", encoding="utf-8")
    [finding] = venv_check.check(venv, _DIST)
    assert "other_toolchain" in finding


def test_hardlinked_interpreter_is_accepted(venv: Path) -> None:
    """Under a sandbox bazel stages a regular file, not a link; the note still decides."""
    link = venv / "bin" / "python3"
    link.unlink()
    link.write_bytes(b"\x7fELF")
    assert venv_check.check_link(venv) == []


def test_missing_own_package_is_named(venv: Path) -> None:
    """A venv that runs but cannot import mikemol.<dist> is missing its srcs."""
    [finding] = venv_check.check(venv, "notthere")
    assert "mikemol.notthere" in finding


def test_shell_run_entry_is_named(venv: Path) -> None:
    """A console script with no shebang is run by the shell, and that is a finding."""
    entry = venv / "bin" / "mikemol-fake"
    entry.write_text("import sys\nsys.exit(0)\n", encoding="utf-8")
    entry.chmod(0o755)
    [finding] = venv_check.check_entries(venv, _DIST)
    assert "mikemol-fake" in finding


def test_usage_error_is_exit_2(capsys: pytest.CaptureFixture[str]) -> None:
    """Too few arguments is a usage error, never a pass."""
    assert venv_check.main([]) == 2
    assert "usage" in capsys.readouterr().err
