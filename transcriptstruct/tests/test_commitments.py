# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The sensor finds an assistant's unpersisted-work statements and not the look-alikes (W1931).

⚑ THE FIXTURES ARE THE MEASURED LINES (the card's evidence, 2026-10-24): three genuine statements
from one session's transcript and the shapes that matched the loose phrase list and were not
commitments (a user-role record quoting a peer, an assistant summary reporting another card's
status). A false positive is a fixture here, never a regex tweak.
"""

from __future__ import annotations

import io
import json
from typing import TYPE_CHECKING, cast

from mikemol.transcriptstruct import commitments
from mikemol.transcriptstruct.cli import main
from mikemol.transcriptstruct.records import parse_lines

if TYPE_CHECKING:
    from pathlib import Path


def _assistant(text: str, uuid: str = "u1") -> str:
    message: dict[str, object] = {
        "role": "assistant",
        "content": [{"type": "text", "text": text}],
    }
    envelope: dict[str, object] = {"type": "assistant", "uuid": uuid, "message": message}
    return json.dumps(envelope)


def _user(text: str) -> str:
    message: dict[str, object] = {"role": "user", "content": text}
    envelope: dict[str, object] = {"type": "user", "uuid": "u0", "message": message}
    return json.dumps(envelope)


def _rows(*lines: str) -> list[commitments.Commitment]:
    return commitments.extract(parse_lines(lines), "sess", "mtools")


def test_the_canonical_form_and_the_measured_variants_are_found_with_what_they_name() -> None:
    """I still need to X, plus the three real statements from the measured day."""
    rows = _rows(
        _assistant("I still need to attach the warrant, W1931. Then rest."),
        _assistant("I haven't yet told estate-dd that the interlock landed."),
        _assistant("The rest of W1918 is still to do: the check rules."),
    )
    assert [(r.family, r.names) for r in rows] == [
        ("canonical", ("W1931",)),
        ("not-yet", ()),
        ("still-to-do", ("W1918",)),
    ]
    first = rows[0]
    assert first.text == "I still need to attach the warrant, W1931."
    assert (first.line, first.uuid, first.session) == (1, "u1", "sess")
    assert first.repo == "mtools"


def test_a_user_record_a_status_report_and_a_quoted_peer_message_are_not_commitments() -> None:
    """The measured false positives: speaker, status of other work, and a quoted message."""
    rows = _rows(
        _user("I have not yet added the note about the retired rule to W1597."),
        _assistant("None of it is built yet, nothing is wired."),
        _assistant("The peer wrote <cross-session-message> I haven't yet added the note."),
    )
    assert rows == []


def test_a_status_report_a_now_not_later_and_a_quoted_phrase_are_not_commitments() -> None:
    """Measured on 108 rows of one session: status sentences, 'now, not later', quoted mentions."""
    rows = _rows(
        _assistant("W1646 is not done."),
        _assistant("The card remains open until the stack lands."),
        _assistant("I'll fix the bundled titles now, not later."),
        _assistant('New rule: say "I still need to X" out loud.'),
        _assistant("Say `next I will X` when you mean it."),
    )
    assert rows == []


def test_a_later_promise_is_still_found() -> None:
    """The lookbehind drops only 'not later'; a plain deferral stays a row."""
    rows = _rows(_assistant("I'll wire the hook later, W1942."))
    assert [(r.family, r.names) for r in rows] == [("next-step", ("W1942",))]


def test_a_file_a_card_and_a_cross_repo_cite_are_all_names() -> None:
    """Names are card cites, repo:W cites and repo-relative files, once each, in order."""
    rows = _rows(_assistant("I still need to edit hooks/src/x.py for nemik:W42 and W7, W7."))
    assert rows[0].names == ("nemik:W42", "W7", "hooks/src/x.py")


def test_the_command_prints_one_json_line_per_statement_then_the_count(tmp_path: Path) -> None:
    """The mode's output: every field of the row, the repo from the project directory, a count."""
    project = tmp_path / "-home-someone-github-mtools"
    project.mkdir()
    log = project / "abc.jsonl"
    log.write_text(_assistant("I still need to wire W7.") + "\n", encoding="utf-8")
    out = io.StringIO()
    assert main([str(log), "--commitments"], out) == 0
    first, count = out.getvalue().splitlines()
    said = cast("dict[str, object]", json.loads(first))
    assert said == {
        "line": 1,
        "uuid": "u1",
        "session": "abc",
        "repo": "mtools",
        "family": "canonical",
        "text": "I still need to wire W7.",
        "names": ["W7"],
    }
    assert count == "# 1 commitment(s)"
