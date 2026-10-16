# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for stage 8: only the operator's own utterances become PROV-O entities (W1386).

⚑ THE CONTROLS ARE THE RECORDS THAT MUST NOT BE HARVESTED: a peer session's message, the harness's
own injection, an assistant turn and tool output wearing the user role. The one genuine human line
proves the harvest can say yes; a human line with no uuid is counted as uncitable, never dropped
silently. Every fixture is SYNTHETIC.
"""

from __future__ import annotations

import io
import json
from typing import TYPE_CHECKING, cast

from mikemol.transcriptstruct.cli import main
from mikemol.transcriptstruct.harvest import OPERATOR_AGENT, harvest
from mikemol.transcriptstruct.records import parse_lines

if TYPE_CHECKING:
    from pathlib import Path

STAMP = "2026-10-16T14:02:11.000Z"


def _user(content: str, uuid: str | None = "u1") -> str:
    message: dict[str, object] = {"role": "user", "content": content}
    envelope: dict[str, object] = {
        "type": "user",
        "message": message,
        "timestamp": STAMP,
        "sessionId": "s-1",
    }
    if uuid is not None:
        envelope["uuid"] = uuid
    return json.dumps(envelope)


def _assistant(text: str) -> str:
    message: dict[str, object] = {"role": "assistant", "content": [{"type": "text", "text": text}]}
    envelope: dict[str, object] = {"type": "assistant", "message": message, "uuid": "a1"}
    return json.dumps(envelope)


LINES = [
    _user("please drain the tier", "h1"),
    _user('<cross-session-message from="x">a peer wrote this</cross-session-message>', "p1"),
    _user("<system-reminder>harness plumbing</system-reminder>", "r1"),
    _assistant("on it"),
    _user("a ruling with no uuid", None),
]


def test_only_the_operators_own_utterance_becomes_an_entity(tmp_path: Path) -> None:
    """The genuine line is harvested with its PROV-O parts; peer, harness and assistant are not."""
    found = harvest(parse_lines(LINES), tmp_path / "t.jsonl")
    assert len(found.entities) == 1
    entity = found.entities[0]
    assert str(entity["@id"]).endswith("/t.jsonl#h1")
    assert entity["mtools:needle"] == "please drain the tier"
    assert entity["mtools:line"] == 1
    assert entity["mtools:session"] == "s-1"
    agent = cast("dict[str, object]", entity["prov:wasAttributedTo"])
    assert agent["@id"] == OPERATOR_AGENT
    stamp = cast("dict[str, object]", entity["prov:generatedAtTime"])
    assert (stamp["@value"], stamp["@type"]) == (STAMP, "xsd:dateTime")


def test_a_human_utterance_with_no_uuid_is_counted_not_silently_dropped(tmp_path: Path) -> None:
    """The line cannot be cited, so it is no entity, but the count says it existed."""
    found = harvest(parse_lines(LINES), tmp_path / "t.jsonl")
    assert found.uncitable == 1


def test_the_cli_prints_json_lines_then_the_denominator(tmp_path: Path) -> None:
    """One JSON line per entity, then a `#` line carrying the counts."""
    path = tmp_path / "t.jsonl"
    path.write_text("\n".join(LINES) + "\n", encoding="utf-8")
    out = io.StringIO()
    assert main([str(path), "--harvest"], out) == 0
    lines = out.getvalue().splitlines()
    first = cast("dict[str, object]", json.loads(lines[0]))
    assert first["mtools:needle"] == "please drain the tier"
    assert lines[-1] == "# 1 entity(ies), 1 human utterance(s) uncitable"
