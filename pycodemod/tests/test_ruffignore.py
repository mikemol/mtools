# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for adding ruff ignore rules as text (mtools:W1374): kept entries, no duplicates.

⚑ THE CONTROLS ARE WHAT MUST NOT MOVE: a rule already listed is not added twice, the other tables
and the entries already there stay exactly as written, and a file with no ignore list is None
(never a guess at where one would go). The results are read back with tomllib, not by eye.
"""

from __future__ import annotations

import tomllib
from typing import cast

from mikemol.pycodemod import ruffignore

_REASON = "Codon has no bare star marker."
_RULE = "boolean-type-hint-positional-argument"
_OTHER = "boolean-default-value-positional-argument"
_SINGLE = (
    '[tool.ruff]\nline-length = 100\n\n[tool.ruff.lint]\nselect = ["ALL"]\n'
    'ignore = ["a", "b"]\n\n[tool.ruff.lint.isort]\nknown-third-party = ["x"]\n'
)
_MULTI = (
    '[tool.ruff.lint]\nselect = ["ALL"]\nignore = [\n    "a",\n    # why\n    "b",\n]\n\n'
    "[tool.ruff.lint.isort]\nknown-first-party = []\n"
)


def _table(text: str, *path: str) -> dict[str, object]:
    node = cast("dict[str, object]", tomllib.loads(text))
    for key in path:
        node = cast("dict[str, object]", node[key])
    return node


def _ignored(text: str) -> list[str]:
    return list(cast("list[str]", _table(text, "tool", "ruff", "lint")["ignore"]))


def test_a_single_line_list_becomes_a_list_with_the_new_rules_and_the_old_ones() -> None:
    """Both old entries stay in order, the new rules follow under the reason, other tables stay."""
    grown = ruffignore.add(_SINGLE, [_RULE, _OTHER], _REASON)
    assert grown is not None
    assert _ignored(grown) == ["a", "b", _RULE, _OTHER]
    assert f"# {_REASON}" in grown
    assert _table(grown, "tool", "ruff", "lint", "isort") == {"known-third-party": ["x"]}


def test_a_multi_line_list_keeps_its_comments_and_gains_the_rules_at_the_end() -> None:
    """The existing comment survives; the new entries are appended before the closing bracket."""
    grown = ruffignore.add(_MULTI, [_RULE], _REASON)
    assert grown is not None
    assert _ignored(grown) == ["a", "b", _RULE]
    assert "    # why\n" in grown


def test_a_rule_already_listed_is_not_added_twice_and_the_text_is_unchanged() -> None:
    """Idempotent: adding the same rule again returns the same text."""
    once = ruffignore.add(_SINGLE, [_RULE], _REASON)
    assert once is not None
    assert ruffignore.add(once, [_RULE], _REASON) == once
    assert _ignored(once).count(_RULE) == 1


def test_a_file_with_no_lint_table_or_no_ignore_list_is_none() -> None:
    """Nowhere to put the entry means no answer, not a guess."""
    assert ruffignore.add("[tool.ruff]\nline-length = 100\n", [_RULE], _REASON) is None
    assert ruffignore.add('[tool.ruff.lint]\nselect = ["ALL"]\n', [_RULE], _REASON) is None
