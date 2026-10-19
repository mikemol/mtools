# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A train is one span with its counts as fields, sent only when something was joined (W1676)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.hooks import traintel

if TYPE_CHECKING:
    from collections.abc import Sequence

_WINDOW = (1_000, 2_000)
_ENV = {"MIKEMOL_ENDPOINTS": "x", "MIKEMOL_OTLP_BIN": "/bin/otlp"}
_NO_STORE = {"MIKEMOL_OTLP_BIN": "/bin/otlp"}
_BAD = traintel.Stats(joined=3, gates=4, bisect_steps=2, rounds=2, landed=2, refused=1)
_GOOD = traintel.Stats(joined=3, gates=1, rounds=1, landed=3)


def test_the_argv_carries_the_service_window_status_and_every_count_as_a_field() -> None:
    """A refused stack makes the span an error; the counts are fields a panel can group by."""
    argv = traintel.argv_for("/bin/otlp", "mtools", _BAD, _WINDOW)
    assert argv[:2] == ["/bin/otlp", "trace"]
    assert argv[argv.index("--service") + 1] == "mikemol-train"
    assert argv[argv.index("--status") + 1] == "ERROR"
    assert argv[argv.index("--start-ns") + 1] == "1000"
    assert argv[argv.index("--end-ns") + 1] == "2000"
    fields = [argv[i + 1] for i, a in enumerate(argv) if a == "--field"]
    assert "gates=4" in fields
    assert "bisect_steps=2" in fields
    assert "joined=3" in fields
    good = traintel.argv_for("/bin/otlp", "mtools", _GOOD, _WINDOW)
    assert good[good.index("--status") + 1] == "OK"


def test_emit_spawns_once_for_a_joined_train_and_never_for_a_train_of_one() -> None:
    """A leader that joined nobody is not a train and leaves no record."""
    spawned: list[Sequence[str]] = []
    assert traintel.emit("mtools", _GOOD, _WINDOW, _ENV, spawned.append)
    assert len(spawned) == 1
    alone = traintel.Stats(joined=1, gates=1, rounds=1, landed=1)
    assert not traintel.emit("mtools", alone, _WINDOW, _ENV, spawned.append)
    assert len(spawned) == 1


def test_the_considered_counter_is_a_metric_of_one_with_the_followers_found() -> None:
    """The continuous sibling: name, value 1, namespace the repo, followers as a field."""
    argv = traintel.considered_argv("/bin/otlp", "mtools", 2)
    assert argv[:2] == ["/bin/otlp", "metric"]
    assert argv[argv.index("--name") + 1] == "mikemol.train.considered"
    assert argv[argv.index("--value") + 1] == "1"
    assert argv[argv.index("--namespace") + 1] == "mtools"
    assert "followers=2" in argv


def test_consider_ticks_even_when_nobody_was_found_and_is_silent_without_a_store() -> None:
    """Unlike the train span, the counter is sent for zero followers, so a quiet one is dark."""
    spawned: list[Sequence[str]] = []
    assert traintel.consider("mtools", 0, _ENV, spawned.append)
    assert len(spawned) == 1
    assert not traintel.consider("mtools", 0, _NO_STORE, spawned.append)
    assert len(spawned) == 1


def test_no_store_or_a_failed_spawn_sends_nothing_and_raises_nothing() -> None:
    """Fire and forget: a missing store or a spawn error never reaches the verdict."""
    spawned: list[Sequence[str]] = []
    assert not traintel.emit("mtools", _GOOD, _WINDOW, _NO_STORE, spawned.append)

    def failing(_argv: Sequence[str]) -> None:
        raise OSError

    assert not traintel.emit("mtools", _GOOD, _WINDOW, _ENV, failing)
    assert not spawned
