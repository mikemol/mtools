# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Replay `split.cases.json` against the port's `split.plan`, and say how each case came out (W645).

A case in that file is the ORIGIN's inputs and its check text, not its answer: `fixture` is the
files, `operands` the origin calls (`statements`, `plan`, `verify`, `_size`, `_defcount`), and
`origin.check` names what the origin's own selftest asserted. The origin is not importable here, so
this adapter does what `conftest.subject` does for the other modes (rehome the fixture, parse the
captured args, call the port) and then judges the port's answer against the check the case names.

Where a case's operands carry the origin's own plan (a `verify` call's `p`), the port's plan is
also COMPARED with it. Those comparisons surface two differences the port makes on purpose. Each is
recorded as a DECLARED difference with its reason, never hidden, and any other difference is
undeclared and fails the replay.

⚑ THE PORT'S PRIVATE HELPERS ARE NOT CALLED. `_size` and `_defcount` are reached through the
public surface (the dry-run `apply` rows and the parts of a bounded plan).
"""

from __future__ import annotations

import ast
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, cast

from mikemol.pycodemod import split, splitscope

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

CASES = Path(__file__).resolve().parent / "split.cases.json"

# ⚑ THE TWO DECLARED DEVIATIONS. A difference whose kind is not a key here is undeclared.
DECLARED: dict[str, str] = {
    "empty-part-00": (
        "the origin always emitted part 00 for the statements before the first def, even when it "
        "held only imports or nothing, and numbered the real parts from 01; the port keeps imports "
        "out of the packing, emits no part 00 when there is no base statement, and numbers from 00"
    ),
    "noqa-to-all": (
        "the origin marked each re-export `# noqa: F401`; the port emits no suppression comment "
        "and declares the re-exports in a generated `__all__`"
    ),
}

_BOUNDS: dict[str, split.Options] = {
    "ls.py": split.Options(max_lines=12),
    "md.py": split.Options(max_lines=500, max_defs=2),
}
_LINE_BOUND = 12
_PAIR = 2
_SIZED = 3


class CaseShapeError(ValueError):
    """The cases file is not the shape the W206 generator writes, or a case has no counterpart."""


@dataclass(frozen=True, slots=True)
class Call:
    """One origin call of a case: the function's name and its captured args, still as text."""

    fn: str
    args: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class Case:
    """One case: its name, the origin check it carries, its calls and its fixture."""

    name: str
    check: str
    calls: tuple[Call, ...]
    fixture: Mapping[str, str]

    @property
    def number(self) -> str:
        """The origin's selftest number, the leading digits of the name."""
        return self.name.split("-", 1)[0]


@dataclass(frozen=True, slots=True)
class Difference:
    """One way the port's plan differs from the origin's recorded one."""

    kind: str
    detail: str

    @property
    def declared(self) -> bool:
        """Whether this kind is a deviation the port makes on purpose."""
        return self.kind in DECLARED


@dataclass(frozen=True, slots=True)
class Outcome:
    """How one case came out: failures of its check, and differences from the origin's plan."""

    case: str
    failures: tuple[str, ...]
    differences: tuple[Difference, ...]

    @property
    def status(self) -> str:
        """`pass`, `declared` (only declared differences) or `differs`."""
        if self.failures or any(not d.declared for d in self.differences):
            return "differs"
        return "declared" if self.differences else "pass"


@dataclass(frozen=True, slots=True)
class Seen:
    """What the port answered to one call."""

    fn: str
    tops: tuple[splitscope.Statement, ...] = ()
    plan: split.Plan | None = None
    origin: Mapping[str, object] | None = None
    verified: bool = False
    counts: tuple[int, ...] = ()
    expected: tuple[int, ...] = ()


# ── reading the cases ─────────────────────────────────────────────────────────────────────────


def _fields(value: object, what: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise CaseShapeError(what)
    return {str(k): v for k, v in cast("dict[object, object]", value).items()}


def _items(value: object, what: str) -> list[object]:
    if not isinstance(value, list):
        raise CaseShapeError(what)
    return list(cast("list[object]", value))


def _texts(value: object, what: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, item in _fields(value, what).items():
        if not isinstance(item, str):
            raise CaseShapeError(what)
        out[key] = item
    return out


def _call(value: object) -> Call:
    fields = _fields(value, "operand")
    fn = fields.get("fn")
    if not isinstance(fn, str):
        msg = "operand fn"
        raise CaseShapeError(msg)
    return Call(fn.partition(":")[2], _texts(fields.get("args"), "operand args"))


def _case(value: object) -> Case:
    fields = _fields(value, "case")
    name = fields.get("case")
    if not isinstance(name, str):
        msg = "case name"
        raise CaseShapeError(msg)
    check = _fields(fields.get("origin"), "origin").get("check")
    return Case(
        name,
        check if isinstance(check, str) else "",
        tuple(_call(c) for c in _items(fields.get("operands"), "operands")),
        _texts(fields.get("fixture"), "fixture"),
    )


def load(path: Path = CASES) -> tuple[Case, ...]:
    """Read a cases file into its cases.

    Returns:
        the cases, in file order.

    """
    raw = cast("object", json.loads(path.read_text(encoding="utf-8")))
    return tuple(_case(c) for c in _items(raw, "cases"))


# ── running the port ──────────────────────────────────────────────────────────────────────────


def _literal(raw: str) -> object:
    try:
        return cast("object", ast.literal_eval(raw))
    except (ValueError, SyntaxError):
        return raw


# The origin's repr writes an empty set as `set()`, which is not a literal.
def _origin_literal(raw: str) -> object:
    return _literal(raw.replace("set()", "[]"))


def _options(args: Mapping[str, str]) -> split.Options:
    base = split.Options()
    lines = _literal(args["max_lines"]) if "max_lines" in args else base.max_lines
    defs = _literal(args["max_defs"]) if "max_defs" in args else base.max_defs
    return split.Options(
        max_lines=lines if isinstance(lines, int) else base.max_lines,
        max_defs=defs if isinstance(defs, int) else None,
    )


def _rehome(case: Case, root: Path) -> dict[str, str]:
    # Write the fixture under `root` and map each original path to its new one.
    if not case.fixture:
        return {}
    old = os.path.commonpath([str(Path(p).parent) for p in case.fixture])
    mapped: dict[str, str] = {}
    for path, text in case.fixture.items():
        target = root / os.path.relpath(path, old)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        mapped[path] = str(target)
    return mapped


def _defs_from(call: Call, root: Path) -> Seen:
    # `_defcount` is private: rebuild the module from the statement texts it counted over, plan it
    # under the definition bound, and count defs among the same ids in the port's own reading.
    raw = _fields(_origin_literal(call.args["by_i"]), "by_i")
    rows = {int(k): _fields(v, "by_i row") for k, v in raw.items()}
    source = root / "recount.py"
    source.write_text("".join(str(rows[i]["text"]) for i in sorted(rows)), encoding="utf-8")
    p = split.plan(str(source), split.Options(max_lines=500, max_defs=_PAIR))
    mine = {t.index: t for t in p.statements}
    wanted = [i for i in _items(_literal(call.args["ids"]), "ids") if isinstance(i, int)]
    return Seen(
        call.fn,
        plan=p,
        counts=(sum(1 for i in wanted if mine[i].is_def),),
        expected=(sum(1 for i in wanted if rows[i].get("is_def") is True),),
    )


def _size_from(call: Call, root: Path) -> Seen:
    # `_size` is private: its public face is the line count of each row `apply` reports.
    source = root / "sized.py"
    source.write_text("def a():\n    return 1\n\ndef b():\n    return 2\n", encoding="utf-8")
    p = split.plan(str(source), split.Options(max_lines=500, max_defs=1))
    rows = split.apply(p, write=False)
    return Seen(
        call.fn,
        plan=p,
        counts=tuple(r.lines for r in rows),
        expected=(len(call.args["code"].split("\n")),),
    )


def _run(case: Case, call: Call, root: Path, where: Mapping[str, str]) -> Seen:
    raw = call.args.get("path", "")
    path = where.get(raw, raw)
    if call.fn == "statements":
        got = splitscope.read(path)
        return Seen(call.fn, tops=got.tops if isinstance(got, splitscope.Source) else ())
    if call.fn == "plan":
        return Seen(call.fn, plan=split.plan(path, _options(call.args)))
    if call.fn == "verify":
        p = split.plan(path, _BOUNDS.get(Path(path).name, split.Options()))
        recorded = (
            _fields(_origin_literal(call.args["p"]), "origin plan") if "p" in call.args else None
        )
        return Seen(call.fn, plan=p, origin=recorded, verified=split.verify(p)[0])
    if call.fn == "_defcount":
        return _defs_from(call, root)
    if call.fn == "_size":
        return _size_from(call, root)
    msg = f"{case.name}: no port counterpart for {call.fn}"
    raise CaseShapeError(msg)


# ── comparing with the origin's recorded plan ─────────────────────────────────────────────────


def compare(origin: Mapping[str, object], p: split.Plan) -> tuple[Difference, ...]:
    """List how the port's plan differs from the origin's recorded one.

    Returns:
        every difference, each of a declared or an undeclared kind.

    """
    found: list[Difference] = []
    imports = {
        _fields(t, "top").get("i")
        for t in _items(origin.get("tops"), "origin tops")
        if _fields(t, "top").get("is_import") is True
    }
    parts = [_items(part, "origin part") for part in _items(origin.get("parts"), "origin parts")]
    kept = [[i for i in part if i not in imports] for part in parts]
    kept = [part for part in kept if part]
    if len(kept) < len(parts):
        found.append(Difference("empty-part-00", f"origin parts {parts} hold {len(kept)} real"))
    files = _texts(origin.get("files"), "origin files")
    if any("noqa" in text for text in files.values()) and "noqa" not in "".join(p.files.values()):
        found.append(Difference("noqa-to-all", "origin re-exports carry a suppression comment"))
    ported = [list(part.ids) for part in p.parts]
    if kept != ported:
        found.append(Difference("partition", f"origin {kept} against port {ported}"))
    return tuple(found)


# ── what each origin check claims of the port's answer ────────────────────────────────────────


def _named(seen: Seen) -> dict[str, splitscope.Statement]:
    return {t.name: t for t in seen.tops}


def _plan_of(seen: Seen) -> split.Plan:
    if seen.plan is None:
        msg = f"{seen.fn}: no plan was made"
        raise CaseShapeError(msg)
    return seen.plan


def _shadow(seen: Sequence[Seen]) -> list[str]:
    return [] if "TABLE" not in _named(seen[0])["f"].free else ["f depends on a shadowed TABLE"]


def _genuine(seen: Sequence[Seen]) -> list[str]:
    return [] if "TABLE" in _named(seen[0])["g"].free else ["g's read of TABLE is no dependency"]


def _impure_at(index: int) -> Callable[[Sequence[Seen]], list[str]]:
    def check(seen: Sequence[Seen]) -> list[str]:
        return [] if not seen[0].tops[index].is_pure else [f"statement {index} reads as pure"]

    return check


def _pure_first(seen: Sequence[Seen]) -> list[str]:
    return [] if seen[0].tops[0].is_pure else ["a bare-name assignment reads as impure"]


def _source_order(seen: Sequence[Seen]) -> list[str]:
    flat = [i for part in _plan_of(seen[0]).parts for i in part.ids]
    return [] if flat.index(2) < flat.index(3) else ["impure statements left source order"]


def _file_use(name: str, want: tuple[bool, bool]) -> Callable[[Sequence[Seen]], list[str]]:
    def check(seen: Sequence[Seen]) -> list[str]:
        got = _named(seen[0])[name]
        return [] if (got.reads_file, got.reads_source) == want else [f"{name} misread"]

    return check


def _several(seen: Sequence[Seen]) -> list[str]:
    ok = len(_plan_of(seen[0]).parts) > 1
    return [] if ok else ["a bound of 12 did not force a second part"]


def _under_bound(seen: Sequence[Seen]) -> list[str]:
    files = _plan_of(seen[0]).files
    return [f"over the bound: {n}" for n, c in files.items() if len(c.split("\n")) > _LINE_BOUND]


def _lossless(seen: Sequence[Seen]) -> list[str]:
    return [] if seen[0].verified else ["verify reported a lossy split"]


def _kept(needle: str) -> Callable[[Sequence[Seen]], list[str]]:
    def check(seen: Sequence[Seen]) -> list[str]:
        joined = "".join(_plan_of(seen[0]).files.values())
        return [] if needle in joined else [f"missing {needle!r}"]

    return check


def _doc_on_entry(seen: Sequence[Seen]) -> list[str]:
    files = _plan_of(seen[0]).files
    on_entry = "mod doc." in files["ls.py"]
    on_part = any("mod doc." in c for n, c in files.items() if n != "ls.py")
    return [] if on_entry and not on_part else ["the docstring left the entry module"]


def _every_part_imported(seen: Sequence[Seen]) -> list[str]:
    p = _plan_of(seen[0])
    entry = p.files[p.entry]
    return [f"{x.file} is not imported" for x in p.parts if x.file.removesuffix(".py") not in entry]


def _no_refusal(seen: Sequence[Seen]) -> list[str]:
    return [] if _plan_of(seen[0]).refusal is None else ["the plan was refused"]


def _size_gate(seen: Sequence[Seen]) -> list[str]:
    got = seen[0]
    sized = sorted(len(c.split("\n")) for c in _plan_of(got).files.values())
    ok = got.expected == (_SIZED,) and sorted(got.counts) == sized
    return [] if ok else [f"apply rows {got.counts} against split('\\n') counts {sized}"]


def _budget(seen: Sequence[Seen]) -> list[str]:
    p = _plan_of(seen[0])
    ok = p.refusal is not None and p.refusal.kind == "budget" and not p.files
    return [] if ok else ["an unsplittable statement was not refused on budget"]


def _names_it(seen: Sequence[Seen]) -> list[str]:
    p = _plan_of(seen[0])
    ok = p.refusal is not None and p.refusal.names == ("bg_00.py",)
    return [] if ok else ["the refusal does not name the part holding the statement"]


def _one_part(seen: Sequence[Seen]) -> list[str]:
    return [] if len(_plan_of(seen[0]).parts) == 1 else ["six small defs did not share a part"]


def _def_bound(seen: Sequence[Seen]) -> list[str]:
    sizes = [len(x.names) for x in _plan_of(seen[0]).parts]
    return [] if sizes == [_PAIR] * 3 else [f"max_defs=2 cut {sizes}"]


def _defs_counted(seen: Sequence[Seen]) -> list[str]:
    bad = [s for s in seen if s.counts != s.expected or s.counts[0] > _PAIR]
    return [] if not bad else [f"def counts differ from the origin's: {len(bad)} call(s)"]


def _unchanged(seen: Sequence[Seen]) -> list[str]:
    p = _plan_of(seen[0])
    again = split.plan(p.path, split.Options(max_lines=500))
    return [] if p.files == again.files else ["omitting max_defs changed the plan"]


def _never_fewer(seen: Sequence[Seen]) -> list[str]:
    p = _plan_of(seen[0])
    bounded = split.plan(p.path, split.Options(max_lines=500, max_defs=_PAIR))
    return [] if len(bounded.parts) >= len(p.parts) else ["a def bound produced fewer parts"]


def _more_than_pair(seen: Sequence[Seen]) -> list[str]:
    ok = len(_plan_of(seen[0]).parts) > _PAIR
    return [] if ok else ["a generous max_defs disabled the line bound"]


CHECKS: dict[str, Callable[[Sequence[Seen]], list[str]]] = {
    "307": _shadow,
    "308": _genuine,
    "309": _impure_at(2),
    "310": _impure_at(3),
    "311": _pure_first,
    "312": _source_order,
    "313": _file_use("near", (True, False)),
    "314": _file_use("own", (True, True)),
    "315": _file_use("neither", (True, False)),
    "316": _several,
    "317": _under_bound,
    "318": _lossless,
    "319": _kept("# ⚑ WHY a exists"),
    "320": _kept("return os.sep  # trailing"),
    "321": _doc_on_entry,
    "322": _every_part_imported,
    "323": _no_refusal,
    "324": _no_refusal,
    "325": _size_gate,
    "326": _budget,
    "327": _names_it,
    "328": _one_part,
    "329": _def_bound,
    "330": _defs_counted,
    "331": _lossless,
    "332": _unchanged,
    "333": _never_fewer,
    "334": _more_than_pair,
}


def judge(case: Case, root: Path) -> Outcome:
    """Run one case's calls through the port and judge the answers against the origin's check.

    Returns:
        the failures of the check and the differences from the origin's recorded plan.

    Raises:
        CaseShapeError: the case has no registered check.

    """
    where = _rehome(case, root)
    seen = [_run(case, call, root, where) for call in case.calls]
    check = CHECKS.get(case.number)
    if check is None:
        msg = f"{case.name}: no check registered"
        raise CaseShapeError(msg)
    differences = [
        d
        for s in seen
        if s.origin is not None and s.plan is not None
        for d in compare(s.origin, s.plan)
    ]
    return Outcome(case.name, tuple(check(seen)), tuple(differences))
