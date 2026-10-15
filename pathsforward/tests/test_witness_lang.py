# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `--witness-lang` through the command line (mtools:W1260).

⚑ THE LANGUAGE IS DECLARED WITH THE QUERY: `--add` and `--update` take `--witness-lang rego|promql`
beside `--witness`, store it on the card, and refuse a witness without it, a language without a
witness, and an unknown language, each before anything is saved.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from mikemol.pathsforward import cli

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

Rec = dict[str, object]

_OK = cli.EXIT_OK
_REFUSED = cli.EXIT_REFUSED


def _state(tmp_path: Path) -> Path:
    card: Rec = {
        "symbol": "W1",
        "title": "t",
        "status": "ready",
        "enables": [],
        "blocked_on": [],
        "blocked_kind": None,
        "next_bounded_step": "s",
        "evidence": "",
        "ticks_blocked": 0,
    }
    doc: Rec = {"counter": 1, "project_root": str(tmp_path), "waypoints": [card], "residue": []}
    path = tmp_path / "paths-forward.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _cards(path: Path) -> list[Rec]:
    doc = cast("Rec", json.loads(path.read_text(encoding="utf-8")))
    return cast("list[Rec]", doc["waypoints"])


def test_add_stores_the_declared_language_beside_the_witness(tmp_path: Path) -> None:
    """`--add T --witness Q --witness-lang promql` mints a card carrying both."""
    path = _state(tmp_path)
    argv = ["--state", str(path), "--add", "wait", "--witness", "up == 1"]
    assert cli.main([*argv, "--witness-lang", "promql"]) == _OK
    minted = _cards(path)[-1]
    assert (minted["witness"], minted["witness_lang"]) == ("up == 1", "promql")


def test_update_sets_both_together_and_update_many_takes_them_too(tmp_path: Path) -> None:
    """The language travels with the witness through `--update` and `--update-many`."""
    path = _state(tmp_path)
    state = ["--state", str(path)]
    one = ["--update", "W1", "--witness", "q", "--witness-lang", "rego"]
    assert cli.main([*state, *one]) == _OK
    many = ["--update-many", "W1", "--witness", "r", "--witness-lang", "promql", "--write"]
    assert cli.main([*state, *many]) == _OK
    card = _cards(path)[0]
    assert (card["witness"], card["witness_lang"]) == ("r", "promql")


def test_a_witness_without_a_language_is_refused_and_nothing_is_saved(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The refusal names the flag, and the queue is byte-identical afterwards."""
    path = _state(tmp_path)
    before = path.read_bytes()
    argv = ["--state", str(path), "--update", "W1", "--witness", "up == 1"]
    assert cli.main(argv) == _REFUSED
    assert "needs its language" in capsys.readouterr().err
    assert path.read_bytes() == before


def test_a_language_alone_and_an_unknown_language_are_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--witness-lang` with no witness, and `sql` as a language, each exit 2 and save nothing."""
    path = _state(tmp_path)
    before = path.read_bytes()
    state = ["--state", str(path), "--update", "W1"]
    assert cli.main([*state, "--witness-lang", "rego"]) == _REFUSED
    assert "give --witness with it" in capsys.readouterr().err
    assert cli.main([*state, "--witness", "q", "--witness-lang", "sql"]) == _REFUSED
    assert "not one of rego, promql" in capsys.readouterr().err
    assert path.read_bytes() == before
