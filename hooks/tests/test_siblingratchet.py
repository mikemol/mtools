# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The sibling-reach ratchet is per file: it may fall, and a file above its baseline is refused."""

from __future__ import annotations

from mikemol.hooks import siblingcensus as census
from mikemol.hooks import siblingratchet as ratchet

REACHES = [
    census.Reach("a.md", 1, "nemik"),
    census.Reach("a.md", 5, "life"),
    census.Reach("b.py", 2, "paperkit"),
    census.Reach("src/adapter/send.py", 9, "nemik"),
]
EXEMPT = ("src/adapter/",)


def test_the_baseline_is_each_files_count_outside_the_exempt_prefix() -> None:
    """A measurement per file; the adapter's reaches are not in it."""
    assert ratchet.baseline_of(REACHES, EXEMPT) == {"a.md": 2, "b.py": 1}


def test_a_file_at_its_baseline_passes_and_a_file_above_it_is_refused_naming_targets() -> None:
    """Equal is allowed; one more is a violation that says what the file now reaches."""
    over = ratchet.violations(REACHES, {"a.md": 2, "b.py": 0}, EXEMPT)
    assert over == [ratchet.Violation("b.py", 1, 0, ("paperkit",))]


def test_a_file_the_baseline_does_not_hold_has_none_allowed() -> None:
    """A new file with a reach cannot hide behind slack elsewhere."""
    over = ratchet.violations(REACHES, {"a.md": 2}, EXEMPT)
    assert [v.file for v in over] == ["b.py"]


def test_the_exempt_prefix_is_neither_counted_nor_refused() -> None:
    """The one allowlisted adapter may reach; nothing else may."""
    over = ratchet.violations(REACHES, ratchet.baseline_of(REACHES, EXEMPT), EXEMPT)
    assert over == []
    without = ratchet.violations(REACHES, {"a.md": 2, "b.py": 1}, ())
    assert [v.file for v in without] == ["src/adapter/send.py"]


def test_a_paydown_is_reported_as_slack_not_as_a_violation() -> None:
    """A file below its baseline is fine, and the slack is what the next write takes."""
    baseline = {"a.md": 5, "gone.md": 3}
    over = ratchet.violations(REACHES, baseline, EXEMPT)
    assert over == [ratchet.Violation("b.py", 1, 0, ("paperkit",))]
    assert ratchet.slack(REACHES, baseline, EXEMPT) == {"a.md": 3, "gone.md": 3}
