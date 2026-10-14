# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that mikemol-commit's verdict lines become structured events, and --ship spools them.

W1168. ⚑ THE GRAMMAR IS READ FROM THE FOUR LINES THE TOOL PRINTS, and the lines that are NOT
verdicts (the routing line, git's own output) are the controls: they must yield no event, or the
log would fill with fabricated verdicts. ⚑ `--ship` IS RUN THROUGH `main` on a throwaway
repository with the shipper replaced by a recorder, so "the output is unchanged and the same text
is shipped" is read from stdout and from what the recorder received.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import TYPE_CHECKING, cast

from mikemol.hooks import commit_kata as ck
from mikemol.hooks import verdictlog

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    import pytest

_COMMITTED = "COMMITTED mtools 5d421dd W1180: subject with [brackets] inside [PUSHED]"
_REFUSED = "REFUSED mtools (rc=1): the cause is above; HEAD is still 0a310f9"
_NOT = "NOT COMMITTED mtools: none of the requested paths is tracked by git"
_RACED = "RACED mtools: HEAD moved to abc1234 x, which this run did not make"
Doc = dict[str, object]


def test_a_committed_line_becomes_fields_and_keeps_the_whole_line() -> None:
    """The sha, the subject (with its own brackets) and the push state are fields."""
    event = verdictlog.event_of(_COMMITTED + "\n")
    assert event == {
        "verdict": "COMMITTED",
        "repo": "mtools",
        "sha": "5d421dd",
        "subject": "W1180: subject with [brackets] inside",
        "pushed": "PUSHED",
        "_msg": _COMMITTED,
    }


def test_a_push_state_with_a_semicolon_is_kept_whole() -> None:
    """`PUSHED; UNVERIFIED ...` is one field, as the tool prints it."""
    line = "COMMITTED mtools abc1234 W1: s [PUSHED; UNVERIFIED: git ls-remote origin failed]"
    event = verdictlog.event_of(line)
    assert event is not None
    assert event["pushed"] == "PUSHED; UNVERIFIED: git ls-remote origin failed"


def test_the_other_three_verdicts_each_give_their_own_fields() -> None:
    """REFUSED carries rc; NOT COMMITTED and RACED carry the reason; each names its repo."""
    refused = verdictlog.event_of(_REFUSED)
    assert refused is not None
    assert (refused["verdict"], refused["repo"], refused["rc"]) == ("REFUSED", "mtools", "1")
    assert refused["why"].startswith("the cause is above")
    nope = verdictlog.event_of(_NOT)
    assert nope is not None
    assert nope["verdict"] == "NOT COMMITTED"
    assert nope["why"].startswith("none of the requested paths")
    raced = verdictlog.event_of(_RACED)
    assert raced is not None
    assert raced["verdict"] == "RACED"


def test_lines_that_are_not_verdicts_give_no_event() -> None:
    """The control: the routing line, git's own line and a sentence that merely says COMMITTED."""
    for line in (
        "mikemol-commit: path: isolated (forced by MIKEMOL_COMMIT_ISOLATED=1); lock: held",
        "[main abc1234] W1: subject",
        "the work was COMMITTED mtools abc1234 s [PUSHED] yesterday",
        "",
    ):
        assert verdictlog.event_of(line) is None


def test_a_block_yields_its_verdicts_in_order_and_skips_the_rest() -> None:
    """Two verdicts around noise: both come back, in order."""
    text = f"noise\n{_COMMITTED}\nmore noise\nNOT COMMITTED r: why\n"
    assert [e["verdict"] for e in verdictlog.events_of(text)] == ["COMMITTED", "NOT COMMITTED"]


def _config(tmp_path: Path) -> Path:
    """Write a host config naming a spool directory under `tmp_path`.

    Returns:
        the config file's path.

    """
    path = tmp_path / "vlog.toml"
    path.write_text(f'spool_dir = "{tmp_path / "spool"}"\n', encoding="utf-8")
    return path


def test_ship_text_spools_the_events_with_the_tool_stream_and_starts_one_drainer(
    tmp_path: Path,
) -> None:
    """One verdict line: one record with its fields and `tool`, one detached drain argv."""
    spawned: list[Sequence[str]] = []
    count = verdictlog.ship_text(f"x\n{_COMMITTED}\n", spawned.append, _config(tmp_path))
    assert count == 1
    assert len(spawned) == 1
    files = sorted((tmp_path / "spool").glob("vlog-*.spool"))
    assert len(files) == 1
    record = cast("Doc", json.loads(files[0].read_text(encoding="utf-8").splitlines()[0]))
    assert (record["verdict"], record["sha"]) == ("COMMITTED", "5d421dd")
    assert record["tool"] == "mikemol-commit"
    assert record["_msg"] == _COMMITTED


def test_ship_text_with_no_verdict_spools_nothing_and_starts_nothing(tmp_path: Path) -> None:
    """The control: output with no verdict leaves no spool and no drainer."""
    spawned: list[Sequence[str]] = []
    assert verdictlog.ship_text("just git output\n", spawned.append, _config(tmp_path)) == 0
    assert not spawned
    assert not (tmp_path / "spool").exists()


def test_an_unwritable_spool_ships_nothing_and_never_raises(tmp_path: Path) -> None:
    """The spool directory is a regular file: the OSError is swallowed, no drainer starts."""
    blocker = tmp_path / "spool"
    blocker.write_text("a file, not a directory", encoding="utf-8")
    spawned: list[Sequence[str]] = []
    assert verdictlog.ship_text(_COMMITTED, spawned.append, _config(tmp_path)) == 0
    assert not spawned


def _git(root: Path, *args: str) -> str:
    """Run the real git and fail loudly.

    Returns:
        git's stdout.

    """
    git = shutil.which("git")
    assert git is not None
    done = subprocess.run([git, "-C", str(root), *args], check=True, capture_output=True, text=True)
    return done.stdout


def test_main_with_ship_prints_the_same_output_and_ships_the_text_it_printed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A plain commit with --ship: exit 0, the verdict on stdout, and the recorder got it too."""
    for name in [name for name in os.environ if name.startswith("GIT_")]:
        monkeypatch.delenv(name)
    for key, value in {
        "GIT_CEILING_DIRECTORIES": str(tmp_path),
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.invalid",
        "GIT_CONFIG_NOSYSTEM": "1",
        "HOME": str(tmp_path),
        ck.HELD_ENV: "1",
        ck.ISOLATED_ENV: "0",
    }.items():
        monkeypatch.setenv(key, value)
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "--quiet", "-b", "main")
    (root / "a.txt").write_text("one\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "--quiet", "-m", "first")
    (root / "a.txt").write_text("two\n", encoding="utf-8")
    shipped: list[str] = []

    def record(text: str) -> int:
        shipped.append(text)
        return 0

    monkeypatch.setattr(ck, "ship_text", record)
    code = ck.main([str(root), "--waypoint", "W1", "--subject", "subject", "--ship", "a.txt"])
    printed = capsys.readouterr().out
    assert code == 0
    assert any(line.startswith("COMMITTED repo ") for line in printed.splitlines())
    assert len(shipped) == 1
    assert shipped[0] in printed
    assert "COMMITTED repo " in shipped[0]
