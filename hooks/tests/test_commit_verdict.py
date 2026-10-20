# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the verdict counter: one bounded sample per printed verdict (W1730).

⚑ NO PROGRAM IS STARTED: the spawn is a recorder. The controls are the failures the sample must
survive (no store, a child that cannot start) and the labels that must NOT carry the subject.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.hooks import commit_verdict

if TYPE_CHECKING:
    from collections.abc import Sequence

ENV = {"MIKEMOL_OTLP_BIN": "/opt/mikemol-otlp", "MIKEMOL_ENDPOINTS": "/host/endpoints.json"}
NO_STORE = {"MIKEMOL_OTLP_BIN": "/opt/mikemol-otlp"}
COMMITTED = "COMMITTED mtools abc1234 W1: a subject that must not become a label [pushed]"
REFUSED = "REFUSED mtools (rc=1): the cause is above; HEAD is still abc1234"
MARKS = "pre-commit: phase lint 100\npre-commit: phase bazel 200\nbazel output\n"
WITHDRAWN_RC = 75


def _fields(argv: Sequence[str]) -> list[str]:
    return [argv[i + 1] for i, part in enumerate(argv) if part == "--field"]


def test_each_verdict_line_reads_as_one_of_the_named_kinds() -> None:
    """The four lines the commit prints, and the control: an unknown line is not a commit."""
    assert commit_verdict.kind_of(COMMITTED, 0) == "COMMITTED"
    assert commit_verdict.kind_of(REFUSED, 1) == "REFUSED"
    assert commit_verdict.kind_of("NOT COMMITTED mtools: exit 0 but HEAD did not move", 1) == (
        "NOT_COMMITTED"
    )
    assert commit_verdict.kind_of("RACED mtools: HEAD moved", 1) == "RACED"
    assert commit_verdict.kind_of("something else", 1) == "NOT_COMMITTED"


def test_a_refusal_at_the_withdraw_exit_is_withdrawn_and_any_other_is_refused() -> None:
    """The gate's exit 75 is the withdraw marker read at a phase boundary."""
    assert commit_verdict.kind_of(REFUSED, WITHDRAWN_RC) == "WITHDRAWN"
    assert commit_verdict.kind_of(REFUSED, 1) == "REFUSED"
    assert commit_verdict.kind_of(COMMITTED, WITHDRAWN_RC) == "COMMITTED"


def test_the_stage_is_the_last_phase_the_output_marked_or_a_dash() -> None:
    """The control for the dash: output without a mark names no stage."""
    assert commit_verdict.stage_of(MARKS) == "bazel"
    assert commit_verdict.stage_of("no marks here\n") == "-"


def test_the_sample_is_a_one_labelled_by_repo_verdict_and_stage_alone() -> None:
    """No subject, sha or check label reaches a series."""
    argv = commit_verdict.plan("/bin/otlp", "mtools", "REFUSED", "bazel")
    assert argv[:2] == ["/bin/otlp", "metric"]
    assert argv[argv.index("--name") + 1] == "mikemol.commit.verdict"
    assert argv[argv.index("--value") + 1] == "1"
    assert _fields(argv) == ["repo=mtools", "verdict=REFUSED", "stage=bazel"]


def test_emit_sends_one_sample_for_a_printed_verdict() -> None:
    """The kind and the stage come from the line, the exit and the gate's output."""
    spawned: list[Sequence[str]] = []
    assert commit_verdict.emit("mtools", (REFUSED, 1, MARKS), ENV, spawned.append)
    assert len(spawned) == 1
    assert _fields(spawned[0]) == ["repo=mtools", "verdict=REFUSED", "stage=bazel"]


def test_no_store_or_a_failed_spawn_sends_nothing_and_raises_nothing() -> None:
    """Fire and forget: the verdict is already printed."""
    spawned: list[Sequence[str]] = []
    assert not commit_verdict.emit("mtools", (COMMITTED, 0, ""), NO_STORE, spawned.append)
    assert not spawned

    def failing(_argv: Sequence[str]) -> None:
        raise OSError

    assert not commit_verdict.emit("mtools", (COMMITTED, 0, ""), ENV, failing)
