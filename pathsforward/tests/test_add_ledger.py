# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`--add` ledgers `minted` under the new symbol (W534), as the atomize docstring says."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from mikemol.pathsforward import cli, ledger
from mikemol.pathsforward.atomize import advances
from mikemol.pathsforward.ledger import Parsed

if TYPE_CHECKING:
    from pathlib import Path

_TITLE = "a freshly minted waypoint"
_COUNTER = 3
_NEW = f"W{_COUNTER + 1}"


def _state(root: Path, *, locked: bool) -> Path:
    """Write a minimal state copy under `root`, tick-locked or not.

    Returns:
        the state path.

    """
    root.mkdir(parents=True, exist_ok=True)
    doc: dict[str, object] = {
        "counter": _COUNTER,
        "project_root": str(root),
        "waypoints": [],
        "residue": [],
    }
    path = root / "paths-forward.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    if locked:
        cli.main(["--state", str(path), "--lock", "A"])
    return path


def _entries(path: Path) -> list[Parsed]:
    """Read the ledger back, keeping only parsed lines.

    Returns:
        the parsed lines.

    """
    ledger_path = path.with_suffix(".ledger")
    if not ledger_path.exists():
        return []
    return [p for p in ledger.read(ledger_path) if isinstance(p, Parsed)]


def test_add_appends_exactly_one_minted_line(tmp_path: Path) -> None:
    """--add writes exactly one ledger line, parsing back as `minted` for the new symbol."""
    path = _state(tmp_path, locked=False)
    before = _entries(path)
    code = cli.main(["--state", str(path), "--add", _TITLE, "--caused-by", "repo:W9"])
    new = _entries(path)[len(before) :]
    assert code == cli.EXIT_OK
    assert len(new) == 1
    assert (new[0].entry.symbol, new[0].entry.outcome, new[0].entry.mechanism) == (
        _NEW,
        "minted",
        "-",
    )
    assert (new[0].entry.note, new[0].entry.evidence) == (_TITLE, "repo:W9")


def test_a_minted_line_is_not_an_advance(tmp_path: Path) -> None:
    """The atomize reader counts no advance for a symbol whose only ledger line is its mint."""
    path = _state(tmp_path, locked=False)
    cli.main(["--state", str(path), "--add", _TITLE])
    assert advances(_NEW, list(_entries(path))) == 0


def test_a_multiline_title_is_refused_and_changes_nothing(tmp_path: Path) -> None:
    """A title with a newline exits 2 and leaves the state file and the ledger untouched."""
    path = _state(tmp_path, locked=False)
    state_before = path.read_bytes()
    entries_before = _entries(path)
    code = cli.main(["--state", str(path), "--add", "first\nsecond"])
    assert code == cli.EXIT_REFUSED
    assert path.read_bytes() == state_before
    assert _entries(path) == entries_before


def test_the_kind_follows_minted_during(tmp_path: Path) -> None:
    """An unlocked add ledgers kind `interrupt`; a locked one ledgers kind `tick`."""
    unlocked = _state(tmp_path / "u", locked=False)
    locked = _state(tmp_path / "l", locked=True)
    cli.main(["--state", str(unlocked), "--add", _TITLE])
    cli.main(["--state", str(locked), "--add", _TITLE])
    assert _entries(unlocked)[-1].entry.kind == "interrupt"
    assert _entries(locked)[-1].entry.kind == "tick"
