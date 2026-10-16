# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`--show` with several symbols: one record each, in order, naming any that resolve to none."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, cast

from mikemol.pathsforward import cli

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

type Rec = dict[str, object]

_SHOW = "--show"
_REFUSED = cli.EXIT_REFUSED
_SYMBOL_LINE = re.compile(r'^  "symbol": "(W\d+)"', re.MULTILINE)


def _card(symbol: str) -> Rec:
    return {
        "symbol": symbol,
        "title": f"title of {symbol}",
        "status": "ready",
        "enables": [],
        "touches": [],
        "blocked_on": [],
        "blocked_kind": None,
        "next_bounded_step": "",
        "evidence": "",
        "issued_at": "2026-10-16T08:00:00Z",
        "ticks_blocked": 0,
    }


def _file(tmp_path: Path) -> Path:
    path = tmp_path / "paths-forward.json"
    doc: Rec = {
        "counter": 9,
        "waypoints": [_card("W1"), _card("W2"), _card("W3")],
        "residue": [{"symbol": "W4", "title": "gone", "dropped_at": "t", "reason": "r"}],
    }
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _printed(out: str) -> list[str]:
    """Read the symbol line of each indented record in `out`.

    Returns:
        one symbol per record, in the order printed.

    """
    return cast("list[str]", _SYMBOL_LINE.findall(out))


def test_several_symbols_print_in_the_order_given(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Live cards and a residue entry, asked for out of queue order, print in that order."""
    assert cli.main(["--state", str(_file(tmp_path)), _SHOW, "W3", "W4", "W1"]) == 0
    assert _printed(capsys.readouterr().out) == ["W3", "W4", "W1"]


def test_an_unknown_symbol_is_named_the_rest_still_print_and_the_exit_refuses(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """W9 was never issued: W1 and W2 print, W9 is named on stderr, and the exit is a refusal."""
    argv = ["--state", str(_file(tmp_path)), _SHOW, "W1", "W9", "W2"]
    assert cli.main(argv) == _REFUSED
    shown = capsys.readouterr()
    assert _printed(shown.out) == ["W1", "W2"]
    assert "W9: in neither waypoints nor residue" in shown.err


def test_one_symbol_prints_as_it_always_did(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The control: a single symbol is one indented record and a zero exit."""
    assert cli.main(["--state", str(_file(tmp_path)), _SHOW, "W2"]) == 0
    out = capsys.readouterr().out
    assert _printed(out) == ["W2"]
    assert out.startswith('{\n  "symbol": "W2"')
