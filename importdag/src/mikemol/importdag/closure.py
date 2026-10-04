# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Name a claim witness's engine-module closure roots, and the files and contents it can toggle.

The build stages the transitive closure of the engine modules a witness touches instead of the flat
engine. The roots come from the syntax tree, never from a text search, because a text search
matches a name in prose or in a string. Two edge kinds carry modules:

- IMPORT: a bare `import X` or `from X import`, at module level (shared by every witness) or in a
  witness body. Only an import root expands to its cone, because loading a module loads what it
  imports. A fixture module imported at its top is an ordinary import root, since the fixture
  modules' own top-level imports carry the honest capability cone.
- READ: a `"x.py"` string constant. A witness that reads a module's source with `read_text` never
  loads its imports, so a pure read root does not expand: it contributes its own definition sites
  only, because a source mutation can flip a source-inspection assert while its cone's cannot. A
  module both imported and read is an import root, and the cone wins.

Calls between functions of the check module are followed, so a witness that calls a local helper
inherits the helper's imports. The output is one row per claim and module:

- `claim`, tab, the module path, for every module in an import cone.
- `claim`, tab, `read:` and the path, for every pure read root.
- `claim`, tab, `file-` or `file+`, a colon and the path, for each file the witness tests with
  `exists()`. The toggle is the opposite of the file's current state, checked at analysis time.
- `claim`, tab, `content-` or `content+`, tab, the path, tab, the substring, for each substring
  the witness tests with `in` against a file's text. Present means drop it, absent means inject it.

Besides imports, two indirect edges are followed. A witness that resolves a `concept:KEY` constant
inherits the cone of that key's witness, transitively, because the resolver runs the key's witness
in a fresh interpreter that an import walk cannot see across. A witness that names a sibling
generator script as a path inherits the engine modules that script imports, because the script does
its own flat import in its own interpreter. A cone that is too small for the process it stages dies
at that process's first import, so each of these was a measured failure before it was derived.

    python3 -m mikemol.importdag.closure --check CHECK.py [--relpath REL] ENGINE.py ...
"""

from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass
from pathlib import Path

from mikemol.importdag.dagderive import flat_imports, node_imports

DISPATCH = ("CLAIMS", "CONCEPTS", "WITNESSES")
"""The names a project's claim dispatch table is spelled with. A project that adds a spelling adds
it here, where the parse lives, because a table read under the wrong name yields an empty closure
and the build then runs one monolithic sweep per claim."""

CONCEPT_PREFIX = "concept:"

type FuncDef = ast.FunctionDef | ast.AsyncFunctionDef


class Args(argparse.Namespace):
    """The parsed command line, with the types argparse's own namespace does not carry."""

    check: str
    relpath: str
    engine: list[str]


@dataclass(frozen=True)
class Witness:
    """One check module parsed against an engine, with everything its claims are read from."""

    names: dict[str, str]
    igraph: dict[str, set[str]]
    check: Path
    relpath: str
    tree: ast.Module
    funcs: dict[str, FuncDef]
    claims: dict[str, str]


