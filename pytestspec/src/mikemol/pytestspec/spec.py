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
