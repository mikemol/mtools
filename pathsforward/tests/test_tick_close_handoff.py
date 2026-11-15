# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The real `--tick-close` verb ends on the reviewer hand-off line the tool itself timed (W2154).

⚑ THE LINE LANDED AT cfe689c WITH A PURE-FUNCTION TEST ONLY (test_landed): nothing ran the verb and
read its last output line. This runs `cli.main` on a temporary queue and checks the LAST printed
line against the ledger line the same close wrote, so a time typed by hand, or a hand-off printed
before another line, fails here.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, cast

from mikemol.pathsforward import cli

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

    from mikemol.pathsforward.model import Json

_HOLDER = "mtools-tick-opus"
_HANDOFF = re.compile(r"^G1-HANDOFF (\S+) (\S+) closed=(\S+) session=(\S+)$")


def _state(tmp_path: Path) -> Path:
    card: Json = {
        "symbol": "W1",
        "title": "tW1",
        "status": "working",
        "blocked_on": [],
        "blocked_kind": None,
        "next_bounded_step": "s",
        "evidence": "",
        "ticks_blocked": 0,
    }
    doc: Json = {"counter": 1, "project_root": str(tmp_path), "waypoints": [card], "residue": []}
    path = tmp_path / "paths-forward.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _last_line(text: str) -> str:
    return [line for line in text.splitlines() if line.strip()][-1]


def test_a_close_ends_on_the_handoff_line_carrying_the_ledger_lines_own_time(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The last line names this repo, the card and the timestamp the ledger line begins with."""
    path = _state(tmp_path)
    assert cli.main(["--state", str(path), "--lock", _HOLDER]) == cli.EXIT_OK
    capsys.readouterr()
    code = cli.main(
        ["--state", str(path), "--tick-close", _HOLDER, "W1", "advanced", "unblock", "the note"]
    )
    out = capsys.readouterr().out
    assert code == cli.EXIT_OK
    found = _HANDOFF.match(_last_line(out))
    assert found is not None, out
    repo, symbol, closed, _session = cast("tuple[str, str, str, str]", found.groups())
    ledger = (tmp_path / "paths-forward.ledger").read_text(encoding="utf-8")
    ticks = [line for line in ledger.splitlines() if line.split()[1:2] == ["tick"]]
    assert (repo, symbol, closed) == (tmp_path.parent.name, "W1", ticks[-1].split()[0])


def test_a_refused_close_prints_no_handoff_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The negative control: an outcome outside the declared set writes no tick line to name."""
    path = _state(tmp_path)
    assert cli.main(["--state", str(path), "--outcomes-set", "advanced", "blocked"]) == cli.EXIT_OK
    assert cli.main(["--state", str(path), "--lock", _HOLDER]) == cli.EXIT_OK
    capsys.readouterr()
    code = cli.main(
        ["--state", str(path), "--tick-close", _HOLDER, "W1", "nonsense", "unblock", "the note"]
    )
    out = capsys.readouterr().out
    assert code == cli.EXIT_REFUSED
    assert "G1-HANDOFF" not in out
