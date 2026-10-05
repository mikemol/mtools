# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Cut an oversized module into SIBLING modules: a pure plan, and a separate, explicit write (W595).

Cleanroomed from substrate's `scratch/_pycodemod_split.py` (`--split`). `size` names a file too big
to read, `layout` says where its top-level statements are, and a split MOVES them. The origin did
the planning and the writing in one `--apply` flag read from argv; here they are two functions.

⚑⚑ `plan` WRITES NOTHING AND `apply` WRITES ONLY WHEN TOLD, IN WORDS. `apply(plan, write=None)`
raises: the choice between a dry run (`write=False`) and a write (`write=True`) is a required
operand, never a default and never read from the environment. A plan that was refused, or that
skipped its file, cannot be applied at all, and neither can a plan whose file changed since.

⚑ SIBLINGS, NOT A SUBPACKAGE. A body reading `Path(__file__).resolve().parent` asks WHICH DIRECTORY
AM I IN; one level down answers differently and every assertion over it goes on passing about the
wrong tree. A `__file__` read as SOURCE TEXT cannot survive any placement (the part sees only its
own share), so those statements are REPORTED as hazards, never relocated in silence. A string
literal naming the original's basename is the same hazard spelled differently.

⚑ THE PART GRAPH IS ACYCLIC BY CONSTRUCTION: parts are packed from a topological order of the
strongly-connected components of the statement graph, so part i references only parts < i. A cycle
is CO-LOCATED, not refused (`def f(): return T` beside `T = {"k": f}` is a cycle in the graph and
not in Python). A component too big for one part is refused, on size, and the refusal names it.

⚑ EACH CANDIDATE PART IS RENDERED BEFORE IT IS COMMITTED. Its `from <sibling> import` header
depends on where its dependencies landed, so a reserve for it reports parts under the bound and
writes them over it. In topological order every dependency is already placed and the cost is exact.

⚑ SIDE EFFECTS KEEP THEIR SOURCE ORDER: only a def, class, import or bare-name binding is pure;
a subscript store, a loop or a bare call is pinned against every statement sharing a module name.

⚑ THE LICENCE HEADER TRAVELS. The original's leading comment block stays on the entry module
verbatim (shebang and coding line included), and the SPDX and copyright lines of it open every part.

⚑ NO SUPPRESSION COMMENT IS EMITTED. Re-exports are declared in a generated `__all__`, which also
names every part, because a part nothing imports never runs and takes its side effects with it.
A module that already declares `__all__` is REFUSED: its list would need merging by hand.

