# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The gate's phase marks are read back out of its output and become child spans (W1493)."""

from mikemol.hooks import commit_span, gatephase
from mikemol.hooks.commit_span import Ids, Moments
from mikemol.hooks.gatephase import Mark

_IDS = Ids("t" * 32, "c" * 16, "q" * 16, "g" * 16)
_MOMENTS = Moments(submit_ns=100, lease_ns=1_000, end_ns=9_000)


def test_whole_mark_lines_are_read_in_the_order_printed() -> None:
    """Other gate output between the marks is ignored."""
    text = (
        "pre-commit: checking hooks\n"
        "pre-commit: phase prebuild 2000\n"
        "1675 passed in 85s\n"
        "pre-commit: phase pytest-hooks 3000\n"
    )
    assert gatephase.marks(text) == [Mark("prebuild", 2000), Mark("pytest-hooks", 3000)]


def test_a_line_that_is_not_a_whole_mark_is_skipped() -> None:
    """No name, a time that is not a number, or a name with a space is not a mark."""
    text = (
        "pre-commit: phase 2000\n"
        "pre-commit: phase bazel soon\n"
        "pre-commit: phase two words 3000\n"
        "pre-commit: phase bazel 4000\n"
    )
    assert gatephase.marks(text) == [Mark("bazel", 4000)]


def test_each_phase_runs_to_the_next_mark_and_the_last_to_the_verdict() -> None:
    """The spans are children of gating and named for the phase."""
    laid = commit_span.pieces(_MOMENTS, _IDS, "commit", [Mark("a", 2_000), Mark("b", 5_000)])
    phases = [p for p in laid if p.parent_id == _IDS.gating]
    assert [(p.name, p.start_ns, p.end_ns) for p in phases] == [
        ("commit.gating.a", 2_000, 5_000),
        ("commit.gating.b", 5_000, 9_000),
    ]


def test_a_mark_outside_the_gating_window_is_clamped_into_it() -> None:
    """A phase never starts before the lease or ends after the verdict."""
    laid = commit_span.pieces(_MOMENTS, _IDS, "commit", [Mark("early", 10), Mark("late", 99_000)])
    phases = [p for p in laid if p.parent_id == _IDS.gating]
    assert [(p.start_ns, p.end_ns) for p in phases] == [(1_000, 9_000), (9_000, 9_000)]


def test_no_marks_leaves_the_three_spans_alone() -> None:
    """A gate that prints none is traced exactly as before."""
    names = [p.name for p in commit_span.pieces(_MOMENTS, _IDS, "commit", [])]
    assert names == ["commit", "commit.queued", "commit.gating"]
