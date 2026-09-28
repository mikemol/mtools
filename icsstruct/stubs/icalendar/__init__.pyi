# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# ⚑⚑ THE SURFACE icsstruct CALLS, AND NOTHING ELSE (W258). icalendar 7.3 ships py.typed, but its
# own annotations carry `Any` through `type[Calendar]` and `decoded`, which the strict block's
# `disallow_any_expr` refuses at every call site. So this stub replaces them: it narrows every
# `Any` to `object`, and the expansion layer narrows `object` with isinstance, where a wrong guess
# is a runtime refusal rather than a silent pass.
#
# ⚑ `tests/test_stub_authority.py` runs stubtest over this file. A stub is an unchecked claim
# until something checks it.

from collections.abc import Callable
from pathlib import Path
from typing import Literal, overload

class Component:
    name: str | None
    def walk(
        self,
        name: str | None = None,
        select: Callable[[Component], bool] = ...,
    ) -> list[Component]: ...
    def decoded(self, name: str, default: object = ...) -> object: ...
    def get(self, key: str, default: object = None) -> object: ...

# ⚑ OVERLOADED ON `multiple`, as icalendar's own annotations are: with a union return, every
# single-calendar caller would carry an isinstance the library already rules out (measured: with
# the stub removed, mypy reports that isinstance as `redundant-expr`).
class Calendar(Component):
    @overload
    @classmethod
    def from_ical(cls, st: str | bytes | Path, multiple: Literal[False] = False) -> Calendar: ...
    @overload
    @classmethod
    def from_ical(cls, st: str | bytes | Path, multiple: Literal[True]) -> list[Calendar]: ...
