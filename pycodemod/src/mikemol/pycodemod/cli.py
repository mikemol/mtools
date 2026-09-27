# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""The driver: one `MODES` map over the ported library, plus refusing redirects.

Every retired or DO-NOT-PORT origin spelling gets one too. Cleanroomed against substrate's
`scratch/pycodemod.py` MODES table (W43; the DRIVER MODE MAP drafted in `.claude/queue.md`). This
slice adds `bindings` (`definitions.bindings`) to the twenty-three modes already wired:
`calls`
(`sites.scan`), `owes` (`owes.fix_owes_callers`), `dead` (`dead.dead`), `attr-reads`
(`imports.attr_reads`), `importers` (`imports.importers`), `swallows` (`swallows.swallows`),
`exits` (`exit.exits`), `verdicts` (`graph.verdict_returners`), `disagreement`
(`placement.disagreement`), `placement` (`placement.placement`, default forms) and
`modstate` (`modstate.module_state`), `layout` (`layout.layout`), `collisions`
(`rivals.collisions`), `reifies` (`ordering.reifies`), `escapes` (`core.escapes`),
`catchers` (`exit.catchers`), `interlock` (`exit.interlock`) and `commentary-lost`
(`commentary.commentary_lost` over `owes.git_show`), `ambient` (`ambient.ambient`) and
`callgraph` (`graph.callgraph`), `reaches` (`graph.reaches`), `guarded`
(`arguments.guarded`) and `key-reads` (`strings.key_reads`).

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
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.pycodemod import report
from mikemol.pycodemod.ambient import ambient as run_ambient
from mikemol.pycodemod.arguments import guarded as run_guarded
from mikemol.pycodemod.commentary import commentary_lost as run_commentary_lost
from mikemol.pycodemod.core import escapes as run_escapes
from mikemol.pycodemod.dead import dead as run_dead
from mikemol.pycodemod.definitions import bindings as run_bindings
from mikemol.pycodemod.exit import catchers as run_catchers
from mikemol.pycodemod.exit import exits as run_exits
from mikemol.pycodemod.exit import interlock as run_interlock
from mikemol.pycodemod.graph import DEPTH, callgraph, reaches, verdict_returners
from mikemol.pycodemod.imports import attr_reads
from mikemol.pycodemod.imports import importers as run_importers
from mikemol.pycodemod.layout import layout as run_layout
from mikemol.pycodemod.modstate import module_state
from mikemol.pycodemod.ordering import reifies as run_reifies
from mikemol.pycodemod.owes import GitRefusedError, fix_owes_callers, git_show
from mikemol.pycodemod.placement import disagreement as run_disagreement
from mikemol.pycodemod.placement import placement as run_placement
from mikemol.pycodemod.rivals import collisions as run_collisions
from mikemol.pycodemod.sites import Site, scan
from mikemol.pycodemod.strings import key_reads
from mikemol.pycodemod.swallows import swallows as run_swallows

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mikemol.pycodemod.core import Escape
    from mikemol.pycodemod.exit import Catcher, ExitRow, Interlock
    from mikemol.pycodemod.graph import VerdictDef
    from mikemol.pycodemod.imports import AttrRead, ImportRow
    from mikemol.pycodemod.layout import Group
    from mikemol.pycodemod.modstate import ModuleState
    from mikemol.pycodemod.ordering import Reification
    from mikemol.pycodemod.placement import Disagreement, Placement
    from mikemol.pycodemod.rivals import Collision
    from mikemol.pycodemod.swallows import Swallow

_REFUSED = 2
_INTERNAL = "internal: argparse returned no"
_ABSENT = "-"
_UNREAD = ("unread", "unreadable, undecodable or uncompilable")

# ⚑ `--attr` and `--importers` are WIRED, as `attr-reads` and `importers` (W34): they stop being
# redirects and become real modes. Nothing else here is retired yet.
RETIRED: dict[str, str] = {}

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


def _int(ns: argparse.Namespace, name: str) -> int:
    raw: object = getattr(ns, name, None)
    if not isinstance(raw, int):
        msg = f"{_INTERNAL} {name} int"
        raise TypeError(msg)
    return raw


