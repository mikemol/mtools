# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.hooks.waypoint_trailer` (W491): the commit-msg `Waypoint:` trailer."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.hooks import waypoint_trailer

if TYPE_CHECKING:
    from pathlib import Path

_SUBJECT = "hooks: a subject line\n\nA body paragraph.\n"


def _run(tmp_path: Path, message: str) -> int:
    """Write `message` as a commit-message file and run the check on it.

    Returns:
        the check's exit status.

    """
    msg = tmp_path / "COMMIT_EDITMSG"
    msg.write_text(message, encoding="utf-8")
    return waypoint_trailer.main([str(msg)])


def test_a_message_without_the_trailer_is_refused(tmp_path: Path) -> None:
    """A message with no `Waypoint:` line is refused."""
    assert _run(tmp_path, _SUBJECT) == 1


def test_a_waypoint_number_trailer_is_accepted(tmp_path: Path) -> None:
    """`Waypoint: W174` is accepted."""
    assert _run(tmp_path, _SUBJECT + "\nWaypoint: W174\n") == 0


def test_a_waypoint_none_trailer_is_accepted(tmp_path: Path) -> None:
    """`Waypoint: none` is accepted."""
    assert _run(tmp_path, _SUBJECT + "\nWaypoint: none\n") == 0


def test_a_malformed_waypoint_trailer_is_refused(tmp_path: Path) -> None:
    """`Waypoint: 174` (no `W`) is refused."""
    assert _run(tmp_path, _SUBJECT + "\nWaypoint: 174\n") == 1


def test_a_trailer_only_in_a_git_comment_line_is_refused(tmp_path: Path) -> None:
    """A `# Waypoint:` line git will strip does not count."""
    assert _run(tmp_path, _SUBJECT + "# Waypoint: W174\n") == 1
