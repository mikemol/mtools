# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W207/W214: the generic `reference` implementation for every W206 case.

A case's `fixture` is {original absolute path: source}; its `operands` is the origin's call list,
[{fn: "<module>.py:<function>", args: {name: repr-string}}]. The adapter recreates every fixture
file under one directory named by the fixture's content, rewrites the original root in each arg,
parses each arg back with ast.literal_eval (keeping the raw string when it is not a literal), and
calls the origin function by name. The result is the list of each call's return value, normalized
to JSON with that root written as `<root>`, so a Rego spec can name a file.

W229: `pytest_spec_cache_key` vouches for a `reference` result under pytestspec's
`--result-cache`, keyed on everything the origin reads (see `cache_key`).

Run with substrate/scratch on PYTHONPATH. The `subject` implementation is per mode (W207).
"""

import ast
import dataclasses
import hashlib
import importlib
import inspect
import json
import os
import sys
import tempfile
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, cast

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

type JSON = bool | int | float | str | list[JSON] | dict[str, JSON] | None
type Adapter = Callable[[object, object], object]
ROOT = "<root>"
# W225: one base per session; each fixture lives under a hash of its content (see rehome).
BASE = Path(tempfile.mkdtemp(prefix="w206-"))
# W229: a callee whose result depends on something no key here covers (commentary_lost runs git).
UNCACHEABLE = frozenset({"_pycodemod_commentary.py:commentary_lost"})
# W229: the corpus digest, computed once per session (see corpus_digest).
_DIGEST: dict[str, str] = {}


class CaseDataError(ValueError):
    """A case's fixture or operands are not the shape the W206 generator writes."""


class OriginBlindError(RuntimeError):
    """W347: the origin was imported without libcst, so its parser-backed modes return [].

    `_pycodemod_core` and `_pycodemod_query` set `cst = None` on ImportError, and `rivals`, `scan`
    and `dead` then return an empty list rather than raising. A replay in that environment is a
    blind instrument: measured on rivals, 26 of 35 cases read [[]] that read real rows with libcst.
    """


class OriginCall(Protocol):
    """An origin function, called with the captured args by name."""

    def __call__(self, *args: object, **kwargs: object) -> object:
        """Run the origin function."""


class Rooted(Protocol):
    """An origin module that reads its corpus root from a module-global `ROOT`."""

    ROOT: object


def str_map(value: object, what: str) -> dict[str, str]:
    """Narrow a decoded JSON object whose keys and values are all strings.

    Returns:
        the same mapping, typed.

    Raises:
        CaseDataError: when it is not a {str: str} mapping.

    """
    if not isinstance(value, dict):
        raise CaseDataError(what)
    out: dict[str, str] = {}
    for key, item in cast("dict[object, object]", value).items():
        if not isinstance(key, str) or not isinstance(item, str):
            raise CaseDataError(what)
        out[key] = item
    return out


def calls(operands: object) -> list[tuple[str, dict[str, str]]]:
    """Narrow the operands list to (fn, args) pairs.

    Returns:
        one (fn, args) pair per origin call, in order.

    Raises:
        CaseDataError: when operands is not a list of {fn: str, args: {str: str}}.

    """
    if not isinstance(operands, list):
        msg = "operands"
        raise CaseDataError(msg)
    out: list[tuple[str, dict[str, str]]] = []
    for call in cast("list[object]", operands):
        if not isinstance(call, dict):
            msg = "operand"
            raise CaseDataError(msg)
        fields = cast("dict[object, object]", call)
        fn = fields.get("fn")
        if not isinstance(fn, str):
            msg = "operand fn"
            raise CaseDataError(msg)
        out.append((fn, str_map(fields.get("args"), "operand args")))
    return out


def _above(raw: str, root: str) -> str | None:
    """Return the path a captured operand names, when it is an ancestor of `root`.

    Returns:
        the ancestor path, or None when the operand is not an absolute path above `root`.

    """
    try:
        value = cast("object", ast.literal_eval(raw))
    except (ValueError, SyntaxError):
        value = raw
    # W189 records `*roots` as a list of paths, so a list's members are operands too
    members = cast("list[object]", value) if isinstance(value, (list, tuple)) else [value]
    for member in members:
        if isinstance(member, str) and Path(member).is_absolute():
            path = os.path.normpath(member)
            if root.startswith(path + os.sep):
                return path
    return None


