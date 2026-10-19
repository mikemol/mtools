# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""An evidence string holding a home-directory path is refused on write (W1606)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from mikemol.pathsforward import cli, homepath

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

    from mikemol.pathsforward.model import Json

_HOME = "/srv/people/alice"


def _card() -> Json:
    return {
        "symbol": "W1",
        "title": "t",
        "status": "ready",
        "blocked_on": [],
        "blocked_kind": None,
        "next_bounded_step": "s",
        "evidence": "",
        "ticks_blocked": 0,
    }


def test_a_path_under_the_hosts_home_directories_is_named(monkeypatch: pytest.MonkeyPatch) -> None:
    """The prefix is read from the running host, so no module writes a user's home."""
    monkeypatch.setenv("HOME", _HOME)
    assert homepath.names_home("see /srv/people/bob/.claude/x.jsonl line 4")
    assert homepath.names_home("the transcript is at /srv/people/alice/t.jsonl")


def test_a_relative_citation_and_a_bare_prefix_name_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Project, session and line is the citation; the parent directory alone is not a path."""
    monkeypatch.setenv("HOME", _HOME)
    assert not homepath.names_home("project mtools session 20759004 line 80121")
    assert not homepath.names_home("lives under /srv/people")


def test_a_host_whose_home_has_no_parent_never_refuses(monkeypatch: pytest.MonkeyPatch) -> None:
    """With the home at the root there is no prefix to match, so nothing is refused."""
    monkeypatch.setenv("HOME", "/")
    assert not homepath.names_home("anything /x/y")


def test_evidence_append_refuses_a_home_path_and_names_the_redact_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Through the CLI: exit 2, the message names --evidence-redact, the queue is unchanged."""
    monkeypatch.setenv("HOME", _HOME)
    queue = tmp_path / ".claude" / "paths-forward.json"
    queue.parent.mkdir()
    waypoints = cast("list[object]", [_card()])
    doc: dict[str, object] = {"counter": 1, "residue": [], "waypoints": waypoints}
    queue.write_text(json.dumps(doc), encoding="utf-8")
    before = queue.read_text(encoding="utf-8")
    argv = ["--state", str(queue), "--update", "W1"]
    cited = [*argv, "--evidence-append", f"read {_HOME}/.claude/t.jsonl"]
    assert cli.main(cited) == cli.EXIT_REFUSED
    assert "--evidence-redact" in capsys.readouterr().err
    assert queue.read_text(encoding="utf-8") == before
    assert cli.main([*argv, "--evidence-append", "project mtools line 4"]) == cli.EXIT_OK
