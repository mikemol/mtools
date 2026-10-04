# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The pure perturbation leaf: given a .py source and a mutation SPEC, emit the perturbed source.

Ported from paperkit's `paperkit/mutate.py` (mtools:W556). A perturbation TOGGLES an element's
PRESENCE between the actual source and a nearby counterfactual: drop the present, inject the absent.

    ""                the IDENTITY: byte-identical, the baseline point of the mutation set. An eval
                      against it measures the UNMUTATED check in the same sandbox.
    <qualname>        DROP a def's BEHAVIOUR: its body becomes an uncatchable raise, the rest
    or  def:<qn>      byte-identical, so a witness flips only if it EXERCISES that def.
    branch:<qn>#<n>   DROP one BRANCH ARM's behaviour: the arm's body becomes the SAME uncatchable
                      raise. A finer, still MONOTONE atom than def:. An arm enclosed by an
                      `except BaseException` or bare `except:` handler is REFUSED (the raise would
                      be swallowed, so the mutation would not be monotone): see branch_sites.
    flip:<qn>#<n>     INVERT one CONDITION (`if C` becomes `if not (C)`). NON-monotone: a
                      wrong-but-non-crashing value flips only if the witness ASSERTS on it.
    data-:<name>#<n>  DROP one KEY or ELEMENT of a module-level dict, list, set or tuple LITERAL.
                      Monotone like def: and branch:. A dict read ONLY via `.get(k, DEFAULT)` or
                      `except KeyError` is REFUSED (the default swallows the drop).
    dflip:<name>#<n>  PERTURB one VALUE of a dict value or list element to a counterfactual (a
                      valid-enum sibling where the literal has a finite value domain, else a
                      distinct marker). NON-monotone. A consumer never asks it of a bare set
                      membership.
    import-:<name>    DROP `import <name>` or `from <name> import ...` (present becomes absent).
    import+:<name>    INJECT `import <name>` (absent becomes present), the NEGATIVE polarity that
                      falsifies a "module does NOT import X" assertion.
    regex:<name>|<pattern>|<replacement>|<scope>
                      the OPEN operator of `mikemol.mutation.regexop`, as one string. `|` separates
                      the four fields (all four always present); inside a field `%7C` is a literal
                      `|` and `%25` a literal `%`, any other `%` is REFUSED. <scope> is empty (whole
                      file), `def=<qualname>` or `lines=<a>-<b>`. A regex matching nothing is an
                      UnappliedError (a KeyError).

The mechanical AST surgery ONLY, not the sensitivity interpretation. A spec that names no such
element is LOUD (a KeyError): a real miss is never a silent no-op. CLI:
`mikemol-mutate <module.py> <spec>` prints the perturbed module to stdout.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from mikemol.mutation import regexop

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

type FuncNode = ast.FunctionDef | ast.AsyncFunctionDef
type Literal = ast.Dict | ast.List | ast.Set | ast.Tuple
type DefSite = tuple[str, FuncNode]
type BranchSite = tuple[str, int, tuple[ast.stmt, ast.stmt]]
type FlipSite = tuple[str, int, ast.expr]
type DataSite = tuple[str, int, str, ast.expr | None, ast.expr]

_RAISE = "raise BaseException('PAPERKIT_MUT')\n"
_MARKER = '"PAPERKIT_PERTURB"'
_GET_WITH_DEFAULT = 2  # `<name>.get(key, DEFAULT)`: two arguments carry a default
_ARGC = 2  # the command line is exactly `<module.py> <spec>`
_USAGE = "usage: mikemol-mutate <module.py> <spec>\n"


class Bodied(Protocol):
    """What `mutate_lines` needs of a node: a body whose span ends at `end_lineno`."""

    body: list[ast.stmt]
    end_lineno: int | None


def _end_line(node: ast.stmt | ast.expr) -> int:
    """Return the last line of a parsed node (a parsed node always carries one).

    Returns:
        The node's end line.

    """
    return node.end_lineno or node.lineno


def _end_col(node: ast.stmt | ast.expr) -> int:
    """Return the end column of a parsed node (a parsed node always carries one).

    Returns:
        The node's end column.

    """
    return node.end_col_offset or 0


def _const_value(node: ast.Constant) -> object:
    """Return the value of a constant node, typed `object` so no `Any` escapes into callers.

    Returns:
        The constant's value.

    """
    value: object = node.value
    return value


