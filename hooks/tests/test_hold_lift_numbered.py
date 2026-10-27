# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A numbered answer to a question that quotes a card's ask lifts its hold (W1525, widened).

⚑ THE CONTROLS (the operator, host line 104311, "This is the way"): the answer must number an item
of the assistant message immediately before it, that item must share distinctive words with the
card's ask (two, not one, and not the generic ones), an item the answer does not number does not
count, a message that is not numbered or no message before it lifts nothing, and a reader that
fails leaves the card held. The record is still verified as origin human, as before.
"""

import json
from collections.abc import Sequence
from pathlib import Path

from mikemol.hooks import hold_lift

_READER = "/r/mikemol-transcriptstruct"
_LINE = 104181
_ASK = (
    "Decide the library-imposed parameter name question at the policy level for every stub alike: "
    "panflute Doc.__init__ format shadows a builtin "
    "operator: decide the panflute Doc.__init__ format shadow, measured: (1) declare the TRUE "
    "signature (metadata, format, api_version), which flags as one NEW key in the lint ratchet; "
    "(2) declare Doc.__init__: object, an opaque boundary; (3) a project-level ruff ignorelist"
)
_QUESTION = (
    "Three decisions remain:\n"
    '1. **Ratchet "falling":** direction only, or a days-to-zero bound, and its starting value.\n'
    "2. **The panflute stub:**\n"
    "   - (a) the true signature plus a counted lint entry;\n"
    "   - (b) an opaque constructor;\n"
    "   - (c) ignore `format`, ideally in stubs only.\n"
    "3. **BuildBuddy enterprise license:** whether to license it, and whether SSO covers it."
)


def _prose(*, asked: str | None = _QUESTION, said: str = "1. a bound.\n2. (a)\n3. no.") -> str:
    rows: list[dict[str, object]] = []
    if asked is not None:
        rows.append({"line": _LINE - 4, "kind": "assistant", "text": asked})
    rows.append({"line": _LINE, "kind": "human", "text": said})
    return "".join(json.dumps(r) + "\n" for r in rows) + "# 2 hit(s)\n"


class _Reader:
    """A stand-in transcript reader answering --verify, --human and --prose from a script."""

    def __init__(self, prose: tuple[int, str]) -> None:
        self.prose = prose
        self.argvs: list[list[str]] = []

    def __call__(self, argv: Sequence[str]) -> tuple[int, str]:
        self.argvs.append(list(argv))
        if "--verify" in argv:
            verdict: dict[str, object] = {"ok": True, "kind": "human"}
            return 0, json.dumps(verdict) + "\n"
        if "--prose" in argv:
            return self.prose
        return 0, "# 0 hit(s)\n"


def _warrant() -> dict[str, object]:
    derived: dict[str, object] = {
        "@id": "urn:claude:transcript:-home-mikemol-github/695f3e0a-d36f#bde02714-1533",
        "mtools:line": _LINE,
    }
    return {"prov:wasDerivedFrom": derived}


def _lifts(prose: tuple[int, str], ask: str = _ASK) -> bool:
    return hold_lift.verifies(_READER, _warrant(), "W1977", _Reader(prose), ask)


def test_the_writers_urn_warrant_cites_the_session_file_under_the_projects_directory() -> None:
    """The form the writer writes now is read; before, no current warrant could lift anything."""
    path, uuid, line = hold_lift.cited(_warrant()) or ("", "", 0)
    expected = Path.home() / ".claude/projects/-home-mikemol-github/695f3e0a-d36f.jsonl"
    assert (path, uuid, line) == (str(expected), "bde02714-1533", _LINE)


def test_an_answer_to_the_numbered_item_that_quotes_the_ask_lifts_the_hold() -> None:
    """The answer `2. (a)` numbers item 2, the panflute stub, which shares several words."""
    assert _lifts((0, _prose()))


def test_an_answer_to_an_item_that_does_not_quote_the_ask_does_not_lift() -> None:
    """Only item 1 (the ratchet question) is answered: one shared word, ratchet, is not enough."""
    assert not _lifts((0, _prose(said="1. a days-to-zero bound.")))


def test_an_unnumbered_answer_or_unnumbered_question_lifts_nothing() -> None:
    """The rule is about numbered answers, so prose neither releases nor is released."""
    assert not _lifts((0, _prose(said="the true signature, please")))
    assert not _lifts((0, _prose(asked="Which stub shape should the panflute signature take?")))


def test_no_assistant_message_before_the_answer_lifts_nothing() -> None:
    """The question is the message immediately before; with none in the window there is none."""
    assert not _lifts((0, _prose(asked=None)))


def test_a_reader_that_fails_leaves_the_card_held() -> None:
    """A hook that cannot read the record must not lift on faith."""
    assert not _lifts((2, ""))


def test_the_question_is_the_assistant_message_nearest_before_the_answer() -> None:
    """An older numbered message that happens to quote the ask is not the question asked."""
    older: dict[str, object] = {
        "line": 1,
        "kind": "assistant",
        "text": "1. panflute signature format opaque",
    }
    newer: dict[str, object] = {
        "line": _LINE - 4,
        "kind": "assistant",
        "text": "1. unrelated deploy question",
    }
    human: dict[str, object] = {"line": _LINE, "kind": "human", "text": "1. yes"}
    text = "".join(json.dumps(r) + "\n" for r in (older, newer, human))
    assert not _lifts((0, text))


def test_without_an_ask_the_prose_is_never_read() -> None:
    """The widening needs the card's ask; a caller that gives none keeps the old rule."""
    reader = _Reader((0, _prose()))
    assert not hold_lift.verifies(_READER, _warrant(), "W1977", reader)
    assert not any("--prose" in argv for argv in reader.argvs)


def test_generic_words_and_a_single_shared_word_are_not_a_quotation() -> None:
    """Two distinctive words are needed, and `decide`, `question` and `options` are not."""
    assert not hold_lift.quotes_ask("decide the question: whether options exist", _ASK)
    assert not hold_lift.quotes_ask("the ratchet question", _ASK)
    assert hold_lift.quotes_ask("the panflute signature", _ASK)
