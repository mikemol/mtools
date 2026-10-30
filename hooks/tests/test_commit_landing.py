# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Each landed card gets one landing log record: card, sha, gate seconds, and whether it pushed."""

import json
from collections.abc import Mapping, Sequence
from typing import cast

import pytest

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


def test_a_stack_run_ships_its_refusals_under_the_submit_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """W2128: emit_stack hands the output, the submit key and the waypoints to emit_refusals."""
    calls: list[tuple[str, str, Sequence[str]]] = []

    def record(
        text: str,
        env: Mapping[str, str],
        spawn: object = None,
        stack_key: str = "",
        waypoints: Sequence[str] = (),
    ) -> int:
        del env, spawn
        calls.append((text, stack_key, waypoints))
        return 0

    monkeypatch.setattr("mikemol.hooks.commit_span.emit_refusals", record)
    moments = commit_span.Moments(1, 2, 3)
    env = {commit_span.SUBMIT_ENV: "9"}
    text = "REFUSED mtools (rc=1): why\n"
    commit_span.emit_stack(text, moments, ["W4"], env, lambda _argv: None)
    assert calls == [(text, "9", ["W4"])]


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


def test_a_refusal_is_a_verdict_row_with_its_reason_and_code() -> None:
    """W2128: REFUSED, NOT COMMITTED and RACED each make a record; a landing makes none."""
    text = (
        "COMMITTED mtools aaa1111 W1: first [PUSHED]\n"
        "REFUSED mtools (rc=1): the tip was gated once and refused\n"
        "NOT COMMITTED mtools: refused at submit: an import only a later entry adds\n"
        "RACED mtools: HEAD moved while the stack was gated\n"
    )
    got = commit_span.refusal_records(text, "77", ["W1", "W2"])
    assert [(r["verdict"], r["rc"]) for r in got] == [
        ("REFUSED", "1"),
        ("NOT COMMITTED", ""),
        ("RACED", ""),
    ]
    assert got[0]["reason"] == "the tip was gated once and refused"
    assert (got[0]["waypoints"], got[0]["stack_key"], got[0]["path"]) == ("W1,W2", "77", "stack")
    assert commit_span.refusal_records("COMMITTED mtools aaa1111 W1: x [PUSHED]\n") == []


def test_a_refusal_row_is_sent_to_the_same_service_with_its_verdict_field() -> None:
    """emit_refusals starts one log child per non-landing verdict, the record on its stdin."""
    sent: list[tuple[Sequence[str], str]] = []
    text = "REFUSED mtools (rc=1): why not\n"
    count = commit_span.emit_refusals(text, _ENV, lambda a, t: sent.append((a, t)), "5", ["W9"])
    assert count == len(sent) == 1
    argv, body = sent[0]
    assert argv[:_TWO] == ["/opt/mikemol-otlp", "log"]
    assert "verdict=REFUSED" in argv
    assert cast("dict[str, str]", json.loads(body))["reason"] == "why not"


def test_a_run_that_only_landed_ships_no_refusal_row() -> None:
    """The control: COMMITTED output starts no verdict child."""
    sent: list[tuple[Sequence[str], str]] = []
    text = "COMMITTED mtools aaa1111 W1: first [PUSHED]\n"
    assert commit_span.emit_refusals(text, _ENV, lambda a, t: sent.append((a, t))) == 0
    assert sent == []


def test_a_failed_start_ends_the_run_quietly() -> None:
    """A spawn that raises OSError stops the batch without raising into the commit."""

    def broken(_argv: Sequence[str], _text: str) -> None:
        message = "no such program"
        raise FileNotFoundError(message)

    assert commit_span.emit_landings(_TEXT, _GATE_S, _ENV, broken) == 0
