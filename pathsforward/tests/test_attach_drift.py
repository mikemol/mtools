# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `--check` on attachments: a missing or edited file is a finding (W932).

⚑ THE UNCHANGED FILE IS THE POSITIVE CONTROL: without it, an arm asserting a finding cannot be told
from a check that reports every attachment. No link is created here (operator 2026-10-02); the link
arm patches `Path.is_symlink` for one named path.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.pathsforward import attach, check
from mikemol.pathsforward.model import validate

if TYPE_CHECKING:
    from collections.abc import Callable

    import pytest

    from mikemol.pathsforward.model import State

_LETTER = "letter.md"
_BODY = b"as cited\n"


def _state(root: Path) -> State:
    """Build a queue whose W1 attaches `letter.md`, pinned to the bytes first written.

    Returns:
        the state.

    """
    (root / _LETTER).write_bytes(_BODY)
    return validate(
        {
            "counter": 1,
            "project_root": str(root),
            "waypoints": [
                {
                    "symbol": "W1",
                    "title": "t",
                    "status": "ready",
                    "blocked_on": [],
                    "blocked_kind": None,
                    "enables": [],
                    "evidence": "",
                    "attachments": [{"path": _LETTER, "sha256": hashlib.sha256(_BODY).hexdigest()}],
                }
            ],
            "residue": [],
        }
    )


def _is_link(linked: Path) -> Callable[[Path], bool]:
    """Build a stand-in for `Path.is_symlink` that answers True for one path only.

    Returns:
        the method to patch in.

    """

    def probe(self: Path) -> bool:
        return self == linked

    return probe


def test_an_unchanged_attachment_is_not_found(tmp_path: Path) -> None:
    """The positive control: the bytes still hash alike, so nothing is reported."""
    state = _state(tmp_path)
    assert attach.drift(state) == []
    assert not any(_LETTER in f for f in check.check(state))


def test_an_edited_attachment_is_found(tmp_path: Path) -> None:
    """The file changed after it was cited."""
    state = _state(tmp_path)
    (tmp_path / _LETTER).write_bytes(b"edited later\n")
    assert attach.drift(state) == [f"W1: attachments: {_LETTER!r} changed since it was attached"]
    assert any("changed since" in f for f in check.check(state))


def test_a_missing_attachment_is_found(tmp_path: Path) -> None:
    """The file is gone."""
    state = _state(tmp_path)
    (tmp_path / _LETTER).unlink()
    assert attach.drift(state) == [f"W1: attachments: {_LETTER!r} is missing or not a plain file"]


def test_a_directory_in_its_place_is_found(tmp_path: Path) -> None:
    """Something that is not a plain file is reported the same way."""
    state = _state(tmp_path)
    (tmp_path / _LETTER).unlink()
    (tmp_path / _LETTER).mkdir()
    assert len(attach.drift(state)) == 1


def test_a_link_is_reported_and_never_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A path that answers as a link is missing as far as the pin goes; none exists on disk."""
    state = _state(tmp_path)
    monkeypatch.setattr(Path, "is_symlink", _is_link(tmp_path / _LETTER))
    assert attach.drift(state) == [f"W1: attachments: {_LETTER!r} is missing or not a plain file"]
