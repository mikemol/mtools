# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the span builder: a span round-trips the wire with ids, times and status (W1408).

⚑ THE CONTROLS ARE WHAT A RECEIVER SILENTLY MISREADS: a trace id that is not 16 bytes, a span id
that is not 8, an all-zero id, an end before its start and a status nobody defined are each refused
here by name, because the receiver would drop or mangle them without an error. The positive checks
read the request back through the same published wheel after serialising it, so the field numbers
are the wheel's and not this module's claim.
"""

from __future__ import annotations

import base64
from dataclasses import replace
from typing import cast

import pytest
from google.protobuf.json_format import MessageToDict
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest

from mikemol.otlp import metrics, spans

RESOURCE = metrics.Resource("mikemol-commit", "mtools", "host-1", "0.1.0")
START = 1_760_000_000_000_000_000
END = START + 2_500_000_000
TRACE = bytes(range(1, 17))
SPAN = bytes(range(1, 9))
PARENT = bytes(range(9, 17))
BASE = spans.Entry("commit", TRACE, SPAN, spans.Timing(START, END))
Doc = dict[str, object]


def _span(entry: spans.Entry) -> Doc:
    wire = ExportTraceServiceRequest.FromString(spans.request(RESOURCE, entry).SerializeToString())
    doc = MessageToDict(wire)
    resource = cast("list[Doc]", doc["resourceSpans"])[0]
    scope = cast("list[Doc]", resource["scopeSpans"])[0]
    return cast("list[Doc]", scope["spans"])[0]


def test_a_span_carries_its_ids_name_and_times() -> None:
    """The parsed span has the exact id bytes, the name and both nanosecond times."""
    span = _span(BASE)
    assert base64.b64decode(cast("str", span["traceId"])) == TRACE
    assert base64.b64decode(cast("str", span["spanId"])) == SPAN
    assert span["name"] == "commit"
    assert (span["startTimeUnixNano"], span["endTimeUnixNano"]) == (str(START), str(END))


def test_a_child_span_names_its_parent_and_a_root_has_none() -> None:
    """parent_id rides as parentSpanId; with none given the field is absent."""
    child = _span(replace(BASE, parent_id=PARENT))
    assert base64.b64decode(cast("str", child["parentSpanId"])) == PARENT
    assert "parentSpanId" not in _span(BASE)


def test_attributes_keep_their_kinds_and_status_carries_code_and_message() -> None:
    """Labels are typed values; an ERROR status keeps its message."""
    entry = replace(
        BASE, labels={"sha": "abc", "ok": False, "n": 3}, status="ERROR", message="refused"
    )
    span = _span(entry)
    pairs = [(a["key"], a["value"]) for a in cast("list[Doc]", span["attributes"])]
    assert pairs == [
        ("n", {"intValue": "3"}),
        ("ok", {"boolValue": False}),
        ("sha", {"stringValue": "abc"}),
    ]
    assert span["status"] == {"message": "refused", "code": "STATUS_CODE_ERROR"}


def test_the_four_resource_attributes_ride_with_the_span() -> None:
    """The same resource the metric and log builders send."""
    wire = ExportTraceServiceRequest.FromString(spans.request(RESOURCE, BASE).SerializeToString())
    first = cast("list[Doc]", MessageToDict(wire)["resourceSpans"])[0]
    keys = [a["key"] for a in cast("list[Doc]", cast("Doc", first["resource"])["attributes"])]
    assert keys == ["host.name", "service.name", "service.namespace", "service.version"]


@pytest.mark.parametrize(
    ("bad", "field"),
    [
        (replace(BASE, trace_id=TRACE[:8]), "trace_id"),
        (replace(BASE, trace_id=bytes(16)), "trace_id"),
        (replace(BASE, span_id=SPAN + b"x"), "span_id"),
        (replace(BASE, span_id=bytes(8)), "span_id"),
        (replace(BASE, parent_id=b"short"), "parent_id"),
        (replace(BASE, timing=spans.Timing(END, START)), "end_ns"),
        (replace(BASE, status="FINE"), "unknown status"),
    ],
)
def test_a_span_a_receiver_would_misread_is_refused_by_field(bad: spans.Entry, field: str) -> None:
    """The control: each malformed span raises ValueError naming the field it broke."""
    with pytest.raises(ValueError, match=field):
        spans.request(RESOURCE, bad)


def test_fresh_ids_have_the_right_widths_and_are_not_zero() -> None:
    """new_ids gives 16 and 8 bytes, never all zero, and two draws differ."""
    first, second = spans.new_ids(), spans.new_ids()
    assert (len(first[0]), len(first[1])) == (spans.TRACE_ID_BYTES, spans.SPAN_ID_BYTES)
    assert any(first[0])
    assert any(first[1])
    assert first != second
