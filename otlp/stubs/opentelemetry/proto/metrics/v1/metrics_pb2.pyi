# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
# The slice of opentelemetry-proto's metric messages this dist builds.

from collections.abc import Iterable

from opentelemetry.proto.common.v1.common_pb2 import InstrumentationScope, KeyValue
from opentelemetry.proto.resource.v1.resource_pb2 import Resource

AGGREGATION_TEMPORALITY_CUMULATIVE: int

class NumberDataPoint:
    as_int: int
    as_double: float
    def __init__(
        self, *, time_unix_nano: int = ..., attributes: Iterable[KeyValue] = ...
    ) -> None: ...

class Gauge:
    def __init__(self, *, data_points: Iterable[NumberDataPoint] = ...) -> None: ...

class Sum:
    def __init__(
        self,
        *,
        data_points: Iterable[NumberDataPoint] = ...,
        aggregation_temporality: int = ...,
        is_monotonic: bool = ...,
    ) -> None: ...

class Metric:
    def __init__(
        self,
        *,
        name: str = ...,
        description: str = ...,
        unit: str = ...,
        gauge: Gauge = ...,
        sum: Sum = ...,
        metadata: Iterable[KeyValue] = ...,
    ) -> None: ...

class ScopeMetrics:
    def __init__(
        self, *, scope: InstrumentationScope = ..., metrics: Iterable[Metric] = ...
    ) -> None: ...

class ResourceMetrics:
    def __init__(
        self, *, resource: Resource = ..., scope_metrics: Iterable[ScopeMetrics] = ...
    ) -> None: ...
