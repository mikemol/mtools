# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The default evaluator: a pinned `opa eval` over one spec and one case.

⚑⚑ AN ABSENT OR WRONG-VERSION opa IS AN ERROR, NEVER A SKIP. A spec that was not evaluated has
measured nothing. The pin is the version luthen's specs are written against: a different opa is
a different checker, and its verdicts are not these specs' verdicts.
"""

import json
import shutil
import subprocess
from pathlib import Path
from typing import cast

from mikemol.pytestspec.spec import Case, Evaluator, SpecDataError, Verdict

PINNED = "1.20.2"
# ⚑ BOUNDED: a hung opa must fail the case, not hang the suite.
_TIMEOUT = 60


class OpaUnavailableError(RuntimeError):
    """opa is absent, is not the pinned version, or failed to evaluate."""


def _field(text: str, prefix: str) -> str | None:
    """Find the first line starting with `prefix` (after leading space).

    ⚑ Line parsing, not a regex: `re.Match.group` is typed `str | Any`, which the strict bar
    refuses, and these are one-token fields.

    Returns:
        the first whitespace-delimited token after the prefix, or None.

    """
    for line in text.splitlines():
        rest = line.strip()
        if rest.startswith(prefix):
            tokens = rest.removeprefix(prefix).split()
            return tokens[0] if tokens else None
    return None


def resolve(opa: str = "opa") -> str:
    """Find opa and confirm it is the pinned version.

    Returns:
        the absolute path of the opa binary.

    Raises:
        OpaUnavailableError: opa is not on PATH, `opa version` fails, or it is not `PINNED`.

    """
    path = shutil.which(opa)
    if path is None:
        msg = f"opa not found on PATH (need {PINNED})"
        raise OpaUnavailableError(msg)
    proc = subprocess.run(
        [path, "version"], capture_output=True, text=True, check=False, timeout=_TIMEOUT
    )
    version = _field(proc.stdout, "Version:")
    if proc.returncode != 0 or version is None:
        msg = f"{path} version: exit {proc.returncode}, no Version line"
        raise OpaUnavailableError(msg)
    if version != PINNED:
        msg = f"{path} is opa {version}, not the pinned {PINNED}"
        raise OpaUnavailableError(msg)
    return path


def package_of(spec: Path) -> str:
    """Read a spec's Rego package.

    Returns:
        the dotted package name, as in `package pycodemod.guarded`.

    Raises:
        SpecDataError: the spec declares no package.

    """
    name = _field(spec.read_text(encoding="utf-8"), "package ")
    if name is None:
        msg = f"{spec.name}: no `package` line"
        raise SpecDataError(msg)
    return name


def _strings(value: object) -> tuple[str, ...]:
    """Read a Rego set (JSON list) of messages as strings, sorted so order never matters.

    Returns:
        the messages; an absent rule reads as none.

    """
    if not isinstance(value, list):
        return ()
    return tuple(sorted(str(v) for v in cast("list[object]", value)))


def _first(value: object) -> object:
    """Take the first element of a JSON list.

    Returns:
        the element, or None when `value` is not a non-empty list.

    """
    if isinstance(value, list) and value:
        return cast("list[object]", value)[0]
    return None


def _key(value: object, key: str) -> object:
    """Read one key of a JSON object.

    Returns:
        the value, or None when `value` is not an object.

    """
    if isinstance(value, dict):
        return cast("dict[str, object]", value).get(key)
    return None


def verdict_from(output: str) -> Verdict:
    """Parse `opa eval --format json` output for `data.<package>`.

    ⚑ An EMPTY result (the package is undefined, so opa found nothing to evaluate) is WITHHELD,
    not admitted: no rule ran, so nothing was measured.

    Returns:
        the case's verdict.

    """
    doc = cast("object", json.loads(output))
    value = _key(_first(_key(_first(_key(doc, "result")), "expressions")), "value")
    if not isinstance(value, dict):
        return Verdict(withheld=("opa returned no package document: nothing was evaluated",))
    # ⚑⚑ MEASURED (W200): `package s` with NO RULES evaluates to `{}`, and read as ADMITTED — a
    # spec with nothing in it passed every case. A defined `deny` rule is an empty set when
    # nothing is denied, so an ABSENT `deny` key means no rule could deny: withheld.
    if "deny" not in value:
        return Verdict(withheld=("the spec defines no `deny` rule: nothing could fail",))
    return Verdict(deny=_strings(_key(value, "deny")), withheld=_strings(_key(value, "withheld")))


def evaluator(opa: str = "opa") -> Evaluator:
    """Build the default evaluator; opa is resolved and version-checked on first use.

    Returns:
        a callable that evaluates one case against one spec.

    """
    resolved: list[str] = []

    def evaluate(spec: Path, case: Case) -> Verdict:
        if not resolved:
            resolved.append(resolve(opa))
        proc = subprocess.run(
            [
                resolved[0],
                "eval",
                "--format",
                "json",
                "--stdin-input",
                "--data",
                str(spec),
                f"data.{package_of(spec)}",
            ],
            input=json.dumps(case),
            capture_output=True,
            text=True,
            check=False,
            timeout=_TIMEOUT,
        )
        if proc.returncode != 0:
            msg = f"opa eval exit {proc.returncode}: {proc.stderr.strip()[:500]}"
            raise OpaUnavailableError(msg)
        return verdict_from(proc.stdout)

    return evaluate
