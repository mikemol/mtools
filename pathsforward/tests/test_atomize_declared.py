# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Atomize counts only a queue's declared advance outcomes, and the deny-list otherwise (W539)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from mikemol.pathsforward import cli
from mikemol.pathsforward.atomize import advances, atomize
from mikemol.pathsforward.ledger import Entry, Parsed, line

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_STAMP = "2026-10-04T00:00:00Z"
_ADVANCE = frozenset({"advanced"})
_DECLARED = {"advance": ["advanced"], "other": ["filed"]}
_TWICE = 2


def _tick(symbol: str, outcome: str, kind: str = "tick") -> Parsed:
    return Parsed(_STAMP, Entry(kind, symbol, outcome, "-", "note"))


def _queue(root: Path, **top: object) -> Path:
    """Write a one-waypoint state, and a ledger holding one hand-written `filed` tick line.

    Returns:
        the state path.

    """
    root.mkdir(parents=True, exist_ok=True)
    doc: dict[str, object] = {
        "counter": 1,
        "project_root": str(root),
        "waypoints": [
            {
                "symbol": "W1",
                "title": "t",
                "status": "ready",
                "blocked_on": [],
                "next_bounded_step": "s",
                "evidence": "",
                "ticks_blocked": 0,
            }
        ],
        "residue": [],
        **top,
    }
    path = root / "paths-forward.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    ledger = path.with_suffix(".ledger")
    ledger.write_text(line(Entry("tick", "W1", "filed", "-", "n"), _STAMP) + "\n", encoding="utf-8")
    return path


def test_an_undeclared_queue_counts_any_word_but_the_deny_list() -> None:
    """With no declared set, `filed` counts as an advance, exactly as before this change."""
    entries = [_tick("W1", "filed"), _tick("W1", "minted"), _tick("W1", "advanced")]
    assert advances("W1", list(entries)) == _TWICE


def test_a_declared_advance_set_ignores_a_word_outside_it() -> None:
    """El-openglo's `tick W98 filed` read as an advance; under a declared set it does not."""
    entries = [_tick("W1", "filed"), _tick("W1", "advanced")]
    assert advances("W1", list(entries), _ADVANCE) == 1


def test_a_declared_set_counts_only_what_it_names() -> None:
    """A word in the declared advance set counts once per line, on tick and interrupt kinds."""
    entries = [_tick("W1", "advanced"), _tick("W1", "advanced", "interrupt")]
    assert advances("W1", list(entries), _ADVANCE) == _TWICE


def test_the_split_still_resets_the_count_under_a_declared_set() -> None:
    """`atomized` zeroes the count whether or not the queue declared its sets."""
    entries = [_tick("W1", "advanced"), _tick("W1", "atomized"), _tick("W1", "advanced")]
    assert advances("W1", list(entries), _ADVANCE) == 1


def test_a_false_atomize_from_a_filed_line_disappears_under_a_declared_set() -> None:
    """The top ready waypoint is flagged by a `filed` line only when the queue did not declare."""
    top: list[dict[str, object]] = [{"symbol": "W1", "title": "t", "status": "ready"}]
    entries = [_tick("W1", "filed")]
    assert (atomize(top, list(entries)), atomize(top, list(entries), _ADVANCE)) == (
        "ATOMIZE W1 (advanced 1 times without landing)",
        None,
    )


def test_the_cli_wires_the_declared_set_into_the_atomize_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--check` prints ATOMIZE for a `filed` line on an undeclared queue and not on a declared one.

    ⚑ el-openglo:W106 (W539): the same ledger and the same top waypoint, differing only in whether
    the queue declared `ledger_outcomes`. This is the false `ATOMIZE W98` the card exists to end.
    """
    cli.main(["--state", str(_queue(tmp_path / "undeclared")), "--check"])
    undeclared = capsys.readouterr().out
    cli.main(["--state", str(_queue(tmp_path / "declared", ledger_outcomes=_DECLARED)), "--check"])
    declared = capsys.readouterr().out
    assert ("ATOMIZE W1" in undeclared, "ATOMIZE W1" in declared) == (True, False)
