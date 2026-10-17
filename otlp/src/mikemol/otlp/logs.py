# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Log payloads: one record as an OTLP `ExportLogsServiceRequest` (W1411).

⚑ SAME RESOURCE, SAME WHEEL, AS THE METRIC BUILDER. A log record carries the four resource
attributes luthen's receiver needs (`service.name`, `service.namespace`, `host.name`,
`service.version`, see `metrics.Resource`), its own time in nanoseconds, a severity (number AND
text, because a receiver filters on the number and a reader reads the text) and the record's
attributes. The body is a string; a structured record puts its fields in the attributes, where a
query can reach them.

⚑ AN UNKNOWN SEVERITY IS REFUSED, NOT GUESSED: a record sent as INFO that the caller meant as ERROR
is a failure that reads as a success. Only INFO, WARN and ERROR are built until a caller needs
another.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import ExportLogsServiceRequest
from opentelemetry.proto.common.v1.common_pb2 import AnyValue, InstrumentationScope
from opentelemetry.proto.logs.v1.logs_pb2 import (
    SEVERITY_NUMBER_ERROR,
    SEVERITY_NUMBER_INFO,
    SEVERITY_NUMBER_WARN,
    LogRecord,
    ResourceLogs,
    ScopeLogs,
)

from mikemol.otlp.metrics import SCOPE, Resource, Value, attributes, resource_message

SEVERITIES: Mapping[str, int] = {
    "INFO": SEVERITY_NUMBER_INFO,
    "WARN": SEVERITY_NUMBER_WARN,
    "ERROR": SEVERITY_NUMBER_ERROR,
}


@dataclass(frozen=True, slots=True)
class Entry:
    """One log record: its text, when it happened, how serious it was and its attributes."""

    body: str
    time_ns: int
    severity: str = "INFO"
    labels: Mapping[str, Value] | None = None


def request(resource: Resource, entry: Entry) -> ExportLogsServiceRequest:
    """Build a request carrying one log record.

    Returns:
        the request, ready to serialise.

    Raises:
        ValueError: when the severity is not one of INFO, WARN and ERROR.

    """
    if entry.severity not in SEVERITIES:
        msg = f"unknown severity {entry.severity!r}; one of {sorted(SEVERITIES)}"
        raise ValueError(msg)
    record = LogRecord(
        time_unix_nano=entry.time_ns,
        severity_number=SEVERITIES[entry.severity],
        severity_text=entry.severity,
        body=AnyValue(string_value=entry.body),
        attributes=attributes(entry.labels or {}),
    )
    scope = ScopeLogs(scope=InstrumentationScope(name=SCOPE), log_records=[record])
    return ExportLogsServiceRequest(
        resource_logs=[ResourceLogs(resource=resource_message(resource), scope_logs=[scope])]
    )