def _is_str_const(node: ast.expr) -> bool:
    """Say whether the node is a string literal.

    Returns:
        True for a string constant.

    """
    return isinstance(node, ast.Constant) and isinstance(_const_value(node), str)


def def_sites(text: str) -> list[DefSite]:
    """Return every def or method in a .py source as (qualname, node), in source order.

    Mutation resolution for CODE is the DEFINITION, not the file: corrupting a whole file breaks
    its import and flips every witness identically; replacing one function's BODY leaves the
    module importable, so a witness flips only if it exercises that function. A one-liner
    (`def f(): return 1`) shares its signature line with the body, so a line-span replacement
    cannot isolate the body: it is skipped.

    Returns:
        The (qualname, node) pairs, empty when the source does not parse.

    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    out: list[DefSite] = []

    def rec(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
                if child.body[0].lineno > child.lineno:
                    out.append((prefix + child.name, child))
                rec(child, prefix + child.name + ".")
            elif isinstance(child, ast.ClassDef):
                rec(child, prefix + child.name + ".")
            else:
                rec(child, prefix)

    rec(tree, "")
    return out


def _base_catching_regions(tree: ast.AST) -> set[ast.AST]:
    """Return the AST nodes living in a `try` BODY whose handlers catch BaseException.

    A bare `except:` counts. A raise planted anywhere in such a region would be SWALLOWED, so a
    branch mutation there is non-monotone and must be refused. Intra-def only: a dynamic catcher
    (a suppress context manager, or a caller-frame handler outside the def) is invisible here.

    Returns:
        The protected nodes.

    """
    unsafe: set[ast.AST] = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Try) and any(
            h.type is None or (isinstance(h.type, ast.Name) and h.type.id == "BaseException")
            for h in n.handlers
        ):
            for stmt in n.body:
                unsafe.update(ast.walk(stmt))
    return unsafe


def _arms(stmt: ast.AST) -> list[list[ast.stmt]]:
    """Return the mutable sub-bodies of a compound statement.

    Returns:
        The bodies, empty for a statement with no arms.

    """
    if isinstance(stmt, ast.If):
        return [stmt.body, stmt.orelse]
    if isinstance(stmt, (ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith)):
        return [stmt.body]
    if isinstance(stmt, ast.Try):
        return [stmt.body, *(h.body for h in stmt.handlers), stmt.orelse, stmt.finalbody]
    return []


def branch_sites(text: str) -> list[BranchSite]:
    """Return every mutable BRANCH ARM as (qualname, n, (first_stmt, last_stmt)).

    The arms of `if/elif/else`, `for` and `while` bodies, `try` bodies and handlers, and `with`
    bodies, WITHIN each def, numbered `#n` per def in stable source order. Each arm's body becomes
    the same uncatchable raise as def:, so a witness flips only if it REACHES that arm. REFUSES an
    arm inside a BaseException-catching region (the raise would be swallowed).

    Returns:
        The sites, empty when the source does not parse.

    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    unsafe = _base_catching_regions(tree)
    out: list[BranchSite] = []

    def rec(node: ast.AST, prefix: str, counter: list[int]) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
                rec(child, prefix + child.name + ".", [0])
            elif isinstance(child, ast.ClassDef):
                rec(child, prefix + child.name + ".", counter)
            else:
                arms = _arms(child) if prefix else []
                for body in arms:
                    if body and body[0] not in unsafe:
                        out.append((prefix.rstrip("."), counter[0], (body[0], body[-1])))
                        counter[0] += 1
                rec(child, prefix, counter)

    rec(tree, "", [0])
    return out