def rehome(fixture: dict[str, str], operands: Iterable[str] = ()) -> tuple[str, str]:
    """Write the fixture files under a root named by their content.

    W225: the root is BASE plus a hash of the fixture, so a case replayed with the same fixture
    gets the same paths. An origin memo keyed by path (resorts' _PRODUCER_CACHE) then survives
    across cases instead of missing on every fresh mkdtemp().

    Returns:
        (original root, new root); both empty strings when there are no fixture files.

    """
    if not fixture:
        return "", ""
    old = os.path.commonpath([str(Path(p).parent) for p in fixture])
    # W424: an operand naming a directory ABOVE every fixture (py-files 108 walks
    # <tree>/bazel-bin while its only file is bazel-bin/mutants/m.py) must be rewritten too,
    # so the old root widens to it; the layout is then part of the key, or a cached tree
    # written under the narrower root would be reused with the wrong shape.
    for raw in operands:
        above = _above(raw, old)
        if above is not None:
            old = above
    key: list[object] = [old, fixture]
    keyed = json.dumps(key, sort_keys=True).encode()
    digest = hashlib.sha256(keyed).hexdigest()[:16]
    new = BASE / digest
    if not new.exists():
        for path, source in fixture.items():
            target = new / os.path.relpath(path, old)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(source, encoding="utf-8")
    return old, str(new)


def parse(raw: str, old: str, new: str) -> object:
    """Read one captured arg back: a literal when it is one, else the raw string.

    Returns:
        the literal value, or the (re-rooted) string itself.

    """
    text = raw.replace(old, new) if old else raw
    try:
        return cast("object", ast.literal_eval(text))
    except (ValueError, SyntaxError):
        return text


def normal(value: object, root: str) -> JSON:
    """Reduce a return value to JSON: sequences to lists, sets sorted, anything else by repr.

    Returns:
        a JSON value, with `root` written as `<root>` in every string.

    """
    if isinstance(value, str):
        return value.replace(root, ROOT) if root else value
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, dict):
        items = cast("dict[object, object]", value).items()
        return {cast("str", normal(str(k), root)): normal(v, root) for k, v in items}
    if isinstance(value, (set, frozenset)):
        members = cast("set[object] | frozenset[object]", value)
        return sorted((normal(v, root) for v in members), key=repr)
    # an iterator's repr names an address, not a result (W411: crossings returns a generator)
    if isinstance(value, (list, tuple, Iterator)):
        return [normal(v, root) for v in cast("Iterable[object]", value)]
    return normal(repr(value), root)


GLOBAL_ROOT = "<global ROOT>"


def bind(func: OriginCall, args: dict[str, object]) -> tuple[list[object], dict[str, object]]:
    """Bind captured args to the callee's own signature (W421).

    The W189 capture records `*roots` under its parameter NAME and adds keys that are not
    parameters (`<global ROOT>`, dotted `k.kk` expansions of a dict argument), so passing
    every key by name fails. Positional parameters go positionally, in order, so that a
    following `*args` can be splatted; keyword-only ones go by name; other keys are dropped.

    Returns:
        (positional args, keyword args).

    """
    positional: list[object] = []
    keyword: dict[str, object] = {}
    gap = False
    for name, param in inspect.signature(func).parameters.items():
        if name not in args:
            gap = True
            continue
        value = args[name]
        if param.kind.name == "VAR_POSITIONAL":
            positional.extend(cast("Iterable[object]", value))
        elif param.kind.name == "VAR_KEYWORD":
            keyword.update(cast("dict[str, object]", value))
        elif param.kind.name == "KEYWORD_ONLY" or gap:
            keyword[name] = value
        else:
            positional.append(value)
    return positional, keyword


