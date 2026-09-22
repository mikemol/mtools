# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The shell hook's maintainer modes: what each reports, and that could-not-look is never clean.

⚑ EVERY MODE IS DRIVEN THROUGH `main(argv)`, the entry the console script calls, so an arm cannot
pass on a function the command line never reaches.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.hooks import shellcheck, shellcheck_cli

if TYPE_CHECKING:
    from pathlib import Path

# The exit code that means "could not look" — distinct from 0 (clean) and 1 (findings).
_COULD_NOT_LOOK = 2

_needs_linter = pytest.mark.skipif(
    shellcheck.linter() is None, reason="no shellcheck on PATH or at the mise shim")


def _absent(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Make the linter unfindable: an empty PATH and a shim that does not exist."""
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    monkeypatch.setattr(shellcheck, "MISE_SHIM", tmp_path / "no-shim")


def _script(tmp_path: Path, name: str, body: str) -> Path:
    """Write one file under a fixture tree and return its path.

    Returns:
        the written path.

    """
    path = tmp_path / "tree" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_a_non_shell_file_reports_not_shell_and_exits_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A python file is NOT SHELL, a different fact from clean, and exits 0."""
    path = _script(tmp_path, "x.py", "print(1)\n")
    assert shellcheck_cli.main(["--check-file", str(path)]) == 0
    assert "NOT SHELL" in capsys.readouterr().out


def test_an_unreadable_file_exits_two(tmp_path: Path) -> None:
    """A path that cannot be read exits 2 — the could-not-look code."""
    assert shellcheck_cli.main(["--check-file", str(tmp_path / "missing.sh")]) == _COULD_NOT_LOOK


def test_a_shell_file_with_no_linter_exits_two(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A shell file the linter cannot judge exits 2, never 0 as the origin did."""
    path = _script(tmp_path, "run.sh", "echo $x\n")
    _absent(monkeypatch, tmp_path)
    assert shellcheck_cli.main(["--check-file", str(path)]) == _COULD_NOT_LOOK


def test_a_tree_with_no_linter_exits_two(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A census that cannot lint a shell file is UNKNOWN, not a clean count."""
    _script(tmp_path, "run.sh", 'echo "hi"\n')
    _absent(monkeypatch, tmp_path)
    assert shellcheck_cli.main(["--check-tree", str(tmp_path / "tree")]) == _COULD_NOT_LOOK
    assert "shell files:" not in capsys.readouterr().out


def test_explain_with_no_linter_exits_two(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Explaining a command the linter cannot judge exits 2."""
    _absent(monkeypatch, tmp_path)
    assert shellcheck_cli.main(["--explain", "echo $x"]) == _COULD_NOT_LOOK


def test_no_mode_is_a_usage_error() -> None:
    """With no mode the tool refuses rather than guessing one."""
    with pytest.raises(SystemExit) as exc:
        shellcheck_cli.main([])
    assert exc.value.code == _COULD_NOT_LOOK


@pytest.mark.needs_shellcheck
@_needs_linter
def test_a_file_with_a_finding_exits_one_and_names_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A shell file with a defect exits 1 and prints the rule."""
    path = _script(tmp_path, "run.sh", "#!/bin/bash\necho $1\n")
    assert shellcheck_cli.main(["--check-file", str(path)]) == 1
    assert "SC2086" in capsys.readouterr().out


@pytest.mark.needs_shellcheck
@_needs_linter
def test_a_clean_file_exits_zero(tmp_path: Path) -> None:
    """A clean shell file exits 0 — the arm that makes exit 1 mean something."""
    path = _script(tmp_path, "run.sh", '#!/bin/bash\necho "hi"\n')
    assert shellcheck_cli.main(["--check-file", str(path)]) == 0


@pytest.mark.needs_shellcheck
@_needs_linter
def test_a_tree_census_counts_its_population(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The census reports N shell files and M with findings, skipping non-shell and VCS dirs."""
    _script(tmp_path, "bad.sh", "#!/bin/bash\necho $1\n")
    _script(tmp_path, "good.sh", '#!/bin/bash\necho "hi"\n')
    _script(tmp_path, "notes.py", "print(1)\n")
    _script(tmp_path, ".git/hook.sh", "echo $1\n")
    assert shellcheck_cli.main(["--check-tree", str(tmp_path / "tree")]) == 1
    assert "shell files: 2   with findings: 1" in capsys.readouterr().out


@pytest.mark.needs_shellcheck
@_needs_linter
def test_a_file_honours_its_trees_waiver(tmp_path: Path) -> None:
    """A dated waiver in the governing pyproject clears the file — the mode reads the tree's set."""
    path = _script(tmp_path, "run.sh", "#!/bin/bash\necho $1\n")
    (tmp_path / "tree" / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\n\n[tool.mikemol-hooks.shellcheck.exclude]\n'
        'SC2086 = "word splitting is intended at this site, measured 2026-09-22"\n',
        encoding="utf-8",
    )
    assert shellcheck_cli.main(["--check-file", str(path)]) == 0


@pytest.mark.needs_shellcheck
@_needs_linter
def test_explain_reports_a_finding_and_exits_one(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Explaining a defective command exits 1 and names the rule."""
    monkeypatch.chdir(tmp_path)
    assert shellcheck_cli.main(["--explain", "[ $x = y ]"]) == 1
    assert "SC2086" in capsys.readouterr().out


@pytest.mark.needs_shellcheck
@_needs_linter
def test_explain_of_clean_shell_exits_zero(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Explaining clean shell exits 0."""
    monkeypatch.chdir(tmp_path)
    assert shellcheck_cli.main(["--explain", 'echo "hi"']) == 0
