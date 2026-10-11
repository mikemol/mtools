# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the work-claims hook, over a fake fence verb and a fake process table.

W994. ⚑ THE CLAIM TAKEN FOR THE WORKING CARD IS THE POSITIVE CONTROL: the held-elsewhere advice, the
idempotent second prompt, the release, the SessionEnd sweep and the notices only mean something
beside a prompt that does claim the tag with the session as owner.
"""

from __future__ import annotations

import io
import json
import os
from typing import TYPE_CHECKING

from mikemol.hooks import work_claims_hook

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    import pytest

HOOK = 5000
SHELL = 4000
SESSION = 3000
START = 777
STARTTIME_AT = 19
BAZEL = "claim:label:touch:mtools:bazel"
TYPING = "claim:label:touch:mtools:typing"
ME = f"{SESSION}:{START}"
THEM = "999:123"
REFUSED = 3


def _stat(pid: int, comm: str, ppid: int, start: int) -> str:
    """Build a stat line with the state, parent and start-time fields where the kernel puts them.

    Returns:
        the line.

    """
    after = ["S", str(ppid)] + ["0"] * (STARTTIME_AT - 2) + [str(start), "0"]
    return f"{pid} ({comm}) " + " ".join(after)


def _table(*, session: bool = True) -> dict[int, str]:
    name = "claude" if session else "node"
    return {
        HOOK: _stat(HOOK, "python3", SHELL, 1),
        SHELL: _stat(SHELL, "sh", SESSION, 2),
        SESSION: _stat(SESSION, name, 1, START),
    }


class _Fence:
    """A fake mikemol-membudget: it keeps a claim table and records every call."""

    def __init__(self, held: dict[str, str] | None = None, refuse: tuple[str, ...] = ()) -> None:
        self.held = dict(held or {})
        self.refuse = refuse
        self.calls: list[list[str]] = []

    def __call__(self, argv: Sequence[str], _timeout: float) -> tuple[int, str]:
        verb, rest = argv[1], list(argv[2:])
        self.calls.append([verb, *rest])
        if verb == "claims":
            rows = [
                f"{label} owner={who} id=aaaaaaaaaaaa age=1s" for label, who in self.held.items()
            ]
            return 0, "\n".join(rows) + "\n"
        if verb == "claim" and rest[0] in self.refuse:
            return REFUSED, "membudget: REFUSED — fence.admit: waiting (CLAIMED): held by 999:123\n"
        return 0, "aaaaaaaaaaaa\n"

    def verbs(self) -> list[str]:
        return [call[0] for call in self.calls]


def _project(tmp_path: Path, *cards: tuple[str, str], tool: bool = True) -> Path:
    project = tmp_path / "mtools"
    (project / ".claude").mkdir(parents=True)
    waypoints: list[dict[str, object]] = [
        {"symbol": "W1", "status": s, "touches": [t]} for s, t in cards
    ]
    queue: dict[str, object] = {"waypoints": waypoints}
    (project / ".claude" / "paths-forward.json").write_text(json.dumps(queue), encoding="utf-8")
    if tool:
        binary = project / work_claims_hook.MEMBUDGET
        binary.parent.mkdir(parents=True)
        binary.write_text("#!/bin/sh\n", encoding="utf-8")
        binary.chmod(0o755)
    return project


def _lines(project: Path, event: str, fence: _Fence, table: dict[int, str]) -> list[str]:
    return work_claims_hook.claim_lines(project, event, fence, table.get, HOOK)


def test_a_working_card_claims_its_tag_with_the_session_as_owner(tmp_path: Path) -> None:
    """The control: the claim verb is called for the tag, owned by the claude process."""
    project = _project(tmp_path, ("working", "bazel"))
    fence = _Fence()
    assert _lines(project, "UserPromptSubmit", fence, _table()) == []
    assert fence.calls[-1] == ["claim", BAZEL, "--owner-pid", str(SESSION)]


def test_a_claim_another_session_holds_becomes_one_advisory_line(tmp_path: Path) -> None:
    """Exit 3 from the ledger is advice naming the holder, never a failure."""
    project = _project(tmp_path, ("working", "bazel"))
    lines = _lines(project, "UserPromptSubmit", _Fence(refuse=(BAZEL,)), _table())
    assert len(lines) == 1
    assert "mtools:bazel is held elsewhere" in lines[0]
    assert "held by 999:123" in lines[0]


def test_a_claim_already_held_by_this_session_is_not_taken_again(tmp_path: Path) -> None:
    """The second prompt asks the ledger what it holds and claims nothing."""
    project = _project(tmp_path, ("working", "bazel"))
    fence = _Fence(held={BAZEL: ME})
    assert _lines(project, "UserPromptSubmit", fence, _table()) == []
    assert fence.verbs() == ["claims"]


def test_a_tag_no_card_works_any_more_is_released_but_a_peers_claim_is_not(tmp_path: Path) -> None:
    """Mine and unwanted goes; a claim another owner holds stays."""
    project = _project(tmp_path, ("ready", "bazel"))
    fence = _Fence(held={TYPING: ME, BAZEL: THEM})
    assert _lines(project, "UserPromptSubmit", fence, _table()) == []
    assert ["release", TYPING, "--owner-pid", str(SESSION)] in fence.calls
    assert not any(call[:2] == ["release", BAZEL] for call in fence.calls)


def test_session_end_releases_every_claim_this_session_holds_and_claims_nothing(
    tmp_path: Path,
) -> None:
    """With a card still working, SessionEnd still wants nothing."""
    project = _project(tmp_path, ("working", "bazel"))
    fence = _Fence(held={BAZEL: ME, TYPING: ME})
    assert _lines(project, "SessionEnd", fence, _table()) == []
    assert sorted(c[1] for c in fence.calls if c[0] == "release") == [BAZEL, TYPING]
    assert "claim" not in fence.verbs()


def test_a_missing_fence_venv_is_said_only_when_there_was_something_to_claim(
    tmp_path: Path,
) -> None:
    """A working card gets a notice; an idle queue gets silence."""
    busy = _project(tmp_path / "a", ("working", "bazel"), tool=False)
    idle = _project(tmp_path / "b", ("ready", "bazel"), tool=False)
    said = _lines(busy, "UserPromptSubmit", _Fence(), _table())
    assert said == ["work claim: not taken (the fence membudget venv is not built)"]
    assert _lines(idle, "UserPromptSubmit", _Fence(), _table()) == []


def test_the_bazel_built_membudget_is_found_when_the_checkouts_venv_has_none(
    tmp_path: Path,
) -> None:
    """The bazel-bin venv is looked in first, and a checkout venv without the script is skipped."""
    project = _project(tmp_path, ("working", "bazel"), tool=False)
    assert work_claims_hook.find_tool(project) is None
    built = project / "bazel-bin" / "fence" / ".venv" / "bin" / "mikemol-membudget"
    built.parent.mkdir(parents=True)
    built.write_text("#!/bin/sh\n", encoding="utf-8")
    built.chmod(0o755)
    assert work_claims_hook.find_tool(project) == built
    fence = _Fence()
    assert _lines(project, "UserPromptSubmit", fence, _table()) == []
    assert fence.verbs() == ["claims", "claim"]


def test_no_claude_ancestor_is_said_and_nothing_is_claimed(tmp_path: Path) -> None:
    """Without a session process to own it, no claim is made and the notice says why."""
    project = _project(tmp_path, ("working", "bazel"))
    fence = _Fence()
    said = _lines(project, "UserPromptSubmit", fence, _table(session=False))
    assert said == ["work claim: not taken (no claude session process above this hook)"]
    assert fence.calls == []


def test_the_command_name_is_read_from_between_the_outer_parentheses() -> None:
    """A comm with spaces and a parenthesis is still read whole."""
    assert work_claims_hook.comm_in(_stat(1, "we (ird) name", 0, 0)) == "we (ird) name"
    assert work_claims_hook.comm_in("no parentheses") is None


def test_an_unreadable_queue_claims_nothing(tmp_path: Path) -> None:
    """A malformed queue file is no claims, not an error."""
    project = _project(tmp_path, ("working", "bazel"))
    (project / ".claude" / "paths-forward.json").write_text("{not json", encoding="utf-8")
    fence = _Fence()
    assert _lines(project, "UserPromptSubmit", fence, _table()) == []
    assert "claim" not in fence.verbs()


def test_the_same_advice_is_not_repeated_within_a_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The first emission is new, an identical second one is not, a changed one is."""
    monkeypatch.setattr("tempfile.tempdir", str(tmp_path))
    assert not work_claims_hook.unchanged_since_last("sess-1", "line")
    assert work_claims_hook.unchanged_since_last("sess-1", "line")
    assert not work_claims_hook.unchanged_since_last("sess-1", "other")
    assert not work_claims_hook.unchanged_since_last("bad id", "line")


