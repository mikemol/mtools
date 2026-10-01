# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The record layer: every response in exactly one record, the unreadable ones with a reason."""

from __future__ import annotations

import copy

import pytest

from mikemol.gmailstruct.records import Message, Unreadable, message

# ⚑ SYNTHETIC: the shape of a `users.messages.get?format=metadata` response, nothing from a real
# mailbox (@example.invalid).
_ID = "18f0000000000001"
_WELL_FORMED: dict[str, object] = {
    "id": _ID,
    "threadId": "18f0000000000000",
    "labelIds": ["INBOX", "UNREAD"],
    "snippet": "Lunch on Thursday?",
    "internalDate": "1727780400000",
    "payload": {
        "headers": [
            {"name": "From", "value": "Ada <ada@example.invalid>"},
            {"name": "To", "value": "bob@example.invalid"},
            {"name": "Received", "value": "from a.example.invalid"},
            {"name": "Subject", "value": "Lunch"},
            {"name": "Received", "value": "from b.example.invalid"},
        ],
    },
}
_NOT_AN_OBJECT = Unreadable(id=None, reason="response is not a JSON object")


def _with(**changes: object) -> dict[str, object]:
    out = copy.deepcopy(_WELL_FORMED)
    out.update(changes)
    return out


def _without(*keys: str) -> dict[str, object]:
    return {k: v for k, v in copy.deepcopy(_WELL_FORMED).items() if k not in keys}


def test_well_formed_response_reads_in_full() -> None:
    """The positive control: no damage reported where there is none, and no field lost."""
    assert message(_WELL_FORMED) == Message(
        id=_ID,
        thread_id="18f0000000000000",
        labels=("INBOX", "UNREAD"),
        snippet="Lunch on Thursday?",
        internal_date_ms=1727780400000,
        headers=(
            ("From", "Ada <ada@example.invalid>"),
            ("To", "bob@example.invalid"),
            ("Received", "from a.example.invalid"),
            ("Subject", "Lunch"),
            ("Received", "from b.example.invalid"),
        ),
    )


def test_headers_keep_their_order_and_repeats() -> None:
    """Headers are ordered pairs: a mapping would keep one Received header and lose the other."""
    rec = message(_WELL_FORMED)
    assert isinstance(rec, Message)
    assert [value for name, value in rec.headers if name == "Received"] == [
        "from a.example.invalid",
        "from b.example.invalid",
    ]


def test_absent_labels_and_snippet_read_as_empty() -> None:
    """The API omits labelIds and snippet when there are none; that absence is what it holds."""
    rec = message(_without("labelIds", "snippet"))
    assert isinstance(rec, Message)
    assert rec.labels == ()
    assert not rec.snippet


@pytest.mark.parametrize("key", ["threadId", "internalDate", "payload"])
def test_missing_required_field_is_unreadable_with_its_id(key: str) -> None:
    """An absent required field makes the message Unreadable, never a skip, and keeps its id."""
    rec = message(_without(key))
    assert isinstance(rec, Unreadable)
    assert rec.id == _ID
    assert key in rec.reason


@pytest.mark.parametrize(
    ("changes", "named"),
    [
        ({"internalDate": 1727780400000}, "internalDate"),
        ({"internalDate": "-5"}, "internalDate"),
        ({"labelIds": "INBOX"}, "labelIds"),
        ({"labelIds": ["INBOX", 7]}, "labelIds"),
        ({"snippet": None}, "snippet"),
        ({"payload": {"headers": [{"name": "From"}]}}, "payload.headers[0]"),
        ({"payload": {"headers": ["From: x"]}}, "payload.headers[0]"),
    ],
)
def test_wrongly_typed_field_is_unreadable_never_coerced(
    changes: dict[str, object], named: str
) -> None:
    """A present field of the wrong type is Unreadable naming it; nothing is converted to fit."""
    rec = message(_with(**changes))
    assert isinstance(rec, Unreadable)
    assert named in rec.reason


@pytest.mark.parametrize("value", [None, [], "id", 3])
def test_non_object_response_is_unreadable_without_id(value: object) -> None:
    """A response that is not a JSON object still yields one record, with no id to carry."""
    assert message(value) == _NOT_AN_OBJECT


def test_every_response_yields_exactly_one_record() -> None:
    """A count over the output is a count over the input, readable and unreadable alike."""
    batch: list[object] = [_WELL_FORMED, _without("threadId"), None, _with(snippet=None)]
    kinds = [type(message(value)) for value in batch]
    assert kinds == [Message, Unreadable, Unreadable, Unreadable]
