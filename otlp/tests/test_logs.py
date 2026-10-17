# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the log builder: a record round-trips the wire with its severity (W1411).

⚑ THE CONTROLS ARE THE FIELDS A RECEIVER FILTERS ON: severity arrives as both the number and the
text, the time is the record's own, attributes keep their kinds, the resource attributes are the
metric builder's four, and an unknown severity is refused rather than sent as INFO. Each check reads
the request back through the same published wheel after serialising it.
"""

from __future__ import annotations

from typing import cast

import pytest
from google.protobuf.json_format import MessageToDict
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import ExportLogsServiceRequest

from mikemol.otlp import logs, metrics

RESOURCE = metrics.Resource("mikemol-vlog", "mtools", "host-1", "0.1.0")
NOW = 1_760_000_000_000_000_000
Doc = dict[str, object]


def _record(entry: logs.Entry) -> Doc:
    wire = ExportLogsServiceRequest.FromString(logs.request(RESOURCE, entry).SerializeToString())
    doc = MessageToDict(wire)
    resource = cast("list[Doc]", doc["resourceLogs"])[0]
    scope = cast("list[Doc]", resource["scopeLogs"])[0]
    return cast("list[Doc]", scope["logRecords"])[0]


def test_a_record_carries_its_body_time_severity_number_and_text() -> None:
    """The parsed record has the body, the nanosecond time and both halves of the severity."""
    record = _record(logs.Entry("commit refused", NOW, "ERROR"))
    assert cast("Doc", record["body"]) == {"stringValue": "commit refused"}
    assert record["timeUnixNano"] == str(NOW)
    assert (record["severityNumber"], record["severityText"]) == ("SEVERITY_NUMBER_ERROR", "ERROR")


def test_attributes_keep_their_kinds_and_the_default_severity_is_info() -> None:
    """A label is a string, an int or a bool value, in key order; no severity means INFO."""
    entry = logs.Entry("landed", NOW, labels={"sha": "abc", "ok": True, "n": 3})
    record = _record(entry)
    pairs = [(a["key"], a["value"]) for a in cast("list[Doc]", record["attributes"])]
    assert pairs == [
        ("n", {"intValue": "3"}),
        ("ok", {"boolValue": True}),
        ("sha", {"stringValue": "abc"}),
    ]
    assert record["severityText"] == "INFO"


def test_the_four_resource_attributes_ride_with_the_record() -> None:
    """The same resource the metric builder sends, so a log and a metric attribute alike."""
    wire = ExportLogsServiceRequest.FromString(
        logs.request(RESOURCE, logs.Entry("x", NOW)).SerializeToString()
    )
    resource = cast("Doc", cast("list[Doc]", MessageToDict(wire)["resourceLogs"])[0]["resource"])
    keys = [a["key"] for a in cast("list[Doc]", resource["attributes"])]
    assert keys == ["host.name", "service.name", "service.namespace", "service.version"]


def test_an_unknown_severity_is_refused_not_sent_as_info() -> None:
    """The control: DEBUG is not built, so it raises and names the allowed three."""
    with pytest.raises(ValueError, match="unknown severity"):
        logs.request(RESOURCE, logs.Entry("x", NOW, "DEBUG"))