def test_main_prints_context_for_a_held_claim_and_always_exits_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """End to end over the payload: one additionalContext JSON, exit 0."""
    project = _project(tmp_path, ("working", "bazel"))
    table = _table()
    table[os.getpid()] = table.pop(HOOK)
    monkeypatch.setattr("tempfile.tempdir", str(tmp_path / "tmp"))
    monkeypatch.setenv(work_claims_hook.PROJECT_DIR_ENV, str(project))
    monkeypatch.setattr(work_claims_hook, "run_both", _Fence(refuse=(BAZEL,)))
    monkeypatch.setattr(work_claims_hook, "read_stat", table.get)
    event = {"hook_event_name": "UserPromptSubmit", "session_id": "s1"}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(event)))
    assert work_claims_hook.main() == 0
    said = capsys.readouterr().out
    assert '"hookEventName": "UserPromptSubmit"' in said
    assert '"additionalContext": "work claim: mtools:bazel is held elsewhere' in said


def test_an_event_it_does_not_serve_and_a_bad_payload_say_nothing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Other events and unreadable input exit 0 with no output."""
    for raw in ('{"hook_event_name": "Stop"}', "not json"):
        monkeypatch.setattr("sys.stdin", io.StringIO(raw))
        assert work_claims_hook.main() == 0
    assert not capsys.readouterr().out
