# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A card the automatic prune frees is named first in the tick-open output as ready (W1598)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from mikemol.pathsforward import cli

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

    from mikemol.pathsforward.model import Json


def _card(symbol: str, status: str, blocked_on: list[str] | None = None) -> Json:
    return {
        "symbol": symbol,
        "title": f"t{symbol}",
        "status": status,
        "blocked_on": blocked_on or [],
        "blocked_kind": "agent" if blocked_on else None,
        "next_bounded_step": "s",
        "evidence": "",
        "ticks_blocked": 0,
    }


def _write(queue: Path, *cards: Json) -> None:
    queue.parent.mkdir(parents=True, exist_ok=True)
    waypoints = cast("list[object]", list(cards))
    doc: dict[str, object] = {
        "counter": len(cards),
        "project_root": str(queue.parent.parent),
        "residue": [],
        "waypoints": waypoints,
    }
    queue.write_text(json.dumps(doc), encoding="utf-8")


def test_the_freed_card_is_named_before_the_blocker_changes_and_the_rest_of_the_open(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """W2 landing frees W1: `UNBLOCKED W1` precedes the BLOCKER line and the bump line."""
    queue = tmp_path / ".claude" / "paths-forward.json"
    argv = ["--state", str(queue), "--root", str(tmp_path), "--tick-open", "tester"]
    _write(queue, _card("W1", "blocked", ["W2"]), _card("W2", "working"))
    assert cli.main(argv) == cli.EXIT_OK
    capsys.readouterr()
    assert cli.main(["--state", str(queue), "--unlock", "tester"]) == cli.EXIT_OK
    _write(queue, _card("W1", "blocked", ["W2"]), _card("W2", "done"))
    assert cli.main(argv) == cli.EXIT_OK
    out = capsys.readouterr().out
    freed = out.index("UNBLOCKED W1")
    assert freed < out.index("BLOCKER W1 <- W2 working -> done")
    assert freed < out.index("bumped ")
    assert freed < out.index("tick open as tester")


def test_a_queue_that_frees_nothing_opens_as_before(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The control: no landed blocker, no UNBLOCKED line, and the open still completes."""
    queue = tmp_path / ".claude" / "paths-forward.json"
    _write(queue, _card("W1", "blocked", ["W2"]), _card("W2", "working"))
    argv = ["--state", str(queue), "--root", str(tmp_path), "--tick-open", "tester"]
    assert cli.main(argv) == cli.EXIT_OK
    out = capsys.readouterr().out
    assert "UNBLOCKED" not in out
    assert "tick open as tester" in out
