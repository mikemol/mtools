# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The git log is asked for in UTC ISO stamps, and `--git-repo` feeds `--intents` from it (W1934).

⚑ THE QUESTION IS A VALUE (`command`, `child_env`), READ WITHOUT RUNNING GIT; the one run is the
failing one, a path that is no repository, which must give None and not a partial log.
"""

import io
import json
from pathlib import Path
from typing import cast

import pytest

from mikemol.transcriptstruct import cli, gitlog, intents

_US = "\x1f"
_RS = "\x1e"
Doc = dict[str, object]


def test_the_question_names_the_repo_utc_iso_stamps_and_the_trailer_records(
    tmp_path: Path,
) -> None:
    """The argv holds the repository and the format; the environment is UTC."""
    argv = gitlog.command("/usr/bin/git", tmp_path)
    assert argv[:3] == ["/usr/bin/git", "-C", str(tmp_path)]
    assert "--format=%H%x1f%cd%x1f%B%x1e" in argv
    assert "--date=format-local:%Y-%m-%dT%H:%M:%SZ" in argv
    assert gitlog.child_env()["TZ"] == "UTC"


def test_a_path_that_is_no_repository_reads_as_no_log(tmp_path: Path) -> None:
    """Asking git about a path that is no repository gives None, never a partial log."""
    assert gitlog.read(tmp_path / "absent") is None


def _state_of(text: str) -> object:
    return cast("Doc", json.loads(text.splitlines()[0]))["state"]


def test_git_repo_feeds_the_intents_mode_and_a_log_file_wins_over_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The trailers come from the repository's log; `--git-log`, when given, is read instead."""
    asked: list[Path] = []

    def fake(repo: Path) -> str | None:
        asked.append(repo)
        return f"aaa{_US}2026-10-30T09:00:00Z{_US}x\n\nWaypoint: W7\n{_RS}"

    monkeypatch.setattr(cli, "read_git_log", fake)
    project = tmp_path / "-home-someone-github-mtools"
    project.mkdir()
    transcript = project / "abc.jsonl"
    message: Doc = {
        "role": "assistant",
        "content": [{"type": "text", "text": "I still need to land W7."}],
    }
    record: Doc = {
        "type": "assistant",
        "uuid": "u1",
        "timestamp": "2026-10-30T08:00:00.000Z",
        "message": message,
    }
    transcript.write_text(json.dumps(record) + "\n", encoding="utf-8")
    queue = tmp_path / "queue.json"
    card: Doc = {"symbol": "W7", "status": "ready"}
    doc: Doc = {"waypoints": [card]}
    queue.write_text(json.dumps(doc), encoding="utf-8")
    args = [str(transcript), "--intents", "--queue", str(queue), "--bound", "2026-10-30T12:00:00Z"]
    out = io.StringIO()
    assert cli.main([*args, "--git-repo", str(tmp_path)], out) == 0
    assert asked == [tmp_path]
    assert _state_of(out.getvalue()) == intents.LANDED
    empty = tmp_path / "empty.log"
    empty.write_text("", encoding="utf-8")
    out = io.StringIO()
    assert cli.main([*args, "--git-repo", str(tmp_path), "--git-log", str(empty)], out) == 0
    assert asked == [tmp_path]
    assert _state_of(out.getvalue()) == intents.MISSED
