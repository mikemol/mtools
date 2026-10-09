# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for nested citations: `parent/child:W<n>` parses, resolves, and never escapes."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from mikemol.pathsforward import foreign
from mikemol.pathsforward.model import foreign_symbol, is_reference

if TYPE_CHECKING:
    from pathlib import Path

Rec = dict[str, object]

_THREE = 3
_SEVEN = 7


def _nested(root: Path, repo: str, done: str = "W1") -> None:
    """Write a queue under `root/<repo>` (a path of any depth) whose `done` waypoint is done."""
    path = root.joinpath(*repo.split("/"), ".claude", "paths-forward.json")
    path.parent.mkdir(parents=True)
    waypoint: Rec = {
        "symbol": done,
        "title": "t",
        "status": "done",
        "blocked_on": [],
        "blocked_kind": None,
        "next_bounded_step": None,
        "evidence": "",
        "ticks_blocked": 0,
    }
    doc: Rec = {"counter": _THREE, "waypoints": [waypoint], "residue": []}
    path.write_text(json.dumps(doc), encoding="utf-8")


def test_a_flat_citation_is_unchanged() -> None:
    """Existing citations keep their meaning."""
    assert foreign_symbol("luthen-observability:W55") == ("luthen-observability", 55)


def test_a_nested_citation_names_its_path() -> None:
    """The repo part is the whole path, segments joined by a slash."""
    assert foreign_symbol("parent/child:W3") == ("parent/child", _THREE)
    assert foreign_symbol("a/b/c:W7") == ("a/b/c", _SEVEN)


@pytest.mark.parametrize(
    "ref",
    [
        "a//b:W1",
        "/a:W1",
        "a/:W1",
        "a/../b:W1",
        "../a:W1",
        "a/.hidden:W1",
        ".a/b:W1",
        "a\\b:W1",
        "a/b:W0",
        "a/b:W",
    ],
)
def test_a_citation_with_an_empty_dot_led_or_malformed_part_is_not_one(ref: str) -> None:
    """Each segment is shaped like a repo name, so none can be empty, `..` or dot-led."""
    assert foreign_symbol(ref) is None
    assert not is_reference(ref)


def test_a_nested_citation_is_a_reference() -> None:
    """The reference check accepts it wherever a flat one is accepted."""
    assert is_reference("parent/child:W3")


def test_a_nested_queue_is_read_at_its_path(tmp_path: Path) -> None:
    """`parent/child` resolves to `<root>/parent/child/.claude/paths-forward.json`."""
    _nested(tmp_path, "parent/child")
    landed, why = foreign.landed(tmp_path, "parent/child", "W1")
    assert landed
    assert why.startswith("W1 is done in ")
    assert why.endswith("parent/child/.claude/paths-forward.json")


def test_a_segment_that_leaves_the_root_is_refused_by_name(tmp_path: Path) -> None:
    """A `..` segment is refused before any read, however deep."""
    _nested(tmp_path, "parent/child")
    landed, why = foreign.landed(tmp_path, "parent/../parent/child", "W1")
    assert not landed
    assert "refused" in why


def test_an_empty_or_dot_led_segment_is_refused(tmp_path: Path) -> None:
    """An empty segment is a refusal, not a lookup of the parent; a hidden directory is no name."""
    _nested(tmp_path, "parent")
    for name in ("parent/", "parent//child", "/parent", "parent/.hidden", ".parent/child"):
        landed, why = foreign.landed(tmp_path, name, "W1")
        assert not landed
        assert "refused" in why


def test_a_nested_name_with_no_queue_says_so(tmp_path: Path) -> None:
    """Absent is absent: named, not refused."""
    landed, why = foreign.landed(tmp_path, "parent/child", "W1")
    assert not landed
    assert "no queue file" in why
