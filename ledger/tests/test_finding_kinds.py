# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.ledger.finding_kinds`: substrate's suite, and its letter's §3.1.

⚑ THE THIRD OUTCOME IS CASED IN BOTH DIRECTIONS. UNRUNNABLE must never be CLOSED or OPEN, and a
command that RAN and failed must never be UNRUNNABLE — either case alone holds against a reader
that always answers the same.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Protocol, cast

import pytest

from mikemol.ledger import finding_kinds

if TYPE_CHECKING:
    from pathlib import Path

_OK = [sys.executable, "-c", "pass"]
_BAD = [sys.executable, "-c", "raise SystemExit(3)"]
_ABSENT = ["/nonexistent/binary/entirely"]
_OUTCOMES = 3

# A suite tail in the house shape: per-case FAIL lines, then the score LAST.
_HOUSE_TAIL = """
running the thing
FAIL a_case_that_broke: got 3 != want 4
FAIL a_second_case: got 1 != want 2
somesuite: 18/20
"""

# A refusal whose announcing line is NOT last — the shape `tail[-1]` got wrong.
_REFUSAL_TAIL = """
store.tenant: refusing an unstated tenant — pass --sandbox or --live
pass --dry-run to see WHOSE backend that PID currently is
"""


class _RunWithoutCwd(Protocol):
    """`run` as a caller who forgot `cwd` would call it — the shape the signature must refuse."""

    def __call__(self, *argv: str) -> tuple[int | None, str]: ...


def test_the_package_exposes_no_root() -> None:
    """There is no module-level root: THE LETTER'S §3.1."""
    assert not hasattr(finding_kinds, "ROOT")


def test_run_without_a_cwd_is_a_type_error() -> None:
    """A `run` without `cwd` refuses to guess a directory.

    ⚑ Installed, a guessed root is `site-packages`, and every relative witness reads UNRUNNABLE.
    """
    unguarded = cast("_RunWithoutCwd", finding_kinds.run)
    with pytest.raises(TypeError, match="cwd"):
        unguarded(*_OK)


def test_run_runs_in_the_directory_it_is_given(tmp_path: Path) -> None:
    """A relative command resolves against the caller's `cwd`, not the package's location."""
    (tmp_path / "probe.py").write_text("print('here')\n", encoding="utf-8")
    code, out = finding_kinds.run(sys.executable, "probe.py", cwd=tmp_path)
    assert code == 0
    assert "here" in out


def test_a_process_that_never_started_is_none_not_a_number(tmp_path: Path) -> None:
    """The exit code is None when the process never started — never collapsed into a number."""
    code, _ = finding_kinds.run(*_ABSENT, cwd=tmp_path)
    assert code is None


def test_an_unstartable_command_is_unrunnable_under_both_kinds(tmp_path: Path) -> None:
    """UNRUNNABLE under selftest AND refuses — NOT closed, which "non-zero means refusing" gives."""
    assert finding_kinds.selftest(_ABSENT, "n/a", cwd=tmp_path)[0] == finding_kinds.UNRUNNABLE
    code, note = finding_kinds.refuses(_ABSENT, "n/a", cwd=tmp_path)
    assert code == finding_kinds.UNRUNNABLE
    assert "did not run" in note


def test_a_command_that_ran_and_failed_is_a_refusal(tmp_path: Path) -> None:
    """The other direction: a command that RAN and exited non-zero IS a refusal, not UNRUNNABLE."""
    gone = [sys.executable, str(tmp_path / "no_such_module_at_all.py")]
    assert finding_kinds.refuses(gone, "n/a", cwd=tmp_path)[0] == finding_kinds.CLOSED


def test_selftest_and_refuses_are_exact_duals(tmp_path: Path) -> None:
    """The two kinds are inverses: selftest closes on 0; refuses closes otherwise, and says GONE."""
    assert finding_kinds.selftest(_OK, "x", cwd=tmp_path)[0] == finding_kinds.CLOSED
    assert finding_kinds.selftest(_BAD, "x", cwd=tmp_path)[0] == finding_kinds.OPEN
    assert finding_kinds.refuses(_BAD, "x", cwd=tmp_path)[0] == finding_kinds.CLOSED
    code, note = finding_kinds.refuses(_OK, "x", cwd=tmp_path)
    assert code == finding_kinds.OPEN
    assert "GONE" in note


def test_the_three_outcomes_stay_distinct() -> None:
    """CLOSED, OPEN and UNRUNNABLE are three different integers."""
    outcomes = {finding_kinds.CLOSED, finding_kinds.OPEN, finding_kinds.UNRUNNABLE}
    assert len(outcomes) == _OUTCOMES


def test_the_vacuous_kinds_are_honest_and_name_themselves() -> None:
    """A standing fact always holds; an unwitnessed one is always UNRUNNABLE; each names itself."""
    assert finding_kinds.standing("a fact") == (finding_kinds.CLOSED, "STANDING — a fact")
    code, note = finding_kinds.unwitnessed("a gap")
    assert code == finding_kinds.UNRUNNABLE
    assert "UNWITNESSED" in note


def test_the_failing_case_is_quoted_with_its_score_and_count() -> None:
    """The FAIL line is quoted, not the score; the score rides alongside; further failures count."""
    case = finding_kinds.failing_case(_HOUSE_TAIL)
    assert "a_case_that_broke" in case
    assert "18/20" in case
    assert "more" in case


def test_the_refusal_line_is_quoted_not_the_trailing_hint() -> None:
    """The announcing line is quoted, and the incidental last line is not."""
    refusal = finding_kinds.evidence(_REFUSAL_TAIL)
    assert "refusing" in refusal
    assert "--dry-run" not in refusal


def test_a_citation_miss_is_flagged_never_passed_off() -> None:
    """No refusal word, an empty read, and a score with no FAIL line each admit the gap."""
    assert "no refusal line found" in finding_kinds.evidence("just some chatter\n")
    assert "exit code is the whole evidence" in finding_kinds.evidence("")
    assert "NO `FAIL <case>` line" in finding_kinds.failing_case("somesuite: 4/9\n")