def flip_sites(text: str) -> list[FlipSite]:
    """Return every mutable CONDITION as (qualname, n, test_node): the test of each `if`/`while`.

    Numbered `#n` per def in stable source order. A flip INVERTS the condition, which is
    non-monotone, so this is a SEPARATE generator from branch_sites.

    Returns:
        The sites, empty when the source does not parse.

    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    out: list[FlipSite] = []

    def rec(node: ast.AST, prefix: str, counter: list[int]) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
                rec(child, prefix + child.name + ".", [0])
            elif isinstance(child, ast.ClassDef):
                rec(child, prefix + child.name + ".", counter)
            else:
                if prefix and isinstance(child, ast.If | ast.While):
                    out.append((prefix.rstrip("."), counter[0], child.test))
                    counter[0] += 1
                rec(child, prefix, counter)

    rec(tree, "", [0])
    return out


def _split_qn_n(arg: str) -> tuple[str, int]:
    """Split `<qualname>#<n>`: the finer atoms address a site WITHIN a def.

    Returns:
        The qualname and the integer index.

    """
    qn, _, n = arg.rpartition("#")
    return qn, int(n)


def _mutate_branch(text: str, arg: str) -> str:
    """Drop one branch arm's behaviour: its body becomes the uncatchable raise.

    Returns:
        The perturbed source.

    Raises:
        KeyError: when `arg` (`<qualname>#<n>`) is not a branch-arm site.

    """
    qualname, n = _split_qn_n(arg)
    for qn, i, (b0, blast) in branch_sites(text):
        if qn == qualname and i == n:
            lines = text.splitlines(keepends=True)
            lines[b0.lineno - 1 : _end_line(blast)] = [" " * b0.col_offset + _RAISE]
            return "".join(lines)
    msg = f"mutant: 'branch:{qualname}#{n}' is not a branch-arm site in the module"
    raise KeyError(msg)


def flip_condition(text: str, qualname: str, n: int) -> str:
    """Invert one condition, `if C:` becoming `if not (C):`, by a span rewrite of its source.

    Never routed through `mutate_lines`: a value swap is not a raise, and is non-monotone.

    Returns:
        The perturbed source.

    Raises:
        KeyError: when the site does not exist or has no recoverable source span.

    """
    for qn, i, test in flip_sites(text):
        if qn == qualname and i == n:
            src = ast.get_source_segment(text, test)
            if src is None:
                msg = f"mutant: 'flip:{qualname}#{n}' has no recoverable source span"
                raise KeyError(msg)
            lines = text.splitlines(keepends=True)
            first, last = test.lineno, _end_line(test)
            head = lines[first - 1][: test.col_offset]
            tail = lines[last - 1][_end_col(test) :]
            lines[first - 1 : last] = [head + "not (" + src + ")" + tail]
            return "".join(lines)
    msg = f"mutant: 'flip:{qualname}#{n}' is not a condition site in the module"
    raise KeyError(msg)


def _op_flip(text: str, arg: str) -> str:
    """Apply the `flip:` operator: parse `<qualname>#<n>` and invert that condition.

    Returns:
        The perturbed source.

    """
    return flip_condition(text, *_split_qn_n(arg))


def _get_swallowed(node: ast.AST) -> set[str]:
    """Name a dict read as `<name>.get(key, DEFAULT)`, which hides a dropped key.

    Returns:
        The one name, or nothing when the node is no such call.

    """
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "get"
        and isinstance(node.func.value, ast.Name)
        and len(node.args) >= _GET_WITH_DEFAULT
    ):
        return {node.func.value.id}
    return set()


def _handler_names(handler: ast.ExceptHandler) -> list[ast.expr]:
    """Return the exception expressions a handler names (a tuple spreads, bare names none).

    Returns:
        The named exception expressions.

    """
    if isinstance(handler.type, ast.Name):
        return [handler.type]
    if isinstance(handler.type, ast.Tuple):
        return list(handler.type.elts)
    return []


def _keyerror_swallowed(node: ast.AST) -> set[str]:
    """Name the subscripted dicts in a `try` body whose handler recovers from a KeyError.

    Returns:
        The names, empty when the node is no such `try`.

    """
    if not isinstance(node, ast.Try) or not any(
        isinstance(t, ast.Name) and t.id == "KeyError"
        for h in node.handlers
        for t in _handler_names(h)
    ):
        return set()
    return {
        d.value.id
        for stmt in node.body
        for d in ast.walk(stmt)
        if isinstance(d, ast.Subscript) and isinstance(d.value, ast.Name)
    }


def _swallowing_dicts(tree: ast.AST) -> set[str]:
    """Return the names of module-level dicts read in a way that would SWALLOW a dropped key.

    Any access `<name>.get(k, DEFAULT)` with a real default, or a `try: <name>[k]` guarded by
    `except KeyError`. A data- DROP of such a dict is non-monotone, so its sites are REFUSED.
    Static and conservative: a dynamic access is invisible here.

    Returns:
        The names whose sites must be refused.

    """
    unsafe: set[str] = set()
    for n in ast.walk(tree):
        unsafe |= _get_swallowed(n)
        unsafe |= _keyerror_swallowed(n)
    return unsafe


def _data_assigns(tree: ast.Module) -> list[tuple[str, Literal]]:
    """Return every module-level `<NAME> = <dict/list/set/tuple literal>` as (name, node).

    Only a single Name target: a tuple-unpack, attribute or subscript target has no stable name.

    Returns:
        The (name, literal node) pairs in source order.

    """
    out: list[tuple[str, Literal]] = []
    for stmt in tree.body:
        if (
            isinstance(stmt, ast.Assign)
            and len(stmt.targets) == 1
            and isinstance(stmt.targets[0], ast.Name)
        ):
            name, v = stmt.targets[0].id, stmt.value
        elif (
            isinstance(stmt, ast.AnnAssign)
            and isinstance(stmt.target, ast.Name)
            and stmt.value is not None
        ):
            name, v = stmt.target.id, stmt.value
        else:
            continue
        if isinstance(v, (ast.Dict, ast.List, ast.Set, ast.Tuple)):
            out.append((name, v))
    return out


def data_sites(text: str) -> list[DataSite]:
    """Return every mutable DATA site as (qualname, n, kind, key_node or None, value_node).

    Each top-level key or element of a module-level dict, list, set or tuple literal, numbered
    `#n` in stable source order. A dict whose reads swallow a dropped key (`.get(k, DEFAULT)` or
    `except KeyError`) is REFUSED, the precondition that keeps data- monotone.

    Returns:
        The sites, empty when the source does not parse.

    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    unsafe = _swallowing_dicts(tree)
    out: list[DataSite] = []
    for name, v in _data_assigns(tree):
        if name in unsafe:
            continue
        if isinstance(v, ast.Dict):
            out.extend(
                (name, i, "dict", k, val)
                for i, (k, val) in enumerate(zip(v.keys, v.values, strict=True))
                if k is not None
            )
        else:
            out.extend((name, i, type(v).__name__, None, el) for i, el in enumerate(v.elts))
    return out


