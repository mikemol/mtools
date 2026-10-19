# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W1515: narrow a parameter's annotation from what the body does with it, not from callers.

    uses = uses_of(source)            # {"Class.method": {"param": Use(keys=, attrs=, ...)}}
    narrow(uses["f"]["cfg"])          # Narrowed(kind="typeddict", detail=("name", "size"))

⚑ THE TRACED TYPE IS THE BROAD ONE (el-openglo via github-8f, 2026-10-18): what callers passed
(`observed`, W1514) is a bare `ndarray` or a `dict[str, int | str]`, and the house mypy flags need
the narrow forms, a `TypedDict`, an `NDArray`, a `Protocol`. monkeytype on el-openglo's worst file
took 965 house findings to 866 because of exactly that. The body says what the value must support,
so this reads the body and prefers it to the traced type.

⚑ WHAT THE BODY DOES, AND THE FORM THAT FOLLOWS, IN THIS ORDER:

    constant string keys subscripted        TypedDict of those keys (dict methods alone allowed)
    array attributes (shape, dtype, ...)    NDArray
    any other attribute read or called      Protocol of those names
    dict methods alone                      Mapping
    called as a function                    Callable
    indexed, iterated or sized              Sequence, Iterable or Sized
    none of these                           unconstrained, so the traced type is kept

⚑ A PARAMETER IS NEVER NARROWED PAST WHAT THE BODY SHOWS: a name used only as an operand (`n + 1`)
is `unconstrained`, and the caller keeps the observed type rather than a guess. This module states a
form; whether it lowers the house mypy count is W1516's measurement, and a file whose count does
not fall is not rewritten.

`self` and `cls` are skipped; a nested function's own parameters are its own.
"""

import ast
from dataclasses import dataclass, field

_SKIPPED = frozenset({"self", "cls"})
_MAPPING_METHODS = frozenset({"get", "items", "keys", "values", "setdefault", "update", "pop"})
_ARRAY_ATTRS = frozenset(
    {
        "shape",
        "dtype",
        "ndim",
        "size",
        "T",
        "reshape",
        "astype",
        "sum",
        "mean",
        "min",
        "max",
        "flatten",
        "ravel",
        "transpose",
        "tolist",
        "argmax",
        "argmin",
        "any",
        "all",
        "copy",
        "view",
    }
)


@dataclass
class Use:
    """What one function's body does with one parameter."""

    keys: set[str] = field(default_factory=set)
    attrs: set[str] = field(default_factory=set)
    called: bool = False
    iterated: bool = False
    indexed: bool = False
    sized: bool = False


@dataclass(frozen=True)
class Narrowed:
    """The form the body supports, and the names that form carries."""

    kind: str
    detail: tuple[str, ...] = ()


def narrow(use: Use) -> Narrowed:
    """Name the narrowest form the observed uses support.

    Returns:
        the form; `unconstrained` when the body shows nothing about the value.

    """
    keyed = bool(use.keys) and use.attrs <= _MAPPING_METHODS
    rules = (
        (keyed, Narrowed("typeddict", tuple(sorted(use.keys)))),
        (bool(use.attrs & _ARRAY_ATTRS), Narrowed("ndarray")),
        (bool(use.attrs - _MAPPING_METHODS), Narrowed("protocol", tuple(sorted(use.attrs)))),
        (bool(use.attrs), Narrowed("mapping")),
        (use.called, Narrowed("callable")),
        (use.indexed, Narrowed("sequence")),
        (use.iterated, Narrowed("iterable")),
        (use.sized, Narrowed("sized")),
    )
    return next((form for fits, form in rules if fits), Narrowed("unconstrained"))


def _names(args: ast.arguments) -> list[str]:
    every = [*args.posonlyargs, *args.args, *args.kwonlyargs]
    every += [a for a in (args.vararg, args.kwarg) if a is not None]
    return [a.arg for a in every]


class _Walker(ast.NodeVisitor):
    """Collect each function's per-parameter uses, keyed by qualified name."""

    def __init__(self) -> None:
        self.found: dict[str, dict[str, Use]] = {}
        self._scope: list[str] = []
        self._uses: list[dict[str, Use]] = []

    def _function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        names = [n for n in _names(node.args) if n not in _SKIPPED]
        self._uses.append({n: Use() for n in names})
        self._scope.append(node.name)
        self.generic_visit(node)
        self._scope.pop()
        self.found[".".join([*self._scope, node.name])] = self._uses.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._function(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._scope.append(node.name)
        self.generic_visit(node)
        self._scope.pop()

    def _use(self, node: ast.expr) -> Use | None:
        if isinstance(node, ast.Name) and self._uses:
            return self._uses[-1].get(node.id)
        return None

    def visit_Subscript(self, node: ast.Subscript) -> None:
        use = self._use(node.value)
        if use is not None:
            key = node.slice
            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                use.keys.add(key.value)
            else:
                use.indexed = True
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        use = self._use(node.value)
        if use is not None:
            use.attrs.add(node.attr)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        use = self._use(node.func)
        if use is not None:
            use.called = True
        if isinstance(node.func, ast.Name) and node.func.id == "len" and node.args:
            sized = self._use(node.args[0])
            if sized is not None:
                sized.sized = True
        self.generic_visit(node)

    def _iterated(self, node: ast.expr) -> None:
        use = self._use(node)
        if use is not None:
            use.iterated = True

    def visit_For(self, node: ast.For) -> None:
        self._iterated(node.iter)
        self.generic_visit(node)

    def visit_comprehension(self, node: ast.comprehension) -> None:
        self._iterated(node.iter)
        self.generic_visit(node)


def uses_of(source: str) -> dict[str, dict[str, Use]]:
    """Read what every function of a module's source does with each of its parameters.

    Returns:
        qualified function name mapped to parameter name mapped to its uses.

    """
    walker = _Walker()
    walker.visit(ast.parse(source))
    return walker.found
