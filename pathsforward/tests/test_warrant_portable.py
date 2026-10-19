# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A warrant cites its transcript by project and session, never by a home path (W1630)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from mikemol.pathsforward import homepath, warrant
from mikemol.pathsforward.model import Json, State

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_UUID = "0f3c-uuid"
_GOOD: Json = {"ok": True, "reason": "", "line": 7, "timestamp": "2026-10-16T14:02:11Z"}
_HUMAN: Json = {**_GOOD, "kind": "human"}
_NAMED = "-srv-people-alice-repo/sess1"


def _transcript(root: Path) -> Path:
    return root / "alice" / ".claude" / "projects" / "-srv-people-alice-repo" / "sess1.jsonl"


def _card() -> Json:
    return {
        "symbol": "W1",
        "title": "t",
        "status": "ready",
        "blocked_on": [],
        "blocked_kind": None,
        "next_bounded_step": None,
        "evidence": "",
        "ticks_blocked": 0,
    }


def test_a_transcript_is_named_by_its_project_directory_and_session(tmp_path: Path) -> None:
    """Two words of the path are the citation; the rest is this host's."""
    assert warrant.transcript_name(_transcript(tmp_path)) == _NAMED


def test_both_forms_of_one_record_reduce_to_one_key() -> None:
    """The old file URL and the new urn name the same session and record."""
    old = f"file:///srv/people/alice/.claude/projects/-d/sess1.jsonl#{_UUID}"
    new = f"urn:claude:transcript:-d/sess1#{_UUID}"
    assert warrant.record_key(old) == warrant.record_key(new) == f"sess1#{_UUID}"


def test_the_reader_command_keeps_its_name_and_the_transcript_by_symbol(tmp_path: Path) -> None:
    """The reader's directory and the transcript's path are both gone; the other words stay."""
    transcript = _transcript(tmp_path)
    argv = ["/opt/bin/mikemol-transcriptstruct", str(transcript), "--verify", _UUID]
    got = warrant.portable_reader(argv, transcript)
    assert got == f"mikemol-transcriptstruct claude:transcript:{_NAMED} --verify {_UUID}"


def test_a_built_warrant_names_no_path_under_the_hosts_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The control is the old shape: it holds the home prefix; the new one does not."""
    monkeypatch.setenv("HOME", str(tmp_path / "alice"))
    transcript = _transcript(tmp_path)
    cited = warrant.Citation(transcript, _UUID, claim="operator", line=7)
    argv = ["/opt/bin/reader", str(transcript), "--verify", _UUID]
    built = warrant.build("urn:nemik:r/W1", cited, _HUMAN, argv)
    assert not homepath.names_home(json.dumps(built))
    assert homepath.names_home(transcript.resolve().as_uri())


def test_a_warrant_held_in_the_old_form_is_not_attached_again_in_the_new(tmp_path: Path) -> None:
    """One record, one warrant per card, across the change of form."""
    transcript = _transcript(tmp_path)
    cited = warrant.Citation(transcript, _UUID, claim="operator", line=7)
    old = warrant.build("urn:nemik:r/W1", cited, _HUMAN, ["reader"])
    record = cast("Json", old["prov:wasDerivedFrom"])
    record["@id"] = f"file:///srv/people/alice/.claude/projects/-d/sess1.jsonl#{_UUID}"
    card = _card()
    card["warrants"] = [old]
    state = State({"waypoints": [card]}, [card], [], 1)
    new_form = warrant.build("urn:nemik:r/W1", cited, _HUMAN, ["reader"])
    drifted = cast("Json", new_form["prov:wasDerivedFrom"])
    drifted["@id"] = f"urn:claude:transcript:-d/sess1#{_UUID}"
    assert not warrant.attach(state, "W1", new_form)
    assert len(cast("list[Json]", card["warrants"])) == 1
