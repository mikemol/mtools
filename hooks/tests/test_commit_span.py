# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the commit's three spans: one trace, two phases, the verdict's own status (W1440).

⚑ NO PROGRAM IS STARTED: the spawn is a recorder. The controls are what makes a trace lie: a child
span not pointing at the commit span, a phase boundary that is not shared (queued must END where
gating STARTS or the gap is time nobody accounts for), a refusal reading as OK, and a run with no
store configured or no verdict line starting anything.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.hooks import commit_kata, commit_span

if TYPE_CHECKING:
    from collections.abc import Sequence

    import pytest

COMMITTED = "COMMITTED mtools abc1234 W9: a subject [PUSHED]\n"
REFUSED = "pre-commit: gate jobs=4\nREFUSED mtools (rc=1): the cause is above\n"
MOMENTS = commit_span.Moments(100, 160, 400)
IDS = commit_span.Ids("t" * 32, "c" * 16, "q" * 16, "g" * 16)
THREE = 3
ENV = {commit_span.BIN_ENV: "/opt/mikemol-otlp", commit_span.ENDPOINTS_ENV: "/host/endpoints.json"}


def _plan(text: str) -> list[list[str]]:
    event = commit_span.verdict_of(text)
    assert event is not None
    return commit_span.plan("otlp", event, "W9", (IDS, commit_span.pieces(MOMENTS, IDS)))


def _flag(argv: Sequence[str], name: str) -> str:
    return argv[argv.index(name) + 1]


def test_the_verdict_is_the_last_verdict_line_and_nothing_else_counts() -> None:
    """Gate chatter before it is ignored; output with no verdict line gives no event."""
    event = commit_span.verdict_of(REFUSED)
    assert event is not None
    assert (event["verdict"], event["repo"]) == ("REFUSED", "mtools")
    assert commit_span.verdict_of("pre-commit: gate jobs=4\n") is None


def test_the_phases_meet_at_the_lease_and_together_cover_the_whole() -> None:
    """The wait ends where the gate starts, and the commit span is submit to verdict."""
    whole, queued, gating = commit_span.pieces(MOMENTS, IDS)
    assert (whole.start_ns, whole.end_ns) == (100, 400)
    assert (queued.start_ns, queued.end_ns) == (100, 160)
    assert (gating.start_ns, gating.end_ns) == (160, 400)
    assert queued.end_ns == gating.start_ns


def test_three_argvs_share_one_trace_and_the_children_name_the_commit_as_parent() -> None:
    """The commit span has no parent; both phases point at it; all three carry the trace id."""
    commit, queued, gating = _plan(COMMITTED)
    assert "--parent-id" not in commit
    assert _flag(queued, "--parent-id") == IDS.commit
    assert _flag(gating, "--parent-id") == IDS.commit
    assert {_flag(a, "--trace-id") for a in (commit, queued, gating)} == {IDS.trace}
    names = [_flag(a, "--name") for a in (commit, queued, gating)]
    assert names == ["commit", "commit.queued", "commit.gating"]


def test_attributes_name_the_repo_waypoint_sha_and_verdict() -> None:
    """The fields a panel groups by ride on every span, and the namespace is the repo."""
    commit = _plan(COMMITTED)[0]
    assert _flag(commit, "--namespace") == "mtools"
    fields = [commit[i + 1] for i, word in enumerate(commit) if word == "--field"]
    assert fields == ["repo=mtools", "waypoint=W9", "sha=abc1234", "verdict=COMMITTED"]


def test_a_refusal_is_an_error_span_and_a_landing_is_ok() -> None:
    """The control: REFUSED must not read as OK in the trace."""
    assert _flag(_plan(COMMITTED)[0], "--status") == "OK"
    assert _flag(_plan(REFUSED)[0], "--status") == "ERROR"


def test_emit_starts_three_children_when_a_binary_and_a_store_are_configured() -> None:
    """The positive control: configured and a verdict present, three spawns."""
    started: list[Sequence[str]] = []
    assert commit_span.emit(COMMITTED, MOMENTS, "W9", ENV, started.append) == THREE
    assert [a[0] for a in started] == ["/opt/mikemol-otlp"] * THREE


def test_emit_starts_nothing_without_a_store_or_a_verdict() -> None:
    """No MIKEMOL_ENDPOINTS, or no verdict line: silent, nothing spawned."""
    started: list[Sequence[str]] = []
    no_store = {commit_span.BIN_ENV: "/opt/mikemol-otlp"}
    assert commit_span.emit(COMMITTED, MOMENTS, "W9", no_store, started.append) == 0
    assert commit_span.emit("no verdict here\n", MOMENTS, "W9", ENV, started.append) == 0
    assert not started


def test_a_child_that_cannot_start_never_raises_into_the_commit() -> None:
    """The control: the first spawn raising OSError gives 0 started and no exception."""

    def broken(argv: Sequence[str]) -> None:
        del argv
        raise OSError

    assert commit_span.emit(COMMITTED, MOMENTS, "W9", ENV, broken) == 0


STACK_OK = (
    "COMMITTED mtools aaa1111 W1: first [PUSHED]\nCOMMITTED mtools bbb2222 W2: second [PUSHED]\n"
)
STACK_BAD = (
    "COMMITTED mtools aaa1111 W1: first [LOCAL]\nREFUSED mtools (rc=1): the cause is above\n"
)


def test_a_stack_folds_into_one_event_committed_only_when_every_entry_is() -> None:
    """Two COMMITTED lines make one COMMITTED event with both shas and the count."""
    event = commit_span.stack_event(STACK_OK)
    assert event is not None
    assert event["verdict"] == "COMMITTED"
    assert event["sha"] == "aaa1111,bbb2222"
    assert event["entries"] == "2"


def test_a_stack_with_one_refusal_reads_as_that_refusal() -> None:
    """The control: a COMMITTED then a REFUSED is REFUSED, so the trace is an ERROR."""
    event = commit_span.stack_event(STACK_BAD)
    assert event is not None
    assert event["verdict"] == "REFUSED"
    assert commit_span.stack_event("no verdict\n") is None


def test_a_stack_is_one_trace_named_commit_stack_with_its_waypoints_joined() -> None:
    """Three spans, not one per entry: the shared gate is counted once."""
    started: list[Sequence[str]] = []
    count = commit_span.emit_stack(STACK_OK, MOMENTS, ["W1", "W2"], ENV, started.append)
    assert count == THREE
    names = [_flag(a, "--name") for a in started]
    assert names == ["commit.stack", "commit.stack.queued", "commit.stack.gating"]
    fields = [started[0][i + 1] for i, word in enumerate(started[0]) if word == "--field"]
    assert "waypoint=W1,W2" in fields
    assert "entries=2" in fields


def test_the_tee_buffer_writes_through_and_keeps_a_copy(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Live output is unchanged: standard output sees each write at once, the buffer keeps it."""
    tee = commit_kata.TeeBuffer()
    assert tee.write("COMMITTED x\n") == len("COMMITTED x\n")
    assert capsys.readouterr().out == "COMMITTED x\n"
    assert tee.getvalue() == "COMMITTED x\n"
