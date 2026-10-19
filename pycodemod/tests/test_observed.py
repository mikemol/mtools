# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The tracer records the types a run passes and returns, only under its root (W1514).

⚑ A REAL MODULE IS RUN UNDER THE REAL `sys.monitoring`: each test writes a small module into a temp
directory, loads it with `runpy`, calls its functions inside an `Observer` on that directory, and
reads back what was seen. The controls are that code outside the root is not recorded, that a tool
id taken by another tool is refused by name, and that the id is freed even when the block raises.
"""

import json
import runpy
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast

import pytest

from mikemol.pycodemod import observed

_SOURCE = """\
class Box:
    def put(self, item):
        return None


def add(a, b):
    return a + b


def head(xs):
    return xs


def many(*args, **kw):
    return len(args)
"""
_TWO = 2
_THREE = 3
_IDS = range(6)


class _Box(Protocol):
    def put(self, item: object) -> object: ...


class _Many(Protocol):
    def __call__(self, *args: object, **kw: object) -> object: ...


@dataclass(frozen=True)
class _Funcs:
    box: Callable[[], _Box]
    add: Callable[[object, object], object]
    head: Callable[[object], object]
    many: _Many


def _functions(tmp_path: Path) -> _Funcs:
    path = tmp_path / "mod.py"
    path.write_text(_SOURCE, encoding="utf-8")
    ns = cast("dict[str, object]", runpy.run_path(str(path)))
    return _Funcs(
        cast("Callable[[], _Box]", ns["Box"]),
        cast("Callable[[object, object], object]", ns["add"]),
        cast("Callable[[object], object]", ns["head"]),
        cast("_Many", ns["many"]),
    )


def _only(seen: dict[str, observed.Signature], qualname: str) -> observed.Signature:
    (found,) = [sig for key, sig in seen.items() if key.endswith(f"::{qualname}")]
    return found


def _free_ids() -> list[int]:
    return [t for t in _IDS if sys.monitoring.get_tool(t) is None]


def test_the_types_each_call_passed_and_returned_are_collected_per_parameter(
    tmp_path: Path,
) -> None:
    """add(1, 2) and add("x", "y") leave int and str on both parameters and on the return."""
    fn = _functions(tmp_path)
    with observed.Observer(tmp_path) as seen:
        fn.add(1, _TWO)
        fn.add("x", "y")
    add = _only(seen.observed(), "add")
    assert add.params == {"a": {"int", "str"}, "b": {"int", "str"}}
    assert add.returns == {"int", "str"}


def test_a_container_is_spelled_with_its_element_types(tmp_path: Path) -> None:
    """A list of ints, a dict of str to float, a tuple and an empty list each read as they are."""
    fn = _functions(tmp_path)
    with observed.Observer(tmp_path) as seen:
        for value in ([1, _TWO], {"k": 1.5}, (1, "a"), [], [[1]]):
            fn.head(value)
    got = _only(seen.observed(), "head").params["xs"]
    assert got == {"list[int]", "dict[str, float]", "tuple[int, str]", "list", "list[list]"}


def test_none_a_method_and_varargs_are_named(tmp_path: Path) -> None:
    """None reads None, a method's item is typed, *args and **kw are recorded."""
    fn = _functions(tmp_path)
    with observed.Observer(tmp_path) as seen:
        fn.box().put(1)
        fn.many(1, _TWO, flag=True)
    signatures = seen.observed()
    assert _only(signatures, "Box.put").returns == {"None"}
    assert _only(signatures, "Box.put").params == {"item": {"int"}}
    many = _only(signatures, "many")
    assert many.params == {"args": {"tuple[int, int]"}, "kw": {"dict[str, bool]"}}


def test_self_is_skipped_and_code_outside_the_root_is_never_recorded(tmp_path: Path) -> None:
    """json.dumps runs in the standard library: nothing from it appears, and no `self` key."""
    fn = _functions(tmp_path)
    with observed.Observer(tmp_path) as seen:
        fn.box().put(1)
        json.dumps("a")
    keys = list(seen.observed())
    assert all(key.startswith(str(tmp_path.resolve())) for key in keys)
    assert "self" not in _only(seen.observed(), "Box.put").params


def test_observe_runs_a_call_and_returns_what_it_saw(tmp_path: Path) -> None:
    """The one-call form gives the same signatures as the context manager."""
    fn = _functions(tmp_path)
    got = observed.observe(tmp_path, lambda: fn.add(_THREE, _THREE))
    assert _only(got, "add").returns == {"int"}


def test_a_held_tool_id_is_refused_by_name_and_the_id_is_freed_after_a_raise(
    tmp_path: Path,
) -> None:
    """Every free id taken: NoToolIdError. A block that raises still frees the id it took."""
    before = _free_ids()
    for tool in before:
        sys.monitoring.use_tool_id(tool, "test-holder")
    try:
        with pytest.raises(observed.NoToolIdError), observed.Observer(tmp_path):
            pass
    finally:
        for tool in before:
            sys.monitoring.free_tool_id(tool)
    with pytest.raises(ZeroDivisionError), observed.Observer(tmp_path):
        _ = 1 / 0
    assert _free_ids() == before
