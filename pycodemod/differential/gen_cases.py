# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W206/W221: per-mode .cases.json from the W187 capture joined to the W126 mode map.

Each origin check i becomes one case, named "<i>-<slug>", in its mode's file beside this script.
The case keeps what the origin called (fn, operands) and the fixtures it read, never a
result: --impl fills that. A check declares `unmeasured`, with a reason, when no call was
captured (its capture class is the reason) or when it is listed in MISATTRIBUTED; either way
it is counted and never passes. Refuses (exit 1) unless every mode's case count equals the
mode map's.
"""

import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import cast

# W470: the generator, its two inputs and the case files it writes share one tracked home.
HOME = Path(__file__).resolve().parent
OUT = HOME

# Checks whose captured call is not what the check judges. Each is declared here with its
# reason, never by editing a generated case, so a regeneration keeps it.
_RE_SELFTEST = (
    "the check runs re.search on a literal (the regex's self-test); the captured "
    "shape_sites call is the previous check's, carried over (W220)"
)
_VARARGS = (
    "the capture keeps named parameters and drops *roots, so py_files replays with no "
    "argument and walks the whole default corpus"
)
_EARLIER = "the capture keeps only a check's latest call, and this check judges an earlier one:"
MISATTRIBUTED: dict[int, str] = {
    154: f"{_EARLIER} set(_t0) - set(_t1) needs the whole-file census _t0 (W215)",
    155: f"{_EARLIER} it reads the whole-file census _t0; the captured call is the split (W215)",
    156: f"{_EARLIER} it reads the whole-file census _t0; the captured call is the split (W215)",
    180: f"{_EARLIER} set(_t0) - set(_t2) needs the whole-file census _t0 (W215)",
    165: f"{_VARARGS}; the check also runs from the fixture dir as cwd (W219)",
    166: f"{_VARARGS}; the check judges that the call RAISES PopulationError (W219)",
    167: f"{_VARARGS} (W219)",
    160: "the check compares modes() against the module constant MODES, which no call "
    "returns, so the capture holds only one side of the comparison (W216)",
    188: _RE_SELFTEST,
    189: _RE_SELFTEST,
}

# W212/W222: the replay raises on these, and every raise is a capture defect, not an adapter
# gap (W36-differential.md ## W212). Declared per bucket until the capture is repaired.
_REPR = (
    "the capture stored a non-literal operand (an AST node, a registry, a mode table) as its "
    "repr, so the replay hands the callee a str (W212)"
)
_MODULE = "the recorded callee resolves to the module type itself, not a function (W212)"
_ABSENT = (
    "the recorded callee is a method, a selftest-local helper or a <genexpr>, not a "
    "module-level function, so the replay cannot find it (W212)"
)
_KNOCK_ON = "a downstream effect of a repr'd registry operand (W212)"
_BUCKETS: tuple[tuple[str, tuple[int, ...]], ...] = (
    (
        _REPR,
        (
            318,
            319,
            320,
            321,
            322,
            330,
            331,
            21,
            22,
            23,
            24,
            25,
            26,
            27,
            28,
            339,
            345,
            347,
            348,
            349,
            353,
            354,
            355,
            356,
            357,
            359,
        ),
    ),
    (_MODULE, (338, 340, 341, 346, 350, 351, 363, 369, 98, 102)),
    (_ABSENT, (336, 337, 342, 364, 365, 366, 367, 368, 9, 10, 11, 12, 13, 99, 100, 101)),
    (_KNOCK_ON, (335, 344)),
)
MISATTRIBUTED |= {i: reason for reason, cases in _BUCKETS for i in cases}

# W226: these checks read accounting that resorts() stamps on ITSELF (population, skipped,
# producer_population); the capture keeps return values only, so half of each claim is absent.
_FN_ATTRS = (
    "the check reads function attributes resorts() stamps on itself (population, skipped, "
    "producer_population); the capture keeps only the return value (W226)"
)
MISATTRIBUTED |= dict.fromkeys((388, 389, 390), _FN_ATTRS)

# W399: the same class beyond resorts: each check reads state a call does not RETURN, so the
# captured return value is not what it judges (found writing reifies/funcnames/ambient specs).
MISATTRIBUTED |= dict.fromkeys(
    (382, 383),
    "the check reads reifies.population/.skipped, attributes reifies() stamps on itself; the "
    "capture keeps only the return value (W399)",
)
MISATTRIBUTED |= dict.fromkeys(
    (397, 398),
    "the check reads portable_sites.core_built, an attribute portable_sites() stamps on "
    "itself; the capture keeps only the return value (W399)",
)
MISATTRIBUTED[407] = (
    "the check reads the module constant _amb.KNOWN_MISSES; no call returns it (W399)"
)
MISATTRIBUTED[408] = (
    "the check reads ambient.population, an attribute ambient() stamps on itself; the "
    "capture keeps only the return value (W399)"
)

# W408: a case the REFERENCE fails by the origin's own verdict is an expected denial, pinned
# by rule id (pytestspec reads the id before the first `:` of the deny message). 225 is the
# origin's one FAIL (W106: 407/408, row 225): `_DAG` moved to an import site, and
# module_state declines to classify an import, so the reference is denied by rule `225`.
EXPECTED_DENY: dict[int, list[str]] = {225: ["225"]}

# W455: a case whose only callee the port deliberately does not carry. pytestspec deselects it
# under every --impl but the origin (03fac34), so the reference still measures the origin here.
_NO_SQLNAME = (
    "the port carries no sqlname: pycodemod cli.py lists it in _DO_NOT_PORT_NAMES (the store's "
    "q_ query bridge stays with substrate)"
)
DO_NOT_PORT: dict[int, str] = dict.fromkeys(range(36, 41), _NO_SQLNAME)
# W443: portable_sites backs the `portable` mode, which the port declares do-not-port; a case
# already declared unmeasured keeps that (397, 398), since unmeasured is assigned first.
_NO_PORTABLE = (
    "the port carries no portable mode: pycodemod cli.py lists it in _DO_NOT_PORT_NAMES "
    "(portable_sites is substrate's raw-SQL EXPLAIN survey)"
)
DO_NOT_PORT |= dict.fromkeys(range(396, 399), _NO_PORTABLE)


class CaptureError(ValueError):
    """A W187 capture record is not the shape the capture writes."""


@dataclass(frozen=True)
class Call:
    """One origin call: the function, its repr'd operands, and the files it read."""

    fn: str
    operands: dict[str, str]
    fixtures: dict[str, str]