def reference(fixture: object, operands: object) -> object:
    """Run the origin's calls on the case's fixture.

    Returns:
        the JSON-normalized return value of each call, in order.

    Raises:
        OriginBlindError: the origin was imported without libcst (W347).

    """
    captured = calls(operands)
    old, new = rehome(
        str_map(fixture, "fixture"), [raw for _fn, args in captured for raw in args.values()]
    )
    out: list[JSON] = []
    for fn, args in captured:
        module, _, name = fn.partition(":")
        target = importlib.import_module(module.removesuffix(".py"))
        if hasattr(target, "cst") and cast("object", target.cst) is None:
            msg = f"{module} imported without libcst; run under a venv that has it (W347)"
            raise OriginBlindError(msg)
        func = cast("OriginCall", getattr(target, name))
        parsed = {k: parse(v, old, new) for k, v in args.items()}
        positional, keyword = bind(func, parsed)
        if GLOBAL_ROOT not in parsed:
            out.append(normal(func(*positional, **keyword), new))
            continue
        # W189: the case rebinds the module-global ROOT to its temp tree. The module stays
        # imported across cases, so the rebinding is undone after the call or it leaks.
        rooted = cast("Rooted", target)
        before = rooted.ROOT
        rooted.ROOT = parsed[GLOBAL_ROOT]
        try:
            out.append(normal(func(*positional, **keyword), new))
        finally:
            rooted.ROOT = before
    return out


class SubjectGapError(LookupError):
    """The port has no counterpart registered for an origin callee: never a silent pass."""


class HasRows(Protocol):
    """A port result that carries its findings as `rows` of dataclasses."""

    rows: list[object]


def _rows(value: object) -> JSON:
    """Reshape a port result object carrying `rows` of dataclasses into the origin's lists.

    Returns:
        one list of field values per row, in field order.

    """
    out: list[JSON] = []
    for row in cast("HasRows", value).rows:
        fields = cast("tuple[object, ...]", dataclasses.astuple(cast("DataclassInstance", row)))
        out.append([normal(f, "") for f in fields])
    return out


def _same(value: object) -> JSON:
    """Pass a port result through when it already has the origin's shape.

    Returns:
        the value, JSON-normalized.

    """
    return normal(value, "")


def _sites(value: object) -> JSON:
    """Reshape port `Sites` rows to the origin's [path, kind, name, line], dropping `column`.

    The port added the column so two sites on one line stay distinct; the origin never had it.

    Returns:
        one four-field list per row.

    """
    out: list[JSON] = []
    for row in cast("HasRows", value).rows:
        fields = cast("tuple[object, ...]", dataclasses.astuple(cast("DataclassInstance", row)))
        out.append([normal(f, "") for f in fields[:4]])
    return out


def _source(value: object) -> JSON:
    """Reshape port `Source` rows to the origin's [path, start, end, text], dropping `qualname`.

    The port added the qualified name; the origin never had it (W448).

    Returns:
        one four-field list per row.

    """
    out: list[JSON] = []
    for row in cast("HasRows", value).rows:
        path, start, end, _qualname, text = cast(
            "tuple[str, int, int, str, str]", dataclasses.astuple(cast("DataclassInstance", row))
        )
        out.append([path, start, end, text])
    return out


# W432: origin callee -> (port module, port function, reshape into the origin's result shape).
# One entry per mode as its translator lands (W208); an unlisted callee raises SubjectGapError.
SUBJECT: dict[str, tuple[str, str, Callable[[object], JSON]]] = {
    "_pycodemod_query.py:shape_sites": ("mikemol.pycodemod.shapes", "shape_sites", _rows),
    "_pycodemod_core.py:roundtrip": ("mikemol.pycodemod.core", "roundtrip", _same),
    "_pycodemod_query.py:key_reads": ("mikemol.pycodemod.strings", "key_reads", _rows),
    "_pycodemod_query.py:literal_sites": ("mikemol.pycodemod.strings", "literal_sites", _rows),
    "_pycodemod_query.py:rivals": ("mikemol.pycodemod.rivals", "rivals", _rows),
    "_pycodemod_query.py:scan": ("mikemol.pycodemod.sites", "scan", _sites),
    "_pycodemod_query.py:dead": ("conftest", "port_dead", _same),
    "_pycodemod_query.py:framework_dispatch": (
        "mikemol.pycodemod.dead",
        "framework_dispatch",
        _same,
    ),
    "_pycodemod_core.py:flagged_argv": ("mikemol.pycodemod.core", "flagged_argv", _same),
    "_pycodemod_core.py:operand_tail": ("mikemol.pycodemod.core", "operand_tail", _same),
    "_pycodemod_query.py:values": ("conftest", "port_values", _same),
    "_pycodemod_query.py:callgraph": ("conftest", "port_callgraph", _same),
    "_pycodemod_query.py:reaches": ("conftest", "port_reaches", _same),
    "_pycodemod_query.py:forwards": ("conftest", "port_forwards", _same),
    "_pycodemod_query.py:asserted": ("conftest", "port_asserted", _same),
    "_pycodemod_query.py:reifies": ("mikemol.pycodemod.ordering", "reifies", _rows),
    "_pycodemod_ambient.py:ambient": ("conftest", "port_ambient", _rows),
    "_pycodemod_query.py:bindings": ("conftest", "port_bindings", _same),
    "_pycodemod_query.py:funcnames": ("mikemol.pycodemod.funcnames", "funcnames", _rows),
    "_pycodemod_query.py:_generic_func_names": (
        "mikemol.pycodemod.funcnames",
        "generic_names",
        _same,
    ),
    "_pycodemod_query.py:source_of": ("mikemol.pycodemod.definitions", "source_of", _source),
    "_pycodemod_census.py:module_size": ("conftest", "port_module_size", _same),
    "_pycodemod_census.py:module_size_all": ("conftest", "port_module_size_all", _same),
    "_pycodemod_census.py:module_state": ("conftest", "port_module_state", _same),
    "_pycodemod_census.py:crossings": ("conftest", "port_crossings", _same),
    "_pycodemod_census.py:importers": ("mikemol.pycodemod.imports", "importers", _rows),
    "_pycodemod_census.py:aliases": ("mikemol.pycodemod.aliases", "aliases", _rows),
}


