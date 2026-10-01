# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the orchestrator: one process per stage, each holding one GPU context, in order.

No membudget runs and no child starts: the command runner is a fake that records what it was
asked to run.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.audiostruct.cli import LEDGER_ENV, MAXLOAD_ENV, Plan, orchestrate

if TYPE_CHECKING:
    from collections.abc import Mapping

_PLAN = Plan(
    membudget="/opt/fence/bin/mikemol-membudget",
    ledger="/gpu.ledger",
    program=["mikemol-audio"],
    workdir="/work",
    sources=["a.wav"],
)
# membudget's exit code when admission refuses a lease.
_REFUSED = 3


def test_each_stage_holds_one_context_on_the_named_ledger() -> None:
    """Three children, in stage order, each wrapped in `membudget hold 1` with its stage's label.

    ⚑ Every child gets the named ledger as MEMBUDGET_FILE and the load gate off, as the ledger's
    other user runs it. Without MEMBUDGET_FILE, membudget holds on its host-memory default and
    never contends with the GPU's other users.
    """
    ran: list[tuple[list[str], dict[str, str]]] = []

    def run(argv: list[str], env: Mapping[str, str]) -> int:
        ran.append((argv, dict(env)))
        return 0

    assert orchestrate(_PLAN, run) == 0
    assert [argv for argv, _ in ran] == [
        [
            "/opt/fence/bin/mikemol-membudget",
            "hold",
            "1",
            f"audiostruct-{stage}",
            "--",
            "mikemol-audio",
            "--stage",
            stage,
            "--workdir",
            "/work",
            "a.wav",
        ]
        for stage in ("transcribe", "align", "diarize")
    ]
    assert all(env == {LEDGER_ENV: "/gpu.ledger", MAXLOAD_ENV: "0"} for _, env in ran)


def test_the_first_failing_stage_stops_the_run() -> None:
    """A refused lease or a crashed stage returns its code, and no later stage starts."""
    labels: list[str] = []

    def run(argv: list[str], _env: Mapping[str, str]) -> int:
        labels.append(argv[3])
        return _REFUSED if argv[3] == "audiostruct-align" else 0

    assert orchestrate(_PLAN, run) == _REFUSED
    assert labels == ["audiostruct-transcribe", "audiostruct-align"]
