# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""suite_check against hand-built distributions: a good one passes, and each defect is named."""

from __future__ import annotations

from typing import TYPE_CHECKING

import suite_check

if TYPE_CHECKING:
    from pathlib import Path

_GOOD_BUILD = 'py_test(\n    name = "t",\n    main = "@mikemol_rules_py//:pytest_main.py",\n)\n'
_GOOD_TEST = '"""Prose may say Path(__file__).resolve() freely."""\n\ndef test_x() -> None:\n    pass\n'
_RESOLVING_TEST = "from pathlib import Path\n\nHERE = Path(__file__).resolve().parent\n"


def _dist(root: Path, build: str, test: str) -> Path:
    (root / "tests").mkdir()
    (root / "BUILD.bazel").write_text(build, encoding="utf-8")
    (root / "tests" / "test_a.py").write_text(test, encoding="utf-8")
    return root


def test_good_distribution_has_no_findings(tmp_path: Path) -> None:
    """The positive control: pytest as main, no resolve, and prose naming the defect is fine."""
    assert suite_check.check(_dist(tmp_path, _GOOD_BUILD, _GOOD_TEST)) == []


def test_module_as_main_is_named(tmp_path: Path) -> None:
    """A py_test running its own module as main is a finding, and so is pytest's main missing."""
    dist = _dist(tmp_path, 'py_test(\n    main = src,\n)\n', _GOOD_TEST)
    missing, as_module = suite_check.check(dist)
    assert "no py_test names" in missing
    assert "pytest never collects" in as_module


def test_missing_build_is_named(tmp_path: Path) -> None:
    """A distribution with no BUILD is one finding, not a silent pass."""
    (tmp_path / "tests").mkdir()
    [finding] = suite_check.check_main(tmp_path)
    assert "missing" in finding


def test_resolving_file_is_named_with_its_line(tmp_path: Path) -> None:
    """A test calling resolve() on a __file__ path is named, with its module and line."""
    [finding] = suite_check.check(_dist(tmp_path, _GOOD_BUILD, _RESOLVING_TEST))
    assert finding.endswith("test_a.py:3: resolves out of the runfiles tree")


def test_main_reports_exit_codes(tmp_path: Path) -> None:
    """0 on a good distribution, 1 on findings, 2 on a usage error."""
    good = tmp_path / "good"
    good.mkdir()
    bad = tmp_path / "bad"
    bad.mkdir()
    _dist(good, _GOOD_BUILD, _GOOD_TEST)
    _dist(bad, _GOOD_BUILD, _RESOLVING_TEST)
    codes = [suite_check.main([str(good)]), suite_check.main([str(bad)]), suite_check.main([])]
    assert codes == [0, 1, 2]


_UNGUARDED = (
    "def test_x() -> None:\n"
    "    offenders = [p for p in range(3) if p > 5]\n"
    "    assert not offenders\n"
)
_GUARDED_BELOW = (
    "def test_x() -> None:\n"
    "    swept = list(range(3))\n"
    "    offenders = [p for p in swept if p > 5]\n"
    "    assert not offenders\n"
    "    assert len(swept) >= 3\n"
)
_VERDICT_AND_LITERAL = (
    "def test_x() -> None:\n"
    "    fired = analyze('ls')\n"
    "    assert not fired\n"
    "    empty = []\n"
    "    assert not empty\n"
)


def test_unguarded_population_negative_is_named(tmp_path: Path) -> None:
    """`assert not` over a derived population, with nothing truthy beside it, is a finding."""
    [finding] = suite_check.check(_dist(tmp_path, _GOOD_BUILD, _UNGUARDED))
    assert finding.endswith("test_a.py:3: test_x asserts `not offenders` and nothing truthy")


def test_guard_below_the_negative_counts(tmp_path: Path) -> None:
    """A truthy assertion after the negative guards it; the whole function is walked."""
    assert suite_check.check(_dist(tmp_path, _GOOD_BUILD, _GUARDED_BELOW)) == []


def test_verdict_calls_and_literals_are_not_populations(tmp_path: Path) -> None:
    """A declared verdict call and a literal collection are not population-shaped negatives."""
    assert suite_check.check(_dist(tmp_path, _GOOD_BUILD, _VERDICT_AND_LITERAL)) == []
    assert "analyze" in suite_check.VERDICT_CALLS
