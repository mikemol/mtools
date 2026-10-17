# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
# The slice of opentelemetry-proto's metrics export request this dist builds and reads back.

from collections.abc import Iterable

from opentelemetry.proto.metrics.v1.metrics_pb2 import ResourceMetrics

class ExportMetricsServiceRequest:
    def __init__(self, *, resource_metrics: Iterable[ResourceMetrics] = ...) -> None: ...
    def SerializeToString(self) -> bytes: ...
    @staticmethod
    def FromString(data: bytes) -> ExportMetricsServiceRequest: ...
