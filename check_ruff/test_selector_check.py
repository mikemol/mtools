# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""selector_check against hand-written configs and a fake ruff: agreement passes, a rename is named."""

from __future__ import annotations

from typing import TYPE_CHECKING

import selector_check

if TYPE_CHECKING:
    from pathlib import Path

_NAMES = {"S603": "subprocess-without-shell-equals-true", "CPY001": "missing-copyright-notice"}

_RENAMED = (
    "[tool.ruff.lint.per-file-ignores]\n"
    "# S603: this module shells out to the checker it runs.\n"
    '"src/x.py" = ["subprocess-without-shell-equals-true"]\n'
)
_AGREES = (
    "[tool.ruff.lint.per-file-ignores]\n"
    "# S603: this module shells out to the checker it runs.\n"
    '"src/x.py" = ["S603"]\n'
)
_OTHER_RULE = (
    "[tool.ruff.lint.per-file-ignores]\n"
    "# Declared here, the way the peer's CPY001 ignore was declined.\n"
    '"src/x.py" = ["subprocess-without-shell-equals-true"]\n'
)


def _name(code: str) -> str | None:
    return _NAMES.get(code)


def test_a_comment_citing_the_renamed_code_is_named() -> None:
    """The selector says the rule's name while the comment above still cites its code."""
    [finding] = selector_check.check(_RENAMED, _name)
    assert finding.startswith("pyproject.toml:3: the selector names this rule by NAME")
    assert "['S603']" in finding


def test_a_comment_and_selector_in_the_same_spelling_agree() -> None:
    """A code in the prose and the same code in the selector is agreement, not a finding."""
    assert selector_check.check(_AGREES, _name) == []


def test_a_comment_naming_a_different_rule_is_not_a_finding() -> None:
    """Prose citing another rule to explain the entry is normal, so it is never flagged."""
    assert selector_check.check(_OTHER_RULE, _name) == []


def test_an_unknown_code_is_never_a_finding() -> None:
    """A code ruff does not know cannot contradict anything, so it is passed over."""
    assert selector_check.check(_RENAMED, lambda _code: None) == []


def test_main_reports_exit_codes(tmp_path: Path) -> None:
    """0 on an agreeing config, 1 on a missing one, 2 on a usage error (no ruff is run)."""
    config = tmp_path / "pyproject.toml"
    config.write_text("[tool.ruff]\n", encoding="utf-8")
    missing = str(tmp_path / "absent.toml")
    codes = [
        selector_check.main(["ruff", str(config)]),
        selector_check.main(["ruff", missing]),
        selector_check.main([]),
    ]
    assert codes == [0, 1, 2]