class HasValues(Protocol):
    """The port's `Values`: rows of (where, value, context) and the total call count."""

    rows: list[object]
    total: int


def port_values(name: str, kw: str | int, paths: list[str]) -> JSON:
    """Compose the port's `values(scan(paths, name), kw)` into the origin's (rows, total).

    The origin took (name, kw, paths); the port takes a scan narrowed to `name`. A port row's
    `where` carries a column the origin never had, so the row is [path, line, value, context].

    Returns:
        [[[path, line, value, context], ...], total].

    """
    sites = _port("mikemol.pycodemod.sites", "scan")(paths, name)
    got = cast("HasValues", _port("mikemol.pycodemod.arguments", "values")(sites, kw))
    rows: list[JSON] = []
    for row in got.rows:
        where, value, context = cast(
            "tuple[tuple[object, ...], object, object]",
            dataclasses.astuple(cast("DataclassInstance", row)),
        )
        rows.append(
            [normal(where[0], ""), normal(where[1], ""), normal(value, ""), normal(context, "")]
        )
    return [rows, got.total]


class HasDead(Protocol):
    """The port's dead report: the unexcused dead defs, as dataclass rows."""

    dead: list[object]


def _port(module: str, name: str) -> OriginCall:
    return cast("OriginCall", getattr(importlib.import_module(module), name))


def port_dead(paths: list[str]) -> JSON:
    """Compose the port's `dead(scan(paths))`: the origin took paths, the port takes a scan.

    Returns:
        the origin's [path, name, line] per dead def; the port's `exempt` list is not the
        origin's `dead` result, so it is not carried here.

    """
    report = cast(
        "HasDead",
        _port("mikemol.pycodemod.dead", "dead")(_port("mikemol.pycodemod.sites", "scan")(paths)),
    )
    out: list[JSON] = []
    for row in report.dead:
        fields = cast("tuple[object, ...]", dataclasses.astuple(cast("DataclassInstance", row)))
        out.append([normal(f, "") for f in fields])
    return out


class CallgraphCollisionError(ValueError):
    """Two port callers fold onto one origin `stem.scope` key; merging them would hide the split."""


def port_callgraph(paths: list[str]) -> JSON:
    """Compose the port's `callgraph(scan(paths))` into the origin's {"stem.scope": [callees]}.

    The port keys a caller by (file, qualified scope); the origin by basename stem and innermost
    def. The scope is kept as the port spells it (a method reads `K.m`, not `m`), and two files
    sharing a stem REFUSE rather than merge, so the port's finer split is never folded away.

    Returns:
        caller key to sorted callee names.

    Raises:
        CallgraphCollisionError: two port callers map to one origin key.

    """
    graph = cast(
        "dict[tuple[str, str], set[str]]",
        _port("mikemol.pycodemod.graph", "callgraph")(
            _port("mikemol.pycodemod.sites", "scan")(paths)
        ),
    )
    out: dict[str, JSON] = {}
    for (path, scope), callees in sorted(graph.items()):
        key = f"{Path(path).stem}.{scope}"
        if key in out:
            raise CallgraphCollisionError(key)
        out[key] = [normal(c, "") for c in sorted(callees)]
    return out


