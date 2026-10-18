# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A hold on a human is lifted by a record of the operator's own words, read again now (W1525)."""

import json
from collections.abc import Sequence
from pathlib import Path

import pytest

from mikemol.hooks import hold_lift, standing_facts

_UUID = "f4501ac9-b3ef-4388-b195-6d9f93bcea5d"
_LINE = 77561
_READER = "/r/mikemol-transcriptstruct"


def _warrant(reader: str = "evil-command --anything") -> dict[str, object]:
    derived: dict[str, object] = {
        "@id": f"file:///t/session.jsonl#{_UUID}",
        "mtools:line": _LINE,
        "mtools:reader": reader,
    }
    return {"prov:wasDerivedFrom": derived}


class _Reader:
    """A stand-in transcript reader: records every argv and answers from a script."""

    def __init__(self, verify: tuple[int, str], hits: str) -> None:
        self.verify = verify
        self.hits = hits
        self.argvs: list[list[str]] = []

    def __call__(self, argv: Sequence[str]) -> tuple[int, str]:
        self.argvs.append(list(argv))
        return self.verify if "--verify" in argv else (0, self.hits)


def _verdict(*, ok: bool) -> str:
    body: dict[str, object] = {"ok": ok, "kind": "human"}
    return json.dumps(body) + "\n"


_OK = (0, _verdict(ok=True))
_ROW = '{"line": 77561, "kind": "human", "text": "W1510 is applied"}\n# 1 hit(s)\n'


def test_the_writers_warrant_shape_yields_the_cited_path_uuid_and_line() -> None:
    """The record is found from what the writer stores, not from its stored command."""
    assert hold_lift.cited(_warrant()) == ("/t/session.jsonl", _UUID, _LINE)


@pytest.mark.parametrize("bad", [None, {}, {"prov:wasDerivedFrom": {"@id": "x"}}])
def test_a_warrant_not_shaped_as_the_writer_writes_it_cites_nothing(bad: object) -> None:
    """Anything else is not a warrant to lift on."""
    assert hold_lift.cited(bad) is None


def test_a_human_record_naming_the_card_lifts_it() -> None:
    """Origin human by the reader's own verdict, and the same line names the symbol."""
    reader = _Reader(_OK, _ROW)
    assert hold_lift.verifies(_READER, _warrant(), "W1510", reader)


def test_the_command_stored_in_the_warrant_is_never_run() -> None:
    """A queue file is editable by any session, so only this module's own reader runs."""
    reader = _Reader(_OK, _ROW)
    hold_lift.verifies(_READER, _warrant("rm -rf /"), "W1510", reader)
    assert {argv[0] for argv in reader.argvs} == {_READER}


def test_a_record_the_reader_will_not_verify_as_human_does_not_lift() -> None:
    """A tool result or a peer's message fails --verify, and the hold stays."""
    reader = _Reader((4, ""), _ROW)
    assert not hold_lift.verifies(_READER, _warrant(), "W1510", reader)


def test_a_verdict_that_is_not_ok_does_not_lift() -> None:
    """Exit zero is not enough: the verdict must say ok."""
    reader = _Reader((0, _verdict(ok=False)), _ROW)
    assert not hold_lift.verifies(_READER, _warrant(), "W1510", reader)


def test_a_human_record_that_names_another_card_does_not_lift() -> None:
    """The line must match this card's symbol, so a lift for W9 cannot free W1510."""
    reader = _Reader(_OK, "# 0 hit(s)\n")
    assert not hold_lift.verifies(_READER, _warrant(), "W1510", reader)


def test_a_symbol_is_matched_whole_not_as_a_prefix() -> None:
    """W15 must not be freed by a record that names W1510: the pattern is anchored by word."""
    reader = _Reader(_OK, _ROW)
    hold_lift.verifies(_READER, _warrant(), "W15", reader)
    pattern = reader.argvs[-1][reader.argvs[-1].index("--human") + 1]
    assert pattern == r"\bW15\b"


def test_no_reader_leaves_every_hold_held(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A hook that cannot read the record must not lift on faith."""
    monkeypatch.setenv("HOME", str(tmp_path))
    row: dict[str, object] = {"symbol": "W1510", "warrants": [_warrant()]}
    assert not hold_lift.lifted(row, _Reader(_OK, _ROW), {"PATH": str(tmp_path / "empty")})


def test_a_row_with_no_warrant_is_not_lifted(tmp_path: Path) -> None:
    """The ordinary hold: nothing to verify."""
    reader = tmp_path / "reader"
    reader.write_text("", encoding="utf-8")
    env = {hold_lift.READER_ENV: str(reader)}
    assert not hold_lift.lifted({"symbol": "W1510"}, _Reader(_OK, _ROW), env)


def test_held_symbols_leaves_out_a_row_whose_warrant_lifts_it(tmp_path: Path) -> None:
    """Standing 5 reads this set, so the writer may then change the lifted row."""
    rows = [
        {"symbol": "W1", "status": "blocked", "blocked_kind": "human"},
        {"symbol": "W2", "status": "blocked", "blocked_kind": "human"},
    ]
    state = tmp_path / "q.json"
    doc: dict[str, object] = {"waypoints": rows}
    state.write_text(json.dumps(doc), encoding="utf-8")
    assert standing_facts.held_symbols(state, lambda row: row.get("symbol") == "W2") == ["W1"]
