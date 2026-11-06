# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that every launcher in `hooks/bin` is a regular file, the dispatchers one (W1173).

⚑ A TRACKED LINK IS NOT CARRIED INTO EVERY CHECKOUT AND SNAPSHOT AS A LINK, so a launcher that is
one can be absent where a hook needs it, and the repository's rule is that no link is created. The
four dispatching launchers (`no-chaining`, `no-verify`, `pycheck`, `shellcheck`) used to be links to
`mikemol-hook-structural-query`, which dispatches on the BASENAME of its own path, so a regular copy
with identical bytes works under each name. ⚑ THE CONTROL IS THE ORIGINAL ITSELF: it is a regular
file and the copies are measured against its bytes, not against an expectation written beside them.
"""

from __future__ import annotations

from pathlib import Path

_BIN = Path(__file__).parent.parent / "bin"
_ORIGINAL = "mikemol-hook-structural-query"
_COPIES = (
    "mikemol-hook-no-chaining",
    "mikemol-hook-no-verify",
    "mikemol-hook-pycheck",
    "mikemol-hook-shellcheck",
)
_EXECUTE = 0o111


def test_no_launcher_in_bin_is_a_link() -> None:
    """Every entry of hooks/bin is a regular file: none is a link, whatever it points at."""
    entries = sorted(_BIN.iterdir())
    assert entries, "hooks/bin is empty, so this witness would pass over nothing"
    links = [entry.name for entry in entries if entry.is_symlink()]
    assert links == []


def test_the_dispatching_launchers_hold_the_originals_bytes_and_are_executable() -> None:
    """Each copy equals the structural-query launcher byte for byte and keeps its execute bit."""
    original = (_BIN / _ORIGINAL).read_bytes()
    assert original.startswith(b"#!/usr/bin/env bash")
    for name in _COPIES:
        launcher = _BIN / name
        assert launcher.read_bytes() == original, name
        assert launcher.stat().st_mode & _EXECUTE, name
