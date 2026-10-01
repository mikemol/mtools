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
