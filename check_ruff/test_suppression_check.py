# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""suppression_check with a fake ruff: an honoured directive passes, a dead one is named."""

from __future__ import annotations

from typing import TYPE_CHECKING

import suppression_check

if TYPE_CHECKING:
    from pathlib import Path

_DIRECTIVE = "import subprocess  # ruff: ignore[suspicious-subprocess-import]\n"


def _dist(root: Path, source: str) -> Path:
    (root / "pyproject.toml").write_text("[tool.ruff]\n", encoding="utf-8")
    (root / "src").mkdir()
    (root / "src" / "m.py").write_text(source, encoding="utf-8")
    return root


def _ruff(output: str, seen: list[list[str]]) -> suppression_check.Runner:
    def run(files: list[str], dist: Path) -> str:
        del dist
        seen.append(files)
        return output

    return run


def test_an_honoured_directive_passes(tmp_path: Path) -> None:
    """Ruff reports nothing for the claimed rule, so the directive holds; src is swept too."""
    seen: list[list[str]] = []
    assert suppression_check.check(_dist(tmp_path, _DIRECTIVE), _ruff("", seen)) == []
    assert seen == [["src/m.py"]]


def test_a_resurfaced_finding_for_a_claimed_rule_is_named(tmp_path: Path) -> None:
    """A finding for the rule a directive names means the directive died; it is reported."""
    out = "src/m.py:1:8: S404 [*] suspicious-subprocess-import\n"
    [finding] = suppression_check.check(_dist(tmp_path, _DIRECTIVE), _ruff(out, []))
    assert finding == out.strip()


def test_a_finding_for_an_unclaimed_rule_is_not_this_checks_business(tmp_path: Path) -> None:
    """Another rule's finding belongs to the ruff target; a red here is only about suppression."""
    out = "src/m.py:1:1: D100 undocumented-public-module\n"
    assert suppression_check.check(_dist(tmp_path, _DIRECTIVE), _ruff(out, [])) == []


def test_an_invalid_directive_is_always_claimed() -> None:
    """Ruff's own invalid-rule report is claimed even when no directive names it."""
    rules = suppression_check.claimed(["x = 1  # ruff: ignore[a, b]\n"])
    assert rules >= {"a", "b", "RUF102", "invalid-rule-code"}


def test_a_distribution_without_directives_runs_no_ruff(tmp_path: Path) -> None:
    """With nothing to check, ruff is not run and the result is empty, never a guess."""
    seen: list[list[str]] = []
    assert suppression_check.check(_dist(tmp_path, "x = 1\n"), _ruff("S404", seen)) == []
    assert seen == []


def test_main_reports_exit_codes(tmp_path: Path) -> None:
    """0 with no directives, 1 with no pyproject.toml, 2 on a usage error (no ruff is run)."""
    good = tmp_path / "good"
    good.mkdir()
    _dist(good, "x = 1\n")
    bare = tmp_path / "bare"
    bare.mkdir()
    codes = [
        suppression_check.main(["ruff", str(good)]),
        suppression_check.main(["ruff", str(bare)]),
        suppression_check.main([]),
    ]
    assert codes == [0, 1, 2]
