# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
# The slice of opentelemetry-proto's logs export request this dist builds and reads back.

from collections.abc import Iterable

from opentelemetry.proto.logs.v1.logs_pb2 import ResourceLogs

class ExportLogsServiceRequest:
    def __init__(self, *, resource_logs: Iterable[ResourceLogs] = ...) -> None: ...
    def SerializeToString(self) -> bytes: ...
    @staticmethod
    def FromString(data: bytes) -> ExportLogsServiceRequest: ...
