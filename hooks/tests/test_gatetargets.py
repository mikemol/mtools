# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol-gate-targets`: a gate's fresh targets become rows, cached ones do not.

W1783, W1735. ⚑ THE CACHED RESULT IS THE NEGATIVE CONTROL: a result bazel replayed is not a
measurement of this run, so no row may carry it, and the per-run count says how many were fresh,
zero included. The build events are written by the test in bazel's own shape (read from a real
`--build_event_json_file`), the logs are files under `tmp_path`, and the send is a recording seam,
so nothing here starts a process or reaches a store.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from mikemol.hooks import commit_span, gatetargets

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    import pytest

_MUTANT = "//hooks:mutants_17"
_PYTEST = "//hooks:test_gatejobs"
_OTHER = "//hooks:ruff"
_START_MS = 1_792_000_000_000
_WALL_MS = 12_500
_FINISHED_NS = (_START_MS + _WALL_MS) * gatetargets.MILLIS
_NOW_NS = 7
_LOG = "x\nshard cpu=63.5s children=4 idle_wall=15.9s\ny\n"
_CPU_S = 63.5
_CHILDREN = 4
_WALL_S = 12.5
_RETRY_WALL_MS = 2000
_RETRY_WALL_S = 2.0
_STARTED_EVENT = '{"id": {"started": {}}}'
_ONE = 1
_TWO = 2


def _event(
    label: str,
    *,
    cached: bool = False,
    remote: bool = False,
    wall_ms: int = _WALL_MS,
    status: str | None = gatetargets.PASSED,
) -> str:
    info: dict[str, object] = {"cachedRemotely": remote}
    result: dict[str, object] = {
        "testAttemptDurationMillis": str(wall_ms),
        "testAttemptStartMillisEpoch": str(_START_MS),
        "cachedLocally": cached,
        "executionInfo": info,
    }
    if status is not None:
        result["status"] = status
    key: dict[str, object] = {"label": label, "run": 1, "shard": 1, "attempt": 1}
    event: dict[str, object] = {"id": {"testResult": key}, "testResult": result}
    return json.dumps(event)


def _reader(logs: dict[str, str]) -> gatetargets.Reader:
    def read(label: str) -> str | None:
        return logs.get(label)

    return read


def _names(rows: Sequence[gatetargets.Row]) -> list[object]:
    return [row["name"] for row in rows]


def test_a_test_result_gives_its_label_wall_time_and_finish_time() -> None:
    """The build event's fields, converted: milliseconds to seconds, start plus wall to ns."""
    [result] = gatetargets.results_of([_event(_MUTANT)])
    expected = gatetargets.Result(
        _MUTANT, _WALL_S, cached=False, finished_ns=_FINISHED_NS, status=gatetargets.PASSED
    )
    assert result == expected


def test_a_replayed_result_is_cached_whether_locally_or_remotely() -> None:
    """Both cache flags mean the measurement is an old one."""
    assert gatetargets.results_of([_event(_MUTANT, cached=True)])[0].cached
    assert gatetargets.results_of([_event(_PYTEST, remote=True)])[0].cached
    assert not gatetargets.results_of([_event(_OTHER)])[0].cached


def test_noise_in_the_file_is_skipped_and_the_last_attempt_of_a_target_wins() -> None:
    """Not JSON, not a test result, a label that is no label: skipped; a retry replaces."""
    lines = [
        "not json",
        _STARTED_EVENT,
        _event("not a label"),
        _event(_MUTANT, wall_ms=1000),
        _event(_PYTEST),
        _event(_MUTANT, wall_ms=_RETRY_WALL_MS),
    ]
    results = gatetargets.results_of(lines)
    assert [r.label for r in results] == [_MUTANT, _PYTEST]
    assert results[0].wall_s == _RETRY_WALL_S


def test_a_kind_is_mutants_pytest_or_other() -> None:
    """The three kinds the contract names, and the bare target of an unsharded grid."""
    assert gatetargets.kind_of(_MUTANT) == gatetargets.MUTANTS
    assert gatetargets.kind_of("//ratchet:mutants") == gatetargets.MUTANTS
    assert gatetargets.kind_of(_PYTEST) == gatetargets.PYTEST
    assert gatetargets.kind_of(_OTHER) == gatetargets.OTHER


