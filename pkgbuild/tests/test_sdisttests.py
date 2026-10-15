# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that `sdist-tests` extracts each sdist, installs its wheel and runs its own tests.

W1147. ⚑ THE RUNNER IS A FAKE that records each command with its working directory, so the venv
and pip are never started here; the real run over the 34 built dists is the measurement. ⚑ THE
CONTROLS: an install that fails is its own stage, a dist with no tests is not a failure, a folder
without exactly one sdist and one wheel is, and the wheels of every dist are in the link directory
when pip is asked (a sibling dependency resolves from there, not from the host).
"""

from __future__ import annotations

import io
import json
import tarfile
from pathlib import Path
from typing import TYPE_CHECKING, cast

from mikemol.pkgbuild import sdisttests

if TYPE_CHECKING:
    from collections.abc import Sequence

    import pytest

Row = dict[str, object]
_USAGE = 2
_PASSED = 16
_THREE = 3


class _Fake:
    """A fake command runner: records argv and cwd, answers by what the command is."""

    def __init__(self, *, pip: int = 0, tests: tuple[int, str] = (0, "16 passed in 0.14s")) -> None:
        self.pip = pip
        self.tests = tests
        self.calls: list[tuple[list[str], Path]] = []
        self.linked: list[str] = []

    def __call__(self, argv: Sequence[str], cwd: Path) -> tuple[int, str]:
        self.calls.append((list(argv), cwd))
        if "pip" in argv:
            links = Path(argv[argv.index("--find-links") + 1])
            self.linked = sorted(p.name for p in links.iterdir())
            return self.pip, "pip said no" if self.pip else ""
        if "pytest" in argv and "-m" in argv and argv[argv.index("-m") + 1] == "pytest":
            return self.tests
        return 0, ""


def _folder(out: Path, name: str, *, tests: bool = True, project: str = "") -> Path:
    folder = out / name
    folder.mkdir(parents=True)
    with tarfile.open(folder / f"mikemol_{name}-0.1.0.tar.gz", "w:gz") as archive:
        marker = tarfile.TarInfo(f"mikemol_{name}-0.1.0/pyproject.toml")
        marker.size = len(project.encode())
        archive.addfile(marker, io.BytesIO(project.encode()))
        if tests:
            test = tarfile.TarInfo(f"mikemol_{name}-0.1.0/tests/test_x.py")
            test.size = 0
            archive.addfile(test, io.BytesIO(b""))
    (folder / f"mikemol_{name}-0.1.0-py3-none-any.whl").write_bytes(b"wheel")
    return folder


def _rows(capsys: pytest.CaptureFixture[str]) -> dict[str, Row]:
    lines = capsys.readouterr().out.splitlines()
    rows = [cast("Row", json.loads(line)) for line in lines]
    return {str(r["dist"]): r for r in rows}


def test_pytest_counts_are_read_from_the_last_lines() -> None:
    """passed, failed, error(s) and skipped are each found; text before them is ignored."""
    assert sdisttests.counts_of("noise\n16 passed in 0.14s") == {"passed": _PASSED}
    got = sdisttests.counts_of("x\n3 failed, 5 passed, 2 skipped in 1s")
    assert got == {"failed": 3, "passed": 5, "skipped": 2}
    assert sdisttests.counts_of("1 error in 0.1s") == {"error": 1}


def test_a_dist_installs_its_wheel_beside_the_sibling_wheels_and_runs_its_extracted_tests(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """venv, then pip with --find-links over every wheel, then pytest from the extracted tree."""
    out = tmp_path / "out"
    _folder(out, "alpha")
    _folder(out, "beta")
    fake = _Fake()
    assert sdisttests.run([str(out), "alpha"], fake) == 0
    row = _rows(capsys)["alpha"]
    assert (row["ok"], row["passed"]) == (True, _PASSED)
    assert fake.linked == [
        "mikemol_alpha-0.1.0-py3-none-any.whl",
        "mikemol_beta-0.1.0-py3-none-any.whl",
    ]
    venv, pip, tests = (call for call, _ in fake.calls)
    assert venv[1:3] == ["-m", "venv"]
    assert pip[-1] == "pytest"
    assert pip[-2].endswith("mikemol_alpha-0.1.0-py3-none-any.whl")
    assert "tests" in tests
    assert "faulthandler_timeout=60" in tests
    assert fake.calls[2][1].name == "mikemol_alpha-0.1.0"


def test_an_install_that_fails_is_reported_as_the_install_stage_and_no_test_runs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The control: pip exits 1, so the row says `install` with its output and pytest is not run."""
    out = tmp_path / "out"
    _folder(out, "alpha")
    fake = _Fake(pip=1)
    assert sdisttests.run([str(out)], fake) == 1
    row = _rows(capsys)["alpha"]
    assert (row["ok"], row["stage"], row["detail"]) == (False, "install", "pip said no")
    assert len(fake.calls) == _USAGE