def _str_list(ns: argparse.Namespace, name: str) -> list[str]:
    raw: object = getattr(ns, name, None)
    if not isinstance(raw, list):
        msg = f"{_INTERNAL} {name} list"
        raise TypeError(msg)
    return [str(item) for item in raw]


def _write_site(site: Site) -> None:
    sys.stdout.write(f"{site.kind} {site.name} {site.path}:{site.line}:{site.column}\n")


def _write_attr_read(row: AttrRead) -> None:
    sys.stdout.write(
        f"attr {row.receiver}.{row.attr} {row.path}:{row.line}:{row.column} ({row.context})\n"
    )


def _write_import_row(row: ImportRow) -> None:
    sys.stdout.write(f"{row.form} {','.join(row.names)} {row.path}:{row.line}\n")


def _write_swallow(row: Swallow) -> None:
    sys.stdout.write(
        f"swallow {row.kind} exit={row.exit} feeds={row.feeds} {row.path}:{row.line}\n"
    )


def _write_exit_row(row: ExitRow) -> None:
    sys.stdout.write(f"exit {row.verdict} {row.spelling} {row.path}:{row.line} ({row.why})\n")


def _write_verdict(row: VerdictDef) -> None:
    sys.stdout.write(f"verdict {row.name} {','.join(row.kinds)} {row.path}:{row.line}\n")


def _write_interlock(row: Interlock) -> None:
    owner = row.defname or _ABSENT
    sys.stdout.write(f"interlock {row.callee} {owner} {row.path}:{row.line}\n")


def _write_catcher(row: Catcher) -> None:
    owner = row.defname or _ABSENT
    sys.stdout.write(
        f"catcher {row.kind} silent={row.silent} reraises={row.reraises} {owner} "
        f"{row.path}:{row.line}\n"
    )


def _write_escape(row: Escape) -> None:
    sys.stdout.write(f"escape {row.seq!r} {row.path}:{row.line} {row.text}\n")


def _write_reification(row: Reification) -> None:
    sys.stdout.write(f"reifies {row.why} {row.kind} {row.name} {row.path}:{row.line}\n")


def _write_collision(row: Collision) -> None:
    sites = ",".join(f"{path}:{line}" for path, line in row.sites)
    sys.stdout.write(f"collision {row.name} {sites}\n")


def _write_group(row: Group) -> None:
    sys.stdout.write(
        f"layout {row.kind} {row.name} code={row.code} {row.path}:{row.first}-{row.last}\n"
    )


def _write_module_state(row: ModuleState) -> None:
    mutators = ",".join(row.mutators) or _ABSENT
    sys.stdout.write(
        f"modstate {row.klass} {row.kind} {row.name} mutators={mutators} {row.path}:{row.line}\n"
    )


def _write_placement(row: Placement) -> None:
    sys.stdout.write(f"placement {row.verdict} {row.form} {row.path}:{row.line}\n")


def _write_disagreement(row: Disagreement) -> None:
    intent = row.intent.verdict if row.intent else _ABSENT
    snapshot = row.snapshot.verdict if row.snapshot else _ABSENT
    store = row.store.form if row.store else _ABSENT
    sys.stdout.write(
        f"disagreement {row.kind} {row.path} intent={intent} snapshot={snapshot} store={store}\n"
    )


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


def _handle_callgraph(ns: argparse.Namespace) -> int:
    paths = _str_list(ns, "paths")
    sites = scan(paths)
    graph = callgraph(sites)
    for (path, scope), callees in sorted(graph.items()):
        for callee in sorted(callees):
            sys.stdout.write(f"edge {path}:{scope} -> {callee}\n")
    lines, code = report.incomplete(
        [(s.why, s.error) for s in sites.skipped], len(sites.population)
    )
    _write_lines(lines)
    return code


def _handle_reaches(ns: argparse.Namespace) -> int:
    paths = _str_list(ns, "paths")
    path, _, scope = _str(ns, "start").rpartition(":")
    depth = _int(ns, "depth")
    sites = scan(paths)
    reach = reaches(callgraph(sites), (path, scope), set(_str_list(ns, "target")), depth)
    if not reach.known_start:
        sys.stdout.write(f"refused: no caller {path}:{scope} in the scanned graph\n")
        return _REFUSED
    for target, trail in sorted(reach.found.items()):
        sys.stdout.write(f"reaches {target} via {' -> '.join(trail)}\n")
    if reach.exhausted:
        sys.stdout.write(f"depth {depth} cut the walk short: an absent target is unknown\n")
    lines, code = report.incomplete(
        [(s.why, s.error) for s in sites.skipped], len(sites.population)
    )
    _write_lines(lines)
    return code


