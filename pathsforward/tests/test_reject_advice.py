# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `--reject-advice TOOL RULE REASON`: one command rejects a whole selector.

W1243. ⚑ THE CONTROLS: a rejection changes only the open rows of that tool and rule; an empty
reason and a selector with nothing open are refused and leave the file byte-identical; and the
reason is stored where the next dry run reads it.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from mikemol.pathsforward import advice, cli

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

Rec = dict[str, object]
_TOOL = "--block-matching"
_RULE = "blocks-on"
_REFUSED = 2


def _queue(tmp_path: Path) -> Path:
    rows: list[Rec] = [
        {"tool": _TOOL, "rule": _RULE, "subject": "W1", "action": "block W1", "status": "open"},
        {"tool": _TOOL, "rule": _RULE, "subject": "W2", "action": "block W2", "status": "open"},
        {"tool": _TOOL, "rule": "other", "subject": "W3", "action": "x", "status": "open"},
        {"tool": "--prune-landed", "rule": _RULE, "subject": "W4", "action": "y", "status": "open"},
    ]
    doc: Rec = {
        "counter": 4,
        "project_root": str(tmp_path),
        "waypoints": [],
        "residue": [],
        "advice": rows,
    }
    path = tmp_path / "paths-forward.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _rows(path: Path) -> list[Rec]:
    doc = cast("dict[str, list[Rec]]", json.loads(path.read_text(encoding="utf-8")))
    return doc[advice.KEY]


def _run(path: Path, *words: str) -> int:
    return cli.main(["--state", str(path), "--reject-advice", *words])


def test_one_command_rejects_every_open_row_of_the_tool_and_rule(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """W1 and W2 are rejected with the reason; another rule and another tool are untouched."""
    path = _queue(tmp_path)
    assert _run(path, _TOOL, _RULE, "they wait on W9's sweep") == 0
    assert "rejected 2 piece(s)" in capsys.readouterr().out
    status = {str(r["subject"]): r["status"] for r in _rows(path)}
    assert status == {
        "W1": advice.REJECTED,
        "W2": advice.REJECTED,
        "W3": advice.OPEN,
        "W4": advice.OPEN,
    }
    reasons = {r["reason"] for r in _rows(path) if r["status"] == advice.REJECTED}
    assert reasons == {"they wait on W9's sweep"}


def test_an_empty_reason_or_nothing_open_is_refused_and_changes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The file is byte-identical after a blank reason and after a selector with no open row."""
    path = _queue(tmp_path)
    before = path.read_bytes()
    assert _run(path, _TOOL, _RULE, "   ") == _REFUSED
    assert _run(path, "nosuchtool", "no-such-rule", "reason") == _REFUSED
    assert path.read_bytes() == before
    assert "needs a reason" in capsys.readouterr().err


def test_a_second_rejection_of_the_same_selector_finds_nothing_open(tmp_path: Path) -> None:
    """Rejecting twice is refused the second time: the rows are already rejected, not open."""
    path = _queue(tmp_path)
    assert _run(path, _TOOL, _RULE, "first") == 0
    assert _run(path, _TOOL, _RULE, "second") == _REFUSED
    reasons = {r["reason"] for r in _rows(path) if r["status"] == advice.REJECTED}
    assert reasons == {"first"}
