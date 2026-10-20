# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A REFUSED verdict names the checks the gate's own summary lists as failed (W1728)."""

from __future__ import annotations

from mikemol.hooks import commit_kata, gatephase, stackrun

_SUMMARY = (
    "pre-commit: phase check_stubtest_____the_panflute_stub_still_match 100\n"
    "some output\n"
    "pre-commit: REFUSED — the following check(s) failed:\n"
    "  - corpus: pytest — every case passes\n"
    "  - hooks: pytest — every case passes\n"
    "  - the hermetic suite: //corpus:test_exit_gate //hooks:mypy\n"
    "  - hooks: mypy domain reaches a transitive import\n"
    "  - the warrant pairing\n"
    "not a bullet\n"
    "  - after the block\n"
)
_REFUSED = "REFUSED mtools (rc=1): the cause is above; HEAD is still abc1234"
_COMMITTED = "COMMITTED mtools abc1234 subject [pushed]"
_THREE = 3


def test_the_failed_checks_are_the_bullets_of_the_gates_own_summary() -> None:
    """Read from the summary line to the first line that is not a bullet, in the order printed."""
    found = gatephase.failed_checks(_SUMMARY)
    assert len(found) == _THREE + 2
    assert found[0] == "corpus: pytest — every case passes"
    assert found[-1] == "the warrant pairing"


def test_the_last_phase_mark_is_not_read_as_the_failing_stage() -> None:
    """The gate prints marks only for some stages, so the note never names one."""
    assert "check_stubtest" not in gatephase.stage_note(_SUMMARY)


def test_the_note_names_three_checks_cut_short_and_counts_the_rest() -> None:
    """Three labels, each cut at sixty characters, then 'and N more'."""
    note = gatephase.stage_note(_SUMMARY)
    assert note.startswith("failed: corpus: pytest — every case passes; hooks: pytest")
    assert note.endswith(" and 2 more; ")
    assert "hermetic suite: //corpus:test_exit_gate //hooks:mypy" in note


def test_output_with_no_summary_names_nothing() -> None:
    """An older hook, or a refusal before the first check, says nothing it cannot know."""
    assert not gatephase.stage_note("FAIL: //x:y\n")
    assert not gatephase.stage_note("")


def test_a_refused_line_gains_the_note_before_its_cause_and_others_are_unchanged() -> None:
    """The note sits between the rc and 'the cause is above'; a COMMITTED line is untouched."""
    line = commit_kata.with_stage(_REFUSED, _SUMMARY)
    assert line.startswith("REFUSED mtools (rc=1): failed: corpus: pytest")
    assert line.endswith("the cause is above; HEAD is still abc1234")
    assert commit_kata.with_stage(_COMMITTED, _SUMMARY) == _COMMITTED
    assert commit_kata.with_stage(_REFUSED, "no summary here") == _REFUSED


def test_the_stack_and_train_culprit_clause_carries_the_note() -> None:
    """culprit_note, which both REFUSED lines of a stack use, leads with the failed checks."""
    note = stackrun.culprit_note(_SUMMARY, [])
    assert note.startswith("failed: corpus: pytest — every case passes; ")
    assert note.endswith("culprit: unattributed (the failing check names no path in this stack)")
