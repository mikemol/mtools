# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`--intents` reads the cards and the landed trailers from text and prints each outcome (W2101).

⚑ THE INPUTS ARE TEXT, so the witnesses are text: a queue document, a log in the shape git prints
under `TZ=UTC`, and a transcript whose assistant records carry the stamp the rows compare by.
"""

import io
import json
from pathlib import Path
from typing import cast

from mikemol.transcriptstruct import intents
from mikemol.transcriptstruct.cli import main
from mikemol.transcriptstruct.intents import Card, Trailer
from mikemol.transcriptstruct.intentsio import cards_of, trailers_of

_US = "\x1f"
_RS = "\x1e"
Doc = dict[str, object]


def _assistant(text: str, uuid: str, at: str) -> str:
    message: Doc = {"role": "assistant", "content": [{"type": "text", "text": text}]}
    envelope: Doc = {"type": "assistant", "uuid": uuid, "timestamp": at, "message": message}
    return json.dumps(envelope)


def _queue(*cards: object) -> str:
    doc: Doc = {"waypoints": list(cards)}
    return json.dumps(doc)


def test_cards_are_read_with_status_and_stamp_and_a_bad_document_reads_as_none() -> None:
    """A card with no last_worked has the empty stamp; text that is not a queue gives nothing."""
    done: Doc = {"symbol": "W7", "status": "done", "last_worked": "2026-10-30T10:00:00Z"}
    ready: Doc = {"symbol": "W8", "status": "ready"}
    nameless: Doc = {"status": "ready"}
    doc = _queue(done, ready, nameless, "not a card")
    assert cards_of(doc) == {
        "W7": Card("done", "2026-10-30T10:00:00Z"),
        "W8": Card("ready", ""),
    }
    assert cards_of("not json") == {}
    assert cards_of('{"waypoints": 3}') == {}
    assert cards_of("[1, 2]") == {}


def test_trailers_are_read_per_record_and_prose_and_torn_records_are_not_trailers() -> None:
    """Only a line that is exactly `Waypoint: W<n>` counts; the stamp is its commit's own."""
    new = f"bbb{_US}2026-10-30T12:00:00Z{_US}subject\n\nWaypoint: W1\nWaypoint: W2\n{_RS}"
    old = f"aaa{_US}2026-10-29T08:00:00Z{_US}says Waypoint: W9 inline\n\nWaypoint: W1\n{_RS}"
    torn = f"ccc{_US}2026-10-28T08:00:00Z{_RS}"
    assert trailers_of(new + old + torn) == [
        Trailer("W1", "2026-10-30T12:00:00Z"),
        Trailer("W2", "2026-10-30T12:00:00Z"),
        Trailer("W1", "2026-10-29T08:00:00Z"),
    ]
    assert trailers_of("") == []


def test_the_command_prints_each_intents_outcome_and_how_many_diverged(tmp_path: Path) -> None:
    """W7 landed after its statement, W8 did not: landed, missed, and one divergence counted."""
    project = tmp_path / "-home-someone-github-mtools"
    project.mkdir()
    transcript = project / "abc.jsonl"
    lines = [
        _assistant("I still need to land W7.", "u1", "2026-10-30T08:00:00.000Z"),
        _assistant("I still need to land W8.", "u2", "2026-10-30T08:05:00.000Z"),
    ]
    transcript.write_text("\n".join(lines) + "\n", encoding="utf-8")
    queue = tmp_path / "queue.json"
    first: Doc = {"symbol": "W7", "status": "ready"}
    second: Doc = {"symbol": "W8", "status": "ready"}
    queue.write_text(_queue(first, second), encoding="utf-8")
    log = tmp_path / "git.log"
    log.write_text(f"aaa{_US}2026-10-30T09:00:00Z{_US}x\n\nWaypoint: W7\n{_RS}", encoding="utf-8")
    out = io.StringIO()
    args = [str(transcript), "--intents", "--queue", str(queue), "--git-log", str(log)]
    assert main([*args, "--bound", "2026-10-30T12:00:00Z"], out) == 0
    *rows, count = out.getvalue().splitlines()
    states = [cast("Doc", json.loads(r))["state"] for r in rows]
    assert states == [intents.LANDED, intents.MISSED]
    assert count == "# 2 intent(s), 1 diverged"