class HasReach(Protocol):
    """The port's `Reach`: paths found, plus whether the bound cut the walk and the start exists."""

    found: dict[str, list[str]]
    exhausted: bool
    known_start: bool


def port_reaches(
    callgraph_: dict[str, set[str]], start: str, targets: set[str], depth: int = 6
) -> JSON:
    """Run the port's `reaches` over the origin's {"mod.fn": callees} graph, as the origin's paths.

    The origin splits a caller key at its LAST dot into (module, def); the port's caller is
    (file, scope) and same-file is the hop test, so the module stands in for the file. The port's
    trail spells each hop bare (all hops are same-file); the origin module-qualifies every hop but
    the final target, so the module is put back on those. `exhausted` and `known_start` are
    port-only columns the origin never returned, dropped as `_sites` drops `column`.

    Returns:
        {target: [qualified hops..., target]}.

    """
    graph = {tuple(key.rsplit(".", 1)): callees for key, callees in callgraph_.items()}
    mod, fn = start.rsplit(".", 1)
    got = cast(
        "HasReach", _port("mikemol.pycodemod.graph", "reaches")(graph, (mod, fn), targets, depth)
    )
    out: dict[str, JSON] = {}
    for target, trail in got.found.items():
        hops: list[JSON] = [f"{mod}.{hop}" for hop in trail[:-1]]
        hops.append(trail[-1])
        out[target] = hops
    return out


class HasWhere(Protocol):
    """A port `Where`: a call site's path, line and column."""

    path: str
    line: int
    column: int


def _wheres(rows: list[HasWhere]) -> JSON:
    """Drop the port-only column from each site, leaving the origin's [path, line].

    Returns:
        one [path, line] per site, in the port's (sorted) order.

    """
    out: list[JSON] = []
    for w in rows:
        site: list[JSON] = [w.path, w.line]
        out.append(site)
    return out


class HasForwards(Protocol):
    """The port's `Forwards`: passers, lackers, and the `**` calls that cannot tell."""

    passes: list[HasWhere]
    lacks: list[HasWhere]
    cannot_tell: list[HasWhere]


def port_forwards(name: str, kw: str, paths: list[str]) -> JSON:
    """Compose the port's `forwards(scan(paths, name), kw)` into the origin's (has, lacks).

    ⚑ The port's third side, `cannot_tell` (a `**` splat), is the origin's `lacks` misfiled; it
    is APPENDED as a third element, never folded back into `lacks`, so a splat case diverges.

    Returns:
        [has, lacks, cannot_tell], each a list of [path, line].

    """
    sites = _port("mikemol.pycodemod.sites", "scan")(paths, name)
    got = cast("HasForwards", _port("mikemol.pycodemod.arguments", "forwards")(sites, kw))
    return [_wheres(got.passes), _wheres(got.lacks), _wheres(got.cannot_tell)]


class HasAsserted(Protocol):
    """The port's `Asserted`: calls passing the keyword as a literal or a computed value."""

    literal: list[HasWhere]
    computed: list[HasWhere]


def port_asserted(name: str, kw: str, paths: list[str]) -> JSON:
    """Compose the port's `asserted(scan(paths, name), kw)` into the origin's (literal, computed).

    Returns:
        [literal, computed], each a list of [path, line].

    """
    sites = _port("mikemol.pycodemod.sites", "scan")(paths, name)
    got = cast("HasAsserted", _port("mikemol.pycodemod.arguments", "asserted")(sites, kw))
    return [_wheres(got.literal), _wheres(got.computed)]


def port_ambient(paths: list[str]) -> object:
    """Call the port's `ambient(paths, root)` with the root the origin read ambiently (W441).

    The origin resolved its repo subtrees from `_pycodemod_core.ROOT`; the port takes the root as
    a parameter, so the shim passes that same root rather than inventing one. ⚑ The origin also
    unions a hardcoded `_REPO_SUBTREE_FALLBACK` (Substrate, agda, ...) that the port drops on
    purpose as substrate-specific; no case exercises it, so no reshape covers it.

    Returns:
        the port's `Ambient`, whose `rows` are [path, line, kind, verdict, shown, context].

    """
    root = Path(str(cast("Rooted", importlib.import_module("_pycodemod_core")).ROOT))
    return _port("mikemol.pycodemod.ambient", "ambient")(paths, root)