⚑ THE WRITE IS TMP-FILE-AND-REPLACE, NOT mikemol-atomicwrite: pycodemod does not depend on it, and
a new dependency is a pyproject, BUILD and lockfile change of its own. The entry module is written
LAST, so a crash leaves the original intact and the siblings merely unreferenced. A sibling that
already exists with different content is never overwritten.
"""

from __future__ import annotations

import ast
import heapq
import textwrap
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.pycodemod.core import Skip
from mikemol.pycodemod.splitscope import Refusal, Source, Statement, read, slices

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Mapping, Sequence

_WIDTH = 98
_LICENCE_KEY = "SPDX-License-Identifier"
_COPYRIGHT = "# Copyright"


class ChoiceError(ValueError):
    """`apply` was not told whether to write: the choice is a required operand."""

    def __init__(self) -> None:
        """State the two spellings of the choice."""
        super().__init__("apply needs write=True or write=False; there is no default")


class RefusedError(ValueError):
    """`apply` was handed a plan that cannot be written: refused, skipped, empty, stale or lossy."""

    def __init__(self, path: str, why: str) -> None:
        """Name the file and the reason."""
        super().__init__(f"{path}: {why}")


class ExistsError(FileExistsError):
    """A sibling the plan would write already exists with different content."""


@dataclass(frozen=True, slots=True)
class Options:
    """What a plan is bounded and shaped by.

    `max_lines` and `max_defs` compose: a part is committed only under both, `None` meaning
    unbounded. `keep` names statements that stay in the entry module (the `__main__` guard always
    does). `export` adds private names to the entry's re-exports; the public names are always
    re-exported, and `export_all` re-exports every one.
    """

    max_lines: int = 1200
    max_defs: int | None = None
    prefix: str | None = None
    keep: frozenset[str] = frozenset()
    export: frozenset[str] = frozenset()
    export_all: bool = False


@dataclass(frozen=True, slots=True)
class Part:
    """One new sibling file: which statements (by index) and which names it now holds."""

    file: str
    ids: tuple[int, ...]
    names: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Owed:
    """A caller that imports a moved name the entry module does not re-export."""

    path: str
    line: int
    name: str
    file: str


@dataclass(frozen=True, slots=True)
class Plan:
    """The whole decision, before anything is written. Nothing here has touched the disk."""

    path: str
    parts: tuple[Part, ...] = ()
    files: Mapping[str, str] = field(default_factory=dict)
    moves: tuple[tuple[str, str], ...] = ()
    imports: tuple[str, ...] = ()
    owed: tuple[Owed, ...] = ()
    hazards: tuple[Statement, ...] = ()
    selfnamed: tuple[Statement, ...] = ()
    twice: tuple[str, ...] = ()
    statements: tuple[Statement, ...] = ()
    original: str = ""
    refusal: Refusal | None = None
    skipped: tuple[Skip, ...] = ()

    @property
    def entry(self) -> str:
        """The original's file name: the one file the plan rewrites rather than creates."""
        return Path(self.path).name

    @property
    def applicable(self) -> bool:
        """Whether there is something to write and nothing that forbids writing it."""
        return not self.refusal and not self.skipped and bool(self.files)


@dataclass(frozen=True, slots=True)
class Written:
    """One file `apply` handled: its name, its line count, and whether it was written."""

    name: str
    lines: int
    written: bool


# ── ordering ──────────────────────────────────────────────────────────────────────────────────


def _components(idxs: Collection[int], deps: Mapping[int, set[int]]) -> list[list[int]]:
    live = set(idxs)
    index: dict[int, int] = {}
    low: dict[int, int] = {}
    onstack: set[int] = set()
    stack: list[int] = []
    out: list[list[int]] = []

    def strong(v: int) -> None:
        index[v] = low[v] = len(index)
        stack.append(v)
        onstack.add(v)
        for w in sorted(deps.get(v, ())):
            if w not in live:
                continue
            if w not in index:
                strong(w)
                low[v] = min(low[v], low[w])
            elif w in onstack:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            comp: list[int] = []
            while not comp or comp[-1] != v:
                comp.append(stack.pop())
                onstack.discard(comp[-1])
            out.append(sorted(comp))

    for v in sorted(idxs):
        if v not in index:
            strong(v)
    return out


def _topo(idxs: Collection[int], deps: Mapping[int, set[int]]) -> list[list[int]]:
    comps = _components(idxs, deps)
    home = {i: k for k, c in enumerate(comps) for i in c}
    pending: dict[int, set[int]] = {k: set() for k in range(len(comps))}
    users: dict[int, set[int]] = {k: set() for k in range(len(comps))}
    for i in idxs:
        for d in deps.get(i, ()):
            if d in home and home[d] != home[i]:
                pending[home[i]].add(home[d])
                users[home[d]].add(home[i])
    ready = [(min(comps[k]), k) for k in pending if not pending[k]]
    heapq.heapify(ready)
    out: list[list[int]] = []
    while ready:
        _lo, k = heapq.heappop(ready)
        out.append(comps[k])
        for u in sorted(users[k]):
            pending[u].discard(k)
            if not pending[u]:
                heapq.heappush(ready, (min(comps[u]), u))
    return out


# ── rendering ─────────────────────────────────────────────────────────────────────────────────


def _size(code: str) -> int:
    # The line count a size gate sees: `split("\n")`, trailing newline included.
    return len(code.split("\n"))