def test_the_shard_line_gives_cpu_seconds_and_children_or_nothing() -> None:
    """W1769's line is read from anywhere in a log; no line, no values."""
    assert gatetargets.shard_line(_LOG) == (_CPU_S, _CHILDREN)
    assert gatetargets.shard_line("no such line\n") is None


def test_a_log_is_read_from_the_package_and_target_directory(tmp_path: Path) -> None:
    """`testlogs/<package>/<name>/test.log`; an absent file reads as None."""
    folder = tmp_path / "hooks" / "mutants_17"
    folder.mkdir(parents=True)
    (folder / "test.log").write_text(_LOG, encoding="utf-8")
    read = gatetargets.log_reader(tmp_path)
    assert read(_MUTANT) == _LOG
    assert read("//hooks:absent") is None


def test_a_fresh_mutants_target_gives_wall_cpu_and_children_rows_at_its_finish_time() -> None:
    """The per-run count leads; the target's rows carry the target and kind and its own time."""
    results = gatetargets.results_of([_event(_MUTANT)])
    rows = gatetargets.rows_of(results, _reader({_MUTANT: _LOG}), _NOW_NS)
    assert _names(rows) == [
        gatetargets.EMITTED,
        gatetargets.WALL,
        gatetargets.FAILED,
        gatetargets.CPU,
        gatetargets.CHILDREN,
    ]
    assert rows[0]["value"] == _ONE
    assert rows[0]["time_ns"] == _NOW_NS
    cpu = rows[3]
    assert cpu["value"] == _CPU_S
    assert cpu["time_ns"] == _FINISHED_NS
    assert cpu["fields"] == {"target": _MUTANT, "kind": gatetargets.MUTANTS}


def test_a_cached_target_gives_no_rows_and_a_fully_cached_run_says_zero() -> None:
    """The negative control: nothing from a replayed result, and the count is 0, not absent."""
    results = gatetargets.results_of([_event(_MUTANT, cached=True), _event(_PYTEST, cached=True)])
    rows = gatetargets.rows_of(results, _reader({_MUTANT: _LOG}), _NOW_NS)
    assert _names(rows) == [gatetargets.EMITTED]
    assert not rows[0]["value"]


def test_a_pytest_target_gives_only_its_wall_time_and_a_log_without_the_line_adds_nothing() -> None:
    """CPU and children are mutants-only (nothing else prints the line); no line, no CPU row."""
    results = gatetargets.results_of([_event(_PYTEST), _event(_MUTANT)])
    rows = gatetargets.rows_of(results, _reader({_PYTEST: _LOG, _MUTANT: "no line"}), _NOW_NS)
    wall, failed = gatetargets.WALL, gatetargets.FAILED
    assert _names(rows) == [gatetargets.EMITTED, wall, failed, wall, failed]
    assert rows[0]["value"] == _TWO


def test_a_target_that_did_not_pass_is_one_and_a_passing_one_is_zero() -> None:
    """The target half of a failure history: 1.0 for any final status but PASSED, else 0.0."""
    lines = [
        _event(_MUTANT, status="FAILED"),
        _event(_PYTEST, status="TIMEOUT"),
        _event(_OTHER, status=gatetargets.PASSED),
    ]
    rows = gatetargets.rows_of(gatetargets.results_of(lines), _reader({}), _NOW_NS)
    failed = [(row["fields"], row["value"]) for row in rows if row["name"] == gatetargets.FAILED]
    assert failed == [
        ({"target": _MUTANT, "kind": gatetargets.MUTANTS}, 1.0),
        ({"target": _PYTEST, "kind": gatetargets.PYTEST}, 1.0),
        ({"target": _OTHER, "kind": gatetargets.OTHER}, 0.0),
    ]


def test_a_result_with_no_status_gives_no_failed_row_and_a_replay_gives_none() -> None:
    """No status is no claim either way, and a cached result is not this run's."""
    lines = [_event(_MUTANT, status=None), _event(_PYTEST, cached=True, status="FAILED")]
    rows = gatetargets.rows_of(gatetargets.results_of(lines), _reader({}), _NOW_NS)
    assert gatetargets.FAILED not in _names(rows)


def test_rows_are_chunked_and_every_one_carries_the_repo_label() -> None:
    """One `metrics` child per CHUNK rows, JSON lines on its stdin, `repo` on every row."""
    row = gatetargets.rows_of([], _reader({}), _NOW_NS)[0]
    sends = gatetargets.plan("/bin/otlp", "mtools", [row] * (gatetargets.CHUNK + _ONE))
    assert len(sends) == _TWO
    argv, text = sends[0]
    assert argv[:_TWO] == ["/bin/otlp", "metrics"]
    assert argv[argv.index("--namespace") + _ONE] == "mtools"
    lines = text.splitlines()
    assert len(lines) == gatetargets.CHUNK
    assert '"repo": "mtools"' in lines[0]


