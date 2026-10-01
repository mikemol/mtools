# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Listing pages: every listed id in exactly one record, and a truncated run said so."""

from __future__ import annotations

from mikemol.gmailstruct.records import Listed, Unreadable, pages

# ⚑ SYNTHETIC: the shape of `users.messages.list` responses, no real mailbox.
_FIRST: dict[str, object] = {
    "messages": [
        {"id": "m1", "threadId": "t1"},
        {"id": "m2", "threadId": "t1"},
    ],
    "nextPageToken": "p2",
    "resultSizeEstimate": 201,
}
_LAST: dict[str, object] = {
    "messages": [{"id": "m3", "threadId": "t2"}],
    "resultSizeEstimate": 201,
}


def test_two_pages_list_each_entry_once_in_order() -> None:
    """The positive control: two whole pages give one Listed per entry, in fetch order."""
    assert pages([_FIRST, _LAST]) == [
        Listed("m1", "t1", 0, 0),
        Listed("m2", "t1", 0, 1),
        Listed("m3", "t2", 1, 0),
    ]


def test_estimate_is_never_the_count() -> None:
    """The estimate says 201; three entries were listed, and three records come out."""
    records = pages([_FIRST, _LAST])
    assert all(isinstance(rec, Listed) for rec in records)
    assert _LAST["resultSizeEstimate"] != len(records)


def test_empty_listing_has_no_messages_key_and_no_records() -> None:
    """The API omits messages on an empty page; that reads as no entries, not as damage."""
    assert pages([{"resultSizeEstimate": 0}]) == []


def test_truncated_run_is_a_record() -> None:
    """A last page still carrying nextPageToken means the run stopped early; a record says so."""
    records = pages([_FIRST])
    assert records[0] == Unreadable(id=None, reason="page 0 has nextPageToken: listing truncated")
    assert [rec.id for rec in records[1:]] == ["m1", "m2"]


def test_missing_middle_token_is_a_record() -> None:
    """A page before the last without nextPageToken means pages were joined that do not chain."""
    records = pages([_LAST, _LAST])
    assert Unreadable(id=None, reason="page 0 lacks nextPageToken: listing truncated") in records


def test_bad_entry_is_unreadable_and_keeps_its_place() -> None:
    """An entry out of shape is one Unreadable naming its page and position; its siblings stay."""
    page: dict[str, object] = {"messages": [{"id": "m1"}, "m2", {"id": "m3", "threadId": "t"}]}
    assert pages([page]) == [
        Unreadable(id="m1", reason="page 0 messages[0]: threadId is missing or not a string"),
        Unreadable(id=None, reason="page 0 messages[1] is not an object"),
        Listed("m3", "t", 0, 2),
    ]


def test_unreadable_page_is_one_record() -> None:
    """A page that is not an object, or whose messages is no list, is one record, never a skip."""
    assert pages([None, {"messages": "m1"}]) == [
        Unreadable(id=None, reason="page 0 is not a JSON object"),
        Unreadable(id=None, reason="page 1 messages is missing or not a list"),
    ]
