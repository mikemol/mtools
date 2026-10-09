# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""`orempty`: `cast("Json", X or {})` and its kin become a project's typed narrowing helpers.

⚑⚑ A LITERAL `{}` OR `[]` NEXT TO `or` IS INFERRED `dict[Any, Any]` / `list[Any]`, which a house
that forbids Any expressions refuses at every site, and a `cast` around it does not help: the Any
is INSIDE the cast's operand. The fix is the same each time and provable from the text alone:

    cast("Json", X or {})              ->  as_object(X)
    cast("dict[str, object]", X or {}) ->  as_object(X)
    cast("list[object]", X or [])      ->  as_list(X)
    cast("list[Json]", X or [])        ->  a comprehension over as_list(X) calling as_object

`as_object` and `as_list` are the project's own helpers (luthen's `checks.jsonio` is the model: a
non-dict is an empty object, a non-list an empty list), named by the caller; this module knows the
shapes and nothing about whose helpers they are.

⚑ ANYTHING ELSE IS LEFT ALONE: a cast to another type (`dict[str, str]` needs the values narrowed,
not just the container) is not a site here. Each rewrite adds one `from <module> import <names>`
statement; the project's own import sorter merges it, and an unused `cast` import is the linter's
to drop (the judge runs both).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import libcst as cst
from libcst import matchers as m

if TYPE_CHECKING:
    from collections.abc import Sequence

type Found = dict[str, cst.CSTNode | Sequence[cst.CSTNode]]
type Replacement = cst.MaybeSentinel | cst.RemovalSentinel | cst.CSTNode

OBJECT_TYPES = frozenset({"Json", "dict[str, object]"})
LIST_TYPES = frozenset({"list[object]"})
JSON_LIST = "list[Json]"
EACH = "each"

CAST_OR_EMPTY = m.Call(
    func=m.Name("cast"),
    args=[
        m.Arg(value=m.SaveMatchedNode(m.SimpleString(), "kind")),
        m.Arg(
            value=m.BooleanOperation(
                left=m.SaveMatchedNode(m.DoNotCare(), "left"),
                operator=m.Or(),
                right=m.SaveMatchedNode(m.Dict(elements=[]) | m.List(elements=[]), "empty"),
            )
        ),
    ],
)


@dataclass(frozen=True, slots=True)
class Helpers:
    """Where the narrowing helpers live and what they are called."""

    module: str
    object_fn: str = "as_object"
    list_fn: str = "as_list"


@dataclass(frozen=True, slots=True)
class Planned:
    """The rewritten text, how many sites changed, and which helpers it now needs."""

    text: str
    sites: int
    needs: tuple[str, ...]


def _call(name: str, arg: cst.BaseExpression) -> cst.Call:
    return cst.Call(func=cst.Name(name), args=[cst.Arg(arg)])


@dataclass(slots=True)
class _Rewriter:
    """Build each replacement and remember which helpers the result calls."""

    helpers: Helpers
    sites: int = 0
    needs: set[str] = field(default_factory=set)

    def _comprehension(self, left: cst.BaseExpression) -> cst.ListComp:
        h = self.helpers
        loop = cst.CompFor(target=cst.Name(EACH), iter=_call(h.list_fn, left))
        return cst.ListComp(elt=_call(h.object_fn, cst.Name(EACH)), for_in=loop)

    def _build(
        self, kind: str, empty: cst.CSTNode, left: cst.BaseExpression
    ) -> cst.BaseExpression | None:
        h = self.helpers
        if kind in OBJECT_TYPES and isinstance(empty, cst.Dict):
            self.needs.add(h.object_fn)
            return _call(h.object_fn, left)
        if kind in LIST_TYPES and isinstance(empty, cst.List):
            self.needs.add(h.list_fn)
            return _call(h.list_fn, left)
        if kind == JSON_LIST and isinstance(empty, cst.List):
            self.needs.update((h.object_fn, h.list_fn))
            return self._comprehension(left)
        return None

    def __call__(self, node: cst.CSTNode, found: Found) -> Replacement:
        """Rewrite one matched cast, or leave it when its type and its literal disagree.

        Returns:
            the replacement expression, or `node` itself unchanged.

        """
        kind, left, empty = found["kind"], found["left"], found["empty"]
        if not (
            isinstance(kind, cst.SimpleString)
            and isinstance(left, cst.BaseExpression)
            and isinstance(empty, cst.CSTNode)
        ):
            return node
        built = self._build(str(kind.evaluated_value), empty, left)
        if built is None:
            return node
        self.sites += 1
        return built


def _anchor(body: Sequence[cst.SimpleStatementLine | cst.BaseCompoundStatement]) -> int:
    # The index of the last top-level import statement, or -1 when there is none.
    imports = m.SimpleStatementLine(body=[m.ImportFrom() | m.Import()])
    return max((i for i, stmt in enumerate(body) if m.matches(stmt, imports)), default=-1)


def plan(text: str, helpers: Helpers) -> Planned:
    """Rewrite every matching cast in `text` and add the import its helpers need.

    Returns:
        the Planned text; sites is 0 (and the text unchanged) when nothing matched.

    """
    rewriter = _Rewriter(helpers)

    def replacement(node: cst.CSTNode, found: Found) -> Replacement:
        # libcst treats only a plain function as a replacement callback, never a callable object.
        return rewriter(node, found)

    changed = m.replace(cst.parse_module(text), CAST_OR_EMPTY, replacement)
    if not rewriter.sites or not isinstance(changed, cst.Module):
        return Planned(text, 0, ())
    needs = tuple(sorted(rewriter.needs))
    statement = cst.parse_module(f"from {helpers.module} import {', '.join(needs)}\n").body[0]
    body = list(changed.body)
    body.insert(_anchor(body) + 1, statement)
    return Planned(changed.with_changes(body=body).code, rewriter.sites, needs)