def _splice(text: str, start_node: ast.expr, end_node: ast.expr, replacement: str) -> str:
    """Replace the source span from start_node's start to end_node's end with `replacement`.

    Returns:
        The spliced source.

    """
    lines = text.splitlines(keepends=True)
    head = lines[start_node.lineno - 1][: start_node.col_offset]
    prefix = "".join(lines[: start_node.lineno - 1]) + head
    last = _end_line(end_node)
    suffix = lines[last - 1][_end_col(end_node) :] + "".join(lines[last:])
    return prefix + replacement + suffix


def _rebuild(lit: Literal, drop: set[int]) -> str:
    """Render the literal rebuilt from the entries whose index is not in `drop`.

    Rebuilding keeps the literal PARSEABLE and its TYPE intact (a 1-element tuple keeps its comma,
    an empty set is `set()`), which a byte-minimal comma splice cannot guarantee.

    Returns:
        The rebuilt literal's source.

    """
    if isinstance(lit, ast.Dict):
        keep: ast.expr = ast.Dict(
            keys=[k for j, k in enumerate(lit.keys) if j not in drop],
            values=[v for j, v in enumerate(lit.values) if j not in drop],
        )
    else:
        elts = [e for j, e in enumerate(lit.elts) if j not in drop]
        if isinstance(lit, ast.Set):
            if not elts:
                return "set()"
            keep = ast.Set(elts=elts)
        elif isinstance(lit, ast.List):
            keep = ast.List(elts=elts)
        else:
            keep = ast.Tuple(elts=elts)
    return ast.unparse(ast.fix_missing_locations(keep))


def _drop_data(text: str, arg: str) -> str:
    """Drop one key or element of a module-level literal, keeping it PARSEABLE and its TYPE.

    Rebuilds ONLY the affected literal from the surviving entries, so a source-grep witness over
    an UNRELATED literal never flips.

    Returns:
        The perturbed source.

    Raises:
        KeyError: when `arg` (`<name>#<n>`) is not a data site.

    """
    qualname, n = _split_qn_n(arg)
    for name, i, _kind, _k, _val in data_sites(text):
        if name == qualname and i == n:
            lit = next(v for nm, v in _data_assigns(ast.parse(text)) if nm == qualname)
            dropped = _splice(text, lit, lit, _rebuild(lit, {i}))
            ast.parse(dropped)
            return dropped
    msg = f"mutant: 'data-:{qualname}#{n}' is not a data site in the module"
    raise KeyError(msg)


