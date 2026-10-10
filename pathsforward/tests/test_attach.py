# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for a waypoint's attachments: the shape is checked, the clean record is not (W930).

⚑ THE CLEAN RECORD IS THE POSITIVE CONTROL: without it, an arm that asserts a malformed entry is
found cannot be told from a check that reports every entry.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.pathsforward import attach, check
from mikemol.pathsforward.model import validate

if TYPE_CHECKING:
    from mikemol.pathsforward.model import State

_DIGEST = "ab" * 32
_GOOD = {"path": ".claude/letters/x.md", "sha256": _DIGEST}
_COUNTER = 1


def _state(value: object) -> State:
    """Build a one-waypoint state whose W1 carries the given attachments field.

    Returns:
        the state.

    """
    return validate(
        {
            "counter": _COUNTER,
            "project_root": "/",
            "waypoints": [
                {
                    "symbol": "W1",
                    "title": "t",
                    "status": "ready",
                    "blocked_on": [],
                    "blocked_kind": None,
                    "enables": [],
                    "evidence": "",
                    "attachments": value,
                }
            ],
            "residue": [],
        }
    )


def test_a_clean_attachment_is_not_found_and_is_read_back() -> None:
    """The positive control: a repo-relative path and 64 hex digits yield no finding."""
    state = _state([_GOOD])
    assert attach.findings(state) == []
    assert attach.entries(state.waypoints[0]) == [(".claude/letters/x.md", _DIGEST)]


@pytest.mark.parametrize(
    "entry",
    [
        {"path": "/etc/passwd", "sha256": _DIGEST},
        {"path": "../x.md", "sha256": _DIGEST},
        {"path": "a/../../x.md", "sha256": _DIGEST},
        {"path": "", "sha256": _DIGEST},
        {"path": "x.md", "sha256": "abc"},
        {"path": "x.md", "sha256": "AB" * 32},
        {"path": "x.md"},
        {"sha256": _DIGEST},
        "x.md",
    ],
)
def test_a_malformed_entry_is_found_and_not_read_back(entry: object) -> None:
    """An absolute or climbing path, a bad digest, a missing key or a bare string is refused."""
    state = _state([_GOOD, entry])
    assert len(attach.findings(state)) == 1
    assert attach.entries(state.waypoints[0]) == [(".claude/letters/x.md", _DIGEST)]


def test_a_field_that_is_not_a_list_is_found() -> None:
    """A bare string would otherwise read as a list of characters."""
    assert attach.findings(_state("x.md")) == ["W1: attachments is str, not a list"]


def test_an_absent_field_is_fine_and_the_check_runs_the_property() -> None:
    """No attachments means no finding; the whole check reports a malformed one."""
    assert attach.findings(_state(None)) == []
    assert any("attachments" in f for f in check.check(_state(["x.md"])))