def _handle_guarded(ns: argparse.Namespace) -> int:
    paths = _str_list(ns, "paths")
    sites = scan(paths, _opt_str(ns, "target"))
    result = run_guarded(sites)
    for where, conds in result.under:
        tests = " / ".join(str(c) for c in conds)
        sys.stdout.write(f"under {where.path}:{where.line}:{where.column} if {tests}\n")
    for where in result.top:
        sys.stdout.write(f"top {where.path}:{where.line}:{where.column}\n")
    lines, code = report.incomplete(
        [(s.why, s.error) for s in sites.skipped], len(sites.population)
    )
    _write_lines(lines)
    return code


def _handle_key_reads(ns: argparse.Namespace) -> int:
    paths = _str_list(ns, "paths")
    result = key_reads(paths, _str(ns, "key"))
    for row in result.rows:
        sys.stdout.write(f"key {row.kind} {row.path}:{row.line} ({row.context})\n")
    lines, code = report.incomplete([(s.why, s.error) for s in result.skipped], len(paths))
    _write_lines(lines)
    return code


def _handle_bindings(ns: argparse.Namespace) -> int:
    paths = _str_list(ns, "paths")
    result = run_bindings(paths, _str(ns, "name"))
    for row in result.rows:
        first, last = row.live
        sys.stdout.write(
            f"binding {row.kind} {row.qualname} {row.path}:{row.line} live={first}-{last}\n"
        )
    lines, code = report.incomplete([(s.why, s.error) for s in result.skipped], len(paths))
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


def _handle_commentary_lost(ns: argparse.Namespace) -> int:
    rev = _str(ns, "rev")
    root = _str(ns, "root")
    paths = _str_list(ns, "paths")
    try:
        show = git_show(rev, root)
    except GitRefusedError as exc:
        sys.stdout.write(f"{exc}\n")
        return _REFUSED
    result = run_commentary_lost(paths, Path(root), show)
    for text in result.lost:
        sys.stdout.write(f"lost {','.join(result.origins[text])} {text}\n")
    for text in result.gained:
        sys.stdout.write(f"gained {text}\n")
    for rel in result.absent_before:
        sys.stdout.write(f"absent-before {rel}\n")
    sys.stdout.write(f"commentary-lost before={result.n_before} after={result.n_after}\n")
    lines, code = report.incomplete([_UNREAD for _ in result.unread], len(paths))
    _write_lines(lines)
    return code


def _handle_ambient(ns: argparse.Namespace) -> int:
    paths = _str_list(ns, "paths")
    result = run_ambient(paths, Path(_str(ns, "root")))
    for row in result.rows:
        sys.stdout.write(
            f"ambient {row.verdict} {row.kind} {row.path}:{row.line} {row.shown} ({row.context})\n"
        )
    lines, code = report.incomplete([(s.why, s.error) for s in result.skipped], result.population)
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


def _handle_attr_reads(ns: argparse.Namespace) -> int:
    paths = _str_list(ns, "paths")
    query = _str(ns, "query")
    result = attr_reads(paths, query)
    for row in result.rows:
        _write_attr_read(row)
    lines, code = report.incomplete([(s.why, s.error) for s in result.skipped], len(paths))
    _write_lines(lines)
    return code


def _handle_importers(ns: argparse.Namespace) -> int:
    paths = _str_list(ns, "paths")
    module = _str(ns, "module")
    result = run_importers(paths, module)
    for row in result.rows:
        _write_import_row(row)
    lines, code = report.incomplete([(s.why, s.error) for s in result.skipped], len(paths))
    _write_lines(lines)
    return code


def _handle_swallows(ns: argparse.Namespace) -> int:
    paths = _str_list(ns, "paths")
    result = run_swallows(paths)
    for row in result.rows:
        _write_swallow(row)
    lines, code = report.incomplete([(s.why, s.error) for s in result.skipped], len(paths))
    _write_lines(lines)
    return code