def _edit_line(edit: tuple[Literal, str]) -> int:
    """Return the start line of the literal an edit rebuilds.

    Returns:
        The literal's first line.

    """
    return edit[0].lineno


def drop_data_multi(text: str, specs: list[str]) -> str:
    """Drop several keys or elements at once, COMPOSITION-SAFE.

    A sequential spec-by-spec drop renumbers a literal as it goes, so a group listing several
    indices of ONE literal would lose the later ones. This resolves every (name, index) against
    the ORIGINAL text once and rebuilds each affected literal in a single pass.

    Returns:
        The perturbed source.

    Raises:
        KeyError: when a spec names no data literal or an index out of range.

    """
    by_qn: dict[str, set[int]] = {}
    for spec in specs:
        qn, n = _split_qn_n(spec.removeprefix("data-:"))
        by_qn.setdefault(qn, set()).add(n)
    tree = ast.parse(text)
    assigns = dict(_data_assigns(tree))
    edits: list[tuple[Literal, str]] = []
    for qn, drop_idx in by_qn.items():
        lit = assigns.get(qn)
        if lit is None:
            msg = f"mutant: 'data-:{qn}' is not a data literal in the module"
            raise KeyError(msg)
        count = len(lit.keys) if isinstance(lit, ast.Dict) else len(lit.elts)
        if any(i >= count for i in drop_idx):
            msg = f"mutant: 'data-:{qn}#{max(drop_idx)}' index out of range"
            raise KeyError(msg)
        edits.append((lit, _rebuild(lit, drop_idx)))
    # Reverse source order, so an earlier splice does not invalidate a later node's span.
    for lit, rendered in sorted(edits, key=_edit_line, reverse=True):
        text = _splice(text, lit, lit, rendered)
    ast.parse(text)
    return text


def _leaf_path(entry_value: ast.expr, leaf: ast.expr) -> tuple[int, ...] | None:
    """Return the INDEX-PATH from an entry's value node down to `leaf`, or None if unreachable.

    `()` means the value IS the leaf, `(0,)` the first element of a tuple or list value, `(0, 1)`
    a nested one. A dict-valued position has no positional index.

    Returns:
        The path, or None.

    """
    if entry_value is leaf:
        return ()
    if isinstance(entry_value, ast.Tuple | ast.List):
        for i, el in enumerate(entry_value.elts):
            sub = _leaf_path(el, leaf)
            if sub is not None:
                return (i, *sub)
    return None


def _at_path(entry_value: ast.expr, path: tuple[int, ...]) -> ast.expr | None:
    """Follow an index-path into an entry value.

    Returns:
        The node at the path, or None if the shape does not match.

    """
    node = entry_value
    for i in path:
        if isinstance(node, ast.Tuple | ast.List) and i < len(node.elts):
            node = node.elts[i]
        else:
            return None
    return node


def _domain_of(
    text: str,
    qualname: str,
    value_node: ast.expr,
    leaf: ast.Constant,
    own: str,
) -> list[str]:
    """Return the finite VALUE DOMAIN of a string leaf's POSITION across sibling entries.

    Position-aware, not "every string in the literal": for a dict of `(scope, remark)` tuples the
    domain of the SCOPE leaf is the first-tuple-elements, never the keys or remarks. `own` is the
    leaf's own string value.

    Returns:
        The sorted sibling values other than `own`, empty when there is no finite same-position
        domain.

    """
    path = _leaf_path(value_node, leaf)
    if path is None:
        return []
    lit = next(v for nm, v in _data_assigns(ast.parse(text)) if nm == qualname)
    values = lit.values if isinstance(lit, ast.Dict) else lit.elts
    vals: set[str] = set()
    for ev in values:
        node = _at_path(ev, path)
        if isinstance(node, ast.Constant):
            sibling = _const_value(node)
            if isinstance(sibling, str):
                vals.add(sibling)
    return sorted(vals - {own})