def test_nothing_is_sent_without_a_binary_or_a_store_and_a_failed_spawn_is_false(
    tmp_path: Path,
) -> None:
    """Best effort: no program, no store, an OS error all return False and raise nothing."""
    sent: list[str] = []
    rows = gatetargets.rows_of([], _reader({}), _NOW_NS)

    def record(argv: Sequence[str], text: str) -> None:
        del argv
        sent.append(text)

    def broken(argv: Sequence[str], text: str) -> None:
        del argv, text
        raise OSError

    named = {commit_span.BIN_ENV: "/bin/otlp", commit_span.ENDPOINTS_ENV: "x"}
    assert not gatetargets.emit("mtools", rows, {"HOME": str(tmp_path)}, record)
    assert not gatetargets.emit("mtools", rows, {commit_span.BIN_ENV: "/bin/otlp"}, record)
    assert not sent
    assert gatetargets.emit("mtools", rows, named, record)
    assert len(sent) == _ONE
    assert not gatetargets.emit("mtools", rows, named, broken)


def test_main_reads_the_files_and_reports_and_a_wrong_call_is_usage(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The entry: three arguments or usage; an unreadable BEP is usage; success prints counts."""
    bep = tmp_path / "bep.json"
    bep.write_text(_event(_MUTANT) + "\n" + _event(_PYTEST, cached=True) + "\n", encoding="utf-8")
    monkeypatch.delenv(commit_span.BIN_ENV, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert not gatetargets.main(["mtools", str(bep), str(tmp_path)])
    assert "1 fresh of 2, sent=False" in capsys.readouterr().out
    assert gatetargets.main(["mtools"]) == gatetargets.EXIT_USAGE
    missing = gatetargets.main(["mtools", str(tmp_path / "absent"), str(tmp_path)])
    assert missing == gatetargets.EXIT_USAGE


_RUN_S = 90.0


def _build_events(start_ms: int | str, finish_ms: int | str) -> list[str]:
    started: dict[str, object] = {"id": {"started": {}}, "started": {"startTimeMillis": start_ms}}
    finished: dict[str, object] = {
        "id": {"buildFinished": {}},
        "finished": {"overallSuccess": True, "finishTimeMillis": finish_ms},
    }
    return [json.dumps(started), json.dumps(finished)]


def test_the_gate_wall_time_is_the_finished_event_minus_the_started_one() -> None:
    """int64 milliseconds arrive as JSON strings; the difference is seconds."""
    assert gatetargets.run_seconds(_build_events("1000", "91000")) == _RUN_S
    assert gatetargets.run_seconds(_build_events(1000, 91000)) == _RUN_S


def test_a_gate_wall_time_needs_both_events_in_order_or_it_is_none() -> None:
    """One event, no event, a finish before the start and a non-number each say nothing."""
    started, finished = _build_events("1000", "91000")
    assert gatetargets.run_seconds([started, "not json"]) is None
    assert gatetargets.run_seconds([finished]) is None
    assert gatetargets.run_seconds([]) is None
    assert gatetargets.run_seconds(_build_events("91000", "1000")) is None
    assert gatetargets.run_seconds(_build_events("soon", "later")) is None


def test_main_sends_the_gate_wall_time_beside_the_target_rows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The run row has no target or kind and rides in the same batch as the others."""
    bep = tmp_path / "bep.json"
    lines = [*_build_events("1000", "91000"), _event(_PYTEST)]
    bep.write_text("\n".join(lines) + "\n", encoding="utf-8")
    monkeypatch.setenv(commit_span.BIN_ENV, "/bin/otlp")
    monkeypatch.setenv(commit_span.ENDPOINTS_ENV, "x")
    sent: list[str] = []

    def record(argv: Sequence[str], text: str) -> None:
        del argv
        sent.append(text)

    assert not gatetargets.main(["mtools", str(bep), str(tmp_path)], record)
    last = sent[-1].splitlines()[-1]
    assert f'"name": "{gatetargets.RUN_SECONDS}"' in last
    assert f'"value": {_RUN_S}' in last
    assert '"fields": {"repo": "mtools"}' in last
