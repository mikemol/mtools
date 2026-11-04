# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`--retro-scaffold FILE` prints a retro scaffold for a landing verdict row (W2267)."""

import json
from pathlib import Path

import pytest

from mikemol.pathsforward import cli, landed, retros

_HEAD_STEP = "the step the card carried at submit"
_NOW_STEP = "the step the card carries now"


def _queue(step: str) -> dict[str, object]:
    return {
        "counter": 1,
        "project_root": "",
        "waypoints": [{"symbol": "W1", "title": "t", "status": "ready", "next_bounded_step": step}],
    }


def _head_copy(_root: Path, _rel: str) -> str | None:
    return json.dumps(_queue(_HEAD_STEP))


def _no_head_copy(_root: Path, _rel: str) -> str | None:
    return None


def _setup(tmp_path: Path) -> tuple[Path, Path]:
    state = tmp_path / "repo" / ".claude" / "paths-forward.json"
    state.parent.mkdir(parents=True)
    doc = _queue(_NOW_STEP)
    doc["project_root"] = str(tmp_path / "repo")
    state.write_text(json.dumps(doc), encoding="utf-8")
    row = {"verdict": "REFUSED", "reason": "a check failed", "rc": 1, "waypoints": ["W1"]}
    event = tmp_path / "event.json"
    event.write_text(json.dumps(row), encoding="utf-8")
    return state, event


def test_committed_text_asks_git_for_the_file_at_head(tmp_path: Path) -> None:
    """The path is read as `HEAD:<rel>`, after an end-of-options marker, in the given root."""
    asked: list[list[str]] = []

    def run(argv: list[str]) -> str | None:
        asked.append(argv)
        return "held\n"

    assert landed.committed_text(tmp_path, ".claude/paths-forward.json", run) == "held\n"
    assert asked[0][1:] == [
        "-C",
        str(tmp_path),
        "show",
        "--end-of-options",
        "HEAD:.claude/paths-forward.json",
    ]


def test_committed_text_is_none_when_git_gives_no_answer(tmp_path: Path) -> None:
    """No answer is None, never an empty file."""

    def refuses(_argv: list[str]) -> str | None:
        return None

    assert landed.committed_text(tmp_path, "x", refuses) is None


def test_the_scaffold_reads_its_precommit_from_heads_copy_not_the_working_queue(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The card's step as HEAD held it is the precommit; the working copy has moved on."""
    state, event = _setup(tmp_path)
    monkeypatch.setattr(cli, "_committed_text", _head_copy)
    assert cli.main(["--state", str(state), "--retro-scaffold", str(event)]) == cli.EXIT_OK
    made: dict[str, object] = json.loads(capsys.readouterr().out)
    assert made["precommit"] == f"W1: {_HEAD_STEP}"
    assert made["trigger"] == "REFUSED: a check failed"
    assert retros.retro_refusals(made) == []


def test_an_unreadable_head_copy_falls_back_to_the_working_queue_and_says_so(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The fallback is announced on stderr, and the working step is used."""
    state, event = _setup(tmp_path)
    monkeypatch.setattr(cli, "_committed_text", _no_head_copy)
    assert cli.main(["--state", str(state), "--retro-scaffold", str(event)]) == cli.EXIT_OK
    shown = capsys.readouterr()
    made: dict[str, object] = json.loads(shown.out)
    assert made["precommit"] == f"W1: {_NOW_STEP}"
    assert "using the working queue" in shown.err


def test_a_file_that_is_not_one_json_object_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A list is not a verdict row: usage refusal, nothing printed."""
    state, event = _setup(tmp_path)
    event.write_text("[1, 2]", encoding="utf-8")
    assert cli.main(["--state", str(state), "--retro-scaffold", str(event)]) == cli.EXIT_REFUSED
    shown = capsys.readouterr()
    assert not shown.out
    assert "holds one verdict row" in shown.err
