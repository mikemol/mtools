# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the metric builder: what goes on the wire is what luthen's receiver reads (W1410).

⚑ EVERY CHECK ROUND-TRIPS THROUGH THE WIRE: the request is serialised to protobuf bytes, parsed back
by the same published wheel and read as its canonical JSON mapping, so a field the builder forgot to
set is missing there. (protobuf's int64 fields print as strings in that mapping: a value of 3 reads
"3".) The controls are the distinctions a receiver acts on: an up-down counter is a NON-monotonic
cumulative sum (not a gauge), an int reads as `asInt` and a float as `asDouble`, a bool stays a
bool, and the four resource attributes are present.
"""

from __future__ import annotations

from typing import cast

from google.protobuf.json_format import MessageToDict
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import ExportMetricsServiceRequest

from mikemol.otlp import metrics

RESOURCE = metrics.Resource("mikemol-commit", "mtools", "host-1", "0.1.0")
NOW = 1_760_000_000_000_000_000
HALF = 0.5
Doc = dict[str, object]


def _wire(request: ExportMetricsServiceRequest) -> Doc:
    return MessageToDict(ExportMetricsServiceRequest.FromString(request.SerializeToString()))


def _metric(doc: Doc) -> Doc:
    resource = cast("list[Doc]", doc["resourceMetrics"])[0]
    scope = cast("list[Doc]", resource["scopeMetrics"])[0]
    return cast("list[Doc]", scope["metrics"])[0]


def _point(metric: Doc, kind: str) -> Doc:
    return cast("list[Doc]", cast("Doc", metric[kind])["dataPoints"])[0]


def _pairs(attrs: object) -> list[tuple[str, object]]:
    return [(str(a["key"]), a["value"]) for a in cast("list[Doc]", attrs)]


def test_a_gauge_carries_its_name_unit_time_value_and_labels() -> None:
    """The parsed gauge has the series name, the unit, the point's time, an int value and labels."""
    sample = metrics.Sample("mikemol.commit.depth", 3, NOW, {"repo": "mtools"}, "{commit}")
    metric = _metric(_wire(metrics.gauge(RESOURCE, sample)))
    assert (metric["name"], metric["unit"]) == ("mikemol.commit.depth", "{commit}")
    point = _point(metric, "gauge")
    assert (point["asInt"], point["timeUnixNano"]) == ("3", str(NOW))
    assert _pairs(point["attributes"]) == [("repo", {"stringValue": "mtools"})]


def test_the_four_resource_attributes_are_on_the_wire() -> None:
    """The receiver attributes a series by these; all four arrive, in key order."""
    doc = _wire(metrics.gauge(RESOURCE, metrics.Sample("m", 1, NOW)))
    resource = cast("Doc", cast("list[Doc]", doc["resourceMetrics"])[0]["resource"])
    keys = [key for key, _ in _pairs(resource["attributes"])]
    assert keys == ["host.name", "service.name", "service.namespace", "service.version"]


def test_an_up_down_counter_is_a_non_monotonic_cumulative_sum_not_a_gauge() -> None:
    """The control: a counter that can fall must not be sent as monotonic or as a gauge."""
    sample = metrics.Sample("mikemol.commit.inflight", 2, NOW)
    metric = _metric(_wire(metrics.updown_counter(RESOURCE, sample)))
    assert "sum" in metric
    assert "gauge" not in metric
    total = cast("Doc", metric["sum"])
    assert total["aggregationTemporality"] == "AGGREGATION_TEMPORALITY_CUMULATIVE"
    assert "isMonotonic" not in total


def test_an_int_is_as_int_a_float_is_as_double_and_a_bool_label_stays_a_bool() -> None:
    """Number kinds are not blurred, and True is not sent as 1."""
    whole = _point(_metric(_wire(metrics.gauge(RESOURCE, metrics.Sample("m", 4, NOW)))), "gauge")
    assert "asInt" in whole
    assert "asDouble" not in whole
    sample = metrics.Sample("m", HALF, NOW, {"ok": True})
    part = _point(_metric(_wire(metrics.gauge(RESOURCE, sample))), "gauge")
    assert "asInt" not in part
    assert str(part["asDouble"]) == str(HALF)
    assert _pairs(part["attributes"]) == [("ok", {"boolValue": True})]
