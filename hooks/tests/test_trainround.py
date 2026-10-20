# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A train round is recorded as it ends, with what the admission step held its gate to (W1715)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.hooks import trainround

if TYPE_CHECKING:
    from collections.abc import Sequence

OUTPUT = (
    "gate jobs=2 cores=24 load1=39.4 floor=2 (held at the floor)\n"
    "INFO: Invocation ID: 8064a6a1-39a4-40a5-8a60-dfb4d255af0e\n"
)
FACTS = trainround.GateFacts("2", "24", "39.4", "8064a6a1-39a4-40a5-8a60-dfb4d255af0e")
RED = trainround.RoundRecord(3, 4, "red", "bazel_test; check_hooks", 2, FACTS, (1_000, 2_000))
GREEN = trainround.RoundRecord(1, 2, "green", "", 1, trainround.GateFacts(), (1_000, 2_000))
ENV = {"MIKEMOL_ENDPOINTS": "x", "MIKEMOL_OTLP_BIN": "/bin/otlp"}
NO_STORE = {"MIKEMOL_OTLP_BIN": "/bin/otlp", "HOME": "/nonexistent"}
THREE = 3
TWO = 2


def _flag(argv: Sequence[str], name: str) -> str:
    return argv[argv.index(name) + 1]


def _fields(argv: Sequence[str]) -> dict[str, str]:
    pairs = [argv[i + 1] for i, part in enumerate(argv) if part == "--field"]
    return dict(pair.split("=", 1) for pair in pairs)


def test_the_gates_own_output_gives_the_admitted_jobs_the_load_and_the_invocation() -> None:
    """The throttle is read, not inferred: jobs, cores and load from the admission line."""
    assert trainround.facts_of(OUTPUT) == FACTS


def test_output_that_says_nothing_gives_empty_facts_not_zeros() -> None:
    """The control: an older hook's output has no admission line, and that is not 0 jobs."""
    assert trainround.facts_of("pre-commit: phase lint 1\n") == trainround.GateFacts()


def test_a_round_span_carries_the_round_the_verdict_the_failures_and_the_throttle() -> None:
    """A red round is an ERROR span over its own window, with every question's answer a field."""
    argv = trainround.span_argv("/bin/otlp", "mtools", RED)
    assert _flag(argv, "--status") == "ERROR"
    assert _flag(argv, "--name") == "train.round"
    assert (_flag(argv, "--start-ns"), _flag(argv, "--end-ns")) == ("1000", "2000")
    fields = _fields(argv)
    assert (fields["round"], fields["members"], fields["verdict"]) == ("3", "4", "red")
    assert fields["failed"] == "bazel_test; check_hooks"
    assert (fields["jobs"], fields["load1"]) == ("2", "39.4")
    assert fields["invocation"] == FACTS.invocation


def test_a_green_round_is_an_ok_span() -> None:
    """The control for the error status."""
    argv = trainround.span_argv("/bin/otlp", "mtools", GREEN)
    assert _flag(argv, "--status") == "OK"


def test_the_plan_is_the_span_the_round_sample_and_the_jobs_sample() -> None:
    """Three children when the gate said its jobs; two when it did not."""
    sends = trainround.plan("/bin/otlp", "mtools", RED)
    assert len(sends) == THREE
    assert _flag(sends[1], "--name") == "mikemol.train.round"
    assert _fields(sends[1]) == {"repo": "mtools", "verdict": "red"}
    assert _flag(sends[2], "--value") == "2"
    assert _fields(sends[2]) == {"repo": "mtools", "cores": "24"}
    assert len(trainround.plan("/bin/otlp", "mtools", GREEN)) == TWO


def test_emit_starts_every_child_and_is_silent_without_a_store_or_on_a_failed_spawn() -> None:
    """Fire and forget: the record never changes a verdict."""
    spawned: list[Sequence[str]] = []
    assert trainround.emit("mtools", RED, ENV, spawned.append)
    assert len(spawned) == THREE
    assert not trainround.emit("mtools", RED, NO_STORE, spawned.append)
    assert len(spawned) == THREE

    def failing(_argv: Sequence[str]) -> None:
        raise OSError

    assert not trainround.emit("mtools", RED, ENV, failing)