def _handle_exits(ns: argparse.Namespace) -> int:
    paths = _str_list(ns, "paths")
    result = run_exits(paths)
    for row in result.rows:
        _write_exit_row(row)
    lines, code = report.incomplete([(s.why, s.error) for s in result.skipped], len(paths))
    _write_lines(lines)
    return code


def _handle_verdicts(ns: argparse.Namespace) -> int:
    paths = _str_list(ns, "paths")
    result = verdict_returners(paths)
    for row in result.rows:
        _write_verdict(row)
    lines, code = report.incomplete([(s.why, s.error) for s in result.skipped], len(paths))
    _write_lines(lines)
    return code


def _handle_interlock(ns: argparse.Namespace) -> int:
    paths = _str_list(ns, "paths")
    result = run_interlock(paths)
    for row in result.rows:
        _write_interlock(row)
    lines, code = report.incomplete([(s.why, s.error) for s in result.skipped], len(paths))
    _write_lines(lines)
    return code


def _handle_catchers(ns: argparse.Namespace) -> int:
    paths = _str_list(ns, "paths")
    result = run_catchers(paths)
    for row in result.rows:
        _write_catcher(row)
    lines, code = report.incomplete([(s.why, s.error) for s in result.skipped], len(paths))
    _write_lines(lines)
    return code


def _handle_escapes(ns: argparse.Namespace) -> int:
    paths = _str_list(ns, "paths")
    result = run_escapes(paths)
    for row in result.found:
        _write_escape(row)
    lines, code = report.incomplete([_UNREAD for _ in result.unread], len(paths))
    _write_lines(lines)
    return code


def _handle_reifies(ns: argparse.Namespace) -> int:
    paths = _str_list(ns, "paths")
    result = run_reifies(paths)
    for row in result.rows:
        _write_reification(row)
    lines, code = report.incomplete([(s.why, s.error) for s in result.skipped], len(paths))
    _write_lines(lines)
    return code


def _handle_collisions(ns: argparse.Namespace) -> int:
    paths = _str_list(ns, "paths")
    result = run_collisions(paths)
    for row in result.rows:
        _write_collision(row)
    lines, code = report.incomplete([(s.why, s.error) for s in result.skipped], len(paths))
    _write_lines(lines)
    return code


def _handle_layout(ns: argparse.Namespace) -> int:
    paths = _str_list(ns, "paths")
    result = run_layout(paths)
    for row in result.rows:
        _write_group(row)
    lines, code = report.incomplete([(s.why, s.error) for s in result.skipped], len(paths))
    _write_lines(lines)
    return code


def _handle_modstate(ns: argparse.Namespace) -> int:
    paths = _str_list(ns, "paths")
    result = module_state(paths)
    for row in result.rows:
        _write_module_state(row)
    lines, code = report.incomplete([(s.why, s.error) for s in result.skipped], len(paths))
    _write_lines(lines)
    return code


def _handle_placement(ns: argparse.Namespace) -> int:
    paths = _str_list(ns, "paths")
    result = run_placement(paths)
    for row in result.rows:
        _write_placement(row)
    lines, code = report.incomplete([(s.why, s.error) for s in result.skipped], len(paths))
    _write_lines(lines)
    return code


def _handle_disagreement(ns: argparse.Namespace) -> int:
    paths = _str_list(ns, "paths")
    result = run_disagreement(paths)
    for row in result.rows:
        _write_disagreement(row)
    lines, code = report.incomplete([(s.why, s.error) for s in result.skipped], len(paths))
    _write_lines(lines)
    return code


MODES = {
    "calls": _handle_calls,
    "owes": _handle_owes,
    "dead": _handle_dead,
    "attr-reads": _handle_attr_reads,
    "importers": _handle_importers,
    "swallows": _handle_swallows,
    "exits": _handle_exits,
    "verdicts": _handle_verdicts,
    "disagreement": _handle_disagreement,
    "placement": _handle_placement,
    "modstate": _handle_modstate,
    "layout": _handle_layout,
    "collisions": _handle_collisions,
    "reifies": _handle_reifies,
    "escapes": _handle_escapes,
    "catchers": _handle_catchers,
    "interlock": _handle_interlock,
    "commentary-lost": _handle_commentary_lost,
    "ambient": _handle_ambient,
    "callgraph": _handle_callgraph,
    "reaches": _handle_reaches,
    "guarded": _handle_guarded,
    "key-reads": _handle_key_reads,
    "bindings": _handle_bindings,
}


