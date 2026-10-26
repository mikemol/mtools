# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A gate's admission wait and run time are published as two series (W2053, github-8f).

⚑ THE CONTROLS: the wait is submit to lease and the run is lease to verdict (not the other way and
not their sum), a clock that stepped back reads 0, and with no store or no binary nothing starts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.hooks import commit_span

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    import pytest

_S = 1_000_000_000
_WAIT = 60.0
_RUN = 30.0
_STARTS = 2


def _after(argv: Sequence[str], flag: str) -> str:
    return argv[argv.index(flag) + 1]


def _program(_env: Mapping[str, str]) -> str:
    return "/x/mikemol-otlp"


def _no_program(_env: Mapping[str, str]) -> None:
    return None


def _store(_env: Mapping[str, str]) -> bool:
    return True


def _no_store(_env: Mapping[str, str]) -> bool:
    return False


def test_the_wait_is_submit_to_lease_and_the_run_is_lease_to_verdict() -> None:
    """Submitted at 10 s, leased at 70 s, done at 100 s: a wait of 60 and a run of 30."""
    moments = commit_span.Moments(10 * _S, 70 * _S, 100 * _S)
    assert commit_span.gate_series(moments) == [
        (commit_span.ADMISSION_NAME, _WAIT),
        (commit_span.RUN_NAME, _RUN),
    ]


def test_a_clock_that_stepped_back_reads_zero_not_negative() -> None:
    """A lease earlier than the submit, or a verdict earlier than the lease, is 0."""
    moments = commit_span.Moments(100 * _S, 50 * _S, 10 * _S)
    assert [v for _, v in commit_span.gate_series(moments)] == [0.0, 0.0]


def test_each_figure_starts_one_metric_child_naming_the_repo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With a binary and a store, two children start, each with the repo as namespace and field."""
    monkeypatch.setattr(commit_span, "binary", _program)
    monkeypatch.setattr(commit_span, "store_named", _store)
    sent: list[list[str]] = []

    def spawn(argv: Sequence[str]) -> None:
        sent.append(list(argv))

    moments = commit_span.Moments(10 * _S, 70 * _S, 100 * _S)
    assert commit_span.emit_series("mtools", moments, {}, spawn) == _STARTS
    first, second = sent
    assert first[:2] == ["/x/mikemol-otlp", "metric"]
    assert _after(first, "--namespace") == "mtools"
    assert "repo=mtools" in first
    assert _after(first, "--name") == commit_span.ADMISSION_NAME
    assert _after(first, "--value") == "60.000"
    assert _after(second, "--name") == commit_span.RUN_NAME
    assert _after(second, "--value") == "30.000"


def test_no_store_or_no_binary_starts_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    """The metric is best effort: without a place to send it, nothing runs."""
    sent: list[list[str]] = []

    def spawn(argv: Sequence[str]) -> None:
        sent.append(list(argv))

    moments = commit_span.Moments(0, _S, 2 * _S)
    monkeypatch.setattr(commit_span, "binary", _no_program)
    monkeypatch.setattr(commit_span, "store_named", _store)
    assert commit_span.emit_series("mtools", moments, {}, spawn) == 0
    monkeypatch.setattr(commit_span, "binary", _program)
    monkeypatch.setattr(commit_span, "store_named", _no_store)
    assert commit_span.emit_series("mtools", moments, {}, spawn) == 0
    assert sent == []
