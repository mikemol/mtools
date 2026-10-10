# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `--update W<n> --attach PATH`: it pins a file by hash and refuses what it must.

W931. ⚑ NO LINK IS CREATED HERE (operator 2026-10-02: never create one, not even as a test input).
The link refusal is exercised by making `Path.is_symlink` answer True for one named path, so the
branch runs without a link existing anywhere.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from mikemol.pathsforward import attach, cli, store

if TYPE_CHECKING:
    from collections.abc import Callable

Rec = dict[str, object]

_REPO = "fx"
_LETTER = ".claude/letters/x.md"
_BODY = b"mtools to nemik\n"
_OTHER = ".claude/letters/y.md"


def _queue(tmp_path: Path) -> Path:
    """Write a queue for a repo holding W1 and two letters.

    Returns:
        the state path.

    """
    root = tmp_path / _REPO
    (root / ".claude" / "letters").mkdir(parents=True)
    (root / _LETTER).write_bytes(_BODY)
    (root / _OTHER).write_bytes(b"other\n")
    doc: Rec = {
        "counter": 1,
        "project_root": str(root),
        "waypoints": [
            {
                "symbol": "W1",
                "title": "one",
                "status": "ready",
                "blocked_on": [],
                "blocked_kind": None,
                "next_bounded_step": "s",
                "evidence": "",
                "ticks_blocked": 0,
            }
        ],
        "residue": [],
    }
    path = root / ".claude" / "paths-forward.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _attached(path: Path) -> list[tuple[str, str]]:
    """Read W1's attachments back.

    Returns:
        the well-formed (path, sha256) pairs.

    """
    return attach.entries(store.load(path).waypoints[0])


def _is_link(linked: Path) -> Callable[[Path], bool]:
    """Build a stand-in for `Path.is_symlink` that answers True for one path only.

    Returns:
        the method to patch in.

    """

    def probe(self: Path) -> bool:
        return self == linked

    return probe


def test_attaching_a_file_stores_its_path_and_hash(tmp_path: Path) -> None:
    """The positive control: the stored digest is the sha256 of the file's bytes."""
    path = _queue(tmp_path)
    code = cli.main(["--state", str(path), "--update", "W1", "--attach", _LETTER])
    assert code == cli.EXIT_OK
    assert _attached(path) == [(_LETTER, hashlib.sha256(_BODY).hexdigest())]


def test_a_second_file_is_added_and_a_changed_file_replaces_its_entry(tmp_path: Path) -> None:
    """Other attachments are kept; re-attaching a path updates its hash and keeps one entry."""
    path = _queue(tmp_path)
    root = path.parent.parent
    cli.main(["--state", str(path), "--update", "W1", "--attach", _LETTER])
    cli.main(["--state", str(path), "--update", "W1", "--attach", _OTHER])
    (root / _LETTER).write_bytes(b"edited\n")
    cli.main(["--state", str(path), "--update", "W1", "--attach", _LETTER])
    assert _attached(path) == [
        (_OTHER, hashlib.sha256(b"other\n").hexdigest()),
        (_LETTER, hashlib.sha256(b"edited\n").hexdigest()),
    ]


@pytest.mark.parametrize(
    "bad",
    ["/etc/passwd", "../outside.md", ".claude/../../outside.md", "nowhere.md", ".claude/letters"],
)
def test_an_absolute_climbing_missing_or_directory_path_is_refused(
    tmp_path: Path, bad: str
) -> None:
    """Exit 2 and nothing stored."""
    path = _queue(tmp_path)
    code = cli.main(["--state", str(path), "--update", "W1", "--attach", bad])
    assert code == cli.EXIT_REFUSED
    assert attach.KEY not in store.load(path).waypoints[0]


def test_a_link_anywhere_along_the_path_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The file itself or a directory above it being a link is refused; none exists on disk."""
    path = _queue(tmp_path)
    root = path.parent.parent
    for linked in (root / _LETTER, root / ".claude"):
        monkeypatch.setattr(Path, "is_symlink", _is_link(linked))
        code = cli.main(["--state", str(path), "--update", "W1", "--attach", _LETTER])
        assert code == cli.EXIT_REFUSED
    assert _attached(path) == []
