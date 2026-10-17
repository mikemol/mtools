# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
# The slice of opentelemetry-proto's trace messages this dist builds.

from collections.abc import Iterable

from opentelemetry.proto.common.v1.common_pb2 import InstrumentationScope, KeyValue
from opentelemetry.proto.resource.v1.resource_pb2 import Resource

class Status:
    STATUS_CODE_UNSET: int
    STATUS_CODE_OK: int
    STATUS_CODE_ERROR: int
    def __init__(self, *, message: str = ..., code: int = ...) -> None: ...

class Span:
    SPAN_KIND_INTERNAL: int
    def __init__(
        self,
        *,
        trace_id: bytes = ...,
        span_id: bytes = ...,
        parent_span_id: bytes = ...,
        name: str = ...,
        kind: int = ...,
        start_time_unix_nano: int = ...,
        end_time_unix_nano: int = ...,
        attributes: Iterable[KeyValue] = ...,
        status: Status = ...,
    ) -> None: ...

class ScopeSpans:
    def __init__(
        self, *, scope: InstrumentationScope = ..., spans: Iterable[Span] = ...
    ) -> None: ...

class ResourceSpans:
    def __init__(
        self, *, resource: Resource = ..., scope_spans: Iterable[ScopeSpans] = ...
    ) -> None: ...
