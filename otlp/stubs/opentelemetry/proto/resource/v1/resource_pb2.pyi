# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
# The slice of opentelemetry-proto's resource message this dist builds.

from collections.abc import Iterable

from opentelemetry.proto.common.v1.common_pb2 import KeyValue

class Resource:
    def __init__(self, *, attributes: Iterable[KeyValue] = ...) -> None: ...
