# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W1514: collect the parameter and return types a run observes, with `sys.monitoring`.

    with Observer(root) as seen:
        run_the_code()
    seen.observed()        # {"<file>::<qualname>": Signature(params={...}, returns={...})}

⚑ NEITHER MONKEYTYPE NOR AN OLDER INTERPRETER (el-openglo via github-8f, 2026-10-18): monkeytype
crashes on 3.14's `Union`, and pinning an older Python to run it is the wrong fix. PEP 669's
`sys.monitoring` reports a function's start and return without a trace function, so the tracer is
this module and carries no store, no database and no pinned interpreter.

⚑ WHAT IT RECORDS IS WHAT WAS PASSED, NOT WHAT SHOULD BE DECLARED: a parameter's type is the set of
classes it was observed with, as `module.Class` (bare for builtins), with the element types of a
container it can see cheaply (the first few items of a list, set, tuple or dict). Those are the
broad types callers pass (a bare `ndarray`, a `dict[str, int | str]`); narrowing them to what the
body does with the value is W1515, and judging the result on the house mypy count is W1516.

⚑ ONLY CODE UNDER THE ROOT IS WATCHED: a function whose file is outside it is switched off after
its first event (`DISABLE`), so a run through the standard library costs one event per function
and not one per call.

⚑ A TOOL ID IS CLAIMED, NEVER ASSUMED: coverage and debuggers hold ids too, so the observer takes
the first free one of three and says so when none is.
"""

import builtins
import inspect
import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from itertools import islice
from pathlib import Path
from types import CodeType, FrameType, GeneratorType, TracebackType
from typing import Self, cast

NAME = "mikemol-pycodemod-observed"
_TOOL_IDS = (3, 4, 2)
_SAMPLE = 8
_VARARGS = 0x04
_VARKEYWORDS = 0x08
_SKIPPED = frozenset({"self", "cls"})
_BUILTINS = frozenset(dir(builtins))
_ELSEWHERE: dict[type, str] = {
    TracebackType: "types.TracebackType",
    FrameType: "types.FrameType",
    GeneratorType: "types.GeneratorType",
}


def _builtin_spelling(kind: type) -> str:
    """Spell a type whose module reads `builtins` the way a module can name it.

    ⚑ `type(tb).__module__` IS `builtins` AND ITS QUALNAME IS `traceback`, which is no name a module
    can write: el-openglo's first real annotate run printed `tb: traceback` with no import (mypy:
    Name "traceback" is not defined). A name the builtins namespace holds is kept; the few types
    the interpreter reports under `builtins` without holding them (traceback, frame, generator) are
    spelled through the `types` module that does, which is a dotted name, so the annotator sends it
    to the worklist as needing an import and never writes it bare.

    Returns:
        the bare name when `builtins` holds it, `types.<Name>` for the known few, and
        `builtins.<qualname>` for any other, which the annotator will not write either.

    """
    if kind.__qualname__ in _BUILTINS:
        return kind.__qualname__
    return _ELSEWHERE.get(kind, f"builtins.{kind.__qualname__}")


@dataclass
class Signature:
    """What one function was observed to take and return."""

    params: dict[str, set[str]] = field(default_factory=dict)
    returns: set[str] = field(default_factory=set)


def _name(value: object) -> str:
    kind = type(value)
    if kind.__module__ == "builtins":
        return "None" if value is None else _builtin_spelling(kind)
    return f"{kind.__module__}.{kind.__qualname__}"


def _joined(values: Iterable[object], depth: int) -> str:
    return " | ".join(sorted({type_of(v, depth) for v in islice(values, _SAMPLE)}))


def type_of(value: object, depth: int = 1) -> str:
    """Spell the type of a value, with the element types of a container it can see cheaply.

    Returns:
        the class name, `list[int]`, `tuple[int, str]` or `dict[str, int]`; a deeper container is
        named without its elements, and an empty one without brackets.

    """
    name = _name(value)
    if not depth:
        return name
    if isinstance(value, (list, set, frozenset)):
        items = cast("Iterable[object]", value)
        inner = _joined(items, depth - 1)
        return f"{name}[{inner}]" if inner else name
    if isinstance(value, tuple):
        parts = [type_of(v, depth - 1) for v in islice(cast("Iterable[object]", value), _SAMPLE)]
        return f"tuple[{', '.join(parts)}]" if parts else name
    if isinstance(value, dict):
        mapping = cast("dict[object, object]", value)
        keys, vals = _joined(mapping.keys(), depth - 1), _joined(mapping.values(), depth - 1)
        return f"{name}[{keys}, {vals}]" if keys else name
    return name


def _parameters(code: CodeType) -> list[str]:
    count = code.co_argcount + code.co_kwonlyargcount
    count += bool(code.co_flags & _VARARGS) + bool(code.co_flags & _VARKEYWORDS)
    return list(code.co_varnames[:count])


class NoToolIdError(RuntimeError):
    """Every `sys.monitoring` tool id the observer may use is held by another tool."""


class Observer:
    """Watch the functions of one directory while a block runs."""

    def __init__(self, root: Path) -> None:
        """Name the directory whose code is watched."""
        self.root = str(root.resolve())
        self.seen: dict[str, Signature] = {}
        self._tool = -1

    def __enter__(self) -> Self:
        """Claim a tool id and start both events.

        Returns:
            the observer.

        Raises:
            NoToolIdError: when no id is free.

        """
        monitoring = sys.monitoring
        for tool in _TOOL_IDS:
            if monitoring.get_tool(tool) is None:
                monitoring.use_tool_id(tool, NAME)
                self._tool = tool
                break
        else:
            msg = f"no free sys.monitoring tool id among {_TOOL_IDS}"
            raise NoToolIdError(msg)
        events = monitoring.events
        monitoring.register_callback(self._tool, events.PY_START, self._start)
        monitoring.register_callback(self._tool, events.PY_RETURN, self._return)
        monitoring.set_events(self._tool, events.PY_START | events.PY_RETURN)
        return self

    def __exit__(
        self,
        kind: type[BaseException] | None,
        value: BaseException | None,
        trace: TracebackType | None,
    ) -> None:
        """Stop both events and free the id, whether or not the block raised."""
        monitoring = sys.monitoring
        events = monitoring.events
        monitoring.set_events(self._tool, 0)
        monitoring.register_callback(self._tool, events.PY_START, None)
        monitoring.register_callback(self._tool, events.PY_RETURN, None)
        monitoring.free_tool_id(self._tool)
        self._tool = -1

    def _watched(self, code: CodeType) -> bool:
        return code.co_filename.startswith(self.root)

    def _entry(self, code: CodeType) -> Signature:
        return self.seen.setdefault(f"{code.co_filename}::{code.co_qualname}", Signature())

    def _start(self, code: CodeType, _offset: int) -> object:
        if not self._watched(code):
            return sys.monitoring.DISABLE
        frame = inspect.currentframe()
        caller = None if frame is None else frame.f_back
        if caller is None:
            return None
        values = cast("dict[str, object]", caller.f_locals)
        entry = self._entry(code)
        for place, name in enumerate(_parameters(code)):
            if (place == 0 and name in _SKIPPED) or name not in values:
                continue
            entry.params.setdefault(name, set()).add(type_of(values[name]))
        return None

    def _return(self, code: CodeType, _offset: int, value: object) -> object:
        if not self._watched(code):
            return sys.monitoring.DISABLE
        self._entry(code).returns.add(type_of(value))
        return None

    def observed(self) -> dict[str, Signature]:
        """Give what the block was seen to take and return.

        Returns:
            the signatures by `<file>::<qualname>`.

        """
        return self.seen


def observe(root: Path, call: Callable[[], object]) -> dict[str, Signature]:
    """Run `call` under an observer on `root`.

    Returns:
        what it was seen to take and return.

    """
    with Observer(root) as seen:
        call()
    return seen.observed()
