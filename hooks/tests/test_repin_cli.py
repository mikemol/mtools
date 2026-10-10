# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the repin shell, over a tree of repos built in the test with a recording runner.

W958. ⚑ THE CLEAN REPO'S SUCCESSFUL REWRITE IS THE POSITIVE CONTROL: the refusals (dirty, current,
sync failure, bad sha) only mean something beside a repo that does get rewritten and synced.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.hooks import repin_cli

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    import pytest

_OLD = "03749d56d55741840da13d86533e7e8d698e3be8"
_NEW = "6868dd2e0b7f4a9c1d2e3f405162738495a6b7c8"
_REPO = "https://github.com/mikemol/mtools.git"
_LINE = f'"mikemol-hooks @ git+{_REPO}@{_OLD}#subdirectory=hooks"'
_WHEEL = "vendor/wheels/mikemol_ledger-0.1.0+gc3ca6d2-py3-none-any.whl"


def _tree(tmp_path: Path) -> Path:
    for name, body in {
        "alpha": f"dependencies = [{_LINE}]\n",
        "bravo": f"dependencies = [{_LINE}]\n",
        "charlie": f'mikemol-ledger = {{ path = "{_WHEEL}" }}\n',
        "delta": 'dependencies = ["requests"]\n',
        "mtools": f"dependencies = [{_LINE}]\n",
        ".hidden": f"dependencies = [{_LINE}]\n",
    }.items():
        (tmp_path / name).mkdir()
        (tmp_path / name / "pyproject.toml").write_text(body, encoding="utf-8")
    return tmp_path


class _Runner:
    """Record calls; report `bravo` dirty and let `uv sync` fail where told."""

    def __init__(self, *, failing: frozenset[str] = frozenset()) -> None:
        self.calls: list[tuple[str, tuple[str, ...]]] = []
        self.failing = failing

    def __call__(self, argv: Sequence[str], cwd: Path) -> tuple[int, str]:
        self.calls.append((cwd.name, tuple(argv)))
        if argv[0] == "git":
            return 0, " M pyproject.toml\n" if cwd.name == "bravo" else ""
        return (1, "") if cwd.name in self.failing else (0, "")


def test_the_survey_lists_each_pin_with_its_standing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """mtools, hidden directories and repos without pins are left out; a wheel is VENDORED."""
    root = _tree(tmp_path)
    assert repin_cli.main(["--root", str(root), "--sha", _NEW]) == 0
    assert capsys.readouterr().out.splitlines() == [
        f"alpha\thooks\tpep508\t{_OLD}\tDIFFERS",
        f"bravo\thooks\tpep508\t{_OLD}\tDIFFERS",
        "charlie\tledger\twheel\tc3ca6d2\tVENDORED",
    ]


def test_write_repins_the_clean_repo_syncs_it_and_skips_the_dirty_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The control and the refusal side by side; nothing in the dirty repo or mtools changes."""
    root = _tree(tmp_path)
    runner = _Runner()
    assert repin_cli.main(["--root", str(root), "--sha", _NEW, "--write"], runner) == 0
    assert _NEW in (root / "alpha" / "pyproject.toml").read_text(encoding="utf-8")
    assert _OLD in (root / "bravo" / "pyproject.toml").read_text(encoding="utf-8")
    assert _OLD in (root / "mtools" / "pyproject.toml").read_text(encoding="utf-8")
    assert capsys.readouterr().out.splitlines()[-2:] == [
        "RESULT alpha synced",
        "RESULT bravo skipped-dirty",
    ]
    assert ("alpha", ("uv", "sync")) in runner.calls
    assert ("bravo", ("uv", "sync")) not in runner.calls


def test_no_sync_writes_without_running_uv(tmp_path: Path) -> None:
    """The rewrite alone, leaving the lock to the repo's own session."""
    root = _tree(tmp_path)
    runner = _Runner()
    argv = ["--root", str(root), "--sha", _NEW, "--write", "--no-sync"]
    assert repin_cli.main(argv, runner) == 0
    assert all(call[0] != "uv" for _repo, call in runner.calls)
    assert _NEW in (root / "alpha" / "pyproject.toml").read_text(encoding="utf-8")


def test_a_failed_sync_exits_one_and_says_which_repo(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The text is rewritten, the sync failure is reported and the exit says so."""
    root = _tree(tmp_path)
    runner = _Runner(failing=frozenset({"alpha"}))
    assert repin_cli.main(["--root", str(root), "--sha", _NEW, "--write"], runner) == 1
    assert "RESULT alpha sync-failed" in capsys.readouterr().out


def test_a_repo_already_at_the_target_is_current_and_not_synced(tmp_path: Path) -> None:
    """A second run changes nothing and runs nothing."""
    root = _tree(tmp_path)
    argv = ["--root", str(root), "--sha", _NEW, "--write", "--no-sync"]
    repin_cli.main(argv, _Runner())
    again = _Runner()
    assert repin_cli.main(argv, again) == 0
    assert all(call[0] != "uv" for _repo, call in again.calls)


def test_only_the_named_dists_move(tmp_path: Path) -> None:
    """--dist narrows both the survey and the rewrite."""
    root = _tree(tmp_path)
    argv = ["--root", str(root), "--sha", _NEW, "--write", "--no-sync", "--dist", "nosuch"]
    assert repin_cli.main(argv, _Runner()) == 0
    assert _OLD in (root / "alpha" / "pyproject.toml").read_text(encoding="utf-8")


def test_usage_refusals_exit_two_and_write_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """No --sha with --write, a short sha, an unknown flag and a missing value."""
    root = _tree(tmp_path)
    before = (root / "alpha" / "pyproject.toml").read_text(encoding="utf-8")
    for argv in (
        ["--root", str(root), "--write"],
        ["--root", str(root), "--sha", "abc123", "--write"],
        ["--root", str(root), "--bogus"],
        ["--root"],
    ):
        assert repin_cli.main(argv, _Runner()) == repin_cli.EXIT_USAGE
    assert not capsys.readouterr().out
    assert (root / "alpha" / "pyproject.toml").read_text(encoding="utf-8") == before
