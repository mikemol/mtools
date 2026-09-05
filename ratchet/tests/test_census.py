# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the census: the key's grain, and refusing an untrustworthy read."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.ratchet.census import parse_concise, run_ruff

if TYPE_CHECKING:
    from pathlib import Path


def test_the_key_is_file_and_rule_not_line() -> None:
    """The key is file-and-rule, not file-and-line.

    ⚑⚑ A LINE NUMBER CHANGES WHEN ANYTHING ABOVE IT MOVES.

    A line-keyed baseline reports a whole file as new debt after an unrelated edit — every
    key refused, none of it real — and a gate that cries wolf gets disabled.
    """
    keys = parse_concise([
        "src/a.py:1:1: docstring-missing-returns: msg",
        "src/a.py:99:4: docstring-missing-returns: msg",
    ])
    assert keys == frozenset({"src/a.py:docstring-missing-returns"})


def test_the_key_keeps_the_file_rather_than_collapsing_to_the_rule() -> None:
    """The key keeps the file rather than collapsing to the rule.

    ⚑ Collapsing to the rule loses WHERE the debt is, so paying one file down while another
    regresses reads as unchanged — the substitution blindness, one axis over.
    """
    keys = parse_concise([
        "src/a.py:1:1: compare-to-empty-string: msg",
        "src/b.py:1:1: compare-to-empty-string: msg",
    ])
    assert keys == frozenset({"src/a.py:compare-to-empty-string",
                              "src/b.py:compare-to-empty-string"})


def test_a_path_containing_colons_is_parsed() -> None:
    """A path containing colons is parsed.

    ⚑ The path is matched non-greedily, because `./src/x.py` carries colons that a greedy
    match would swallow into the rule field.
    """
    assert parse_concise(["./src/a.py:3:9: literal-membership: msg"]) == frozenset(
        {"./src/a.py:literal-membership"})


def test_a_non_finding_line_is_dropped() -> None:
    """Summary lines and warnings are not findings."""
    assert parse_concise(["Found 3 errors.", "warning: something", ""]) == frozenset()


def test_an_unexpected_exit_refuses_rather_than_reporting_an_empty_census(
        tmp_path: Path) -> None:
    """An unexpected exit refuses rather than reporting an empty census.

    ⚑⚑⚑ A CENSUS FROM A CHECKER THAT DID NOT RUN IS AN EMPTY SET THAT LOOKS CLEAN.

    Exit 0 and 1 are both success — a clean tree and findings. Anything else means the
    checker failed, and reporting that as an empty census would pay the entire baseline
    down in one run. That is the fail-open shape this ecosystem keeps paying for.
    """
    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    (tmp_path / ".venv" / "bin" / "ruff").write_text("#!/bin/sh\nexit 2\n", encoding="utf-8")
    (tmp_path / ".venv" / "bin" / "ruff").chmod(0o755)
    with pytest.raises(RuntimeError, match="not trustworthy"):
        run_ruff(tmp_path, preview=True)