def _wrap_import(module: str, names: Collection[str]) -> str:
    one = f"from {module} import {', '.join(sorted(names))}\n"
    if len(one) <= _WIDTH + 1:
        return one
    lead = f"from {module} import ("
    pad = " " * len(lead)
    body = textwrap.fill(
        ", ".join(sorted(names)), width=_WIDTH, initial_indent=pad, subsequent_indent=pad
    )
    return f"{lead}{body[len(lead) :]})\n"


@dataclass(frozen=True, slots=True)
class _Ctx:
    by_i: Mapping[int, Statement]
    tops: Sequence[Statement]
    provider: Mapping[str, int]
    prefix: str
    origin: str
    licence: str

    def futures(self) -> list[Statement]:
        return [t for t in self.tops if t.is_future]

    def module(self, pi: int) -> str:
        return f"{self.prefix}{pi:02d}"


def _needs(
    ids: Sequence[int], pi: int, home: Mapping[int, int], ctx: _Ctx
) -> tuple[set[str], dict[int, set[str]]]:
    binds: set[str] = set()
    for i in ids:
        binds |= ctx.by_i[i].binds
    imported = {b for t in ctx.tops if t.is_import for b in t.binds}
    need_import: set[str] = set()
    need_part: dict[int, set[str]] = {}
    for i in ids:
        for n in ctx.by_i[i].free - binds:
            j = ctx.provider.get(n)
            if j is not None and j in home and home[j] != pi:
                need_part.setdefault(home[j], set()).add(n)
            elif n in imported:
                need_import.add(n)
    return need_import, need_part


def _render_part(pi: int, ids: Sequence[int], home: Mapping[int, int], ctx: _Ctx) -> str:
    need_import, need_part = _needs(ids, pi, home, ctx)
    doc = (
        f'"""{ctx.module(pi)}.py: part {pi:02d} of {ctx.origin}, cut by pycodemod split.\n'
        'Statements below are BYTE-IDENTICAL to their originals."""\n'
    )
    head = [ctx.licence, doc]
    head.extend(f.text.lstrip("\n") for f in ctx.futures())
    head.extend(
        t.text.lstrip("\n")
        for t in ctx.tops
        if t.is_import and not t.is_future and t.binds & need_import
    )
    head.extend(_wrap_import(ctx.module(j), need_part[j]) for j in sorted(need_part))
    return "".join(head) + "".join(ctx.by_i[i].text for i in ids)


def _all_block(names: Collection[str]) -> str:
    return "__all__ = [\n" + "".join(f'    "{n}",\n' for n in sorted(names)) + "]\n"


def _defcount(ids: Iterable[int], by_i: Mapping[int, Statement]) -> int:
    return sum(1 for i in ids if by_i[i].is_def)


# ── the cut ───────────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class _Cut:
    base: list[Statement]
    movable: list[Statement]
    entry_ids: set[int]
    doc: Statement | None


def _classify(tops: Sequence[Statement], keep: Collection[str]) -> _Cut:
    first_def = next((t.index for t in tops if t.is_def), len(tops))
    entry_ids = {t.index for t in tops if t.is_main_guard or t.name in keep}
    return _Cut(
        base=[t for t in tops if t.index < first_def and not t.is_docstring and not t.is_import],
        movable=[
            t for t in tops if t.index >= first_def and not t.is_import and t.index not in entry_ids
        ],
        entry_ids=entry_ids,
        doc=next((t for t in tops if t.is_docstring), None),
    )


def _providers(tops: Sequence[Statement]) -> tuple[dict[str, int], tuple[str, ...]]:
    """Map each non-import name to the statement binding it, and list names bound twice.

    Returns:
        (provider, twice).

    """
    binder: dict[str, int] = {}
    twice: set[str] = set()
    for t in tops:
        for n in t.binds:
            if n in binder and not t.is_import and not tops[binder[n]].is_import:
                twice.add(n)
            binder[n] = t.index
    provider = {
        n: i for n, i in binder.items() if not tops[i].is_import and not tops[i].is_docstring
    }
    return provider, tuple(sorted(twice))


