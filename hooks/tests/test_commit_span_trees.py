# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The commit span records the gated tree beside the bazel invocation ids (W1613).

⚑ THE CONTROLS: an output with no `gated-tree:` line adds no field, the same tree twice is one,
a stack's event carries the trees of its run, and a sha of the wrong length is not a tree.
"""

from mikemol.hooks import commit_span

_A = "a" * 40
_B = "b" * 40
_COMMITTED = "COMMITTED mtools abc1234 W9: a subject [PUSHED]\n"
_TWO = "COMMITTED mtools aaa1111 W1: first [PUSHED]\nCOMMITTED mtools bbb2222 W2: second [PUSHED]\n"


def test_the_trees_of_an_output_are_its_gated_tree_lines_distinct_and_in_order() -> None:
    """Two trees and a repeat give the two, in order; a short sha and prose are not trees."""
    text = f"gated-tree: {_A}\nnoise\ngated-tree: {_B}\ngated-tree: {_A}\ngated-tree: abc123\n"
    assert commit_span.trees_of(text) == f"{_A},{_B}"
    assert not commit_span.trees_of("no tree line here\n")


def test_the_verdict_event_carries_the_tree_only_when_the_output_prints_one() -> None:
    """The control: no `gated-tree:` line, no `trees` field."""
    event = commit_span.verdict_of(f"gated-tree: {_A}\n{_COMMITTED}")
    assert event is not None
    assert event["trees"] == _A
    plain = commit_span.verdict_of(_COMMITTED)
    assert plain is not None
    assert "trees" not in plain


def test_a_stack_event_carries_the_trees_of_its_run() -> None:
    """One gate is one trace, so the tree it judged rides on the stack's event."""
    event = commit_span.stack_event(f"gated-tree: {_B}\n{_TWO}")
    assert event is not None
    assert event["trees"] == _B
    plain = commit_span.stack_event(_TWO)
    assert plain is not None
    assert "trees" not in plain


def test_the_tree_rides_on_every_span_of_the_trace_as_a_field() -> None:
    """The plan passes `trees=<sha>` to each `mikemol-otlp trace` argv."""
    event = commit_span.verdict_of(f"gated-tree: {_A}\n{_COMMITTED}")
    assert event is not None
    ids = commit_span.Ids("t" * 32, "p", "q", "r")
    parts = [commit_span.Piece("commit.gating", 1, 2, "s" * 16, "")]
    for argv in commit_span.plan("otlp", event, "W9", (ids, parts)):
        assert f"trees={_A}" in argv
