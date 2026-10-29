# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A repository's declaration decides what its census counts, and a bad one is a refusal (W1957).

⚑ THE CONTROLS ARE THE TWO WAYS A GUESS GOES WRONG: a file that wears a ratchet's NAME but is not
declared must not be counted when a declaration exists, and a declaration that cannot be trusted
must never read as an empty one (that would show every ratchet paid down by breaking one file).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from mikemol.ratchet import cli, declaration, fleetcensus

if TYPE_CHECKING:
    from pathlib import Path


def _put(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _declare(repo: Path, rows: list[dict[str, str]]) -> None:
    body: dict[str, object] = {"ratchets": rows}
    _put(repo / declaration.NAME, json.dumps(body))


def _only_the_declaration(self: Path) -> bool:
    return self.name == declaration.NAME


def test_a_declaration_wins_over_names_and_a_missing_one_falls_back(tmp_path: Path) -> None:
    """Declared rows only when ratchets.json exists; the name classifier when it does not."""
    declared = tmp_path / "declared"
    _put(declared / "gate" / "pace.txt", "a\nb\n")
    _put(declared / "notes" / "emissions-baseline.json", '{"x": 1}')
    _declare(declared, [{"path": "gate/pace.txt", "kind": "baseline"}])
    assert [r.line() for r in fleetcensus.census_repo(declared)] == [
        "declared gate/pace.txt baseline value=2 floor=0 guessed=0"
    ]
    guessed = tmp_path / "guessed"
    _put(guessed / "notes" / "emissions-baseline.json", '{"x": 1}')
    assert [r.line() for r in fleetcensus.census_repo(guessed)] == [
        "guessed notes/emissions-baseline.json baseline value=1 floor=0 guessed=1"
    ]


def test_a_declared_file_that_is_missing_stays_listed_as_unread(tmp_path: Path) -> None:
    """The declaration says it should exist, so it is UNREAD and never quietly left out."""
    _declare(tmp_path, [{"path": "gone.txt", "kind": "allowlist"}])
    rows = fleetcensus.census_repo(tmp_path)
    said = f"{tmp_path.name} gone.txt allowlist value=UNREAD floor=0 guessed=0"
    assert [r.line() for r in rows] == [said]


@pytest.mark.parametrize(
    "document",
    [
        "{nope",
        "[]",
        '{"ratchets": 3}',
        '{"ratchets": ["x"]}',
        '{"ratchets": [{"kind": "baseline"}]}',
        '{"ratchets": [{"path": "/etc/x", "kind": "baseline"}]}',
        '{"ratchets": [{"path": "../x", "kind": "baseline"}]}',
        '{"ratchets": [{"path": "x", "kind": "guess"}]}',
    ],
)
def test_a_declaration_that_cannot_be_trusted_is_refused_not_read_as_empty(
    tmp_path: Path, document: str
) -> None:
    """Not JSON, not an object with a ratchets list, or a row with a bad path or kind."""
    _put(tmp_path / declaration.NAME, document)
    with pytest.raises(declaration.DeclarationError):
        fleetcensus.census_repo(tmp_path)


def test_the_census_command_says_so_and_fails_on_a_bad_declaration(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A refusal is exit 1 naming the file, so a caller never mistakes it for a clean census."""
    _put(tmp_path / declaration.NAME, "{nope")
    assert cli.main(["census", "--repo", str(tmp_path)]) == 1
    captured = capsys.readouterr()
    assert declaration.NAME in captured.err
    assert not captured.out


def test_a_link_is_never_read_as_a_declaration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No link is followed: a declaration that is a link reads as no declaration."""
    _declare(tmp_path, [{"path": "x.txt", "kind": "baseline"}])
    monkeypatch.setattr("pathlib.Path.is_symlink", _only_the_declaration)
    assert declaration.read(tmp_path) is None


def test_a_tombstone_present_at_head_may_not_vanish_or_change() -> None:
    """W1963: the retired list only grows; added tombstones and a reorder are free."""
    gone = declaration.Retired("a.json", "paid-to-zero-and-removed", "abc123")
    moved = declaration.Retired("b.json", "renamed-to", "def456", "c.json")
    extra = declaration.Retired("z.json", "reclassified-not-a-ratchet", "999999")
    assert declaration.lost_retired([gone, moved], [moved, extra, gone]) == []
    said = (
        "ratchets.json: retired a.json (paid-to-zero-and-removed, sha abc123) is gone or changed: "
        "the retired list only grows"
    )
    assert declaration.lost_retired([gone, moved], [moved]) == [said]
    edited = declaration.Retired("b.json", "renamed-to", "def456", "d.json")
    lost = declaration.lost_retired([gone, moved], [gone, edited])
    assert len(lost) == 1
    assert "b.json" in lost[0]
