# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""MIME parts: every node of a format=full tree in exactly one record, bodies decoded or refused."""

from __future__ import annotations

from mikemol.gmailstruct.records import Part, Unreadable, parts

_ID = "18f0000000000001"


def _node(part_id: str, mime: str, body: dict[str, object], **more: object) -> dict[str, object]:
    return {"partId": part_id, "mimeType": mime, "filename": "", "body": body, **more}


# ⚑ SYNTHETIC: a multipart/mixed message with an alternative pair and one attachment.
_TREE = _node(
    "",
    "multipart/mixed",
    {"size": 0},
    parts=[
        _node(
            "0",
            "multipart/alternative",
            {"size": 0},
            parts=[
                _node("0.0", "text/plain", {"size": 8, "data": "SGksIEFkYS4"}),
                _node("0.1", "text/html", {"size": 2, "data": "-_8="}),
            ],
        ),
        {
            "partId": "1",
            "mimeType": "application/pdf",
            "filename": "menu.pdf",
            "body": {"size": 9000, "attachmentId": "att-1"},
        },
    ],
)


def test_every_node_is_one_record_in_tree_order() -> None:
    """The positive control: five nodes, five Parts, depth first, containers included."""
    assert parts({"id": _ID, "payload": _TREE}) == [
        Part((), "", "multipart/mixed", "", None, None),
        Part((0,), "0", "multipart/alternative", "", None, None),
        Part((0, 0), "0.0", "text/plain", "", b"Hi, Ada.", None),
        Part((0, 1), "0.1", "text/html", "", b"\xfb\xff", None),
        Part((1,), "1", "application/pdf", "menu.pdf", None, "att-1"),
    ]


def test_bad_base64url_is_unreadable_naming_the_part() -> None:
    """Body text that does not decode is Unreadable at its path, never passed on as it stands."""
    payload = _node("", "text/plain", {"size": 3, "data": "SGkh!"})
    [rec] = parts({"id": _ID, "payload": payload})
    assert isinstance(rec, Unreadable)
    assert rec.id == _ID
    assert rec.reason.startswith("part root: body.data is not base64url")


def test_bad_part_does_not_hide_its_children() -> None:
    """A node out of shape is one Unreadable, and its children are still walked and counted."""
    payload = {"partId": "", "mimeType": "multipart/mixed", "parts": [_node("0", "text/plain", {})]}
    assert parts({"id": _ID, "payload": payload}) == [
        Unreadable(id=_ID, reason="part root: body is missing or not an object"),
        Part((0,), "0", "text/plain", "", None, None),
    ]


def test_non_object_child_is_unreadable_and_siblings_stay() -> None:
    """A child that is not an object is one record at its path; the next sibling still reads."""
    payload = _node("", "multipart/mixed", {}, parts=["oops", _node("1", "text/plain", {})])
    assert parts({"id": _ID, "payload": payload}) == [
        Part((), "", "multipart/mixed", "", None, None),
        Unreadable(id=_ID, reason="part 0 is not an object"),
        Part((1,), "1", "text/plain", "", None, None),
    ]


def test_response_without_payload_is_one_record() -> None:
    """A response with no payload, or no object at all, is still exactly one record."""
    assert parts({"id": _ID}) == [Unreadable(id=_ID, reason="payload is missing")]
    assert parts(None) == [Unreadable(id=None, reason="response is not a JSON object")]
