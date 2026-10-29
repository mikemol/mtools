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


def test_a_direct_record_carries_the_subject_and_the_path_and_no_stack_keys() -> None:
    """W2126: one shape for every path; a run that is no stack names neither a key nor an index."""
    first, second = commit_span.landing_records(_TEXT, _GATE_S)
    assert first["subject"] == "W1: first"
    assert second["subject"] == "no card here"
    assert (first["path"], second["path"]) == ("direct", "direct")
    assert "stack_key" not in first
    assert "stack_index" not in first


def test_a_stack_record_names_its_key_and_its_place_in_the_stack() -> None:
    """The same landings under a stack key: path stack, the key, and the index in landing order."""
    first, second = commit_span.landing_records(_TEXT, _GATE_S, "1793255768")
    assert (first["path"], first["stack_key"], first["stack_index"]) == ("stack", "1793255768", "0")
    assert (second["stack_key"], second["stack_index"]) == ("1793255768", "1")


def test_every_value_of_a_record_is_a_flat_string() -> None:
    """The host's reader takes no nested object and no boolean: every value stays a string."""
    for record in commit_span.landing_records(_TEXT, _GATE_S, "9"):
        assert all(isinstance(value, str) for value in record.values())


def test_a_stack_run_ships_its_records_under_the_submit_key() -> None:
    """emit_landings with a key sends records that carry it, in the JSON on the child's stdin."""
    sent: list[tuple[Sequence[str], str]] = []
    count = commit_span.emit_landings(
        _TEXT, _GATE_S, _ENV, lambda a, t: sent.append((a, t)), stack_key="42"
    )
    assert count == len(sent) == _TWO
    shipped = cast("dict[str, str]", json.loads(sent[1][1]))
    assert (shipped["path"], shipped["stack_key"], shipped["stack_index"]) == ("stack", "42", "1")


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