def const_str(node: ast.AST) -> str | None:
    """Read a string constant.

    Returns:
        The value when `node` is a string constant, else None.

    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def const_int(node: ast.AST) -> int | None:
    """Read an integer constant.

    Returns:
        The value when `node` is an integer constant, else None.

    """
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value
    return None


def div_literal(node: ast.AST) -> tuple[ast.expr, str] | None:
    """Split a division by a string literal, `LEFT / "text"`.

    Returns:
        The left operand and the literal, or None when `node` is not such a division.

    """
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        text = const_str(node.right)
        if text is not None:
            return node.left, text
    return None


def reads(node: ast.AST, names: set[str]) -> set[str]:
    """Collect the engine stems that a `.py` string constant under `node` names.

    Returns:
        The stem of each string constant ending in `.py` whose stem is in `names`.

    """
    found = (const_str(n) for n in ast.walk(node))
    return {Path(s).stem for s in found if s is not None and s.endswith(".py")} & names


def parents_prefix(node: ast.AST, parts: list[str]) -> str | None:
    """Resolve a `Path(__file__)` chain ending in `.parents[N]` to its sandbox prefix.

    `__file__` sits at the check's repository-relative path in the hermetic sandbox, so
    `parents[N]` is that path with N+1 trailing components dropped. Both a module constant
    assigned from the chain and the chain used inline in a path expression are handled.

    Returns:
        The prefix as a slash-joined string (empty for the root), or None when `node` is not such
        an expression.

    """
    if not (
        isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Attribute)
        and node.value.attr == "parents"
    ):
        return None
    depth = const_int(node.slice)
    uses_file = any(isinstance(x, ast.Name) and x.id == "__file__" for x in ast.walk(node))
    if depth is None or not uses_file:
        return None
    return "/".join(parts[: -(depth + 1)])


def dir_consts(
    relpath: str, stmts: list[ast.stmt], pref: dict[str, str] | None = None
) -> dict[str, str]:
    """Map the directory constants assigned in `stmts` to their sandbox-relative prefix.

    A constant is a `Path(__file__)` chain ending in `.parents[N]`, or a known constant divided by
    a string literal, which extends the known prefix. It is called on the module body for the
    shared constants, then again for each witness to add its function-local ones.

    Returns:
        A new mapping from constant name to prefix, starting from a copy of `pref`.

    """
    parts = relpath.split("/")
    out = dict(pref) if pref else {}
    for n in stmts:
        if not isinstance(n, ast.Assign) or not isinstance(n.targets[0], ast.Name):
            continue
        tgt, v = n.targets[0].id, n.value
        pp = parents_prefix(v, parts)
        div = div_literal(v)
        if pp is not None:
            out[tgt] = pp
        elif div is not None and isinstance(div[0], ast.Name) and div[0].id in out:
            out[tgt] = "/".join(p for p in (out[div[0].id], div[1]) if p)
    return out


def resolve_path(node: ast.AST, pref: dict[str, str], parts: list[str]) -> str | None:
    """Resolve a path expression built from directory constants and string literals.

    The expression is an inline `Path(__file__)` chain, a bare directory constant, or a nested
    division of either by string literals.

    Returns:
        The sandbox path, or None when any part of the expression is not resolvable.

    """
    pp = parents_prefix(node, parts)
    if pp is not None:
        return pp
    if isinstance(node, ast.Name):
        return pref.get(node.id)
    div = div_literal(node)
    if div is None:
        return None
    base = resolve_path(div[0], pref, parts)
    return None if base is None else "/".join(p for p in (base, div[1]) if p)


def exists_paths(node: ast.AST, pref: dict[str, str], parts: list[str]) -> set[str]:
    """Collect the sandbox paths a witness tests with `(BASE / "leaf").exists()`.

    A claim asserting a file's presence or absence is falsifiable by toggling that file, the file
    analogue of toggling an import. Only plain-constant path leaves are resolved, not f-strings or
    loop variables.

    Returns:
        The resolved path of each `exists()` call under `node`.

    """
    out: set[str] = set()
    for c in ast.walk(node):
        if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute):
            p = resolve_path(c.func.value, pref, parts) if c.func.attr == "exists" else None
            if p is not None:
                out.add(p)
    return out


def read_text_target(node: ast.AST) -> ast.expr | None:
    """Find the receiver of a `.read_text()` call.

    Returns:
        The expression `read_text` is called on, or None when `node` is not such a call.

    """
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "read_text"
    ):
        return node.func.value
    return None


def local_reads(fn: ast.AST, pref: dict[str, str], parts: list[str]) -> dict[str, str]:
    """Map each local name bound to `PATH.read_text()` in `fn` to the resolved path.

    Returns:
        The path of every single-target assignment whose value is a `read_text()` call on a
        resolvable path expression.

    """
    out: dict[str, str] = {}
    for n in ast.walk(fn):
        if not (isinstance(n, ast.Assign) and len(n.targets) == 1):
            continue
        target, receiver = n.targets[0], read_text_target(n.value)
        if isinstance(target, ast.Name) and receiver is not None:
            p = resolve_path(receiver, pref, parts)
            if p is not None:
                out[target.id] = p
    return out


def membership_literal(node: ast.AST) -> str | None:
    """Read the literal of a single `"S" in X` comparison.

    Returns:
        The string literal on the left, or None when `node` is not a one-operator `in` test with
        a string literal on the left.

    """
    if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.In):
        return const_str(node.left)
    return None


def content_edges(fn: ast.AST, pref: dict[str, str], parts: list[str]) -> set[tuple[str, str]]:
    """Collect the path and substring pairs a witness tests with `"S" in F.read_text()`.

    A claim asserting that a substring is present in a file is falsifiable by toggling that
    substring, the finest content perturbation: a precise edge drop, not a whole-file corruption
    that flips every reader identically. The comparator is either an inline `read_text()` call or
    a function-local name bound to one; module-level constants are a coarser, later rung.

    Returns:
        Each resolvable path with the string literal tested against its text.

    """
    reads_of = local_reads(fn, pref, parts)
    out: set[tuple[str, str]] = set()
    for c in ast.walk(fn):
        sub = membership_literal(c)
        if sub is None or not isinstance(c, ast.Compare):
            continue
        comp = c.comparators[0]
        receiver = read_text_target(comp)
        p = None
        if receiver is not None:
            p = resolve_path(receiver, pref, parts)
        elif isinstance(comp, ast.Name):
            p = reads_of.get(comp.id)
        if p is not None:
            out.add((p, sub))
    return out


def engine_cone(igraph: dict[str, set[str]], seed: set[str]) -> set[str]:
    """Expand a set of root stems to the full transitive cone of the engine import graph.

    The cone is the set of modules the check actually loads, hence the modules whose definition
    drop can flip it. Roots alone under-scope: a root that reaches another module through its own
    import puts that module in the perturbation surface even though it is not a root.

    Returns:
        The seed and every stem reachable from it through `igraph`.

    """
    seen = set(seed)
    stack = list(seed)
    while stack:
        for imp in igraph.get(stack.pop(), ()):
            if imp not in seen:
                seen.add(imp)
                stack.append(imp)
    return seen


def dispatch_claims(tree: ast.Module) -> dict[str, str]:
    """Read the claim registry: each claim key and the function that witnesses it.

    Returns:
        The function name registered under each constant key of a top-level dict assigned to any
        of the `DISPATCH` names. A key is read as its string form, and only a plain name counts as
        its value.

    """
    claims: dict[str, str] = {}
    for n in tree.body:
        if not (isinstance(n, ast.Assign) and isinstance(n.value, ast.Dict)):
            continue
        if not any(isinstance(t, ast.Name) and t.id in DISPATCH for t in n.targets):
            continue
        for k, v in zip(n.value.keys, n.value.values, strict=True):
            if isinstance(k, ast.Constant) and isinstance(v, ast.Name):
                claims[str(k.value)] = v.id
    return claims


def roots(w: Witness, fnname: str, seen: set[str]) -> tuple[set[str], set[str]]:
    """Collect the import and read roots of one function, following calls to local functions.

    A witness that calls a local helper inherits the helper's roots. `seen` is shared across the
    walk so a recursive pair of helpers terminates.

    Returns:
        The import stems and the read stems of the function and everything it calls locally.

    """
    if fnname in seen or fnname not in w.funcs:
        return set(), set()
    seen.add(fnname)
    fn = w.funcs[fnname]
    names = set(w.names)
    imp, rd = node_imports(fn, names), reads(fn, names)
    for c in ast.walk(fn):
        if isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id in w.funcs:
            ci, cr = roots(w, c.func.id, seen)
            imp |= ci
            rd |= cr
    return imp, rd


def concept_keys(fn: ast.AST, claims: dict[str, str]) -> set[str]:
    """Collect the registered claim keys a witness resolves with a `concept:KEY` constant.

    Returns:
        The key of each string constant under `fn` that starts with the concept prefix and names
        a registered claim.

    """
    out: set[str] = set()
    for c in ast.walk(fn):
        text = const_str(c)
        if text is not None and text.startswith(CONCEPT_PREFIX):
            key = text[len(CONCEPT_PREFIX) :]
            if key in claims:
                out.add(key)
    return out


def resolved_roots(w: Witness, key: str, seen: set[str]) -> tuple[set[str], set[str]]:
    """Collect the roots of a resolved claim key, following further resolved keys transitively.

    The resolver does not import the key's witness: it shells out to the owning library, which
    runs the witness in a fresh interpreter. An import walk cannot see across that boundary, so
    the caller's cone is sized for its own imports and the callee's first import dies.

    Returns:
        The import and read stems of the key's witness and of every key it resolves in turn.

    """
    if key in seen or key not in w.claims:
        return set(), set()
    seen.add(key)
    imp, rd = roots(w, w.claims[key], set())
    for nxt in sorted(concept_keys(w.funcs[w.claims[key]], w.claims)):
        ni, nr = resolved_roots(w, nxt, seen)
        imp |= ni
        rd |= nr
    return imp, rd


def script_roots(w: Witness, fn: ast.AST) -> set[str]:
    """Collect the engine modules imported by every sibling script a witness names as a path.

    A witness that runs a sibling generator as a subprocess does not import what the generator
    imports: the generator does its own path setup and a flat import in a fresh interpreter. The
    population of such witnesses is small only by accident, so the edge is derived rather than
    left to a caller whose module-level imports happen to cover it. A script's own imports seed
    the cone like any other root.

    Returns:
        The engine stems imported by each existing script, other than the check itself, that sits
        beside the check and is named by a `.py` string constant under `fn`. A script that does
        not parse is skipped.

    """
    out: set[str] = set()
    names = set(w.names)
    for c in ast.walk(fn):
        text = const_str(c)
        if text is None or not text.endswith(".py"):
            continue
        script = w.check.parent / Path(text).name
        if not script.exists() or script.resolve() == w.check.resolve():
            continue
        try:
            out |= node_imports(ast.parse(script.read_text(encoding="utf-8")), names)
        except SyntaxError:
            continue
    return out


def module_roots(w: Witness) -> tuple[set[str], set[str]]:
    """Collect the roots every claim shares: the top-level statements of the check module.

    Import and read roots are tracked separately, because only imports expand to a cone. Function
    and class definitions are left to the per-claim walk.

    Returns:
        The import stems and the read stems of the module's top-level statements.

    """
    names = set(w.names)
    base_i: set[str] = set()
    base_r: set[str] = set()
    for stmt in w.tree.body:
        if not isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            base_i |= node_imports(stmt, names)
            base_r |= reads(stmt, names)
    return base_i, base_r


def toggle_rows(key: str, fn: FuncDef, w: Witness) -> list[str]:
    """Render the file and content toggle rows of one claim.

    The toggles are decided against the working directory, which is the repository root at
    analysis time. An absent file toggles to `file+` and a present one to `file-`; a path that is
    a directory is skipped, because a directory's existence is not a single-artifact toggle. A
    content row is `content-` when the substring is present now and `content+` when it is absent.

    Returns:
        The file rows followed by the content rows.

    """
    parts = w.relpath.split("/")
    pref = dir_consts(w.relpath, fn.body, dir_consts(w.relpath, w.tree.body))
    rows: list[str] = []
    for path in sorted(exists_paths(fn, pref, parts)):
        if Path(path).is_dir():
            continue
        op = "file-" if Path(path).exists() else "file+"
        rows.append(f"{key}\t{op}:{path}")
    for path, sub in sorted(content_edges(fn, pref, parts)):
        here = Path(path).read_text(encoding="utf-8") if Path(path).exists() else ""
        op = "content-" if sub in here else "content+"
        rows.append(f"{key}\t{op}\t{path}\t{sub}")
    return rows


def claim_rows(w: Witness, key: str, base: tuple[set[str], set[str]]) -> list[str]:
    """Render every output row of one claim.

    Returns:
        The rows in output order: cone modules, read roots, file toggles, content toggles.

    """
    base_i, base_r = base
    fn = w.funcs[w.claims[key]]
    wi, wr = roots(w, w.claims[key], set())
    for ck in sorted(concept_keys(fn, w.claims)):
        ci, cr = resolved_roots(w, ck, {key})
        wi |= ci
        wr |= cr
    wi |= script_roots(w, fn)
    cone = engine_cone(w.igraph, base_i | wi)
    rows = [f"{key}\t{w.names[stem]}" for stem in sorted(cone)]
    rows += [f"{key}\tread:{w.names[stem]}" for stem in sorted((base_r | wr) - cone)]
    return rows + toggle_rows(key, fn, w)


def load(check: Path, relpath: str, engine: list[str]) -> Witness:
    """Parse a check module and the engine modules it is resolved against.

    The engine paths are read relative to the working directory, and a stem named twice keeps its
    last path. The import graph is built once here, over the flat reading.

    Returns:
        The witness context for `check`, with `relpath` its repository-relative path.

    """
    names = {Path(p).stem: p for p in engine}
    igraph = {
        s: flat_imports(Path(p).read_text(encoding="utf-8"), set(names)) for s, p in names.items()
    }
    tree = ast.parse(check.read_text(encoding="utf-8"))
    funcs = {
        fn.name: fn for fn in tree.body if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    return Witness(
        names=names,
        igraph=igraph,
        check=check,
        relpath=relpath,
        tree=tree,
        funcs=funcs,
        claims=dispatch_claims(tree),
    )


def parse_args(argv: list[str] | None) -> Args:
    """Read the command line with argparse, into a typed namespace.

    The namespace subclass declares the attribute types, so strict typing sees concrete values
    where argparse's own namespace yields `Any`, and `--help` and option abbreviations survive.

    Returns:
        The check path, the optional repository-relative path (empty when not given) and the
        engine module paths.

    """
    ap = argparse.ArgumentParser(
        prog="closure",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--check", required=True, help="the check module, e.g. paper/checks/claims.py")
    ap.add_argument(
        "--relpath",
        default="",
        help="the check's repository-relative path, for parents[N] resolution; defaults to --check",
    )
    ap.add_argument("engine", nargs="+", help="the engine module .py paths (the resolvable names)")
    return ap.parse_args(argv, namespace=Args())


def main(argv: list[str] | None = None) -> int:
    """Print the closure rows of every claim in a check module.

    Returns:
        0 after printing.

    """
    a = parse_args(argv)
    w = load(Path(a.check), a.relpath or a.check, a.engine)
    base = module_roots(w)
    for key in sorted(w.claims):
        for row in claim_rows(w, key, base):
            sys.stdout.write(row + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
