# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for stage 7: a warrant's cited record is read, and a forged citation is refused.

⚑ THE CONTROLS ARE THE FORGERIES: a peer session's message claimed as the operator, a uuid that
names nothing, a right uuid on the wrong line, and a record with no timestamp. Each is refused
with its reason; the one genuine human record is the control that proves the check can say yes.
Every fixture is SYNTHETIC.
"""

from __future__ import annotations

import io
import json
from typing import TYPE_CHECKING, cast

from mikemol.transcriptstruct.cli import main
from mikemol.transcriptstruct.records import parse_lines
from mikemol.transcriptstruct.warrant import verify

if TYPE_CHECKING:
    from pathlib import Path

HUMAN = "u-human"
PEER = "u-peer"
BARE = "u-bare"
STAMP = "2026-10-16T18:00:00.000Z"
_REFUSED = 1


def _line(uuid: str, content: str, stamp: str | None = STAMP) -> str:
    message: dict[str, object] = {"role": "user", "content": content}
    envelope: dict[str, object] = {"type": "user", "uuid": uuid, "message": message}
    if stamp is not None:
        envelope["timestamp"] = stamp
    return json.dumps(envelope)


LINES = [
    _line(HUMAN, "the operator typed this ruling"),
    _line(PEER, '<cross-session-message from="x">a peer wrote this</cross-session-message>'),
    _line(BARE, "no stamp on this one", stamp=None),
]


def test_a_genuine_human_record_holds_and_carries_its_line_and_stamp() -> None:
    """The control: the operator's own record is found, stamped, and kind human."""
    got = verify(parse_lines(LINES), HUMAN, claim="operator", line=1)
    assert got.ok
    assert (got.line, got.timestamp, got.kind) == (1, STAMP, "human")


def test_a_peer_message_claimed_as_the_operator_is_refused() -> None:
    """The forgery: it wears the user role, but its provenance is peer."""
    got = verify(parse_lines(LINES), PEER, claim="operator")
    assert not got.ok
    assert got.kind == "peer"
    assert "not human" in got.reason


def test_the_same_peer_record_is_fine_when_no_operator_is_claimed() -> None:
    """The refusal is about the claim, not the record: an unclaimed peer citation holds."""
    assert verify(parse_lines(LINES), PEER).ok


def test_an_unknown_uuid_is_refused_by_name() -> None:
    """A uuid that names no record says so."""
    got = verify(parse_lines(LINES), "u-missing", claim="operator")
    assert not got.ok
    assert "u-missing" in got.reason


def test_a_right_uuid_on_the_wrong_line_is_refused() -> None:
    """The cited line must be the record's line."""
    got = verify(parse_lines(LINES), HUMAN, line=3)
    assert not got.ok
    assert "line 1, not line 3" in got.reason


def test_a_record_without_a_timestamp_is_refused() -> None:
    """The shape needs generatedAtTime, so a record without one cannot be cited."""
    got = verify(parse_lines(LINES), BARE)
    assert not got.ok
    assert "no timestamp" in got.reason


def test_the_cli_verifies_a_citation_and_exits_one_on_a_forgery(tmp_path: Path) -> None:
    """Exit 0 and ok:true for the human record; exit 1 and the reason for the peer forgery."""
    path = tmp_path / "t.jsonl"
    path.write_text("\n".join(LINES) + "\n", encoding="utf-8")
    good, bad = io.StringIO(), io.StringIO()
    assert main([str(path), "--verify", HUMAN, "--claim", "operator", "--line", "1"], good) == 0
    assert cast("dict[str, object]", json.loads(good.getvalue()))["ok"] is True
    assert main([str(path), "--verify", PEER, "--claim", "operator"], bad) == _REFUSED
    forged = cast("dict[str, object]", json.loads(bad.getvalue()))
    assert forged["ok"] is False
    assert "not human" in str(forged["reason"])
