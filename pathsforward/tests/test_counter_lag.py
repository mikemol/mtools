# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`--regressions` warns when the committed queue counter trails the working one (W2264).

⚑ THE BOUND IS LEARNED, NOT TYPED: the median rise of the counter between the queue file's own
commits, times the lag tolerated. The controls: a fast queue is allowed a bigger lag than a slow
one, a history with no rise gives the minimum, a lag within the bound says nothing, and the warning
never changes the exit status.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from mikemol.pathsforward import cli, landed, regressions

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    import pytest


def _queue_text(counter: int) -> str:
    doc: dict[str, object] = {"counter": counter, "waypoints": [], "residue": []}
    return json.dumps(doc)


def _history(counters: list[int]) -> Callable[[Path, str, int], list[int]]:
    def read(root: Path, rel: str, count: int) -> list[int]:
        del root, rel, count
        return counters

    return read


def test_the_bound_is_the_tolerated_commits_times_the_median_rise() -> None:
    """Counters newest first: rises 10, 10, 40 have median 10, so the bound is 2 x 10."""
    assert regressions.cadence_bound([100, 90, 80, 40]) == regressions.TOLERATED_COMMITS * 10
    assert regressions.cadence_bound([100, 98, 96]) == regressions.TOLERATED_COMMITS * 2


def test_a_history_with_no_rise_gives_the_minimum_not_a_pass() -> None:
    """No cadence yet means strict: an empty list, one counter or a flat one is MIN_BOUND."""
    for counters in ([], [5], [7, 7, 7]):
        assert regressions.cadence_bound(counters) == regressions.MIN_BOUND


def test_a_faster_queue_is_allowed_a_bigger_lag() -> None:
    """The same lag of 30 warns for a slow queue and not for a fast one."""
    head: dict[str, object] = {"counter": 100}
    staged: dict[str, object] = {"counter": 130}
    slow = regressions.cadence_bound([100, 98, 96, 94])
    fast = regressions.cadence_bound([100, 80, 60, 40])
    assert regressions.counter_lag(head, staged, slow) is not None
    assert regressions.counter_lag(head, staged, fast) is None


def test_the_counters_are_read_from_each_commit_of_the_queue_file(tmp_path: Path) -> None:
    """Each sha git lists is shown and its counter read; one without a counter is skipped."""
    shown: dict[str, str] = {"a": '{"counter": 30}', "b": "{}", "c": '{"counter": 10}'}

    def run(argv: list[str]) -> str | None:
        if "log" in argv:
            return "a\nb\nc\n"
        return shown[argv[-1].split(":")[0]]

    got = landed.queue_counters(tmp_path, ".claude/paths-forward.json", 3, run)
    assert got == [30, 10]


def test_only_the_top_level_counter_is_read_whatever_the_key_order_or_a_card_field(
    tmp_path: Path,
) -> None:
    """A waypoint field named counter that comes first must not win over the queue's own."""
    first: dict[str, object] = {"waypoints": [{"counter": 99}], "counter": 5}
    shown: dict[str, str] = {"a": json.dumps(first), "b": '{"counter": 7, "waypoints": []}'}

    def run(argv: list[str]) -> str | None:
        if "log" in argv:
            return "a\nb\n"
        return shown[argv[-1].split(":")[0]]

    assert landed.queue_counters(tmp_path, "q.json", 2, run) == [5, 7]


def test_a_copy_that_is_not_an_object_or_has_no_integer_counter_is_skipped(tmp_path: Path) -> None:
    """Text that is not JSON, a list, a string counter and a boolean counter all read as none."""
    shown: dict[str, str] = {
        "a": "not json {",
        "b": "[1, 2]",
        "c": '{"counter": "5"}',
        "d": '{"counter": true}',
        "e": '{"counter": 8}',
    }

    def run(argv: list[str]) -> str | None:
        if "log" in argv:
            return "a\nb\nc\nd\ne\n"
        return shown[argv[-1].split(":")[0]]

    assert landed.queue_counters(tmp_path, "q.json", 5, run) == [8]


def test_the_command_warns_about_a_lag_and_still_exits_clean(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The warning goes to stderr; the exit status is the loss check's alone."""
    queue = tmp_path / ".claude" / "paths-forward.json"
    queue.parent.mkdir()
    queue.write_text(_queue_text(130), encoding="utf-8")
    head = tmp_path / "head.json"
    head.write_text(_queue_text(100), encoding="utf-8")
    monkeypatch.setattr(landed, "queue_counters", _history([100, 98, 96, 94]))
    assert cli.main(["--state", str(queue), "--regressions", str(head)]) == cli.EXIT_OK
    said = capsys.readouterr().err
    assert "the committed queue counter (100) trails the working queue's (130)" in said
    monkeypatch.setattr(landed, "queue_counters", _history([100, 80, 60, 40]))
    assert cli.main(["--state", str(queue), "--regressions", str(head)]) == cli.EXIT_OK
    assert "trails" not in capsys.readouterr().err
