# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A spec's cases, and the judgment of one case's verdict. No pytest here; the plugin wraps it.

⚑⚑ ONLY `admitted` PASSES. A case the spec denies fails with the deny messages; a case the spec
WITHHOLDS (it has no rule for it) fails as UNMEASURED. It is never a skip, because a skip renders
as a pass in every summary that counts passes, and an unmeasured case is not a passed one.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

CASES_SUFFIX = ".cases.json"


class SpecDataError(ValueError):
    """A spec's case data is absent or malformed."""


@dataclass(frozen=True)
class Verdict:
    """What the spec said about one case: its deny messages and its withheld reasons."""

    deny: tuple[str, ...] = ()
    withheld: tuple[str, ...] = ()


# ⚑ THE EVALUATOR IS A SEAM (W199), so the mapping is witnessed before any opa exists. W200
# supplies the real one: the spec path and one case in, the spec's verdict out.
type Case = dict[str, object]
type Evaluator = Callable[[Path, Case], Verdict]


def cases_path(spec: Path) -> Path:
    """Locate a spec's case data.

    Returns:
        `<stem>.cases.json` beside the spec: `guarded.rego` reads `guarded.cases.json`.

    """
    return spec.with_name(spec.name.removesuffix(".rego") + CASES_SUFFIX)


def load_cases(spec: Path) -> list[tuple[str, Case]]:
    """Read a spec's case data: a JSON list of objects, each naming its `case`.

    Returns:
        (case name, case object) pairs, in file order.

    Raises:
        SpecDataError: the file is absent, is not JSON, or a record is not an object with a
            string `case`. ⚑ An absent file is an ERROR, not zero cases: a spec with no cases
            would otherwise collect nothing and read as a clean run.

    """
    path = cases_path(spec)
    if not path.is_file():
        msg = f"{spec.name}: no case data at {path.name}"
        raise SpecDataError(msg)
    try:
        raw = cast("object", json.loads(path.read_text(encoding="utf-8")))
    except json.JSONDecodeError as exc:
        msg = f"{path.name}: not JSON ({exc.msg})"
        raise SpecDataError(msg) from exc
    if not isinstance(raw, list) or not raw:
        msg = f"{path.name}: expected a non-empty JSON list of cases"
        raise SpecDataError(msg)
    out: list[tuple[str, Case]] = []
    for i, rec in enumerate(cast("list[object]", raw)):
        if not isinstance(rec, dict):
            msg = f"{path.name}: record {i} is not an object"
            raise SpecDataError(msg)
        case = cast("Case", rec)
        name = case.get("case")
        if not isinstance(name, str) or not name:
            msg = f"{path.name}: record {i} has no string `case`"
            raise SpecDataError(msg)
        out.append((name, case))
    return out


def judge(verdict: Verdict) -> str | None:
    """Map a verdict to a pytest outcome.

    Returns:
        None when the case is admitted (nothing denied, nothing withheld); otherwise the failure
        text. Deny is reported before withheld: a case both denied and withheld is a failure
        either way, and the deny is the finding.

    """
    if verdict.deny:
        return "DENIED: " + "; ".join(verdict.deny)
    if verdict.withheld:
        return "UNMEASURED (withheld, not passed): " + "; ".join(verdict.withheld)
    return None


# ⚑⚑ A DISPOSITION IS A DECLARATION, AND EVERY ONE MUST ARGUE ITSELF WITH A `reason` (W201).
#   do-not-port  the origin behaviour is deliberately not carried; the case is not run, and is
#                COUNTED in the collection report, so a deselection is never silent.
#   unmeasured   the author declares the case cannot be measured yet: xfail(strict). It never
#                reads as a pass, and if it starts passing the run FAILS until the declaration
#                is removed. An UNDECLARED withheld verdict stays a plain FAIL (W199).
#   port-fix     the port deliberately corrects the origin: the case must name the case that
#                pins the origin's row (`pairs_with`), so both sides stay pinned.
DO_NOT_PORT = "do-not-port"
UNMEASURED = "unmeasured"
PORT_FIX = "port-fix"
DISPOSITIONS = (DO_NOT_PORT, UNMEASURED, PORT_FIX)


@dataclass(frozen=True)
class Disposition:
    """A case's declared disposition, its reason, and (for port-fix) its paired case."""

    kind: str
    reason: str
    pairs_with: str | None = None


def disposition_of(name: str, case: Case, names: frozenset[str]) -> Disposition | None:
    """Read and validate a case's declared disposition.

    Returns:
        the Disposition, or None when the case declares none.

    Raises:
        SpecDataError: an unknown disposition, a missing `reason`, or a port-fix whose
            `pairs_with` names no other case in the same spec.

    """
    kind = case.get("disposition")
    if kind is None:
        return None
    if not isinstance(kind, str) or kind not in DISPOSITIONS:
        msg = f"case {name}: disposition {kind!r} is not one of {', '.join(DISPOSITIONS)}"
        raise SpecDataError(msg)
    reason = case.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        msg = f"case {name}: a {kind} disposition needs a `reason`"
        raise SpecDataError(msg)
    if kind != PORT_FIX:
        return Disposition(kind, reason)
    pair = case.get("pairs_with")
    if not isinstance(pair, str) or pair == name or pair not in names:
        msg = f"case {name}: port-fix `pairs_with` must name another case in this spec"
        raise SpecDataError(msg)
    return Disposition(kind, reason, pair)
