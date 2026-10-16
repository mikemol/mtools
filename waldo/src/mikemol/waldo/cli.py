# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The waldo command line and the standard invocation shape it prints (W1059).

A repo's own waldo is a few lines that build `Seams` and call `main`; this module reads
`--set NAME [--dry]`, loads `<contracts>/NAME.json`, runs the pipeline, writes the diff to stderr
and the verdict as ONE JSON line to stdout.

⚑ THE STANDARD INVOCATION SHAPE (operator note via github-8f, 2026-10-12): the permission
classifier fires on the SHAPE of a command, and it will probably not object to

    env -C <repo> <absolute interpreter> -m <module> --set <name> [--dry]

An absolute interpreter, the working directory set by `env -C`, one module, a named declared set,
and no pipe, chaining or inline script. `invocation` builds exactly that and nothing else, and
`matches_shape` is the test every command a waldo prints (a refusal's `run`, a halt, a waypoint's
`--next`) must pass. The classifier staying quiet is not a guarantee; the declared set and the
witnesses are the safety.
"""

import argparse
import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from mikemol.waldo.contract import ContractError, parse
from mikemol.waldo.custody import Secret
from mikemol.waldo.pipeline import EXIT_CANNOT, EXIT_OK, Seams, Verdict, execute, verdict_line

SHAPE = re.compile(r"env -C (/[\w./-]+) (/[\w./-]+) -m ([A-Za-z_][\w.]*) --set ([\w.-]+)( --dry)?")


def matches_shape(command: str) -> bool:
    """Say whether a command is of the standard invocation shape.

    Returns:
        True for `env -C <abs repo> <abs interpreter> -m <module> --set <name> [--dry]` exactly.

    """
    return SHAPE.fullmatch(command) is not None


def invocation(repo: Path, interpreter: Path, module: str, name: str, *, dry: bool = False) -> str:
    """Build the standard invocation for a named set.

    Returns:
        the command text.

    Raises:
        ValueError: when a path is not absolute or the built command is not of the standard shape
            (a space or a shell character in a name, for instance).

    """
    if not repo.is_absolute() or not interpreter.is_absolute():
        msg = "the repo and the interpreter must be absolute paths"
        raise ValueError(msg)
    command = f"env -C {repo} {interpreter} -m {module} --set {name}" + (" --dry" if dry else "")
    if not matches_shape(command):
        msg = f"not of the standard invocation shape: {command!r}"
        raise ValueError(msg)
    return command


def _load(contracts: Path, name: str) -> object:
    """Read a contract file.

    Returns:
        the parsed JSON.

    Raises:
        ContractError: when there is no such set or it is not JSON.

    """
    path = contracts / f"{name}.json"
    try:
        return cast("object", json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError) as problem:
        msg = f"cannot read set {name}: {problem}"
        raise ContractError(msg) from problem


def _emit(verdict: Verdict) -> None:
    """Write the diff lines to stderr and the verdict line to stdout."""
    diff = verdict.get("diff")
    if isinstance(diff, list):
        for line in cast("list[object]", diff):
            sys.stderr.write(f"{line}\n")
    sys.stdout.write(verdict_line(verdict) + "\n")


def main(
    argv: Sequence[str] | None,
    seams: Seams,
    contracts: Path,
    *,
    command: str | None = None,
    secrets: Sequence[Secret] = (),
) -> int:
    """Run the named set and print the one verdict line.

    `command`, when given, is the standard invocation of this waldo; it must match the shape and is
    attached to every verdict that is not a success, as `run`.

    Returns:
        0 matched, applied or converged; 1 refused or a step failed; 2 cannot run.

    Raises:
        ValueError: when `command` is not of the standard shape.

    """
    if command is not None and not matches_shape(command):
        msg = f"not of the standard invocation shape: {command!r}"
        raise ValueError(msg)
    ap = argparse.ArgumentParser(prog="waldo", description="Run a declared set.")
    ap.add_argument("--set", required=True, help="the name of <contracts>/<name>.json")
    ap.add_argument("--dry", action="store_true", help="plan and compare; apply nothing")
    ns = ap.parse_args(list(sys.argv[1:] if argv is None else argv))
    name: str = ns.set
    dry: bool = ns.dry
    try:
        contract = parse(_load(contracts, name))
    except ContractError as problem:
        _emit({"state": "cannot-run", "why": str(problem)})
        return EXIT_CANNOT
    code, verdict = execute(contract, seams, dry=dry, secrets=secrets)
    if code != EXIT_OK and command is not None:
        verdict = {**verdict, "run": command}
    _emit(verdict)
    return code
