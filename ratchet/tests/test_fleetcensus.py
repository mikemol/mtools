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
        "alpha .claude/debt-ledger.json debt value=0 floor=0",
        "alpha baselines/ruff-baseline.json baseline value=1 floor=0",
        "beta broken-baseline.json baseline value=UNREAD floor=0",
        "beta ratchet-preview.txt preview value=2 floor=0",
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


def test_the_command_prints_the_rows_and_the_counts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`census ROOT` lists the rows and ends with how many files and how many were unread."""
    _fleet(tmp_path)
    assert cli.main(["census", str(tmp_path)]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[-1] == "# 4 ratchet file(s), 1 unread"
    assert "beta ratchet-preview.txt preview value=2 floor=0" in out
