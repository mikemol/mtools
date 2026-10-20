# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A withdrawn gate's bazel client is interrupted, the server and the group never (W1757)."""

import json
import signal
from pathlib import Path

from mikemol.hooks import bazelstop, commit_counts, commit_withdraw

_STARTED = "100"
_GATE_PID = 5000
_BASH = 5001
_CLIENT = 5002
_GRANDCHILD_CLIENT = 5003
_SERVER = 6000
_OTHER_CLIENT = 7000
_TABLE: list[bazelstop.Process] = [
    (_GATE_PID, 1, "mikemol-commit"),
    (_BASH, _GATE_PID, "bash"),
    (_CLIENT, _BASH, "bazel"),
    (_GRANDCHILD_CLIENT, _CLIENT, "bazel-8.4.2-linux-x86_64"),
    (_SERVER, 1, "bazel"),
    (_OTHER_CLIENT, 1, "bazel"),
]

type Entry = dict[str, str | int | list[str]]


class _Kills:
    """A stand-in for `os.kill` that remembers each call and can say a process is gone."""

    def __init__(self, gone: frozenset[int] = frozenset()) -> None:
        self.calls: list[tuple[int, int]] = []
        self.gone = gone

    def __call__(self, pid: int, sig: int) -> None:
        if pid in self.gone:
            raise ProcessLookupError
        self.calls.append((pid, sig))


def _probe(_pid: int) -> str | None:
    return _STARTED


def _table() -> list[bazelstop.Process]:
    return _TABLE


def test_only_bazels_own_names_are_clients() -> None:
    """The launcher, bazelisk and the versioned download count; a shell or the tool does not."""
    assert bazelstop.is_client("bazel")
    assert bazelstop.is_client("bazelisk")
    assert bazelstop.is_client("bazel-8.4.2-linux-x86_64")
    assert not bazelstop.is_client("bash")
    assert not bazelstop.is_client("mikemol-commit")


def test_the_clients_are_the_descendants_of_the_gate_never_the_server_or_a_stranger() -> None:
    """A detached server and an unrelated client are not under the gate, so they are not named."""
    assert bazelstop.clients_under(_GATE_PID, _TABLE) == [_CLIENT, _GRANDCHILD_CLIENT]


def test_each_client_is_sent_sigint_and_one_that_already_exited_is_skipped() -> None:
    """Bazel's own cancellation is SIGINT, and a client gone by now is not an error."""
    kills = _Kills(gone=frozenset({_GRANDCHILD_CLIENT}))
    assert bazelstop.interrupt(_GATE_PID, kills, _table) == [_CLIENT]
    assert kills.calls == [(_CLIENT, signal.SIGINT)]


def test_withdrawing_an_in_flight_gate_interrupts_its_client_and_still_writes_the_marker(
    tmp_path: Path,
) -> None:
    """The marker stays as the fallback, and the line says which client was interrupted."""
    path = tmp_path / "c"
    entry: Entry = {
        "state": commit_counts.INFLIGHT,
        "pid": _GATE_PID,
        "start": _STARTED,
        "waypoints": ["W9"],
    }
    entries: dict[str, Entry] = {"20": entry}
    path.write_text(json.dumps(entries), encoding="utf-8")
    kills = _Kills()
    code, text = commit_withdraw.withdraw(path, "20", _probe, kills, _table)
    assert code == commit_withdraw.EXIT_WITHDRAWN
    assert f"bazel client was interrupted (pid {_CLIENT}, {_GRANDCHILD_CLIENT})" in text
    assert commit_withdraw.marker_path(path, "20").is_file()
    assert kills.calls == [(_CLIENT, signal.SIGINT), (_GRANDCHILD_CLIENT, signal.SIGINT)]