class HasSkipped(Protocol):
    """A port `Found`: its rows, and the files it could not read as `Skip(path, why, error)`."""

    rows: list[object]
    skipped: list[object]


# W439: the port's Skip.why -> the origin's verdict kind, for a file the origin returned as a row.
_VERDICT = {"unparseable": "<syntax-error>", "unreadable": "<unreadable>"}


def port_bindings(name: str, path: str) -> JSON:
    """Compose the port's `bindings([path], name)` into the origin's per-file rows (W439).

    The origin took one path and returned [kind, qualname, line, live_start, live_end]; the port
    takes paths and returns Binding(path, line, kind, qualname, live). ⚑ A file the origin could
    not read or parse came back as ONE verdict row; the port reports it in `skipped` (a failure is
    not a binding). The skip is carried AS that verdict row, its kind from `why` and its error
    text kept, so the failure is relocated to where the origin's spec reads it, never dropped.

    Returns:
        the origin's rows, or its single verdict row for a skipped file.

    """
    found = cast("HasSkipped", _port("mikemol.pycodemod.definitions", "bindings")([path], name))
    out: list[JSON] = []
    for skip in found.skipped:
        _where, why, error = cast(
            "tuple[str, str, str]", dataclasses.astuple(cast("DataclassInstance", skip))
        )
        out.append([_VERDICT.get(why, f"<{why}>"), error, 0, 0, 0])
    for row in found.rows:
        _where, line, kind, qualname, live = cast(
            "tuple[str, int, str, str, tuple[int, int]]",
            dataclasses.astuple(cast("DataclassInstance", row)),
        )
        out.append([kind, qualname, line, live[0], live[1]])
    return out


def _fields(row: object) -> tuple[object, ...]:
    return cast("tuple[object, ...]", dataclasses.astuple(cast("DataclassInstance", row)))


def port_module_size_all(paths: list[str], threshold: int) -> JSON:
    """Compose the port's `module_sizes(paths, threshold)` into the origin's (rows, n).

    The port's `Size` is (path, code, physical, defs, entrypoints, cap, incidents, why); the
    origin's row is (path, code, defs, len(entrypoints), "; ".join(why), cap, incidents,
    physical). The incident map is the caller's in the port; the origin's own map names only
    substrate files, which no fixture path matches, so none is passed. n is every path given,
    the origin's len(files) (an unread file is counted there, and a `skipped` row here).

    Returns:
        [[row, ...], n].

    """
    got = cast("HasRows", _port("mikemol.pycodemod.size", "module_sizes")(paths, threshold))
    rows: list[JSON] = []
    for row in got.rows:
        path, code, physical, defs, entry, cap, hits, why = _fields(row)
        reason = "; ".join(cast("tuple[str, ...]", why))
        size = len(cast("tuple[int, ...]", entry))
        rows.append([normal(v, "") for v in (path, code, defs, size, reason, cap, hits, physical)])
    return [rows, len(paths)]


def port_module_size(paths: list[str], threshold: int) -> JSON:
    """Filter `port_module_size_all` as the origin's `module_size` does: rows with a why, r[:5].

    Returns:
        [[row[:5], ...], n].

    """
    every = cast("list[list[JSON]]", port_module_size_all(paths, threshold))
    rows = cast("list[list[JSON]]", every[0])
    return [[row[:5] for row in rows if row[4]], every[1]]


def port_module_state(paths: list[str]) -> JSON:
    """Reorder the port's `ModuleState` rows to the origin's (path, name, line, ...) order.

    The origin sorted its tuples, so by (path, name); n is every path given (origin len(files)).
    Rows are sorted on (path, name, port position): the position is unique, so the comparison
    never reaches the row itself, and ties keep the port's line order.

    Returns:
        [[[path, name, line, class, mutators, kind], ...], n].

    """
    got = cast("HasRows", _port("mikemol.pycodemod.modstate", "module_state")(paths))
    keyed: list[tuple[str, str, int, JSON]] = []
    for i, row in enumerate(got.rows):
        path, line, name, klass, muts, kind = _fields(row)
        keyed.append(
            (
                str(path),
                str(name),
                i,
                [normal(v, "") for v in (path, name, line, klass, muts, kind)],
            )
        )
    return [[r for _p, _n, _i, r in sorted(keyed)], len(paths)]


