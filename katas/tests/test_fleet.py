# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `fleet`: git state per workstream, the flush decision, and the probe (W875).

⚑ EVERY CASE BUILDS ITS OWN REPOSITORIES under `tmp_path` with a real `git`, started through
`procrun.capture`; none reads the host's. The detached cases use a fake `mikemol-commit` script that
prints its argv, so what flush asked for is observed rather than inferred.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from mikemol.procrun.proc import capture

from mikemol.katas import commits, fleet

if TYPE_CHECKING:
    from pathlib import Path

_DEADLINE_S = 60.0
_POLL_S = 0.1
_EXECUTABLE = 0o755
_FIRST = "first subject"
_QUEUE_FILES = (".claude/paths-forward.json", ".claude/paths-forward.ledger")
_TWO_PENDING = 2


def _git(path: Path, *args: str) -> None:
    """Run git in `path` as a throwaway identity."""
    capture(("git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(path), *args))


def _repo(root: Path, name: str) -> Path:
    """Make a repo `name` under `root` with one commit holding a queue.

    Returns:
        the repo directory.

    """
    path = root / name
    (path / ".claude").mkdir(parents=True)
    capture(("git", "init", "-q", str(path)))
    for rel in _QUEUE_FILES:
        (path / rel).write_text("{}\n", encoding="utf-8")
    _git(path, "add", "-A")
    _git(path, "commit", "-q", "-m", _FIRST)
    return path


def _fleet(tmp_path: Path, skip: frozenset[str] = frozenset()) -> fleet.Fleet:
    """Build a fleet whose root and logs are under `tmp_path`.

    Returns:
        the fleet.

    """
    return fleet.Fleet(tmp_path / "hosts", tmp_path / "logs", skip)


def _touch_queue(path: Path) -> None:
    """Change a tracked queue file so the repo has a pending queue."""
    (path / ".claude" / "paths-forward.json").write_text('{"x": 1}\n', encoding="utf-8")


def _wait(log: Path) -> str:
    """Poll a detached log until it has ended or the deadline passes.

    Returns:
        the log's state then.

    """
    deadline = time.monotonic() + _DEADLINE_S
    while commits.commit_state(log) in {"", commits.RUNNING} and time.monotonic() < deadline:
        time.sleep(_POLL_S)
    return commits.commit_state(log)


def _fake_commit(tmp_path: Path) -> Path:
    """Write a stand-in `mikemol-commit` that prints its arguments and exits 0.

    Returns:
        the script's path.

    """
    script = tmp_path / "fake-commit"
    script.write_text('#!/bin/sh\nfor a in "$@"; do echo "ARG=$a"; done\n', encoding="utf-8")
    script.chmod(_EXECUTABLE)
    return script


def test_pending_counts_changed_queue_and_inbox_paths(tmp_path: Path) -> None:
    """A modified queue file and a new inbox letter are two pending paths."""
    host = _fleet(tmp_path)
    repo = _repo(host.root, "alpha")
    _touch_queue(repo)
    (repo / "inbox").mkdir()
    (repo / "inbox" / "letter.md").write_text("hi\n", encoding="utf-8")
    assert fleet.pending(host, "alpha") == _TWO_PENDING


def test_a_clean_repo_has_nothing_pending(tmp_path: Path) -> None:
    """Nothing differs from HEAD."""
    host = _fleet(tmp_path)
    _repo(host.root, "alpha")
    assert not fleet.pending(host, "alpha")
    assert not fleet.queue_pending(host, "alpha")


def test_an_inbox_letter_alone_is_not_a_pending_queue(tmp_path: Path) -> None:
    """The queue is the three files; a letter counts as pending but not as queue_pending."""
    host = _fleet(tmp_path)
    repo = _repo(host.root, "alpha")
    (repo / "inbox").mkdir()
    (repo / "inbox" / "letter.md").write_text("hi\n", encoding="utf-8")
    assert fleet.pending(host, "alpha")
    assert not fleet.queue_pending(host, "alpha")


def test_an_index_lock_means_a_commit_is_in_flight(tmp_path: Path) -> None:
    """Some commit, from any session, holds the index."""
    host = _fleet(tmp_path)
    repo = _repo(host.root, "alpha")
    assert not fleet.in_flight(host, "alpha")
    (repo / ".git" / "index.lock").touch()
    assert fleet.in_flight(host, "alpha")


def test_a_status_row_names_the_repo_its_pending_count_and_head(tmp_path: Path) -> None:
    """The row carries the name, `pending=` and the HEAD subject."""
    host = _fleet(tmp_path)
    repo = _repo(host.root, "alpha")
    _touch_queue(repo)
    row = fleet.status_row(host, "alpha")
    assert row.startswith("alpha")
    assert "pending=  1" in row
    assert _FIRST in row


def test_a_status_row_shows_in_flight_and_a_probe(tmp_path: Path) -> None:
    """A held index shows IN-FLIGHT, and a probe log shows its state beside it."""
    host = _fleet(tmp_path)
    repo = _repo(host.root, "alpha")
    (repo / ".git" / "index.lock").touch()
    host.logs.mkdir()
    fleet.log_of(host, "alpha", ".probe").write_text("out\n\nrc=1\n", encoding="utf-8")
    row = fleet.status_row(host, "alpha")
    assert fleet.IN_FLIGHT in row
    assert "probe:FAILED rc=1" in row


def test_status_has_one_row_per_workstream_in_order(tmp_path: Path) -> None:
    """Sorted, and only directories with a queue."""
    host = _fleet(tmp_path)
    _repo(host.root, "zulu")
    _repo(host.root, "alpha")
    (host.root / "plain").mkdir()
    rows = fleet.status(host)
    assert [row.split()[0] for row in rows] == ["alpha", "zulu"]


def test_flush_targets_are_the_repos_with_a_pending_queue(tmp_path: Path) -> None:
    """A clean repo is not a target; a repo with a changed queue file is."""
    host = _fleet(tmp_path)
    _repo(host.root, "clean")
    _touch_queue(_repo(host.root, "dirty"))
    assert fleet.flush_targets(host) == ["dirty"]


def test_the_fleet_skip_list_and_the_callers_both_exclude(tmp_path: Path) -> None:
    """The host's policy list and a one-off skip each keep a repo out."""
    host = _fleet(tmp_path, frozenset({"policy"}))
    for name in ("policy", "oneoff", "wanted"):
        _touch_queue(_repo(host.root, name))
    assert fleet.flush_targets(host, ["oneoff"]) == ["wanted"]


def test_a_repo_with_a_commit_in_flight_is_not_a_target(tmp_path: Path) -> None:
    """An index lock means someone is committing: do not start another."""
    host = _fleet(tmp_path)
    repo = _repo(host.root, "busy")
    _touch_queue(repo)
    (repo / ".git" / "index.lock").touch()
    assert not fleet.flush_targets(host)


def test_a_repo_whose_detached_commit_is_running_is_not_a_target(tmp_path: Path) -> None:
    """A log with no rc line yet is our own commit still going."""
    host = _fleet(tmp_path)
    _touch_queue(_repo(host.root, "going"))
    host.logs.mkdir()
    fleet.log_of(host, "going").write_text("working\n", encoding="utf-8")
    assert not fleet.flush_targets(host)


def test_flush_starts_a_detached_commit_with_the_sync_request(tmp_path: Path) -> None:
    """The fake commit tool receives the repo, the `none` waypoint and the sync subject."""
    host = _fleet(tmp_path)
    _touch_queue(_repo(host.root, "dirty"))
    started = fleet.flush(host, _fake_commit(tmp_path))
    log = fleet.log_of(host, "dirty")
    assert started == ["dirty"]
    assert _wait(log) == commits.DONE
    text = log.read_text(encoding="utf-8")
    assert "ARG=dirty" in text
    assert "ARG=none" in text
    assert f"ARG={fleet.SYNC_SUBJECT}" in text


def test_probe_refuses_a_repo_with_no_hook(tmp_path: Path) -> None:
    """Nothing to probe is a refusal naming the missing hook."""
    host = _fleet(tmp_path)
    _repo(host.root, "alpha")
    assert "no .githooks/pre-commit" in fleet.probe(host, "alpha")


def test_probe_refuses_while_a_commit_is_in_flight(tmp_path: Path) -> None:
    """The probe would collide with the live commit's lock."""
    host = _fleet(tmp_path)
    repo = _repo(host.root, "alpha")
    (repo / ".githooks").mkdir()
    (repo / ".githooks" / "pre-commit").write_text("exit 0\n", encoding="utf-8")
    (repo / ".git" / "index.lock").touch()
    assert "not probing" in fleet.probe(host, "alpha")


def test_probe_runs_the_hook_under_a_temp_index_and_cleans_up(tmp_path: Path) -> None:
    """The hook sees a GIT_INDEX_FILE, and the temp index and the held lock are gone after."""
    host = _fleet(tmp_path)
    repo = _repo(host.root, "alpha")
    (repo / ".githooks").mkdir()
    hook = 'echo "INDEX=$GIT_INDEX_FILE"\ntest -e .git/index.lock && echo "LOCK=held"\n'
    (repo / ".githooks" / "pre-commit").write_text(hook, "utf-8")
    assert not fleet.probe(host, "alpha")
    log = fleet.log_of(host, "alpha", ".probe")
    assert _wait(log) == commits.DONE
    text = log.read_text(encoding="utf-8")
    assert "next-index-probe.lock" in text
    assert "LOCK=held" in text
    assert not (repo / ".git" / "next-index-probe.lock").exists()
    assert not (repo / ".git" / "index.lock").exists()