def _deps(tops: Sequence[Statement], provider: Mapping[str, int]) -> dict[int, set[int]]:
    deps = {
        t.index: {provider[n] for n in t.free if n in provider and provider[n] != t.index}
        for t in tops
    }
    shared = set(provider)
    for a in tops:
        if a.is_pure:
            continue
        touch = (a.binds | a.free) & shared
        for b in tops:
            if b.index != a.index and touch & ((b.binds | b.free) & shared):
                lo, hi = sorted((a.index, b.index))
                deps[hi].add(lo)
    return deps


def _stuck(cut: _Cut, deps: Mapping[int, set[int]], tops: Sequence[Statement]) -> Refusal | None:
    stuck = [t for t in cut.movable if deps[t.index] & cut.entry_ids]
    if not stuck:
        return None
    bound = {d for t in stuck for d in deps[t.index] & cut.entry_ids}
    names = tuple(sorted({t.name for t in stuck} | {tops[d].name for d in bound}))
    return Refusal("entry-dep", "a part would depend on a statement kept in the entry", names)


def _pack(groups: Sequence[Sequence[int]], cut: _Cut, ctx: _Ctx, opt: Options) -> list[list[int]]:
    parts: list[list[int]] = [[t.index for t in cut.base]] if cut.base else []
    home = {t.index: 0 for t in cut.base}
    cur: list[int] = []
    pi = len(parts)
    for grp in groups:
        trial = [*cur, *grp]
        too_big = _size(_render_part(pi, trial, home, ctx)) > opt.max_lines or (
            opt.max_defs is not None and _defcount(trial, ctx.by_i) > opt.max_defs
        )
        if too_big and cur:
            parts.append(cur)
            pi, cur = pi + 1, list(grp)
        else:
            cur = trial
        home.update(dict.fromkeys(grp, pi))
    if cur:
        parts.append(cur)
    return parts


def _licence(src: Source) -> str:
    lines = src.src.splitlines(keepends=True)[: src.head]
    return "".join(ln for ln in lines if _LICENCE_KEY in ln or ln.startswith(_COPYRIGHT))


def _render_entry(
    source: Source, cut: _Cut, parts: Sequence[Sequence[int]], opt: Options, ctx: _Ctx
) -> tuple[str, tuple[str, ...], set[str]]:
    home = {i: pi for pi, ids in enumerate(parts) for i in ids}
    kept = [t for t in ctx.tops if t.index in cut.entry_ids]
    kept_free: set[str] = set().union(*(t.free for t in kept)) if kept else set()
    surface = {
        n
        for n, j in ctx.provider.items()
        if j in home and (opt.export_all or not n.startswith("_") or n in opt.export)
    }
    surface |= {n for n in kept_free if n in ctx.provider and ctx.provider[n] in home}
    pieces = ["".join(source.src.splitlines(keepends=True)[: source.head])]
    if cut.doc is not None:
        pieces.append(cut.doc.text)
    pieces.extend(f.text.lstrip("\n") for f in ctx.futures())
    pieces.extend(
        t.text.lstrip("\n")
        for t in ctx.tops
        if t.is_import and not t.is_future and t.binds & kept_free
    )
    imports: list[str] = []
    exported = set(surface)
    for pi in range(len(parts)):
        mine = {n for n in surface if home[ctx.provider[n]] == pi}
        mod = ctx.module(pi)
        imports.append(_wrap_import(mod, mine) if mine else f"import {mod}\n")
        if not mine:
            exported.add(mod)
    pieces.extend([*imports, _all_block(exported), "".join(t.text for t in kept), source.footer])
    return "".join(pieces), tuple(imports), surface


