# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the flaky-pass gauge: one absolute value per recorded flake (W2009).

⚑ NO PROGRAM IS STARTED: the spawn is a recorder and the git directory is a temp path. The controls
are the failures the number must survive: no store configured (nothing spawned), a child that cannot
be started (the commit sees no exception), and a log that does not exist (a count of zero).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.hooks import flakemetric, flakes

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

ENV = {"MIKEMOL_OTLP_BIN": "/opt/mikemol-otlp", "MIKEMOL_ENDPOINTS": "/host/endpoints.json"}
TWO = 2


def _flag(argv: Sequence[str], name: str) -> str:
    return argv[argv.index(name) + 1]


def _flaked_twice(git_dir: Path) -> None:
    # Two trees, each refused and then passed: two `flake` lines, and one clean pass beside them.
    for tree in ("t1", "t2"):
        flakes.record(git_dir, tree, flakes.REFUSED, ["bazel_test"])
        flakes.record(git_dir, tree, flakes.PASSED, [])
    flakes.record(git_dir, "t3", flakes.PASSED, [])


def test_the_count_is_the_flake_lines_not_the_verdicts(tmp_path: Path) -> None:
    """Six verdict lines and two flakes: the count is the flakes; an absent log is zero."""
    assert flakes.flake_count(tmp_path) == 0
    _flaked_twice(tmp_path)
    assert flakes.flake_count(tmp_path) == TWO


def test_the_plan_is_one_absolute_gauge_carrying_the_repo() -> None:
    """The name, the value and the repo as both namespace and attribute."""
    argv = flakemetric.plan("otlp", "myrepo", 5)
    assert _flag(argv, "--name") == flakemetric.NAME
    assert _flag(argv, "--value") == "5"
    assert _flag(argv, "--namespace") == "myrepo"
    assert _flag(argv, "--field") == "repo=myrepo"


def test_a_recorded_flake_starts_one_gauge_with_the_logs_count(tmp_path: Path) -> None:
    """The positive control: the child is started and carries the number the log holds."""
    _flaked_twice(tmp_path)
    started: list[Sequence[str]] = []
    assert flakemetric.emit(tmp_path, "myrepo", ENV, started.append) is True
    assert len(started) == 1
    assert _flag(started[0], "--value") == str(TWO)


def test_without_a_store_nothing_is_started(tmp_path: Path) -> None:
    """No MIKEMOL_ENDPOINTS and no HOME: the number is not shipped and nothing is spawned."""
    started: list[Sequence[str]] = []
    no_store = {"MIKEMOL_OTLP_BIN": "/opt/mikemol-otlp"}
    assert flakemetric.emit(tmp_path, "myrepo", no_store, started.append) is False
    assert not started


def test_a_child_that_cannot_start_never_raises_into_the_commit(tmp_path: Path) -> None:
    """A spawn raising OSError: False comes back and the exception does not."""

    def broken(argv: Sequence[str]) -> None:
        del argv
        raise OSError

    assert flakemetric.emit(tmp_path, "myrepo", ENV, broken) is False
