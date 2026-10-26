# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A retired ratchet is written down as a tombstone, never inferred from a file going away (W1963).

⚑ THE CONTROLS: a retired entry needs a known reason and a sha, a rename needs its new path and
nothing else may carry one, a path cannot be both declared and retired, a tombstone line has no
`value=` so a reader of ratchet rows skips it, and a retired file is not a ratchet row.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from mikemol.ratchet import cli, declaration, fleetcensus

if TYPE_CHECKING:
    from pathlib import Path


def _declare(repo: Path, ratchets: list[dict[str, str]], retired: object) -> None:
    body: dict[str, object] = {"ratchets": ratchets, "retired": retired}
    (repo / declaration.NAME).write_text(json.dumps(body), encoding="utf-8")


def _entry(**given: str) -> dict[str, str]:
    base = {"path": "old.txt", "reason": "paid-to-zero-and-removed", "sha": "abc1234"}
    return {**base, **given}


def test_all_three_reasons_are_read_and_a_rename_carries_its_new_path(tmp_path: Path) -> None:
    """The list comes back in file order with each entry's path, reason, sha and target."""
    _declare(
        tmp_path,
        [],
        [
            _entry(path="a.txt", reason="reclassified-not-a-ratchet"),
            _entry(path="b.txt"),
            _entry(path="c.txt", reason="renamed-to", to="d.txt"),
        ],
    )
    assert declaration.read_retired(tmp_path) == [
        declaration.Retired("a.txt", "reclassified-not-a-ratchet", "abc1234"),
        declaration.Retired("b.txt", "paid-to-zero-and-removed", "abc1234"),
        declaration.Retired("c.txt", "renamed-to", "abc1234", "d.txt"),
    ]


def test_no_declaration_or_no_retired_list_is_an_empty_list(tmp_path: Path) -> None:
    """Absent is none; a declaration that lists none is none."""
    assert declaration.read_retired(tmp_path) == []
    (tmp_path / declaration.NAME).write_text('{"ratchets": []}', encoding="utf-8")
    assert declaration.read_retired(tmp_path) == []


@pytest.mark.parametrize(
    "bad",
    [
        _entry(reason="gone"),
        _entry(sha=""),
        _entry(path="/etc/x"),
        _entry(path="../x"),
        _entry(reason="renamed-to"),
        _entry(to="elsewhere.txt"),
        _entry(reason="renamed-to", to="/etc/x"),
    ],
)
def test_an_untrustworthy_retired_entry_is_a_refusal(tmp_path: Path, bad: dict[str, str]) -> None:
    """An unknown reason, no sha, a path leaving the repo, a rename without a target is refused."""
    _declare(tmp_path, [], [bad])
    with pytest.raises(declaration.DeclarationError):
        declaration.read_retired(tmp_path)


def test_a_retired_list_that_is_not_a_list_is_a_refusal(tmp_path: Path) -> None:
    """Reading it as empty would show every retirement as never written."""
    _declare(tmp_path, [], {"path": "x"})
    with pytest.raises(declaration.DeclarationError):
        declaration.read_retired(tmp_path)


def test_a_path_both_declared_and_retired_is_a_refusal(tmp_path: Path) -> None:
    """One file cannot be a live ratchet and a tombstone."""
    (tmp_path / "old.txt").write_text("a\n", encoding="utf-8")
    _declare(tmp_path, [{"path": "old.txt", "kind": "baseline"}], [_entry()])
    with pytest.raises(declaration.DeclarationError, match="both declared and retired"):
        declaration.read(tmp_path)


def test_a_tombstone_line_has_no_value_and_a_rename_ends_with_its_target(tmp_path: Path) -> None:
    """No `value=` so an older reader of ratchet rows skips it; the census prints it after them."""
    _declare(
        tmp_path,
        [],
        [_entry(), _entry(path="c.txt", reason="renamed-to", to="d.txt")],
    )
    lines = fleetcensus.tombstones(tmp_path)
    name = tmp_path.name
    assert lines == [
        f"{name} old.txt retired reason=paid-to-zero-and-removed sha=abc1234",
        f"{name} c.txt retired reason=renamed-to sha=abc1234 to=d.txt",
    ]
    assert not any("value=" in line for line in lines)


def test_the_census_prints_tombstones_after_the_rows_and_a_retired_file_is_no_row(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A retired file still on disk is not counted; its tombstone is printed once."""
    (tmp_path / "live.txt").write_text("a\nb\n", encoding="utf-8")
    (tmp_path / "old.txt").write_text("a\n", encoding="utf-8")
    _declare(tmp_path, [{"path": "live.txt", "kind": "baseline"}], [_entry()])
    assert cli.main(["census", "--repo", str(tmp_path)]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0].endswith("live.txt baseline value=2 floor=0 guessed=0")
    assert out[1].endswith("old.txt retired reason=paid-to-zero-and-removed sha=abc1234")
    assert out[-1] == "# 1 ratchet file(s), 0 unread"
    assert not any("old.txt baseline" in line for line in out)
