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


def _num(consts, name):
    return consts[name]


def reach(graph, node):
    return {n for n in graph[node]}


def by_position(items, i):
    return items[i] + items[-1] + items[len(items) - 1]


def sliced_and_keyed(rows, name):
    return rows[1:] + rows[name]


def attribute_keyed(table, entry):
    return table[entry.key]


def of_string(text):
    return text.strip().split(",") + [text.upper()]


def string_and_stream(box):
    return box.strip() + box.write("x")


def shared_method(items):
    return items.count("a")


def label(name):
    return name


def mixed(value):
    return value


def by_keyword(text, count):
    return text, count


def spread(item):
    return item


def keyed_text(cfg):
    return cfg["name"]


def unnamed(orphan):
    return orphan


def drive(args):
    label("a")
    label(f"{args}")
    mixed("a")
    mixed(3)
    by_keyword(text="x", count=1)
    spread(*args)
    keyed_text("x")


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


def test_a_value_subscripted_by_a_variable_key_is_a_mapping_and_by_a_position_a_sequence() -> None:
    """W2111, el-openglo's misreads: consts[name] and graph[node] are mappings, items[i] is not."""
    assert _kind("_num", "consts").kind == "mapping"
    assert _kind("reach", "graph").kind == "mapping"
    assert _kind("attribute_keyed", "table").kind == "mapping"
    assert _kind("by_position", "items").kind == "sequence"
    assert _kind("sliced_and_keyed", "rows").kind == "sequence"


def test_a_parameter_read_only_through_string_only_methods_is_a_str() -> None:
    """W2112: strip, split and upper are str's; add write and it is a stream; count is shared."""
    assert _kind("of_string", "text") == narrowing.Narrowed("str")
    assert _kind("string_and_stream", "box").kind == "protocol"
    assert _kind("shared_method", "items").kind == "protocol"


def test_a_parameter_every_call_in_the_file_gives_a_str_is_a_str_and_no_other_is() -> None:
    """W2112: literals and f-strings in every call make a str; a 3, a `*args`, no call, do not."""
    assert _kind("label", "name") == narrowing.Narrowed("str")
    assert _kind("by_keyword", "text") == narrowing.Narrowed("str")
    assert _kind("by_keyword", "count").kind == "unconstrained"
    assert _kind("mixed", "value").kind == "unconstrained"
    assert _kind("spread", "item").kind == "unconstrained"
    assert _kind("unnamed", "orphan").kind == "unconstrained"
    assert _kind("keyed_text", "cfg").kind == "typeddict"


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
