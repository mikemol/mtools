# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The idle alarm carries one concrete next action: a stackable card, a leaf to atomize (W1591)."""

from __future__ import annotations

import stat
from typing import TYPE_CHECKING

from mikemol.hooks import watchdog
from mikemol.hooks.heartbeat import Beat

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_S = 1_000_000_000
_POLL = 20.0
_STACKABLE = (
    "STACK   mtools:W1586  hooks/a.py\n"
    "WAITING mtools:W1584  hooks/b.py\n"
    "1 stackable of 123 ready; 119 have no manifest\n"
)
_DRAFTS = '[\n {\n  "symbol": "W1493",\n  "manifest": ["hooks/c.py"],\n  "size": "small"\n }\n]\n'


def _seams() -> watchdog.Seams:
    clock = iter([0, 700])

    def now() -> int:
        return next(clock, 700) * _S

    return (lambda: Beat("mikemol-commit", 0, ()), lambda: 3, now, lambda _s: None, lambda: True)


def test_the_hint_names_the_first_stackable_card_and_the_first_draftable_leaf() -> None:
    """A WAITING row is not offered: it waits on something; the STACK row is the one to submit."""
    assert watchdog.next_action(_STACKABLE, _DRAFTS) == "next: stack W1586; atomize W1493"


def test_a_half_with_nothing_to_name_is_left_out_and_neither_is_silence() -> None:
    """No stackable row: only the leaf; no draft: only the stack; neither: no line at all."""
    assert watchdog.next_action("WAITING mtools:W1:  x\n", _DRAFTS) == "next: atomize W1493"
    assert watchdog.next_action(_STACKABLE, "[]") == "next: stack W1586"
    assert not watchdog.next_action("", "")


def test_the_alarm_prints_the_hint_after_the_idle_line(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The reminder carries its own content: the idle line, then the next action."""
    code = watchdog.watch(_seams(), 1.0, _POLL, hint=lambda: "next: stack W9")
    assert code == watchdog.EXIT_IDLE
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].startswith("idle with 3 ready cards")
    assert lines[1] == "next: stack W9"


def test_without_nemik_stackable_the_hint_is_empty_and_nothing_is_raised(tmp_path: Path) -> None:
    """A host with no nemik-stackable gets the idle line alone."""
    assert not watchdog.hint_from("mtools", {watchdog.STACKABLE_ENV: str(tmp_path / "absent")})


def test_the_exit_names_the_heartbeat_file_it_read_and_adds_the_hint_when_there_is_one(
    tmp_path: Path,
) -> None:
    """W1617: the file read is said first, so a path unlike the hook's shows."""
    git_dir = tmp_path / "repo" / ".git"
    absent = {watchdog.STACKABLE_ENV: str(tmp_path / "absent")}
    said = watchdog.exit_notes(git_dir, "repo", absent)
    assert said == f"heartbeat read: {git_dir}/mtools/heartbeat"


def test_the_exit_keeps_the_next_action_for_the_hooks_notice(tmp_path: Path) -> None:
    """W1565: what the exit computed is stored beside the heartbeat, and read back as it was."""
    git_dir = tmp_path / "repo" / ".git"
    assert not watchdog.cached_hint(git_dir)
    rows = tmp_path / "rows"
    rows.write_text(_STACKABLE, encoding="utf-8")
    tool = tmp_path / "nemik-stackable"
    tool.write_text(f"#!/bin/sh\ncat {rows}\n", encoding="utf-8")
    tool.chmod(tool.stat().st_mode | stat.S_IXUSR)
    watchdog.exit_notes(git_dir, "repo", {watchdog.STACKABLE_ENV: str(tool)})
    assert watchdog.cached_hint(git_dir) == "next: stack W1586"


def test_a_found_tool_is_asked_twice_and_its_answers_become_the_line(tmp_path: Path) -> None:
    """The plain call gives the rows, the --propose --json call gives the drafts."""
    rows, drafts = tmp_path / "rows", tmp_path / "drafts"
    rows.write_text(_STACKABLE, encoding="utf-8")
    drafts.write_text(_DRAFTS, encoding="utf-8")
    tool = tmp_path / "nemik-stackable"
    body = f'#!/bin/sh\ncase "$*" in *--json*) cat {drafts};; *) cat {rows};; esac\n'
    tool.write_text(body, encoding="utf-8")
    tool.chmod(tool.stat().st_mode | stat.S_IXUSR)
    said = watchdog.hint_from("mtools", {watchdog.STACKABLE_ENV: str(tool)})
    assert said == "next: stack W1586; atomize W1493"
