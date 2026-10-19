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

import pytest

from mikemol.hooks import commit_counts, commit_span, verdictlog
from mikemol.hooks import commit_kata as ck

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

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


_GATE = "pre-commit: gate jobs=2 cores=24 load1=97.33 floor=2 (held at the floor)"
_REFUSAL = (
    "pre-commit: REFUSED — the following check(s) failed:\n"
    "  - hooks: pytest — every case passes\n"
    "  - the hermetic suite: //hooks:mutants_0 //hooks:mutants_1\n"
    "pre-commit: the failing check(s) said:\n"
    "  --- ruff ---\n"
    "  - not a check, it is a line of a check's own output\n"
)


def test_the_gates_job_line_becomes_a_gate_event_with_its_readings() -> None:
    """Jobs, cores, load and floor are fields; `held` says the floor held the cap up."""
    held = verdictlog.events_of(_GATE)
    assert held == [
        {
            "verdict": "GATE",
            "jobs": "2",
            "cores": "24",
            "load1": "97.33",
            "floor": "2",
            "held": "true",
            "_msg": _GATE,
        }
    ]
    free = verdictlog.events_of("pre-commit: gate jobs=14 cores=24 load1=9.89 floor=2")
    assert free[0]["held"] == "false"


def test_each_check_a_refusal_names_is_an_event_and_nothing_after_the_refusal_is() -> None:
    """Two bullets under the header: two CHECK_FAILED events; the later `- ` line is not one."""
    events = verdictlog.events_of(_REFUSAL)
    assert [e["verdict"] for e in events] == ["CHECK_FAILED", "CHECK_FAILED"]
    assert events[0]["check"] == "hooks: pytest — every case passes"
    assert events[1]["check"].startswith("the hermetic suite:")


def test_a_bullet_with_no_refusal_header_is_not_a_failed_check() -> None:
    """The control: a stray `  - x` line outside a refusal blames no check."""
    assert verdictlog.events_of("  - hooks: pytest — every case passes\n") == []


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
        commit_span.BIN_ENV: "/nonexistent/mikemol-otlp",
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


def _held_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Build a throwaway repo with a modified tracked file, in an environment holding the claim.

    Returns:
        the repository root.

    """
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
        commit_span.BIN_ENV: "/nonexistent/mikemol-otlp",
    }.items():
        monkeypatch.setenv(key, value)
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "--quiet", "-b", "main")
    (root / "a.txt").write_text("one\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "--quiet", "-m", "first")
    (root / "a.txt").write_text("two\n", encoding="utf-8")
    return root


class _Spans:
    """A recorder standing in for the span starter, remembering each call."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, commit_span.Moments, str]] = []

    def __call__(self, text: str, moments: commit_span.Moments, waypoint: str, env: object) -> int:
        del env
        self.calls.append((text, moments, waypoint))
        return 0


def test_main_starts_the_spans_from_the_printed_text_with_ordered_moments(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without --ship the spans still start, from the text printed, submit <= lease <= end."""
    root = _held_repo(tmp_path, monkeypatch)
    spans = _Spans()
    monkeypatch.setattr(ck, "_emit_spans", spans)
    assert ck.main([str(root), "--waypoint", "W1", "--subject", "subject", "a.txt"]) == 0
    text, moments, waypoint = spans.calls[0]
    assert "COMMITTED repo " in text
    assert waypoint == "W1"
    assert 0 < moments.submit_ns <= moments.lease_ns <= moments.end_ns


def test_a_submission_time_left_by_the_first_process_is_kept(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The re-exec'd process reads SUBMIT_ENV: the queued span starts when the first one began."""
    root = _held_repo(tmp_path, monkeypatch)
    left = 12345
    monkeypatch.setenv(commit_span.SUBMIT_ENV, str(left))
    spans = _Spans()
    monkeypatch.setattr(ck, "_emit_spans", spans)
    assert ck.main([str(root), "--waypoint", "W1", "--subject", "subject", "a.txt"]) == 0
    assert spans.calls[0][1].submit_ns == left


def test_a_malformed_submission_time_reads_as_now_and_ship_still_ships(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The controls: garbage in SUBMIT_ENV does not crash the commit, and --ship is not lost."""
    root = _held_repo(tmp_path, monkeypatch)
    monkeypatch.setenv(commit_span.SUBMIT_ENV, "not-a-number")
    shipped: list[str] = []

    def record(text: str) -> int:
        shipped.append(text)
        return 0

    monkeypatch.setattr(ck, "ship_text", record)
    monkeypatch.setattr(ck, "_emit_spans", _Spans())
    assert ck.main([str(root), "--waypoint", "W1", "--subject", "s", "--ship", "a.txt"]) == 0
    assert len(shipped) == 1


def _no_fence(*_args: object) -> str:
    # The empty reason: no claim to exec and none missing, so the commit queues and runs (W1696).
    return ""


class _Counts:
    """A recorder standing in for the live-count writer, remembering each state it was given."""

    def __init__(self) -> None:
        self.states: list[str | None] = []

    def __call__(self, ledger: object, key: str, state: str | None, env: object) -> None:
        del ledger, key, env
        self.states.append(state)


def test_a_commit_that_holds_the_claim_counts_in_flight_then_ends(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Under HELD_ENV the commit was queued by its parent: it records in flight, then its end."""
    root = _held_repo(tmp_path, monkeypatch)
    monkeypatch.setattr(ck, "_emit_spans", _Spans())
    counts = _Counts()
    monkeypatch.setattr(ck, "_note_counts", counts)
    assert ck.main([str(root), "--waypoint", "W1", "--subject", "s", "a.txt"]) == 0
    assert counts.states == [commit_counts.INFLIGHT, None]


def test_a_commit_that_had_to_queue_counts_queued_in_flight_and_ends(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without the claim in hand: queued first, then in flight, then its end."""
    root = _held_repo(tmp_path, monkeypatch)
    monkeypatch.delenv(ck.HELD_ENV)
    monkeypatch.setattr(ck, "claim_of", _no_fence)
    monkeypatch.setattr(ck, "_emit_spans", _Spans())
    counts = _Counts()
    monkeypatch.setattr(ck, "_note_counts", counts)
    assert ck.main([str(root), "--waypoint", "W1", "--subject", "s", "a.txt"]) == 0
    assert counts.states == [commit_counts.QUEUED, commit_counts.INFLIGHT, None]


def test_a_commit_that_raises_still_ends_its_count(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The control: an exception inside the commit must not leave it counted as in flight."""
    root = _held_repo(tmp_path, monkeypatch)
    counts = _Counts()
    monkeypatch.setattr(ck, "_note_counts", counts)

    def explode(*_args: object) -> int:
        msg = "boom"
        raise RuntimeError(msg)

    monkeypatch.setattr(ck, "run_held", explode)
    with pytest.raises(RuntimeError, match="boom"):
        ck.main([str(root), "--waypoint", "W1", "--subject", "s", "a.txt"])
    assert counts.states[-1] is None
