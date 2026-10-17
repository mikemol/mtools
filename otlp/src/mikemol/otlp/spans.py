# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Trace payloads: one span as an OTLP `ExportTraceServiceRequest` (W1408).

⚑ SAME RESOURCE, SAME WHEEL, AS THE METRIC AND LOG BUILDERS. A span carries a 16-byte trace id, an
8-byte span id, an optional 8-byte parent id, a name, its start and end in nanoseconds, attributes
and a status. Luthen's receiver (VictoriaTraces, OTLP protobuf to `/insert/opentelemetry/v1/traces`)
reads it back through its Jaeger API, which is the check on these field numbers.

⚑ A MALFORMED SPAN IS REFUSED, NOT SENT: an id of the wrong length is dropped or mangled by a
receiver without an error, an all-zero id is invalid, an end before its start is a lie about time,
and an unknown status is a guess. Each is a `ValueError` naming the field.
"""

import secrets
from collections.abc import Mapping
from dataclasses import dataclass

from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
from opentelemetry.proto.common.v1.common_pb2 import InstrumentationScope
from opentelemetry.proto.trace.v1.trace_pb2 import ResourceSpans, ScopeSpans, Span, Status

from mikemol.otlp.metrics import SCOPE, Resource, Value, attributes, resource_message

TRACE_ID_BYTES = 16
SPAN_ID_BYTES = 8
STATUSES: Mapping[str, int] = {
    "UNSET": Status.STATUS_CODE_UNSET,
    "OK": Status.STATUS_CODE_OK,
    "ERROR": Status.STATUS_CODE_ERROR,
}


@dataclass(frozen=True, slots=True)
class Timing:
    """When a span began and ended, in nanoseconds since the epoch."""

    start_ns: int
    end_ns: int


@dataclass(frozen=True, slots=True)
class Entry:
    """One span: its name, ids, timing, attributes and status."""

    name: str
    trace_id: bytes
    span_id: bytes
    timing: Timing
    parent_id: bytes = b""
    labels: Mapping[str, Value] | None = None
    status: str = "UNSET"
    message: str = ""


def new_ids() -> tuple[bytes, bytes]:
    """Draw a fresh trace id and span id, neither all zero.

    Returns:
        (16-byte trace id, 8-byte span id).

    """
    trace, span = bytes(TRACE_ID_BYTES), bytes(SPAN_ID_BYTES)
    while not any(trace):
        trace = secrets.token_bytes(TRACE_ID_BYTES)
    while not any(span):
        span = secrets.token_bytes(SPAN_ID_BYTES)
    return trace, span


def _check(entry: Entry) -> None:
    """Refuse a span a receiver would drop or misread.

    Raises:
        ValueError: naming the first bad field.

    """
    if len(entry.trace_id) != TRACE_ID_BYTES or not any(entry.trace_id):
        msg = f"trace_id must be {TRACE_ID_BYTES} bytes and not all zero"
        raise ValueError(msg)
    if len(entry.span_id) != SPAN_ID_BYTES or not any(entry.span_id):
        msg = f"span_id must be {SPAN_ID_BYTES} bytes and not all zero"
        raise ValueError(msg)
    if entry.parent_id and (len(entry.parent_id) != SPAN_ID_BYTES or not any(entry.parent_id)):
        msg = f"parent_id must be empty or {SPAN_ID_BYTES} bytes and not all zero"
        raise ValueError(msg)
    if entry.timing.end_ns < entry.timing.start_ns:
        msg = "end_ns is before start_ns"
        raise ValueError(msg)
    if entry.status not in STATUSES:
        msg = f"unknown status {entry.status!r}; one of {sorted(STATUSES)}"
        raise ValueError(msg)


def request(resource: Resource, entry: Entry) -> ExportTraceServiceRequest:
    """Build a request carrying one span.

    Returns:
        the request, ready to serialise.

    """
    _check(entry)
    span = Span(
        trace_id=entry.trace_id,
        span_id=entry.span_id,
        parent_span_id=entry.parent_id,
        name=entry.name,
        kind=Span.SPAN_KIND_INTERNAL,
        start_time_unix_nano=entry.timing.start_ns,
        end_time_unix_nano=entry.timing.end_ns,
        attributes=attributes(entry.labels or {}),
        status=Status(message=entry.message, code=STATUSES[entry.status]),
    )
    scope = ScopeSpans(scope=InstrumentationScope(name=SCOPE), spans=[span])
    return ExportTraceServiceRequest(
        resource_spans=[ResourceSpans(resource=resource_message(resource), scope_spans=[scope])]
    )
