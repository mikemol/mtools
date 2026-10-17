# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Metric payloads: a gauge or an up-down counter as an OTLP `ExportMetricsServiceRequest` (W1410).

⚑⚑ THE ENCODING IS THE PUBLISHED opentelemetry-proto WHEEL'S, NOT OURS (operator, standards-first;
github-8f 2026-10-17). This module only fills the messages. Luthen measured the receiver
(luthen-observability:W1128): victoria answers protobuf and refuses the JSON body with 400, keeps
dotted metric names, and wants the resource attributes `service.name`, `service.namespace` (the
repo), `host.name` and `service.version`; a request that lacks them is a payload the receiver
cannot attribute, so `Resource` makes them required.

⚑ AN UP-DOWN COUNTER IS A NON-MONOTONIC CUMULATIVE SUM (the OTel data model), not a gauge: a
reader that rates it must know it can fall. A gauge is a last value. Each point carries the time
it was read, in nanoseconds since the epoch, because a point without a time is the receiver's
arrival time and says nothing about when the number was true.

⚑ THE PROTO WHEELS ARE IMPORTED HERE AND NOWHERE ELSE AT MODULE LEVEL, and this module is imported
only when a payload is built, never at a hook's start (measured: 24 ms warm, 79 ms cold).
"""

from collections.abc import Mapping
from dataclasses import dataclass

from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import ExportMetricsServiceRequest
from opentelemetry.proto.common.v1.common_pb2 import AnyValue, InstrumentationScope, KeyValue
from opentelemetry.proto.metrics.v1.metrics_pb2 import (
    AGGREGATION_TEMPORALITY_CUMULATIVE,
    Gauge,
    Metric,
    NumberDataPoint,
    ResourceMetrics,
    ScopeMetrics,
    Sum,
)
from opentelemetry.proto.resource.v1.resource_pb2 import Resource as ProtoResource

Value = str | int | float | bool
SCOPE = "mikemol.otlp"


@dataclass(frozen=True, slots=True)
class Resource:
    """Who is speaking: the four attributes the receiver needs to attribute a series."""

    service_name: str
    service_namespace: str
    host_name: str
    service_version: str


def _value(value: Value) -> AnyValue:
    # bool before int: a bool is an int in Python and must not be sent as 1.
    if isinstance(value, bool):
        return AnyValue(bool_value=value)
    if isinstance(value, int):
        return AnyValue(int_value=value)
    if isinstance(value, float):
        return AnyValue(double_value=value)
    return AnyValue(string_value=value)


def attributes(pairs: Mapping[str, Value]) -> list[KeyValue]:
    """Spell a mapping as OTLP key-values, in key order so the payload is deterministic.

    Returns:
        one KeyValue per pair.

    """
    return [KeyValue(key=key, value=_value(pairs[key])) for key in sorted(pairs)]


def resource_message(resource: Resource) -> ProtoResource:
    """Spell the four attributes as the wire's Resource message (shared with the log builder).

    Returns:
        the protobuf Resource.

    """
    return ProtoResource(
        attributes=attributes(
            {
                "service.name": resource.service_name,
                "service.namespace": resource.service_namespace,
                "host.name": resource.host_name,
                "service.version": resource.service_version,
            }
        )
    )


@dataclass(frozen=True, slots=True)
class Sample:
    """One reading: the series name, its value, when it was true, its labels and its unit."""

    name: str
    value: float
    time_ns: int
    labels: Mapping[str, Value] | None = None
    unit: str = ""


def _point(sample: Sample) -> NumberDataPoint:
    point = NumberDataPoint(
        time_unix_nano=sample.time_ns, attributes=attributes(sample.labels or {})
    )
    if isinstance(sample.value, int):
        point.as_int = sample.value
    else:
        point.as_double = sample.value
    return point


def _request(resource: Resource, metric: Metric) -> ExportMetricsServiceRequest:
    scope = ScopeMetrics(scope=InstrumentationScope(name=SCOPE), metrics=[metric])
    return ExportMetricsServiceRequest(
        resource_metrics=[
            ResourceMetrics(resource=resource_message(resource), scope_metrics=[scope])
        ]
    )


def gauge(resource: Resource, sample: Sample) -> ExportMetricsServiceRequest:
    """Build a request carrying one gauge point.

    Returns:
        the request, ready to serialise.

    """
    body = Gauge(data_points=[_point(sample)])
    return _request(resource, Metric(name=sample.name, unit=sample.unit, gauge=body))


def updown_counter(resource: Resource, sample: Sample) -> ExportMetricsServiceRequest:
    """Build a request carrying one up-down counter point (a non-monotonic cumulative sum).

    Returns:
        the request, ready to serialise.

    """
    total = Sum(
        data_points=[_point(sample)],
        aggregation_temporality=AGGREGATION_TEMPORALITY_CUMULATIVE,
        is_monotonic=False,
    )
    return _request(resource, Metric(name=sample.name, unit=sample.unit, sum=total))
