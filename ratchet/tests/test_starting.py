# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The starting declaration is the census's guess, offered and never imposed (W1959).

⚑ THE POSITIVE CONTROL IS THE ROUND TRIP: write the offered document and the census must read the
same files as DECLARED (`guessed=0`), with the same paths, kinds and values the guess gave. An offer
that changed what the census sees would be a different ratchet, not a starting point.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

import pytest

from mikemol.ratchet import cli, declaration, fleetcensus, starting

if TYPE_CHECKING:
    from pathlib import Path


def _put(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _repo(root: Path) -> Path:
    repo = root / "alpha"
    _put(repo / "baselines" / "ruff-baseline.json", '{"a.py": {"D103": 2}}')
    _put(repo / ".claude" / "debt-ledger.json", "{}")
    _put(repo / "ratchet-preview.txt", "k1\nk2\n")
    _put(repo / "debtplan.json", '{"exclude": ["x"]}')
    _put(repo / "tmp" / "scratch-baseline.json", '{"x": 1}')
    _put(repo / "broken-baseline.json", "{nope")
    # An exemption row (a per-file ignore) is a census row but not a file ratchet: never offered.
    _put(repo / "pyproject.toml", '[tool.ruff.lint.per-file-ignores]\n"a.py" = ["D103"]\n')
    return repo


def test_the_offer_lists_the_readable_ratchet_files_and_names_what_it_left_out(
    tmp_path: Path,
) -> None:
    """Three files by path and kind; the config, the staging file and a broken one are out."""
    text, notes = starting.document(_repo(tmp_path))
    listed = cast("dict[str, list[dict[str, str]]]", json.loads(text))["ratchets"]
    assert listed == [
        {"path": ".claude/debt-ledger.json", "kind": "debt"},
        {"path": "baselines/ruff-baseline.json", "kind": "baseline"},
        {"path": "ratchet-preview.txt", "kind": "preview"},
    ]
    assert notes == ["left out: broken-baseline.json could not be read"]
    assert text.endswith("\n")


def test_the_written_offer_is_read_back_by_the_census_as_declared_and_unchanged(
    tmp_path: Path,
) -> None:
    """The round trip: the same files, kinds and values, now declared and no longer guessed."""
    repo = _repo(tmp_path)
    guessed = [
        row for row in fleetcensus.census_repo(repo) if row.kind in {"debt", "baseline", "preview"}
    ]
    text, _notes = starting.document(repo)
    starting.write(repo, text)
    declared = fleetcensus.census_repo(repo)
    assert declared
    assert all(row.guessed is False for row in declared if row.kind != "exemption")
    key = [(row.ratchet, row.kind, row.value) for row in declared if row.guessed is False]
    wanted = [(r.ratchet, r.kind, r.value) for r in guessed if r.value is not None]
    assert sorted(key) == sorted(wanted)


def test_an_existing_declaration_is_never_overwritten(tmp_path: Path) -> None:
    """The repository's own word stands: both refuse and the file is untouched."""
    repo = _repo(tmp_path)
    _put(repo / declaration.NAME, '{"ratchets": []}')
    with pytest.raises(declaration.DeclarationError):
        starting.document(repo)
    with pytest.raises(declaration.DeclarationError):
        starting.write(repo, "{}")
    assert (repo / declaration.NAME).read_text(encoding="utf-8") == '{"ratchets": []}'


def test_the_command_prints_without_write_and_writes_only_with_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Without `--write` the file does not appear; with it, it does and the command says so."""
    repo = _repo(tmp_path)
    assert cli.main(["declare", str(repo)]) == 0
    assert not (repo / declaration.NAME).exists()
    assert '"ratchets"' in capsys.readouterr().out
    assert cli.main(["declare", str(repo), "--write"]) == 0
    assert (repo / declaration.NAME).is_file()
    assert cli.main(["declare", str(repo), "--write"]) == 1