def _counterfactual(text: str, qualname: str, entry_value: ast.expr, leaf: ast.Constant) -> str:
    """Return a source literal DIFFERENT from `leaf`.

    A valid-enum SAME-POSITION sibling (grading correctness) if the leaf's position has a finite
    domain, else a type-directed distinct marker (grading presence).

    Returns:
        The replacement literal's source.

    """
    v = _const_value(leaf)
    if isinstance(v, str):
        dom = _domain_of(text, qualname, entry_value, leaf, v)
        return repr(dom[0]) if dom else repr(v + "·PAPERKIT_PERTURB")
    if isinstance(v, bool):
        return repr(not v)
    if isinstance(v, int | float):
        return repr(v + 1)
    if v is None:
        return repr("PAPERKIT_PERTURB")
    return _MARKER


def _assign_of(tree: ast.Module, qualname: str) -> ast.Assign | ast.AnnAssign | None:
    """Find the module-level assignment whose target is `qualname`.

    Returns:
        The statement a data literal lives in, or None.

    """
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == qualname for t in node.targets
        ):
            return node
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == qualname
        ):
            return node
    return None


def _first_leaf(val: ast.expr) -> ast.Constant | None:
    """Find the first scalar constant of a value (the value itself when it is one).

    Returns:
        The constant node, or None.

    """
    if isinstance(val, ast.Constant):
        return val
    return next((node for node in ast.walk(val) if isinstance(node, ast.Constant)), None)


def _perturb_assign(
    text: str,
    qualname: str,
    val: ast.expr,
    assign: ast.Assign | ast.AnnAssign | None,
) -> str:
    """Perturb one entry, located by source segment and scoped to its own assignment.

    Located by `ast.get_source_segment`, not raw column slicing: an entry on a line with
    escaped or raw strings desyncs naive column arithmetic from the true span. The replacement is
    scoped entry, then assignment, then module, so a same-text leaf elsewhere is untouched.

    Returns:
        The module text with the entry perturbed.

    """
    asrc = None if assign is None else ast.get_source_segment(text, assign)
    entry_src = ast.get_source_segment(text, val)
    if asrc is None or entry_src is None:
        return _splice(text, val, val, _MARKER)
    leaf = _first_leaf(val)
    leaf_src = None if leaf is None else ast.get_source_segment(text, leaf)
    if leaf is None or leaf_src is None:
        # A value with NO scalar leaf (a call, say): mark its PRESENCE as a whole.
        new_asrc = asrc.replace(entry_src, _MARKER, 1)
    else:
        cf = _counterfactual(text, qualname, val, leaf)
        new_asrc = asrc.replace(entry_src, entry_src.replace(leaf_src, cf, 1), 1)
    return text.replace(asrc, new_asrc, 1)


def _perturb_data(text: str, arg: str) -> str:
    """Perturb one value to a counterfactual (non-monotone: a value swap, never a drop).

    Descends into a nested value to the FIRST scalar leaf, keeping the module parseable.

    Returns:
        The perturbed source.

    Raises:
        KeyError: when `arg` (`<name>#<n>`) is not a data site.

    """
    qualname, n = _split_qn_n(arg)
    assign = _assign_of(ast.parse(text), qualname)
    for name, i, _kind, _k, val in data_sites(text):
        if name == qualname and i == n:
            out = _perturb_assign(text, qualname, val, assign)
            ast.parse(out)
            return out
    msg = f"mutant: 'dflip:{qualname}#{n}' is not a data site in the module"
    raise KeyError(msg)


def mutate_lines(text: str, nodes: Sequence[Bodied]) -> str:
    """Replace each given node's body line-span with an UNCATCHABLE raise, the rest byte-identical.

    So a source-grep witness flips only when ITS grepped text lived in a mutated body, not because
    the file was reformatted. BaseException, not Exception, so a witness's own `except Exception`
    cannot swallow the mutation. Takes a LIST of nodes: several sites may be mutated at once.
    NESTED nodes are collapsed: when an outer span CONTAINS an inner one, replacing the outer body
    already removes the inner, and replacing both would slice a line list a prior replacement
    already shortened. So any node whose span is contained in another's is dropped first.

    Returns:
        The perturbed source.

    """
    spans = [
        (n.body[0].lineno, n.end_lineno or n.body[0].lineno, n.body[0].col_offset) for n in nodes
    ]
    outer = [
        (s, e, c)
        for i, (s, e, c) in enumerate(spans)
        if not any(
            j != i and o_s <= s and e <= o_e and (o_s, o_e) != (s, e)
            for j, (o_s, o_e, _o_c) in enumerate(spans)
        )
    ]
    lines = text.splitlines(keepends=True)
    for s, e, col in sorted(outer, reverse=True):
        lines[s - 1 : e] = [" " * col + _RAISE]
    return "".join(lines)


