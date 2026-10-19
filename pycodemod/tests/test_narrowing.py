# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A parameter is narrowed from what the body does with it, never past what it shows (W1515)."""

from mikemol.pycodemod import narrowing

_SOURCE = """\
def keyed(cfg):
    return cfg["name"] + cfg["size"] + cfg.get("extra")


def arrays(arr):
    return arr.reshape(2).sum()


def stream(fh):
    fh.write("x")
    fh.flush()


def caller(fn):
    return fn(1)


def looped(xs):
    return [x for x in xs]


def indexed(seq):
    return seq[0]


def counted(box):
    return len(box)


def operand(n):
    return n + 1


def mapping_only(table):
    return table.items()


class Box:
    def put(self, item):
        return item.value

    def outer(self, a):
        def inner(a):
            return a["k"]

        return a.shape, inner


async def waiting(handle):
    return await handle.done()
"""


def _kind(qualname: str, param: str) -> narrowing.Narrowed:
    return narrowing.narrow(narrowing.uses_of(_SOURCE)[qualname][param])


def test_constant_string_keys_make_a_typeddict_of_those_keys() -> None:
    """Two subscripted keys and a dict method: the keys, sorted, and nothing about get."""
    assert _kind("keyed", "cfg") == narrowing.Narrowed("typeddict", ("name", "size"))


def test_array_attributes_make_an_ndarray_and_other_attributes_a_protocol() -> None:
    """Reshape and sum are array methods; write and flush are a stream's, named in order."""
    assert _kind("arrays", "arr") == narrowing.Narrowed("ndarray")
    assert _kind("stream", "fh") == narrowing.Narrowed("protocol", ("flush", "write"))


def test_a_call_an_index_a_loop_and_a_len_each_name_their_form() -> None:
    """Callable, Sequence, Iterable and Sized, in that order of preference."""
    assert _kind("caller", "fn").kind == "callable"
    assert _kind("indexed", "seq").kind == "sequence"
    assert _kind("looped", "xs").kind == "iterable"
    assert _kind("counted", "box").kind == "sized"


def test_dict_methods_alone_are_a_mapping_and_a_bare_operand_is_unconstrained() -> None:
    """An operand alone shows nothing, so the traced type is kept; items() shows a mapping."""
    assert _kind("mapping_only", "table").kind == "mapping"
    assert _kind("operand", "n") == narrowing.Narrowed("unconstrained")


def test_self_is_skipped_methods_are_qualified_and_nested_parameters_are_their_own() -> None:
    """Box.put has `item` only; `a` in Box.outer is an array, `a` in inner is its own mapping."""
    uses = narrowing.uses_of(_SOURCE)
    assert set(uses["Box.put"]) == {"item"}
    assert narrowing.narrow(uses["Box.put"]["item"]) == narrowing.Narrowed("protocol", ("value",))
    assert narrowing.narrow(uses["Box.outer"]["a"]).kind == "ndarray"
    assert narrowing.narrow(uses["Box.outer.inner"]["a"]) == narrowing.Narrowed("typeddict", ("k",))


def test_an_async_function_is_read_like_any_other() -> None:
    """Awaiting a method of the handle reads that attribute, so the handle is a protocol."""
    assert _kind("waiting", "handle") == narrowing.Narrowed("protocol", ("done",))
