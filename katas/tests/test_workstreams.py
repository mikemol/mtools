# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `workstreams`: a directory is a workstream when it carries a queue (W872)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.katas import workstreams

if TYPE_CHECKING:
    from pathlib import Path


def _queue(root: Path, name: str) -> None:
    """Give the directory `name` under `root` a paths-forward queue."""
    claude = root / name / ".claude"
    claude.mkdir(parents=True)
    (claude / "paths-forward.json").write_text("{}", encoding="utf-8")


def test_a_directory_with_a_queue_is_a_workstream(tmp_path: Path) -> None:
    """The name is the directory's, two levels above the queue file."""
    _queue(tmp_path, "alpha")
    assert workstreams.repos(tmp_path) == ["alpha"]


def test_a_directory_without_a_queue_is_not(tmp_path: Path) -> None:
    """A checkout with `.claude/` but no queue file, or no `.claude/`, is left out."""
    _queue(tmp_path, "alpha")
    (tmp_path / "beta" / ".claude").mkdir(parents=True)
    (tmp_path / "gamma").mkdir()
    assert workstreams.repos(tmp_path) == ["alpha"]


def test_the_names_are_sorted(tmp_path: Path) -> None:
    """The order is the names', whatever order the filesystem lists them in."""
    for name in ("zulu", "alpha", "mike"):
        _queue(tmp_path, name)
    assert workstreams.repos(tmp_path) == ["alpha", "mike", "zulu"]


def test_a_dot_named_directory_is_never_a_workstream(tmp_path: Path) -> None:
    """A hidden tool tree or a scratch checkout carrying a queue is not one."""
    _queue(tmp_path, "alpha")
    _queue(tmp_path, ".claude-scratch")
    assert workstreams.repos(tmp_path) == ["alpha"]
