# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Each landed card gets one landing log record: card, sha, gate seconds, and whether it pushed."""

import json
from collections.abc import Sequence
from typing import cast

from mikemol.hooks import commit_span

_TEXT = (
    "noise before\n"
    "COMMITTED mtools aaa1111 W1: first [PUSHED]\n"
    "COMMITTED mtools bbb2222 no card here [LOCAL: push failed]\n"
    "REFUSED mtools (rc=1): later entry\n"
)
_ENV = {commit_span.BIN_ENV: "/opt/mikemol-otlp", commit_span.ENDPOINTS_ENV: "/host/e.json"}
_GATE_S = 240.4
_TWO = 2


def test_one_record_per_committed_line_and_none_for_a_refusal() -> None:
    """The two COMMITTED lines make two records and the REFUSED line makes none."""
    got = commit_span.landing_records(_TEXT, _GATE_S)
    assert [(r["sha"], r["card"]) for r in got] == [("aaa1111", "W1"), ("bbb2222", "-")]


def test_the_record_carries_the_gate_seconds_and_the_push_word() -> None:
    """A landing that did not push reads differently from one that did."""
    first, second = commit_span.landing_records(_TEXT, _GATE_S)
    assert (first["gate_s"], first["pushed"]) == ("240", "PUSHED")
    assert second["pushed"].startswith("LOCAL")


def test_each_record_is_sent_as_a_log_line_to_the_otlp_child() -> None:
    """The argv names the service, repo, sha and card, and the stdin is the record as JSON."""
    sent: list[tuple[Sequence[str], str]] = []
    count = commit_span.emit_landings(_TEXT, _GATE_S, _ENV, lambda a, t: sent.append((a, t)))
    assert count == len(sent) == _TWO
    argv, text = sent[0]
    assert argv[:_TWO] == ["/opt/mikemol-otlp", "log"]
    assert "card=W1" in argv
    assert cast("dict[str, str]", json.loads(text))["sha"] == "aaa1111"


def test_with_no_store_nothing_is_started() -> None:
    """No binary or no store names nothing to send to, and the verdict is already printed."""
    sent: list[tuple[Sequence[str], str]] = []
    env = {commit_span.BIN_ENV: "/opt/mikemol-otlp", "HOME": "/nonexistent-home"}
    assert commit_span.emit_landings(_TEXT, _GATE_S, env, lambda a, t: sent.append((a, t))) == 0
    assert sent == []


def test_a_failed_start_ends_the_run_quietly() -> None:
    """A spawn that raises OSError stops the batch without raising into the commit."""

    def broken(_argv: Sequence[str], _text: str) -> None:
        message = "no such program"
        raise FileNotFoundError(message)

    assert commit_span.emit_landings(_TEXT, _GATE_S, _ENV, broken) == 0
