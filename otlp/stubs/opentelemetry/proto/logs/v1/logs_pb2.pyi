# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
# The slice of opentelemetry-proto's log messages this dist builds.

from collections.abc import Iterable

from opentelemetry.proto.common.v1.common_pb2 import AnyValue, InstrumentationScope, KeyValue
from opentelemetry.proto.resource.v1.resource_pb2 import Resource

SEVERITY_NUMBER_INFO: int
SEVERITY_NUMBER_WARN: int
SEVERITY_NUMBER_ERROR: int

class LogRecord:
    def __init__(
        self,
        *,
        time_unix_nano: int = ...,
        severity_number: int = ...,
        severity_text: str = ...,
        body: AnyValue = ...,
        attributes: Iterable[KeyValue] = ...,
    ) -> None: ...

class ScopeLogs:
    def __init__(
        self, *, scope: InstrumentationScope = ..., log_records: Iterable[LogRecord] = ...
    ) -> None: ...

class ResourceLogs:
    def __init__(
        self, *, resource: Resource = ..., scope_logs: Iterable[ScopeLogs] = ...
    ) -> None: ...