def _drop_def(text: str, qualname: str) -> str:
    """Drop one def-site's BEHAVIOUR: its body becomes the uncatchable raise.

    Returns:
        The perturbed source.

    Raises:
        KeyError: when `qualname` is not a def-site.

    """
    for qn, node in def_sites(text):
        if qn == qualname:
            return mutate_lines(text, [node])
    msg = f"mutant: '{qualname}' is not a def-site in the module"
    raise KeyError(msg)


def _drop_import(text: str, name: str) -> str:
    """Remove the top-level `import <name>` or `from <name> import ...` (present to absent).

    Returns:
        The perturbed source.

    Raises:
        KeyError: when `name` is not a top-level import.

    """
    drop: set[int] = set()
    for node in ast.parse(text).body:
        if (isinstance(node, ast.Import) and any(a.name == name for a in node.names)) or (
            isinstance(node, ast.ImportFrom) and node.module == name
        ):
            drop.update(range(node.lineno, _end_line(node) + 1))
    if not drop:
        msg = f"mutant: '{name}' is not a top-level import in the module"
        raise KeyError(msg)
    kept = (ln for i, ln in enumerate(text.splitlines(keepends=True), 1) if i not in drop)
    return "".join(kept)


def _inject_import(text: str, name: str) -> str:
    """Inject `import <name>` GUARDED under `if False:` (absent becomes present in the SOURCE).

    A "module does NOT import X" assertion, whether it greps the source or walks the AST, now
    flips, because the import statement IS there. But it is DEAD code: the optimiser drops the
    `if False:` block from the .pyc, so it never executes and no circular-import breakage flips
    OTHER claims spuriously. Placed after the module docstring and any `from __future__` imports
    (which must stay first).

    Returns:
        The perturbed source.

    """
    after = 0
    for node in ast.parse(text).body:
        if (isinstance(node, ast.Expr) and _is_str_const(node.value)) or (
            isinstance(node, ast.ImportFrom) and node.module == "__future__"
        ):
            after = _end_line(node)
        else:
            break
    lines = text.splitlines(keepends=True)
    lines.insert(after, f"if False:  # PAPERKIT_MUT\n    import {name}\n")
    return "".join(lines)


def _apply_regex_spec(text: str, arg: str) -> str:
    """Apply the `regex:` operator: parse its one-string spec and rewrite the source.

    Returns:
        The perturbed source.

    """
    return regexop.apply_regex(text, regexop.parse_regex_spec(arg))


_OPS: dict[str, Callable[[str, str], str]] = {
    "regex": _apply_regex_spec,
    "def": _drop_def,
    "branch": _mutate_branch,
    "flip": _op_flip,
    "data-": _drop_data,
    "dflip": _perturb_data,
    "import-": _drop_import,
    "import+": _inject_import,
}


def emit_mutant(text: str, spec: str) -> str:
    """Return the source perturbed by `spec` (see the module docstring).

    The EMPTY spec is the IDENTITY. A bare qualname (no colon) is a def-drop.

    Returns:
        The perturbed source.

    Raises:
        KeyError: when the operator is unknown or the spec names no such site.

    """
    if not spec:
        return text
    op, sep, arg = spec.partition(":")
    if not sep:
        return _drop_def(text, spec)
    handler = _OPS.get(op)
    if handler is None:
        msg = f"mutant: unknown mutation op in spec '{spec}'"
        raise KeyError(msg)
    return handler(text, arg)


def main(argv: Sequence[str] | None = None) -> int:
    """Print the perturbed module: `<module.py> <spec>`.

    Returns:
        0 on success, 2 when the arguments are not exactly a module and a spec.

    """
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != _ARGC:
        sys.stderr.write(_USAGE)
        return 2
    module, spec = args
    sys.stdout.write(emit_mutant(Path(module).read_text(encoding="utf-8"), spec))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