@dataclass(frozen=True)
class Record:
    """One origin check as captured."""

    i: int
    name: str
    line: int
    klass: str
    calls: list[Call]


def fields(value: object, what: str) -> dict[str, object]:
    """Narrow a decoded JSON object to string keys.

    Returns:
        the object, typed.

    Raises:
        CaptureError: when it is not an object with string keys.

    """
    if not isinstance(value, dict):
        raise CaptureError(what)
    out: dict[str, object] = {}
    for key, item in cast("dict[object, object]", value).items():
        if not isinstance(key, str):
            raise CaptureError(what)
        out[key] = item
    return out


def text(value: object, what: str) -> str:
    """Narrow to str.

    Returns:
        the string.

    Raises:
        CaptureError: when it is not one.

    """
    if not isinstance(value, str):
        raise CaptureError(what)
    return value


def number(value: object, what: str) -> int:
    """Narrow to int (a JSON bool is not a number here).

    Returns:
        the int.

    Raises:
        CaptureError: when it is not one.

    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise CaptureError(what)
    return value


def str_map(value: object, what: str) -> dict[str, str]:
    """Narrow to a {str: str} object.

    Returns:
        the mapping, typed.

    """
    return {k: text(v, what) for k, v in fields(value, what).items()}


def record(line: str) -> Record:
    """Parse one capture line.

    Returns:
        the typed record.

    Raises:
        CaptureError: when a field is missing or mistyped.

    """
    rec = fields(cast("object", json.loads(line)), "record")
    raw_calls = rec.get("calls")
    if not isinstance(raw_calls, list):
        msg = "calls"
        raise CaptureError(msg)
    calls: list[Call] = []
    for raw in cast("list[object]", raw_calls):
        call = fields(raw, "call")
        calls.append(
            Call(
                fn=text(call.get("fn"), "fn"),
                operands=str_map(call.get("operands"), "operands"),
                fixtures=str_map(call.get("fixtures", {}), "fixtures"),
            )
        )
    return Record(
        i=number(rec.get("i"), "i"),
        name=text(rec.get("name"), "name"),
        line=number(rec.get("line"), "line"),
        klass=text(rec.get("class"), "class"),
        calls=calls,
    )


def slug(value: str) -> str:
    """Lowercase, hyphenated, at most 60 characters.

    Returns:
        the slug, or "case" when nothing survives.

    """
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:60] or "case"


def mode_file(mode: str) -> str:
    """Name a mode's case file; the pre-section checks are the preamble.

    Returns:
        the file stem.

    """
    return "preamble" if mode.startswith("(") else slug(mode)


def case_of(rec: Record) -> dict[str, object]:
    """Build one case, declaring a disposition when the capture cannot measure it.

    Returns:
        the case as it is written to JSON.

    """
    case: dict[str, object] = {
        "case": f"{rec.i:03d}-{slug(rec.name)}",
        "origin": {"check": rec.name, "line": rec.line, "class": rec.klass},
        "operands": [{"fn": c.fn, "args": c.operands} for c in rec.calls],
        "fixture": {k: v for c in rec.calls for k, v in c.fixtures.items()},
    }
    if not rec.calls:
        case["disposition"] = "unmeasured"
        case["reason"] = f"no call captured (capture class {rec.klass}, W187)"
    elif rec.i in MISATTRIBUTED:
        case["disposition"] = "unmeasured"
        case["reason"] = MISATTRIBUTED[rec.i]
    elif rec.i in DO_NOT_PORT:
        case["disposition"] = "do-not-port"
        case["reason"] = DO_NOT_PORT[rec.i]
    if rec.i in EXPECTED_DENY:
        case["expect"] = {"deny": EXPECTED_DENY[rec.i]}
    return case


def main() -> int:
    """Write every mode's case file and compare counts with the mode map.

    Returns:
        0 when every mode's count matches the map, else 1.

    """
    modes: dict[int, str] = {}
    for row in (HOME / "origin-modes.tsv").read_text(encoding="utf-8").splitlines():
        cells = row.split("\t")
        modes[int(cells[0])] = cells[1]
    by_mode: dict[str, list[dict[str, object]]] = {}
    for line in (HOME / "captured.jsonl").read_text(encoding="utf-8").splitlines():
        rec = record(line)
        by_mode.setdefault(mode_file(modes[rec.i]), []).append(case_of(rec))
    OUT.mkdir(exist_ok=True)
    for name, cases in sorted(by_mode.items()):
        path = OUT / f"{name}.cases.json"
        path.write_text(json.dumps(cases, indent=1) + "\n", encoding="utf-8")
    want = Counter(mode_file(m) for m in modes.values())
    got = Counter({name: len(cases) for name, cases in by_mode.items()})
    unmeasured = sum(1 for cs in by_mode.values() for c in cs if "disposition" in c)
    for name in sorted(want | got):
        mark = "" if want[name] == got[name] else "  MISMATCH"
        sys.stdout.write(f"{name}\t{got[name]}\t{want[name]}{mark}\n")
    sys.stdout.write(f"total {got.total()} vs map {want.total()}; unmeasured {unmeasured}\n")
    return 0 if want == got else 1


sys.exit(main())
