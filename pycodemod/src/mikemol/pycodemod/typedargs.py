# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""`typed-args`: one `argparse.Namespace` subclass per parser, so every `args.X` is typed at once.

`parser.parse_args()` returns a bare `Namespace`, whose attributes are `Any`. Under mypy's
`disallow_any_expr` every read of `args.X` is a finding, and a cast at each read is a hand-kept copy
of what the `add_argument` call already says. This plans the other way: derive each destination's
type from its own `add_argument` call, emit `class MainArgs(argparse.Namespace)` with those
annotations just above the function, and pass `namespace=MainArgs()` to `parse_args`.

⚑ ONLY A PARSER THAT LIVES ENTIRELY IN ONE TOP-LEVEL FUNCTION IS TRANSFORMED: created by
`argparse.ArgumentParser(...)`, filled by `add_argument(...)` statements, parsed by one
`args = parser.parse_args(...)`, and referenced nowhere else. Everything else is REFUSED and named
(a subparser, a group, `set_defaults`, a parser handed to another function, a non-literal flag, a
`type=` that is not a plain name, an action this does not model, a module without
`from __future__ import annotations` or `import argparse`). A refusal is a worklist line, never a
guess: "the mechanical 90% and PRINTS the residue".

⚑ THE ANNOTATION STATES WHAT THE PARSER DECLARES, NOT WHAT A DEFAULT HAPPENS TO BE: no `default` on
an option gives `T | None`, `default=None` gives `T | None`, any other default gives `T`;
`store_true`/`store_false` give `bool`; `count` gives `int | None` (argparse's default is None);
`nargs` of `*`, `+` or an integer, and `append`, give `list[T]` (`list[T] | None` for an option
without a default); a positional is `T`. A `cast("T", args.X)` whose `T` already equals the
annotation is dropped, and `cast` leaves the `typing` import only when nothing else uses it.

THE TEXT IS EDITED, NOT RE-EMITTED: libcst gives exact positions and the edits are applied to the
original source bottom-up, so nothing else in the file moves. The caller (the orchestrator) is what
checks the result before it is written.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

import libcst as cst
import libcst.matchers as m
from libcst.metadata import MetadataWrapper, PositionProvider

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from libcst.metadata import CodeRange

COUNT = "count"
BOOLEAN_ACTIONS = frozenset({"store_true", "store_false"})
PLAIN_ACTIONS = frozenset({"store", "append"})
MANY_NARGS = frozenset({"*", "+"})
CAST_ARGS = 2
FUTURE = re.compile(r"^from __future__ import .*\bannotations\b", re.MULTILINE)
CAST_CALL = re.compile(r"\bcast\(")


@dataclass(frozen=True, slots=True)
class Field:
    """One destination of the parser and the annotation its `add_argument` call declares."""

    dest: str
    annotation: str


@dataclass(frozen=True, slots=True)
class Refusal:
    """A parser (or file) this did not transform, and the one reason."""

    line: int
    function: str
    why: str


@dataclass(frozen=True, slots=True)
class Planned:
    """The new text (the old text when nothing was transformed), parsers done, and the refusals."""

    text: str
    parsers: int
    refusals: list[Refusal]


@dataclass(frozen=True, slots=True)
class _Edit:
    start: int
    end: int
    text: str


@dataclass(frozen=True, slots=True)
class _Parser:
    function: cst.FunctionDef
    var: str
    adds: list[cst.Call]
    parse: cst.Call
    args_var: str


@dataclass(frozen=True, slots=True)
class _Source:
    # The text, libcst's position of every node, and the character offset of each line.
    text: str
    spots: Mapping[cst.CSTNode, CodeRange]
    starts: list[int]

    def at(self, node: cst.CSTNode, *, end: bool = False) -> int:
        # The character offset of a node's start (or end).
        pos = self.spots[node].end if end else self.spots[node].start
        return self.starts[pos.line - 1] + pos.column


def _code(node: cst.CSTNode) -> str:
    return cst.Module(body=[]).code_for_node(node)


def _literal(node: cst.BaseExpression) -> str | None:
    # A plain string literal's value, else None.
    if not isinstance(node, cst.SimpleString):
        return None
    value = node.evaluated_value
    return value if isinstance(value, str) else None


def _keywords(call: cst.Call) -> dict[str, cst.BaseExpression]:
    return {a.keyword.value: a.value for a in call.args if a.keyword is not None}


def _positionals(call: cst.Call) -> list[cst.BaseExpression]:
    return [a.value for a in call.args if a.keyword is None and not a.star]


def _is_none(node: cst.BaseExpression) -> bool:
    return isinstance(node, cst.Name) and node.value == "None"


def _is_true(node: cst.BaseExpression | None) -> bool:
    return isinstance(node, cst.Name) and node.value == "True"


def _dest(flags: Sequence[str], keywords: Mapping[str, cst.BaseExpression]) -> str | None:
    explicit = keywords.get("dest")
    if explicit is not None:
        return _literal(explicit)
    if not flags[0].startswith("-"):
        return flags[0]
    longs = [flag for flag in flags if flag.startswith("--")]
    return (longs[0] if longs else flags[0]).lstrip("-").replace("-", "_")


def _element(keywords: Mapping[str, cst.BaseExpression]) -> str | None:
    node = keywords.get("type")
    if node is None:
        return "str"
    return _code(node) if isinstance(node, (cst.Name, cst.Attribute)) else None


def _action(keywords: Mapping[str, cst.BaseExpression]) -> str | None:
    node = keywords.get("action")
    return "store" if node is None else _literal(node)


def _many(keywords: Mapping[str, cst.BaseExpression], action: str) -> bool | None:
    # Whether the destination is a list; None when `nargs` is not modelled.
    nargs = keywords.get("nargs")
    if nargs is None or _is_none(nargs):
        return action == "append"
    if isinstance(nargs, cst.Integer):
        return True
    text = _literal(nargs)
    if text == "?":
        return False
    return True if text in MANY_NARGS else None


def _optional(keywords: Mapping[str, cst.BaseExpression], *, positional: bool) -> bool:
    # Whether the parser can leave the destination as None.
    default = keywords.get("default")
    if default is not None:
        return _is_none(default)
    nargs = keywords.get("nargs")
    question = nargs is not None and _literal(nargs) == "?"
    return question or not (positional or _is_true(keywords.get("required")))


def _simple(dest: str, action: str, keywords: Mapping[str, cst.BaseExpression]) -> Field | None:
    # The two actions whose type does not depend on `type=`.
    if action in BOOLEAN_ACTIONS:
        return Field(dest, "bool")
    if action == COUNT:
        return Field(dest, "int" if "default" in keywords else "int | None")
    return None


def _stored(
    name: str, dest: str, keywords: Mapping[str, cst.BaseExpression], action: str
) -> Field | str:
    # A `store` or `append` destination: element type, list-ness and optionality.
    element = _element(keywords)
    many = _many(keywords, action)
    if element is None or many is None:
        return f"add_argument {name}: type or nargs is not a plain literal or name"
    base = f"list[{element}]" if many else element
    optional = _optional(keywords, positional=not name.startswith("-"))
    return Field(dest, f"{base} | None" if optional else base)


def field_of(call: cst.Call) -> Field | str:
    """Derive the destination an `add_argument` call declares.

    Returns:
        the Field, or the one reason it cannot be derived.

    """
    flags = [_literal(value) for value in _positionals(call)]
    names = [flag for flag in flags if flag is not None]
    if not names or len(names) != len(flags):
        return "add_argument with a name that is not a string literal"
    keywords = _keywords(call)
    dest = _dest(names, keywords)
    action = _action(keywords)
    if dest is None or action is None:
        return f"add_argument {names[0]}: dest or action is not a string literal"
    simple = _simple(dest, action, keywords)
    if simple is not None:
        return simple
    if action not in PLAIN_ACTIONS:
        return f"add_argument {names[0]}: action {action!r} is not modelled"
    return _stored(names[0], dest, keywords, action)


def _small(stmt: cst.BaseStatement) -> cst.BaseSmallStatement | None:
    if not isinstance(stmt, cst.SimpleStatementLine) or len(stmt.body) != 1:
        return None
    return stmt.body[0]


def _call_on(small: cst.BaseSmallStatement | None, var: str, method: str) -> cst.Call | None:
    # `var.method(...)` as an expression statement.
    if not isinstance(small, cst.Expr) or not isinstance(small.value, cst.Call):
        return None
    func = small.value.func
    if isinstance(func, cst.Attribute) and m.matches(func.value, m.Name(var)):
        return small.value if func.attr.value == method else None
    return None


def _assigned(small: cst.BaseSmallStatement | None) -> tuple[str, cst.BaseExpression] | None:
    # `name = value` with one Name target.
    if not isinstance(small, cst.Assign) or len(small.targets) != 1:
        return None
    target = small.targets[0].target
    return (target.value, small.value) if isinstance(target, cst.Name) else None


def _is_parser(value: cst.BaseExpression) -> bool:
    return isinstance(value, cst.Call) and m.matches(
        value.func, m.Attribute(value=m.Name("argparse"), attr=m.Name("ArgumentParser"))
    )


def _parse_call(value: cst.BaseExpression, var: str) -> cst.Call | None:
    # `var.parse_args(...)`.
    if not isinstance(value, cst.Call) or not isinstance(value.func, cst.Attribute):
        return None
    if not m.matches(value.func.value, m.Name(var)) or value.func.attr.value != "parse_args":
        return None
    return value


@dataclass(frozen=True, slots=True)
class _Found:
    var: str | None
    adds: list[cst.Call]
    parse: tuple[cst.Call, str] | None


def _walk(body: Sequence[cst.BaseStatement]) -> _Found | str:
    # The parser variable, its add_argument calls and its parse_args assignment, in order.
    var: str | None = None
    adds: list[cst.Call] = []
    parse: tuple[cst.Call, str] | None = None
    for stmt in body:
        small = _small(stmt)
        made = _assigned(small)
        if made is not None and _is_parser(made[1]):
            if var is not None:
                return "more than one ArgumentParser in the function"
            var = made[0]
        elif var is not None and (add := _call_on(small, var, "add_argument")) is not None:
            adds.append(add)
        elif var is not None and made is not None and (call := _parse_call(made[1], var)):
            parse = (call, made[0])
    if parse is not None and "namespace" in _keywords(parse[0]):
        return _Found(None, [], None)  # already typed: running this again is a no-op
    return _Found(var, adds, parse)


def _scan(function: cst.FunctionDef) -> _Parser | str | None:
    """Find the one parser in a function.

    Returns:
        the parser, None when the function has none (or already types it), or why it is not fit.

    """
    if not isinstance(function.body, cst.IndentedBlock):
        return None
    found = _walk(function.body.body)
    if isinstance(found, str) or found.var is None:
        return None if not isinstance(found, str) else found
    if found.parse is None:
        return f"parser {found.var} is never parsed by a plain `x = {found.var}.parse_args(...)`"
    # `parser.error(...)` exits and touches no namespace field, so it is not a use that matters.
    errors = m.Call(func=m.Attribute(value=m.Name(found.var), attr=m.Name("error")))
    allowed = len(found.adds) + 2 + len(m.findall(function, errors))
    if len(m.findall(function, m.Name(found.var))) != allowed:
        return f"parser {found.var} is used beyond add_argument, parse_args and error"
    return _Parser(function, found.var, found.adds, found.parse[0], found.parse[1])


def _class_name(function: str) -> str:
    return "".join(part.capitalize() for part in function.strip("_").split("_")) + "Args"


def _class_text(name: str, function: str, fields: Sequence[Field]) -> str:
    body = "\n".join(f"    {f.dest}: {f.annotation}" for f in fields)
    doc = f'    """The typed result of `{function}` (generated by pycodemod typed-args)."""'
    return f"class {name}(argparse.Namespace):\n{doc}\n\n{body}\n\n\n"


def _offsets(text: str) -> list[int]:
    starts = [0]
    for line in text.splitlines(keepends=True):
        starts.append(starts[-1] + len(line))
    return starts


def _start(edit: _Edit) -> int:
    return edit.start


def _apply(text: str, edits: list[_Edit]) -> str:
    for edit in sorted(edits, key=_start, reverse=True):
        text = text[: edit.start] + edit.text + text[edit.end :]
    return text


def _has_import_argparse(module: cst.Module) -> bool:
    for stmt in module.body:
        small = _small(stmt)
        if isinstance(small, cst.Import):
            for alias in small.names:
                if alias.asname is None and m.matches(alias.name, m.Name("argparse")):
                    return True
    return False


def _fields(adds: Sequence[cst.Call]) -> list[Field] | str:
    fields: list[Field] = []
    for call in adds:
        got = field_of(call)
        if isinstance(got, str):
            return got
        fields.append(got)
    if len({f.dest for f in fields}) != len(fields):
        return "two add_argument calls share a destination"
    return fields


def _module_reason(module: cst.Module, text: str, taken: set[str], name: str) -> str | None:
    # Why this module cannot take the new class, or None.
    if not FUTURE.search(text):
        return "the module lacks `from __future__ import annotations`"
    if not _has_import_argparse(module):
        return "the module lacks a plain `import argparse`"
    return f"the module already defines {name}" if name in taken else None


def _cast_edits(src: _Source, parser: _Parser, declared: Mapping[str, str]) -> list[_Edit]:
    # `cast("T", args.X)` becomes `args.X` when T is exactly the declared annotation.
    edits: list[_Edit] = []
    for node in m.findall(parser.function, m.Call(func=m.Name("cast"))):
        call = cast("cst.Call", node)
        if len(call.args) != CAST_ARGS:
            continue
        kind, value = call.args[0].value, call.args[1].value
        if not isinstance(value, cst.Attribute):
            continue
        if m.matches(value.value, m.Name(parser.args_var)) and (
            _literal(kind) == declared.get(value.attr.value)
        ):
            edits.append(_Edit(src.at(call), src.at(call, end=True), _code(value)))
    return edits


def _parser_edits(src: _Source, parser: _Parser, name: str, fields: Sequence[Field]) -> list[_Edit]:
    # The class above the function, the namespace keyword, and the casts that became redundant.
    decorators = parser.function.decorators
    top = src.at(decorators[0] if decorators else parser.function)
    text = _class_text(name, parser.function.name.value, fields)
    close = src.at(parser.parse, end=True) - 1
    keyword = ("" if not parser.parse.args else ", ") + f"namespace={name}()"
    declared = {f.dest: f.annotation for f in fields}
    casts = _cast_edits(src, parser, declared)
    return [_Edit(top, top, text), _Edit(close, close, keyword), *casts]


def _cast_import_edit(module: cst.Module, src: _Source, edits: list[_Edit]) -> list[_Edit]:
    # Drop `cast` from `from typing import ...` when nothing in the new text still calls it.
    if CAST_CALL.search(_apply(src.text, edits)):
        return []
    for stmt in module.body:
        small = _small(stmt)
        if not isinstance(small, cst.ImportFrom) or isinstance(small.names, cst.ImportStar):
            continue
        if not isinstance(small.module, cst.Name) or small.module.value != "typing":
            continue
        kept = [_code(a.name) for a in small.names if _code(a.name) != "cast"]
        if len(kept) == len(small.names):
            continue
        begin = src.starts[src.spots[stmt].start.line - 1]
        finish = src.starts[src.spots[stmt].end.line]
        return [_Edit(begin, finish, f"from typing import {', '.join(kept)}\n" if kept else "")]
    return []


def plan(text: str) -> Planned:
    """Plan the typed-args rewrite of one module's source.

    Returns:
        the new text, how many parsers were transformed, and a Refusal for each one that was not.

    """
    try:
        wrapper = MetadataWrapper(cst.parse_module(text))
    except cst.ParserSyntaxError as exc:
        return Planned(text, 0, [Refusal(0, "", f"does not parse: {exc.message}")])
    module = wrapper.module
    src = _Source(text, wrapper.resolve(PositionProvider), _offsets(text))
    taken = {n.name.value for n in module.body if isinstance(n, (cst.ClassDef, cst.FunctionDef))}
    refusals: list[Refusal] = []
    edits: list[_Edit] = []
    done = 0
    for function in (n for n in module.body if isinstance(n, cst.FunctionDef)):
        found = _scan(function)
        if found is None:
            continue
        name = _class_name(function.name.value)
        fields = _fields(found.adds) if not isinstance(found, str) else found
        why = fields if isinstance(fields, str) else _module_reason(module, text, taken, name)
        if isinstance(found, str) or why is not None or isinstance(fields, str):
            reason = found if isinstance(found, str) else (why or "")
            refusals.append(Refusal(src.spots[function].start.line, function.name.value, reason))
            continue
        taken.add(name)
        done += 1
        edits.extend(_parser_edits(src, found, name, fields))
    if any(e.start != e.end for e in edits):
        edits.extend(_cast_import_edit(module, src, edits))
    return Planned(_apply(text, edits), done, refusals)