def _owed(
    callers: Sequence[str], stem: str, moved: Mapping[str, str], surface: Collection[str]
) -> tuple[list[Owed], list[Skip]]:
    owed: list[Owed] = []
    skipped: list[Skip] = []
    for caller in callers:
        try:
            tree = ast.parse(Path(caller).read_text(encoding="utf-8"))
        except (UnicodeDecodeError, OSError, SyntaxError) as exc:
            skipped.append(Skip(caller, "unreadable", type(exc).__name__))
            continue
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom) and (n.module or "").rsplit(".", 1)[-1] == stem:
                owed.extend(
                    Owed(caller, n.lineno, al.name, moved[al.name])
                    for al in n.names
                    if al.name in moved and al.name not in surface
                )
    return owed, skipped


def _budget(
    files: Mapping[str, str], parts: Sequence[Sequence[int]], ctx: _Ctx, opt: Options
) -> Refusal | None:
    over = tuple((n, _size(c)) for n, c in sorted(files.items()) if _size(c) > opt.max_lines)
    over_defs = tuple(
        (f"{ctx.module(pi)}.py", _defcount(ids, ctx.by_i))
        for pi, ids in enumerate(parts)
        if opt.max_defs is not None and _defcount(ids, ctx.by_i) > opt.max_defs
    )
    if not over and not over_defs:
        return None
    named = over or over_defs
    return Refusal(
        "budget",
        "no packing fits: relocation cannot shrink a body or break a cycle, which is authoring",
        tuple(n for n, _ in named),
        named,
    )


def _assemble(
    parts: Sequence[Sequence[int]], ctx: _Ctx
) -> tuple[tuple[Part, ...], tuple[tuple[str, str], ...]]:
    unnamed = {"-", "import"}
    made = tuple(
        Part(
            f"{ctx.module(pi)}.py",
            tuple(ids),
            tuple(ctx.by_i[i].name for i in ids if ctx.by_i[i].name not in unnamed),
        )
        for pi, ids in enumerate(parts)
    )
    where = {
        n: p.file
        for p, ids in zip(made, parts, strict=True)
        for i in ids
        for n in ctx.by_i[i].binds
    }
    return made, tuple(sorted(where.items()))


@dataclass(frozen=True, slots=True)
class _Work:
    cut: _Cut
    ctx: _Ctx
    groups: list[list[int]]
    twice: tuple[str, ...]


def _prepare(path: str, source: Source, opt: Options) -> _Work | Plan:
    tops = source.tops
    cut = _classify(tops, opt.keep)
    if not cut.movable:
        return Plan(path, statements=tops)
    if any("__all__" in t.binds for t in tops):
        reason = "the module declares __all__; merge it by hand"
        return Plan(path, statements=tops, refusal=Refusal("all-declared", reason))
    provider, twice = _providers(tops)
    deps = _deps(tops, provider)
    stuck = _stuck(cut, deps, tops)
    if stuck:
        return Plan(path, statements=tops, refusal=stuck)
    base_ids = {t.index for t in cut.base}
    groups = _topo(
        [t.index for t in cut.movable],
        {i: {d for d in ds if d not in base_ids} for i, ds in deps.items()},
    )
    prefix = opt.prefix or f"{Path(path).stem}_"
    by_i = {t.index: t for t in tops}
    ctx = _Ctx(by_i, tops, provider, prefix, Path(path).name, _licence(source))
    return _Work(cut, ctx, groups, twice)


def _plan_source(path: str, source: Source, opt: Options, callers: Sequence[str]) -> Plan:
    work = _prepare(path, source, opt)
    if isinstance(work, Plan):
        return work
    ctx, tops = work.ctx, source.tops
    parts = _pack(work.groups, work.cut, ctx, opt)
    home = {i: pi for pi, ids in enumerate(parts) for i in ids}
    files = {
        f"{ctx.module(pi)}.py": _render_part(pi, ids, home, ctx) for pi, ids in enumerate(parts)
    }
    entry, imports, surface = _render_entry(source, work.cut, parts, opt, ctx)
    files[Path(path).name] = entry
    refusal = _budget(files, parts, ctx, opt)
    if refusal:
        return Plan(path, statements=tops, refusal=refusal)
    made, moves = _assemble(parts, ctx)
    owed, skipped = _owed(callers, Path(path).stem, dict(moves), surface)
    return Plan(
        path=path,
        parts=made,
        files=files,
        moves=moves,
        imports=imports,
        owed=tuple(owed),
        hazards=tuple(t for t in tops if t.reads_file),
        selfnamed=tuple(t for t in tops if t.names_self and not t.is_docstring),
        twice=work.twice,
        statements=tops,
        original=source.src,
        skipped=tuple(skipped),
    )


