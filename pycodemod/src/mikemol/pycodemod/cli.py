# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""The driver: one `MODES` map over the ported library, plus refusing redirects.

Every retired or DO-NOT-PORT origin spelling gets one too. Cleanroomed against substrate's
`scratch/pycodemod.py` MODES table (W43; the DRIVER MODE MAP drafted in `.claude/queue.md`). This
slice wires the first three modes — `calls` (`sites.scan`), `owes` (`owes.fix_owes_callers`) and
`dead` (`dead.dead`) — plus every retired and DO-NOT-PORT origin flag as a subcommand that refuses
instead of silently accepting an argv the tool no longer answers, or never answered.

⚑⚑ EVERY PRINTER PRINTS ITS DENOMINATOR. `report.incomplete` is the one shared reporter (W46): a
mode that skipped files says how many, and how many were read, rather than a bare row count that
reads as complete either way.

⚑ RETIRED AND DO-NOT-PORT ARE SUBCOMMANDS, NOT SILENTLY-DROPPED FLAGS. Each old spelling still
parses — so a caller who typed it gets a named refusal — and each refusal exits 2, the same code
`owes` uses for a refused git revision: a caller cannot mistake either for a clean empty result.

⚑ `Namespace` ATTRIBUTES ARE NARROWED AT THE EDGE, once, the same discipline mdstruct's driver
uses: this package's mypy refuses an `Any` expression, and argparse hands every attribute back
untyped.
"""

from __future__ import annotations

import argparse
import sys
from typing import TYPE_CHECKING

from mikemol.pycodemod import report
from mikemol.pycodemod.dead import dead as run_dead
from mikemol.pycodemod.owes import GitRefusedError, fix_owes_callers
from mikemol.pycodemod.sites import Site, scan

if TYPE_CHECKING:
    from collections.abc import Sequence

_REFUSED = 2
_INTERNAL = "internal: argparse returned no"

# ⚑ A RETIRED SPELLING NAMES ITS SUCCESSOR MODE. Neither is wired yet in this slice (W34); the
# redirect is honest about that rather than silent about the flag's disappearance.
RETIRED = {
    "attr": "retired — the successor is `imports attr_reads` (not yet wired; W34)",
    "importers": "retired — the successor is `imports importers` (not yet wired; W34)",
}

# ⚑ A DO-NOT-PORT SPELLING NAMES WHERE IT STILL LIVES. These are substrate's own instruments
# (queue.md PYCODEMOD CENSUS/SQL/CONTROL/FINGERPRINT SURVEY), never ported here.
_DO_NOT_PORT_NAMES = (
    "types",
    "artifacts",
    "touches",
    "projects",
    "discriminates",
    "control",
    "fingerprint",
    "portable",
    "rawreads",
    "relalg",
    "snapshots",
    "sql",
    "collision-apex",
    "sqlname",
    "last",
)
DO_NOT_PORT = frozenset(_DO_NOT_PORT_NAMES)


def _str(ns: argparse.Namespace, name: str) -> str:
    raw: object = getattr(ns, name, None)
    if not isinstance(raw, str):
        msg = f"{_INTERNAL} {name} string"
        raise TypeError(msg)
    return raw


def _opt_str(ns: argparse.Namespace, name: str) -> str | None:
    raw: object = getattr(ns, name, None)
    if raw is None or isinstance(raw, str):
        return raw
    msg = f"{_INTERNAL} a string {name}"
    raise TypeError(msg)


def _str_list(ns: argparse.Namespace, name: str) -> list[str]:
    raw: object = getattr(ns, name, None)
    if not isinstance(raw, list):
        msg = f"{_INTERNAL} {name} list"
        raise TypeError(msg)
    return [str(item) for item in raw]


def _write_site(site: Site) -> None:
    sys.stdout.write(f"{site.kind} {site.name} {site.path}:{site.line}:{site.column}\n")


def _write_lines(lines: list[str]) -> None:
    for line in lines:
        sys.stdout.write(f"{line}\n")


def _handle_calls(ns: argparse.Namespace) -> int:
    paths = _str_list(ns, "paths")
    target = _opt_str(ns, "target")
    sites = scan(paths, target)
    for site in sites.rows:
        _write_site(site)
    lines, code = report.incomplete(
        [(s.why, s.error) for s in sites.skipped], len(sites.population)
    )
    _write_lines(lines)
    return code


def _handle_owes(ns: argparse.Namespace) -> int:
    name = _str(ns, "name")
    rev = _str(ns, "rev")
    root = _str(ns, "root")
    paths = _str_list(ns, "paths")
    try:
        owes = fix_owes_callers(name, rev, paths, root)
    except GitRefusedError as exc:
        sys.stdout.write(f"{exc}\n")
        return _REFUSED
    for site in owes.owed:
        _write_site(site)
    lines, code = report.incomplete([(s.why, s.error) for s in owes.skipped], owes.population)
    _write_lines(lines)
    return code


def _handle_dead(ns: argparse.Namespace) -> int:
    paths = _str_list(ns, "paths")
    sites = scan(paths)
    result = run_dead(sites)
    for row in result.dead:
        sys.stdout.write(f"dead {row.name} {row.path}:{row.line}\n")
    for exempt in result.exempt:
        sys.stdout.write(f"exempt {exempt.name} {exempt.path}:{exempt.line} ({exempt.why})\n")
    lines, code = report.incomplete(
        [(s.why, s.error) for s in result.skipped], len(sites.population)
    )
    _write_lines(lines)
    return code


MODES = {
    "calls": _handle_calls,
    "owes": _handle_owes,
    "dead": _handle_dead,
}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mikemol-pycodemod")
    sub = parser.add_subparsers(dest="mode", required=True)

    calls = sub.add_parser("calls", help="where a name is defined, called and used as a value")
    calls.add_argument("--target", default=None, help="a bare or dotted name; every name if unset")
    calls.add_argument("paths", nargs="+")

    owes = sub.add_parser("owes", help="uses of a name in files a revision did not touch")
    owes.add_argument("name")
    owes.add_argument("--rev", required=True, help="a git revision, or WORKING for the diff")
    owes.add_argument("--root", required=True, help="the repo root git resolves the revision in")
    owes.add_argument("paths", nargs="+")

    dead = sub.add_parser("dead", help="defs nothing in the corpus calls or uses")
    dead.add_argument("paths", nargs="+")

    for name in RETIRED:
        redirect = sub.add_parser(name)
        redirect.add_argument("rest", nargs=argparse.REMAINDER)
    for name in DO_NOT_PORT:
        redirect = sub.add_parser(name)
        redirect.add_argument("rest", nargs=argparse.REMAINDER)

    return parser


def main(argv: Sequence[str]) -> int:
    """Parse `argv` and run the named mode, or refuse a retired/DO-NOT-PORT spelling.

    Returns:
        the mode's exit code.

    """
    parser = _build_parser()
    ns = parser.parse_args(argv)
    mode = _str(ns, "mode")
    if mode in RETIRED:
        sys.stdout.write(f"{RETIRED[mode]}\n")
        return _REFUSED
    if mode in DO_NOT_PORT:
        sys.stdout.write(
            f"DO NOT PORT — still lives at substrate's scratch/pycodemod.py --{mode}\n"
        )
        return _REFUSED
    return MODES[mode](ns)


def _console() -> int:
    """Run `main` over the real argv, as the `mikemol-pycodemod` console-script entry point.

    Returns:
        the mode's exit code.

    """
    return main(sys.argv[1:])
