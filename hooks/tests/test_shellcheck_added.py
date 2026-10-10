# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that the shellcheck hook judges an edit by the findings it ADDS (W937).

⚑ gcalculus's check.sh carries four deliberate SC2016 lines, and a correct one-line new stage was
refused for them. The pure arms need no linter; the end-to-end arms skip with a reason without one.
THE CLEAN ADDITION IS THE POSITIVE CONTROL: without it, "an added finding is refused" cannot be told
from a hook that refuses every edit to a file with an old finding.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.hooks import shellcheck

if TYPE_CHECKING:
    from pathlib import Path

_NO_LINTER = shellcheck.linter() is None
_needs_linter = pytest.mark.skipif(_NO_LINTER, reason="no shellcheck on PATH or at the mise shim")

_OLD = "#!/usr/bin/env bash\necho '$HOME'\n"
_CODE = "SC2016"
_MSG = "Expressions don't expand in single quotes, use double quotes for that."
_ONE: list[shellcheck.Finding] = [(_CODE, 2, _MSG)]
_TWO: list[shellcheck.Finding] = [(_CODE, 2, _MSG), (_CODE, 3, _MSG)]
_ANCHOR = "echo '$HOME'\n"


def _edit(target: Path, new: str) -> dict[str, object]:
    """Build an Edit payload that appends `new` after the old content's last line.

    Returns:
        the tool input.

    """
    return {
        "file_path": str(target),
        "old_string": _ANCHOR,
        "new_string": f"{_ANCHOR}{new}",
    }


def test_no_baseline_judges_everything() -> None:
    """A new file, or an unmeasured baseline, has nothing old to subtract."""
    assert shellcheck.added_only(_TWO, None) == _TWO
    assert shellcheck.added_only(_TWO, []) == _TWO


def test_findings_the_file_already_had_are_not_the_edits() -> None:
    """The same finding at a moved line is old: matched by code and message, not by line."""
    moved: list[shellcheck.Finding] = [(_CODE, 9, _MSG)]
    assert shellcheck.added_only(moved, _ONE) == []


def test_one_more_of_the_same_rule_is_added() -> None:
    """Counted, not set-wise: a second SC2016 beyond the one already there is the edit's."""
    assert shellcheck.added_only(_TWO, _ONE) == [(_CODE, 3, _MSG)]


def test_a_different_rule_is_added() -> None:
    """An old SC2016 does not excuse a new SC2086."""
    other: shellcheck.Finding = ("SC2086", 3, "Double quote to prevent.")
    assert shellcheck.added_only([(_CODE, 2, _MSG), other], _ONE) == [other]


@pytest.mark.needs_shellcheck
@_needs_linter
def test_a_clean_line_added_to_a_file_with_an_old_finding_is_allowed(tmp_path: Path) -> None:
    """The positive control, and the gcalculus case: the old finding no longer blocks the edit."""
    target = tmp_path / "check.sh"
    target.write_text(_OLD, encoding="utf-8")
    _subject, found = shellcheck.verdict("Edit", _edit(target, 'echo "ok"\n'))
    assert found == []


@pytest.mark.needs_shellcheck
@_needs_linter
def test_a_second_finding_added_to_a_file_with_an_old_one_is_refused(tmp_path: Path) -> None:
    """The old finding stays excused; the new one of the same rule is not."""
    target = tmp_path / "check.sh"
    target.write_text(_OLD, encoding="utf-8")
    _subject, found = shellcheck.verdict("Edit", _edit(target, "echo '$PATH'\n"))
    assert found is not None
    assert [code for code, _line, _msg in found] == [_CODE]


@pytest.mark.needs_shellcheck
@_needs_linter
def test_a_new_file_with_a_finding_is_refused(tmp_path: Path) -> None:
    """A Write of a file that does not exist yet has no baseline: its findings are all added."""
    target = tmp_path / "new.sh"
    _subject, found = shellcheck.verdict("Write", {"file_path": str(target), "content": _OLD})
    assert found is not None
    assert [code for code, _line, _msg in found] == [_CODE]
