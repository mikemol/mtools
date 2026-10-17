# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
# The slice of opentelemetry-proto's common messages this dist builds. The bazel mypy runner cannot
# see the wheel, so the surface this dist uses is declared here, as mdstruct's stubs do.

class AnyValue:
    string_value: str
    bool_value: bool
    int_value: int
    double_value: float
    def __init__(
        self,
        *,
        string_value: str = ...,
        bool_value: bool = ...,
        int_value: int = ...,
        double_value: float = ...,
    ) -> None: ...

class KeyValue:
    key: str
    value: AnyValue
    def __init__(self, *, key: str = ..., value: AnyValue = ...) -> None: ...

class InstrumentationScope:
    name: str
    def __init__(self, *, name: str = ..., version: str = ...) -> None: ...
