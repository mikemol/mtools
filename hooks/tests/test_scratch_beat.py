# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A scratch call is the session using a tool, so it leaves a heartbeat (W1483)."""

from collections.abc import Sequence
from pathlib import Path

from mikemol.hooks import heartbeat, scratch_cli
from mikemol.hooks.scratch_land import Out


def _out(code: int, said: str) -> Out:
    def out(_argv: Sequence[str]) -> tuple[int, str]:
        return code, said

    return out


def test_a_scratch_call_leaves_a_beat_naming_the_scratch_tool(tmp_path: Path) -> None:
    """The record lands under the git dir that git names for the checkout."""
    git_dir = tmp_path / ".git"
    scratch_cli.beat(tmp_path, _out(0, f"{git_dir}\n"))
    left = heartbeat.read(git_dir)
    assert left is not None
    assert left.tool == scratch_cli.BEAT_TOOL


def test_a_checkout_git_cannot_name_beats_nothing_and_raises_nothing(tmp_path: Path) -> None:
    """When git refuses there is no git dir to write under, and the scratch call goes on."""
    git_dir = tmp_path / ".git"
    scratch_cli.beat(tmp_path, _out(128, f"{git_dir}\n"))
    assert heartbeat.read(git_dir) is None
