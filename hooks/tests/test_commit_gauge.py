# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the commit gauges: two absolute values per transition (W1446).

⚑ NO PROGRAM IS STARTED: the spawn is a recorder and the git directory is a temp path. The controls
are the failures the number must survive: no store configured (the map is still kept, nothing is
spawned), a map that cannot be written (the commit sees no exception), and a child that cannot be
started (the same).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.hooks import commit_counts, commit_gauge

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

ENV = {"MIKEMOL_OTLP_BIN": "/opt/mikemol-otlp", "MIKEMOL_ENDPOINTS": "/host/endpoints.json"}
TWO = 2


def _ledger(tmp_path: Path) -> Path:
    # The shape of a real ledger: <repo>/.git/mtools.
    ledger = tmp_path / "myrepo" / ".git" / "mtools"
    ledger.mkdir(parents=True)
    return ledger


def _flag(argv: Sequence[str], name: str) -> str:
    return argv[argv.index(name) + 1]


def test_the_plan_is_two_absolute_gauges_carrying_the_repo() -> None:
    """Queued first, in flight second, each with its own value and the repo as namespace."""
    argvs = commit_gauge.plan("otlp", "myrepo", commit_counts.Counts(3, 1))
    assert [_flag(a, "--name") for a in argvs] == [
        commit_gauge.QUEUED_NAME,
        commit_gauge.INFLIGHT_NAME,
    ]
    assert [_flag(a, "--value") for a in argvs] == ["3", "1"]
    assert all(_flag(a, "--namespace") == "myrepo" for a in argvs)
    assert all(_flag(a, "--field") == "repo=myrepo" for a in argvs)


def test_a_transition_keeps_the_map_and_starts_both_gauges(tmp_path: Path) -> None:
    """The positive control: the count is returned and two children are started for it."""
    started: list[Sequence[str]] = []
    ledger = _ledger(tmp_path)
    counts = commit_gauge.note(ledger, "k1", commit_counts.QUEUED, ENV, started.append)
    assert counts == commit_counts.Counts(1, 0)
    assert len(started) == TWO
    assert _flag(started[0], "--namespace") == "myrepo"


def test_without_a_store_the_map_is_kept_and_nothing_is_started(tmp_path: Path) -> None:
    """No MIKEMOL_ENDPOINTS: the count is right for the next commit, no child is spawned."""
    started: list[Sequence[str]] = []
    ledger = _ledger(tmp_path)
    no_store = {"MIKEMOL_OTLP_BIN": "/opt/mikemol-otlp"}
    first = commit_gauge.note(ledger, "k1", commit_counts.QUEUED, no_store, started.append)
    assert first == commit_counts.Counts(1, 0)
    assert not started
    assert (ledger / "commit.counts").is_file()


def test_an_unwritable_ledger_gives_none_and_never_raises(tmp_path: Path) -> None:
    """The control: the ledger path is a file, so the map cannot be made; the commit sees None."""
    blocked = tmp_path / "myrepo" / ".git" / "mtools"
    blocked.parent.mkdir(parents=True)
    blocked.write_text("a file where the directory should be", encoding="utf-8")
    assert commit_gauge.note(blocked, "k1", commit_counts.QUEUED, ENV) is None


def test_a_child_that_cannot_start_never_raises_into_the_commit(tmp_path: Path) -> None:
    """A spawn raising OSError: the counts come back and the exception does not."""

    def broken(argv: Sequence[str]) -> None:
        del argv
        raise OSError

    counts = commit_gauge.note(_ledger(tmp_path), "k1", commit_counts.INFLIGHT, ENV, broken)
    assert counts == commit_counts.Counts(0, 1)