_PATHS_ONLY: tuple[tuple[str, str], ...] = (
    ("swallows", "an except whose whole body discards, triaged"),
    ("exits", "a process-exit site, classified main/dispatch/library"),
    ("verdicts", "a def whose returns mix an all-clear with a signal"),
    ("disagreement", "a tool's relation between its intent gate, snapshot and store writes"),
    ("placement", "each guarded file strongest intent-gate verdict and its witness"),
    ("modstate", "every module-level dict, set or list, classed by who writes it"),
    ("layout", "every top-level statement group, in source order, with its code lines"),
    ("collisions", "every public name with two or more reimplementing defs"),
    ("reifies", "every def return that hands back a materialized collection"),
    ("escapes", "string literals whose escape sequence does not exist"),
    ("catchers", "every handler that catches SystemExit, silent or re-raising"),
    ("callgraph", "every caller (file, scope) to each callee name it calls"),
    ("interlock", "every except Exception whose try body calls a name that can exit"),
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mikemol-pycodemod")
    sub = parser.add_subparsers(dest="mode", required=True)

    calls = sub.add_parser("calls", help="where a name is defined, called and used as a value")
    calls.add_argument("--target", default=None, help="a bare or dotted name; every name if unset")
    calls.add_argument("paths", nargs="+")
    grd = sub.add_parser("guarded", help="calls under an if (with its tests) vs at the top")
    grd.add_argument("--target", default=None, help="a bare or dotted name; every name if unset")
    grd.add_argument("paths", nargs="+")
    kr = sub.add_parser("key-reads", help="every read and write of one string key")
    kr.add_argument("key")
    kr.add_argument("paths", nargs="+")
    bnd = sub.add_parser("bindings", help="every binding of a name, with the lines it is live")
    bnd.add_argument("name")
    bnd.add_argument("paths", nargs="+")

    owes = sub.add_parser("owes", help="uses of a name in files a revision did not touch")
    owes.add_argument("name")
    owes.add_argument("--rev", required=True, help="a git revision, or WORKING for the diff")
    owes.add_argument("--root", required=True, help="the repo root git resolves the revision in")
    owes.add_argument("paths", nargs="+")
    lost = sub.add_parser("commentary-lost", help="marked sentences a split dropped")
    lost.add_argument("--rev", required=True, help="the baseline git revision")
    lost.add_argument("--root", required=True, help="the repo root the paths are under")
    lost.add_argument("paths", nargs="+")
    amb = sub.add_parser("ambient", help="filesystem-resolving calls not anchored to a root")
    amb.add_argument("--root", required=True, help="the tree whose subtrees anchor paths")
    amb.add_argument("paths", nargs="+")
    rch = sub.add_parser("reaches", help="target names reachable from a caller, same-file")
    rch.add_argument("--start", required=True, help="the caller, as PATH:SCOPE")
    rch.add_argument("--target", required=True, action="append", help="repeatable")
    rch.add_argument("--depth", type=int, default=DEPTH, help="hops to expand")
    rch.add_argument("paths", nargs="+")

    dead = sub.add_parser("dead", help="defs nothing in the corpus calls or uses")
    dead.add_argument("paths", nargs="+")

    attr_reads_p = sub.add_parser("attr-reads", help="reads of `.name`, or `Recv.*` off `Recv`")
    attr_reads_p.add_argument("query", help="`name`, or `Recv.*` for every attribute off Recv")
    attr_reads_p.add_argument("paths", nargs="+")

    importers_p = sub.add_parser("importers", help="every import of `module`, and the names taken")
    importers_p.add_argument("module")
    importers_p.add_argument("paths", nargs="+")

    for name, text in _PATHS_ONLY:
        sub.add_parser(name, help=text).add_argument("paths", nargs="+")

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
