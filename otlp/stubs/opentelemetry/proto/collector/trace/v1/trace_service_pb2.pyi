# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
# The slice of opentelemetry-proto's trace export request this dist builds and reads back.

from collections.abc import Iterable

from opentelemetry.proto.trace.v1.trace_pb2 import ResourceSpans

class ExportTraceServiceRequest:
    def __init__(self, *, resource_spans: Iterable[ResourceSpans] = ...) -> None: ...
    def SerializeToString(self) -> bytes: ...
    @staticmethod
    def FromString(data: bytes) -> ExportTraceServiceRequest: ...
