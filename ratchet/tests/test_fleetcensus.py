# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The census walks every repository under a root and lists each ratchet file it holds (W1907)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.ratchet import cli, fleetcensus

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def _put(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _fleet(root: Path) -> None:
    _put(root / "alpha" / "baselines" / "ruff-baseline.json", '{"a.py": {"D103": 2}}')
    _put(root / "alpha" / ".claude" / "debt-ledger.json", "{}")
    _put(root / "alpha" / "notes" / "baseline.md", "prose about a baseline")
    _put(root / "beta" / "ratchet-preview.txt", "k1\nk2\n")
    _put(root / "beta" / "broken-baseline.json", "{nope")


def test_each_ratchet_file_is_listed_with_repo_path_kind_value_and_floor(tmp_path: Path) -> None:
    """Both repositories, the dot-directory ledger, the unread file; prose is not a ratchet."""
    _fleet(tmp_path)
    lines = [row.line() for row in fleetcensus.census(tmp_path)]
    assert lines == [
        "alpha .claude/debt-ledger.json debt value=0 floor=0 guessed=1",
        "alpha baselines/ruff-baseline.json baseline value=1 floor=0 sum=2 guessed=1",
        "beta broken-baseline.json baseline value=UNREAD floor=0 guessed=1",
        "beta ratchet-preview.txt preview value=2 floor=0 guessed=1",
    ]


def test_clones_worktrees_and_build_trees_are_not_counted_twice(tmp_path: Path) -> None:
    """A -bak clone, a hidden gate worktree, agent worktrees and a bazel-* tree are skipped."""
    _fleet(tmp_path)
    for skipped in ("alpha-bak2", ".alpha-gate-wt"):
        _put(tmp_path / skipped / "ruff-baseline.json", '{"x": 1}')
    _put(tmp_path / "alpha" / ".claude" / "worktrees" / "a1" / "debt.json", '{"x": 1}')
    _put(tmp_path / "alpha" / "bazel-bin" / "out-baseline.json", '{"x": 1}')
    _put(tmp_path / "alpha" / "a" / "b" / "c" / "d" / "e" / "deep-baseline.json", '{"x": 1}')
    rows = fleetcensus.census(tmp_path)
    paths = {row.ratchet for row in rows}
    assert {row.repo for row in rows} == {"alpha", "beta"}
    assert not any("worktrees" in p or "bazel-bin" in p or "deep-baseline" in p for p in paths)


def test_a_gate_censuses_its_own_repository_and_reads_no_sibling(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """W1923: `census --repo DIR` lists DIR alone, never the repositories beside it."""
    _fleet(tmp_path)
    lines = [row.line() for row in fleetcensus.census_repo(tmp_path / "beta")]
    assert lines == [
        "beta broken-baseline.json baseline value=UNREAD floor=0 guessed=1",
        "beta ratchet-preview.txt preview value=2 floor=0 guessed=1",
    ]
    assert cli.main(["census", "--repo", str(tmp_path / "beta")]) == 0
    out = capsys.readouterr().out.splitlines()
    assert not any(line.startswith("alpha ") for line in out)
    assert out[-1] == "# 2 ratchet file(s), 1 unread"


def test_the_command_prints_the_rows_and_the_counts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`census ROOT` lists the rows and ends with how many files and how many were unread."""
    _fleet(tmp_path)
    assert cli.main(["census", str(tmp_path)]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[-1] == "# 4 ratchet file(s), 1 unread"
    assert "beta ratchet-preview.txt preview value=2 floor=0 guessed=1" in out


_CLEAN = "[tool.ruff]\nline-length = 100\n"
_EXEMPT = '[tool.ruff.lint.per-file-ignores]\n"a.py" = ["x"]\n'


def _total(root: Path) -> int:
    return sum(row.value or 0 for row in fleetcensus.census(root))


def test_a_pyproject_is_listed_as_an_exemption_row_and_unreadable_is_not_zero(
    tmp_path: Path,
) -> None:
    """W2139: one `exemption` row per pyproject; a broken one reads UNREAD, a clean one 0."""
    _put(tmp_path / "alpha" / "pyproject.toml", _EXEMPT)
    _put(tmp_path / "beta" / "pyproject.toml", "[tool.ruff")
    _put(tmp_path / "gamma" / "pyproject.toml", _CLEAN)
    lines = [row.line() for row in fleetcensus.census(tmp_path)]
    assert lines == [
        "alpha pyproject.toml exemption value=1 floor=0",
        "beta pyproject.toml exemption value=UNREAD floor=0",
        "gamma pyproject.toml exemption value=0 floor=0",
    ]


def test_an_allowlist_entry_moved_to_per_file_ignores_reads_unchanged_never_paydown(
    tmp_path: Path,
) -> None:
    """W2139: the entry leaves the counted preview and the same debt appears as an exemption."""
    _put(tmp_path / "alpha" / "ratchet-preview.txt", "k1\nk2\n")
    _put(tmp_path / "alpha" / "pyproject.toml", _CLEAN)
    before = _total(tmp_path)
    _put(tmp_path / "alpha" / "ratchet-preview.txt", "k1\n")
    _put(tmp_path / "alpha" / "pyproject.toml", _EXEMPT)
    assert _total(tmp_path) == before
    _put(tmp_path / "alpha" / "pyproject.toml", _CLEAN)
    assert _total(tmp_path) < before