# the origin's own corpus authorities beyond the port's generic CORPUS_AUTHORITIES
# (an operand in the port)
ORIGIN_AUTHORITIES = ("agda_files", "py_files")


def port_crossings(paths: list[str]) -> JSON:
    """Reorder the port's `Crossing` (path, line, function, klass, what) to the origin's row.

    The origin yielded (path, def, line, klass, ", ".join(what)).

    Returns:
        one [path, def, line, klass, what] per crossing.

    """
    got = cast(
        "HasRows", _port("mikemol.pycodemod.crossings", "crossings")(paths, ORIGIN_AUTHORITIES)
    )
    out: list[JSON] = []
    for row in got.rows:
        path, line, function, klass, what = _fields(row)
        joined = ", ".join(cast("tuple[str, ...]", what))
        out.append([normal(v, "") for v in (path, function, line, klass, joined)])
    return out


# W435: origin callees the port deliberately does not carry, with the reason. A capture can hold
# such a call beside the one its spec reads; it yields a visible marker in its slot, so a rule that
# does read it denies rather than passing. pytestspec's do-not-port deselects a whole CASE, which is
# the wrong grain when the case's own call is ported.
NOT_PORTED: dict[str, str] = {
    "_pycodemod_sql.py:pg_probe_status": "a live postgres reachability probe, not a code query",
}


def subject(fixture: object, operands: object) -> object:
    """Run the PORT on the case's fixture: same rehome, binding and args as `reference`.

    Returns:
        the reshaped, JSON-normalized result of each call, in order.

    Raises:
        SubjectGapError: a callee has no port counterpart registered.

    """
    captured = calls(operands)
    old, new = rehome(
        str_map(fixture, "fixture"), [raw for _fn, args in captured for raw in args.values()]
    )
    out: list[JSON] = []
    for fn, args in captured:
        if fn in NOT_PORTED:
            out.append({"not-ported": NOT_PORTED[fn]})
            continue
        if fn not in SUBJECT:
            msg = f"no port counterpart registered for {fn} (W208)"
            raise SubjectGapError(msg)
        module, name, reshape = SUBJECT[fn]
        func = cast("OriginCall", getattr(importlib.import_module(module), name))
        positional, keyword = bind(func, {k: parse(v, old, new) for k, v in args.items()})
        out.append(normal(reshape(func(*positional, **keyword)), new))
    return out


def pytest_spec_implementations() -> dict[str, Adapter]:
    """Offer the origin as `--impl reference` and the mtools port as `--impl subject`.

    Returns:
        the adapters this directory registers.

    """
    return {"reference": reference, "subject": subject}


def corpus_digest() -> str:
    """Hash every file the origin's default corpus walk reads, by path and content.

    W229: `py_files()` with no roots is the corpus resorts and its peers walk, and it holds the
    origin modules themselves, so this one digest covers both. It is computed once per session:
    a corpus edited mid-session is not seen until the next one.

    Returns:
        a hex digest.

    """
    if "corpus" not in _DIGEST:
        core = importlib.import_module("_pycodemod_core")
        walk = cast("Callable[[], list[str]]", core.py_files)
        digest = hashlib.sha256()
        for path in sorted(walk()):
            digest.update(path.encode())
            digest.update(b"\0")
            digest.update(Path(path).read_bytes())
            digest.update(b"\0")
        _DIGEST["corpus"] = digest.hexdigest()
    return _DIGEST["corpus"]


def cache_key(case: dict[str, object]) -> str | None:
    """Key a case's `reference` result on everything the origin reads.

    Returns:
        a hash of the fixture, the operands, the Python version and the corpus digest; None
        when the case calls an uncacheable callee.

    """
    ops = calls(case.get("operands"))
    if any(fn in UNCACHEABLE for fn, _ in ops):
        return None
    parts: dict[str, object] = {
        "fixture": str_map(case.get("fixture"), "fixture"),
        "operands": [[fn, args] for fn, args in ops],
        "python": sys.version,
        "corpus": corpus_digest(),
    }
    return hashlib.sha256(json.dumps(parts, sort_keys=True).encode()).hexdigest()


def pytest_spec_cache_key(impl: str, case: dict[str, object]) -> str | None:
    """Vouch for a `reference` result's key; no other implementation is keyed here.

    Returns:
        the case's key, or None.

    """
    return cache_key(case) if impl == "reference" else None