def test_failing_tests_make_the_run_exit_one_with_their_tail(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A red suite is `ok` false with the counts and the tail of its output."""
    out = tmp_path / "out"
    _folder(out, "alpha")
    assert sdisttests.run([str(out)], _Fake(tests=(1, "boom\n2 failed, 4 passed in 1s"))) == 1
    row = _rows(capsys)["alpha"]
    assert (row["ok"], row["failed"], row["passed"]) == (False, _USAGE, 4)
    assert "boom" in str(row["detail"])


def test_a_dist_without_tests_is_not_a_failure_and_a_malformed_folder_is(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """No tests directory: ok with a note. Two sdists: not ok."""
    out = tmp_path / "out"
    _folder(out, "plain", tests=False)
    twice = _folder(out, "twice")
    (twice / "extra-0.2.tar.gz").write_bytes(b"x")
    assert sdisttests.run([str(out)], _Fake()) == 1
    rows = _rows(capsys)
    assert rows["plain"]["ok"] is True
    assert rows["plain"]["detail"] == "no tests directory"
    assert rows["twice"]["ok"] is False


_DEV = '[dependency-groups]\ndev = ["pytest", "mypy", "ruff==0.16.6", "setuptools>=77", "twine"]\n'


def test_the_declared_dev_group_is_read_without_the_lint_tools(tmp_path: Path) -> None:
    """Everything declared rides along but pytest, which is always there; a bad file gives none."""
    tree = tmp_path / "tree"
    tree.mkdir()
    (tree / "pyproject.toml").write_text(_DEV, encoding="utf-8")
    assert sdisttests.dev_requirements(tree) == ["mypy", "ruff==0.16.6", "setuptools>=77", "twine"]
    (tree / "pyproject.toml").write_text("[[[", encoding="utf-8")
    assert sdisttests.dev_requirements(tree) == []
    assert sdisttests.dev_requirements(tmp_path / "absent") == []


def test_pip_is_given_the_dev_needs_the_sdist_declares(tmp_path: Path) -> None:
    """The install command names the wheel, pytest, then each declared need."""
    out = tmp_path / "out"
    _folder(out, "alpha", project=_DEV)
    fake = _Fake()
    assert sdisttests.run([str(out)], fake) == 0
    pip = next(call for call, _ in fake.calls if "pip" in call)
    assert pip[-5:] == ["pytest", "mypy", "ruff==0.16.6", "setuptools>=77", "twine"]


def test_tail_sets_how_much_of_a_failure_is_kept_and_a_dangling_tail_is_usage(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--tail 5` keeps the last five characters of a failing run; no number is exit 2."""
    out = tmp_path / "out"
    _folder(out, "alpha")
    fake = _Fake(tests=(1, "0123456789 1 failed"))
    assert sdisttests.run([str(out), "--tail", "5"], fake) == 1
    assert _rows(capsys)["alpha"]["detail"] == "ailed"
    assert sdisttests.run([str(out), "--tail"], fake) == _USAGE
    assert sdisttests.run([str(out), "--tail", "x"], fake) == _USAGE


def test_a_symlinked_folder_is_not_a_dist(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """No symlinks: a link in OUT to a real dist folder is skipped, so the dist is run once."""
    out = tmp_path / "out"
    real = _folder(out, "alpha")
    (out / "link").symlink_to(real, target_is_directory=True)
    assert sdisttests.run([str(out)], _Fake()) == 0
    assert list(_rows(capsys)) == ["alpha"]


def test_the_real_runner_returns_status_and_output_and_a_status_when_it_cannot_start(
    tmp_path: Path,
) -> None:
    """The one seam the fakes replace: a real command's output and status, and a missing program."""
    shell = ["/bin/sh", "-c", "echo out; echo err >&2; exit 3"]
    status, said = sdisttests.run_command(shell, tmp_path)
    assert status == _THREE
    assert "out" in said
    assert "err" in said
    status, said = sdisttests.run_command([str(tmp_path / "absent")], tmp_path)
    assert status == sdisttests.NOT_FOUND
    assert "Error" in said


def test_a_missing_directory_or_no_such_dist_is_a_usage_error(tmp_path: Path) -> None:
    """No argument, a path that is no directory, and a name that matches no folder exit 2."""
    out = tmp_path / "out"
    _folder(out, "alpha")
    assert sdisttests.run([], _Fake()) == _USAGE
    assert sdisttests.run([str(tmp_path / "absent")], _Fake()) == _USAGE
    assert sdisttests.run([str(out), "nope"], _Fake()) == _USAGE