def plan(path: str, options: Options | None = None, callers: Sequence[str] = ()) -> Plan:
    """Decide the cut of one module into siblings. WRITES NOTHING.

    `callers` are other files scanned for `from <stem> import <moved private name>`: those are
    OWED an edit, because the entry module re-exports public names only.

    Returns:
        the plan: the parts, the rewritten entry, owed callers, hazards, and the refusal or the
        skipped file when no plan exists. A module with nothing to move plans no files.

    """
    got = read(path)
    if isinstance(got, Skip):
        return Plan(path, skipped=(got,))
    if isinstance(got, Refusal):
        return Plan(path, refusal=got)
    return _plan_source(path, got, options or Options(), callers)


# ── the evidence, and the write ───────────────────────────────────────────────────────────────


def _texts(code: str) -> list[str]:
    cut = slices(code)
    return cut[1] if cut else []


def verify(p: Plan) -> tuple[bool, str]:
    """Check that every relocated statement reached the output byte-for-byte.

    Losslessness is a set question across a GROUP of files, which a per-file round trip cannot
    answer. Imports are re-derived per part and the docstring stays on the entry, so neither is
    in the multiset compared.

    Returns:
        (ok, detail): whether the multiset of original statement texts survived the move.

    """
    want = Counter(t.text for t in p.statements if not t.is_docstring and not t.is_import)
    got: Counter[str] = Counter()
    for code in p.files.values():
        got.update(_texts(code))
    missing = want - got
    if missing:
        return False, f"{sum(missing.values())} original statement(s) not reproduced byte-for-byte"
    return True, f"{sum(want.values())} statement(s) reproduced byte-for-byte"


def _atomic(path: Path, code: str) -> None:
    tmp = path.with_name(f".{path.name}.split-tmp")
    try:
        tmp.write_text(code, encoding="utf-8")
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)


def _refuse_unless_writable(p: Plan) -> None:
    if p.refusal:
        raise RefusedError(p.path, f"refused, {p.refusal.kind}: {p.refusal.detail}")
    if p.skipped:
        raise RefusedError(p.path, f"skipped, {p.skipped[0].why}")
    if not p.files:
        return
    ok, detail = verify(p)
    if not ok:
        raise RefusedError(p.path, f"lossy, {detail}")
    if Path(p.path).read_text(encoding="utf-8") != p.original:
        raise RefusedError(p.path, "changed since it was planned")


def apply(p: Plan, *, write: bool | None = None) -> tuple[Written, ...]:
    """Write the plan, or say what writing it would do. The choice is REQUIRED.

    The entry module goes last. A sibling that already exists with different content is refused
    before anything is written; one with identical content is rewritten harmlessly. A plan with
    nothing to move (a module already split) applies as no rows, so a second run is a no-op.

    Returns:
        one row per file, with whether it was written.

    Raises:
        ChoiceError: `write` was not stated.
        ExistsError: a sibling exists with different content.

    """
    if write is None:
        raise ChoiceError
    _refuse_unless_writable(p)
    if not p.files:
        return ()
    target = Path(p.path).resolve().parent
    names = [n for n in p.files if n != p.entry] + [p.entry]
    for name in names[:-1]:
        there = target / name
        if there.exists() and there.read_text(encoding="utf-8") != p.files[name]:
            raise ExistsError(str(there))
    rows: list[Written] = []
    for name in names:
        if write:
            _atomic(target / name, p.files[name])
        rows.append(Written(name, _size(p.files[name]), write))
    return tuple(rows)
