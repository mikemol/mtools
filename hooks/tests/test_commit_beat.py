# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A submit is the session using its tools, so it leaves a heartbeat (W1482)."""

from pathlib import Path

from mikemol.hooks import commit_kata, heartbeat


def test_a_submit_leaves_a_beat_naming_the_commit_tool(tmp_path: Path) -> None:
    """The record sits beside the commit ledger, under the git dir."""
    git_dir = tmp_path / ".git"
    commit_kata.beat(git_dir / "mtools")
    left = heartbeat.read(git_dir)
    assert left is not None
    assert left.tool == commit_kata.BEAT_TOOL


def test_two_submits_keep_the_gap_between_them(tmp_path: Path) -> None:
    """The second beat records how long the session was quiet."""
    git_dir = tmp_path / ".git"
    commit_kata.beat(git_dir / "mtools")
    commit_kata.beat(git_dir / "mtools")
    left = heartbeat.read(git_dir)
    assert left is not None
    assert len(left.gaps_ns) == 1


def test_a_repository_with_no_git_dir_beats_nothing_and_raises_nothing() -> None:
    """When the git dir has no name the ledger is None and the beat is skipped."""
    commit_kata.beat(None)


def test_a_git_dir_that_will_not_take_the_file_raises_nothing(tmp_path: Path) -> None:
    """A beat that cannot be written is a missed sample, never a refused commit."""
    blocker = tmp_path / ".git"
    blocker.write_text("a file where the git dir should be", encoding="utf-8")
    commit_kata.beat(blocker / "mtools")
    assert heartbeat.read(blocker) is None


def test_a_fresh_submission_beats_and_a_reexec_under_the_lease_does_not(tmp_path: Path) -> None:
    """The nested run holds the lease already, so only the first entry counts as a tool use."""
    fresh, nested = tmp_path / "fresh" / ".git", tmp_path / "nested" / ".git"
    commit_kata.submit(fresh / "mtools", "1", {})
    commit_kata.submit(nested / "mtools", "1", {commit_kata.HELD_ENV: "1"})
    assert heartbeat.read(fresh) is not None
    assert heartbeat.read(nested) is None
