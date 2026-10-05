# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""The driver: one `MODES` map over the ported library, plus refusing redirects.

Every retired or DO-NOT-PORT origin spelling gets one too. Cleanroomed against substrate's
`scratch/pycodemod.py` MODES table (W43; the DRIVER MODE MAP drafted in `.claude/queue.md`). This
slice adds `writes` (`writes.writes_by_default`) to the forty-two modes already wired:
`calls` (`sites.scan`), `owes` (`owes.fix_owes_callers`), `dead` (`dead.dead`), `attr-reads`
(`imports.attr_reads`), `importers` (`imports.importers`), `swallows` (`swallows.swallows`),
`exits` (`exit.exits`), `verdicts` (`graph.verdict_returners`), `disagreement`
(`placement.disagreement`), `placement` (`placement.placement`, default forms) and
`modstate` (`modstate.module_state`), `layout` (`layout.layout`), `collisions`
(`rivals.collisions`), `reifies` (`ordering.reifies`), `escapes` (`core.escapes`),
`catchers` (`exit.catchers`), `interlock` (`exit.interlock`) and `commentary-lost`
(`commentary.commentary_lost` over `owes.git_show`), `ambient` (`ambient.ambient`) and
`callgraph` (`graph.callgraph`), `reaches` (`graph.reaches`), `guarded`
(`arguments.guarded`), `key-reads` (`strings.key_reads`), `bindings`
(`definitions.bindings`), `aliases` (`aliases.aliases`), `funcnames`
(`funcnames.funcnames`), `size` (`size.module_sizes`), `deps` (`deps.import_census`), `crossings`
(`crossings.crossings`), `shapes` (`shapes.shape_sites`), `commentary`
(`commentary.commentary_census`), `discards` (`discards.discards`), `forwards`
(`arguments.forwards`), `asserted` (`arguments.asserted`), `values`
(`arguments.values`), `literals` (`strings.literal_sites`), `commentary-kinds`
(`commentary.commentary_kinds`), `commentary-blocks` (`commentary.commentary_blocks`),
`source-of` (`definitions.source_of`), `alias-hint` (`hints.alias_hint`), `rivals`
(`rivals.rivals`) and `resorts` (`ordering.resorts` over `ordering.reifies`).

⚑⚑ `funcnames` NEEDS THE OPTIONAL `sqlalchemy` EXTRA, SO IT IS IMPORTED UNDER A GUARD: the
driver must still run every other mode without it. Absent, `funcnames` REFUSES with the
import error's own words and exit 2 — never an empty census.

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
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.pathwalk.walk import WorktreeRefusedError, expand

from mikemol.pycodemod import control_report, report
from mikemol.pycodemod.aliases import aliases as run_aliases
from mikemol.pycodemod.ambient import ambient as run_ambient
from mikemol.pycodemod.arguments import asserted as run_asserted
from mikemol.pycodemod.arguments import forwards as run_forwards
from mikemol.pycodemod.arguments import guarded as run_guarded
from mikemol.pycodemod.arguments import values as run_values
from mikemol.pycodemod.commentary import (
    COMMENTARY_MARKS,
    commentary_blocks,
    commentary_census,
    commentary_kinds,
)
from mikemol.pycodemod.commentary import commentary_lost as run_commentary_lost
from mikemol.pycodemod.core import escapes as run_escapes
from mikemol.pycodemod.crossings import crossings as run_crossings
from mikemol.pycodemod.dead import dead as run_dead
from mikemol.pycodemod.definitions import bindings as run_bindings
from mikemol.pycodemod.definitions import source_of
from mikemol.pycodemod.deps import ManifestError, import_census
from mikemol.pycodemod.discards import discards as run_discards
from mikemol.pycodemod.exit import catchers as run_catchers
from mikemol.pycodemod.exit import exits as run_exits
from mikemol.pycodemod.exit import interlock as run_interlock
from mikemol.pycodemod.graph import DEPTH, callgraph, reaches, verdict_returners
from mikemol.pycodemod.header import COMPLETE, WRONG
from mikemol.pycodemod.header import plan as header_plan
from mikemol.pycodemod.hints import alias_hint
from mikemol.pycodemod.imports import attr_reads
from mikemol.pycodemod.imports import importers as run_importers
from mikemol.pycodemod.layout import layout as run_layout
from mikemol.pycodemod.modstate import module_state
from mikemol.pycodemod.ordering import reifies as run_reifies
from mikemol.pycodemod.ordering import resorts as run_resorts
from mikemol.pycodemod.owes import GitRefusedError, fix_owes_callers, git_show
from mikemol.pycodemod.placement import disagreement as run_disagreement
from mikemol.pycodemod.placement import placement as run_placement
from mikemol.pycodemod.relations import relname_sites
from mikemol.pycodemod.rivals import collisions as run_collisions
from mikemol.pycodemod.rivals import rivals as run_rivals
from mikemol.pycodemod.shapes import shape_sites
from mikemol.pycodemod.sites import Site, scan
from mikemol.pycodemod.size import OVERLARGE_LINES, module_sizes
from mikemol.pycodemod.strings import key_reads, literal_sites
from mikemol.pycodemod.swallows import swallows as run_swallows
from mikemol.pycodemod.writes import writes_by_default

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from mikemol.pycodemod.core import Escape
    from mikemol.pycodemod.exit import Catcher, ExitRow, Interlock
    from mikemol.pycodemod.funcnames import FuncCalls
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


def _census_flags(ns: argparse.Namespace) -> control_report.CensusFlags:
    return control_report.CensusFlags(
        readers=_opt_str(ns, "readers"),
        receivers=_opt_str(ns, "receivers"),
        connections=_opt_str(ns, "connections"),
        boundary=_opt_str(ns, "boundary"),
    )


def _handle_control(ns: argparse.Namespace) -> int:
    return control_report.print_control(_str_list(ns, "paths"), _census_flags(ns))


def _handle_constructs(ns: argparse.Namespace) -> int:
    return control_report.print_constructs(_str_list(ns, "paths"), _census_flags(ns))


_run_funcnames: Callable[[Sequence[str]], FuncCalls] | None
_moved: type[Exception]
try:
    from mikemol.pycodemod.funcnames import RegistryMovedError, funcnames

    _run_funcnames, _moved, _NO_EXTRA = funcnames, RegistryMovedError, ""
except ImportError as _missing:
    _run_funcnames, _moved, _NO_EXTRA = None, RuntimeError, str(_missing)

# ⚑ `--attr` and `--importers` are WIRED, as `attr-reads` and `importers` (W34): they stop being
# redirects and become real modes. ⚑ The origin's `--fix-owes-callers` IS RETIRED UNDER A NEW NAME
# (W72): its port is the `owes` mode, so the old spelling refuses naming it rather than failing as
# an unknown subcommand that names nothing.
RETIRED: dict[str, str] = {
    "fix-owes-callers": (
        "retired: `fix-owes-callers` is now `owes NAME --rev REV --root ROOT PATHS`"
        " (owes.fix_owes_callers)"
    ),
}

# ⚑ A DO-NOT-PORT SPELLING NAMES WHERE IT STILL LIVES. These are substrate's own instruments
# (queue.md PYCODEMOD CENSUS/SQL/CONTROL/FINGERPRINT SURVEY), never ported here.
_DO_NOT_PORT_NAMES = (
    "types",
    "artifacts",
    "touches",
    "projects",
    "discriminates",
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


def _flag(ns: argparse.Namespace, name: str) -> bool:
    raw: object = getattr(ns, name, None)
    if not isinstance(raw, bool):
        msg = f"{_INTERNAL} {name} flag"
        raise TypeError(msg)
    return raw


def _opt_str_list(ns: argparse.Namespace, name: str) -> list[str]:
    raw: object = getattr(ns, name, None)
    if raw is None:
        return []
    return _str_list(ns, name)


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


# A keyword name reads as itself, an all-digit argument as a positional ordinal.
def _argument(text: str) -> str | int:
    return int(text) if text.isdigit() else text


def _handle_values(ns: argparse.Namespace) -> int:
    paths = _str_list(ns, "paths")
    sites = scan(paths, _str(ns, "target"))
    result = run_values(sites, _argument(_str(ns, "argument")))
    for row in result.rows:
        where = row.where
        sys.stdout.write(
            f"value {row.value!r} {row.context} {where.path}:{where.line}:{where.column}\n"
        )
    sys.stdout.write(f"values: {len(result.rows)} of {result.total} calls pass it\n")
    lines, code = report.incomplete(
        [(s.why, s.error) for s in sites.skipped], len(sites.population)
    )
    _write_lines(lines)
    return code


def _handle_asserted(ns: argparse.Namespace) -> int:
    paths = _str_list(ns, "paths")
    sites = scan(paths, _opt_str(ns, "target"))
    result = run_asserted(sites, _str(ns, "keyword"))
    for label, rows in (("literal", result.literal), ("computed", result.computed)):
        for where in rows:
            sys.stdout.write(f"{label} {where.path}:{where.line}:{where.column}\n")
    sys.stdout.write(f"asserted: {len(result.literal)} literal, {len(result.computed)} computed\n")
    lines, code = report.incomplete(
        [(s.why, s.error) for s in sites.skipped], len(sites.population)
    )
    _write_lines(lines)
    return code


def _handle_forwards(ns: argparse.Namespace) -> int:
    paths = _str_list(ns, "paths")
    sites = scan(paths, _opt_str(ns, "target"))
    result = run_forwards(sites, _str(ns, "keyword"))
    buckets = (
        ("passes", result.passes),
        ("lacks", result.lacks),
        ("cannot-tell", result.cannot_tell),
    )
    for label, rows in buckets:
        for where in rows:
            sys.stdout.write(f"{label} {where.path}:{where.line}:{where.column}\n")
    counts = ", ".join(f"{len(rows)} {label}" for label, rows in buckets)
    sys.stdout.write(f"forwards: {counts}\n")
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


def _handle_literals(ns: argparse.Namespace) -> int:
    paths = _str_list(ns, "paths")
    result = literal_sites(paths, _str(ns, "text"))
    for row in result.rows:
        sys.stdout.write(
            f"literal {row.role} {row.path}:{row.line} ({row.context}) {row.value!r}\n"
        )
    lines, code = report.incomplete([(s.why, s.error) for s in result.skipped], len(paths))
    _write_lines(lines)
    return code


def _handle_relname(ns: argparse.Namespace) -> int:
    paths = _str_list(ns, "paths")
    result = relname_sites(paths, _str(ns, "name"))
    for row in result.rows:
        sys.stdout.write(
            f"relname {row.kind} {row.role} {row.path}:{row.line} ({row.context}) {row.value!r}\n"
        )
    lines, code = report.incomplete([(s.why, s.error) for s in result.skipped], len(paths))
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


def _handle_alias_hint(ns: argparse.Namespace) -> int:
    paths = _str_list(ns, "paths")
    result = alias_hint(_str(ns, "name"), _str_list(ns, "defs"), paths)
    for row in result.rows:
        aliases = ",".join(row.aliases)
        modules = ",".join(row.modules)
        sys.stdout.write(f"alias-hint {row.path}:{row.line} via={aliases} from={modules}\n")
    sys.stdout.write(f"alias-hint sites={len(result.rows)}\n")
    lines, code = report.incomplete([(s.why, s.error) for s in result.skipped], len(paths))
    _write_lines(lines)
    return code


def _handle_rivals(ns: argparse.Namespace) -> int:
    paths = _str_list(ns, "paths")
    result = run_rivals(_str(ns, "name"), paths)
    for row in result.rows:
        sys.stdout.write(
            f"rivals {row.path}:{row.line} {row.verdict} "
            f"callee={row.callee or _ABSENT} statements={row.statements}\n"
        )
    sys.stdout.write(f"rivals defs={len(result.rows)}\n")
    lines, code = report.incomplete([(s.why, s.error) for s in result.skipped], len(paths))
    _write_lines(lines)
    return code


def _handle_source_of(ns: argparse.Namespace) -> int:
    paths = _str_list(ns, "paths")
    result = source_of(paths, _str(ns, "name"))
    for row in result.rows:
        sys.stdout.write(f"source-of {row.qualname} {row.path}:{row.start}-{row.end}\n")
        sys.stdout.write(f"{row.text}\n")
    sys.stdout.write(f"source-of definitions={len(result.rows)}\n")
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


def _handle_aliases(ns: argparse.Namespace) -> int:
    paths = _str_list(ns, "paths")
    result = run_aliases(
        paths, local_only=not _flag(ns, "all_modules"), extra_local=_opt_str_list(ns, "local")
    )
    for row in result.rows:
        bound = ",".join(row.bound) or _ABSENT
        sys.stdout.write(
            f"alias {row.form} {row.module} bound={bound} {row.scope} {row.path}:{row.line}\n"
        )
    lines, code = report.incomplete([(s.why, s.error) for s in result.skipped], len(paths))
    _write_lines(lines)
    return code


def _handle_funcnames(ns: argparse.Namespace) -> int:
    paths = _str_list(ns, "paths")
    if _run_funcnames is None:
        sys.stdout.write(f"refused: {_NO_EXTRA}\n")
        return _REFUSED
    try:
        result = _run_funcnames(paths)
    except _moved as exc:
        sys.stdout.write(f"refused: {exc}\n")
        return _REFUSED
    for row in result.rows:
        sys.stdout.write(f"funcname {row.kind} {row.name} {row.caller} {row.path}:{row.line}\n")
    lines, code = report.incomplete([(s.why, s.error) for s in result.skipped], len(paths))
    _write_lines(lines)
    return code


def _handle_size(ns: argparse.Namespace) -> int:
    paths = _str_list(ns, "paths")
    result = module_sizes(paths, _int(ns, "base"))
    for row in result.rows:
        verdict = "over" if row.code > row.cap else "under"
        why = ",".join(row.why) or _ABSENT
        sys.stdout.write(
            f"size {verdict} code={row.code} cap={row.cap} physical={row.physical} "
            f"defs={row.defs} why={why} {row.path}\n"
        )
    lines, code = report.incomplete([(s.why, s.error) for s in result.skipped], len(paths))
    _write_lines(lines)
    return code


def _handle_discards(ns: argparse.Namespace) -> int:
    paths = _str_list(ns, "paths")
    result = run_discards(_str(ns, "name"), paths)
    for label, rows in (("dropped", result.dropped), ("used", result.using)):
        for path, line, col in rows:
            sys.stdout.write(f"discards {label} {path}:{line}:{col}\n")
    sys.stdout.write(f"discards: {len(result.dropped)} dropped, {len(result.using)} used\n")
    lines, code = report.incomplete([(s.why, s.error) for s in result.skipped], len(paths))
    _write_lines(lines)
    return code


def _handle_commentary(ns: argparse.Namespace) -> int:
    paths = _str_list(ns, "paths")
    marks = _opt_str_list(ns, "mark") or COMMENTARY_MARKS
    result = commentary_census(paths, marks)
    for row in result.rows:
        sys.stdout.write(f"commentary lines={row.lines} distinct={row.distinct} {row.path}\n")
    for key, places in sorted(result.texts.items()):
        if len(places) > 1:
            where = " ".join(f"{path}:{line}" for path, line in places)
            sys.stdout.write(f"repeated x{len(places)} {key!r} {where}\n")
    lines, code = report.incomplete([(s.why, s.error) for s in result.skipped], len(paths))
    _write_lines(lines)
    return code


def _handle_commentary_kinds(ns: argparse.Namespace) -> int:
    paths = _str_list(ns, "paths")
    marks = _opt_str_list(ns, "mark") or COMMENTARY_MARKS
    result = commentary_kinds(paths, marks)
    kinds = (
        ("comment", result.comment),
        ("docstring", result.docstring),
        ("executable", result.executable),
        ("unparsed", result.unparsed),
    )
    for kind, hits in kinds:
        for hit in hits:
            sys.stdout.write(f"commentary-kinds {kind} {hit.path}:{hit.line} {hit.text}\n")
    counts = " ".join(f"{kind}={len(hits)}" for kind, hits in kinds)
    sys.stdout.write(f"commentary-kinds {counts}\n")
    lines, code = report.incomplete([(s.why, s.error) for s in result.skipped], len(paths))
    _write_lines(lines)
    return code


def _handle_commentary_blocks(ns: argparse.Namespace) -> int:
    paths = _str_list(ns, "paths")
    marks = _opt_str_list(ns, "mark") or COMMENTARY_MARKS
    result = commentary_blocks(paths, marks)
    for block in result.found:
        owner = block.enclosing or _ABSENT
        cites = ",".join(block.cited) or _ABSENT
        sys.stdout.write(
            f"commentary-blocks {block.path}:{block.start}-{block.end} {owner} "
            f"cites={cites} {block.text}\n"
        )
    sys.stdout.write(f"commentary-blocks blocks={len(result.found)}\n")
    lines, code = report.incomplete([(s.why, s.error) for s in result.skipped], len(paths))
    _write_lines(lines)
    return code


def _handle_shapes(ns: argparse.Namespace) -> int:
    paths = _str_list(ns, "paths")
    try:
        result = shape_sites(_str(ns, "pattern"), paths, in_code_only=not _flag(ns, "anywhere"))
    except re.error as exc:
        sys.stdout.write(f"refused: bad pattern: {exc}\n")
        return _REFUSED
    for row in result.rows:
        sys.stdout.write(f"shape {row.path}:{row.line} {row.text}\n")
    lines, code = report.incomplete([(s.why, s.error) for s in result.skipped], len(paths))
    _write_lines(lines)
    return code


def _handle_crossings(ns: argparse.Namespace) -> int:
    paths = _str_list(ns, "paths")
    result = run_crossings(paths, _opt_str_list(ns, "authority"))
    for row in result.rows:
        what = ",".join(row.what) or _ABSENT
        sys.stdout.write(f"crossing {row.klass} {row.function} {what} {row.path}:{row.line}\n")
    lines, code = report.incomplete([(s.why, s.error) for s in result.skipped], len(paths))
    _write_lines(lines)
    return code


def _handle_deps(ns: argparse.Namespace) -> int:
    paths = _str_list(ns, "paths")
    try:
        result = import_census(paths, Path(_str(ns, "manifest")), _opt_str_list(ns, "vendored"))
    except ManifestError as exc:
        sys.stdout.write(f"refused: {exc}\n")
        return _REFUSED
    for row in result.rows:
        sys.stdout.write(f"dep {row.verdict} {row.module} files={row.files} e.g. {row.example}\n")
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
    lines, code = report.incomplete([(s.why, s.error) for s in result.skipped], len(paths))
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
    lines, code = report.incomplete([(s.why, s.error) for s in result.skipped], len(paths))
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


def _handle_resorts(ns: argparse.Namespace) -> int:
    paths = _str_list(ns, "paths")
    result = run_resorts(paths, run_reifies(paths))
    for row in result.rows:
        producers = ",".join(f"{path}:{line}" for path, line in row.producers)
        sys.stdout.write(
            f"resorts {row.path}:{row.line} {row.why} {row.caller} -> {row.callee} "
            f"producers={producers}\n"
        )
    sys.stdout.write(f"resorts sites={len(result.rows)}\n")
    # Both passes read the same paths, so the consumer pass's skips are the producer's:
    # reporting both would count each unreadable file twice.
    lines, code = report.incomplete([(s.why, s.error) for s in result.skipped], len(paths))
    _write_lines(lines)
    return code


def _handle_writes(ns: argparse.Namespace) -> int:
    paths = _str_list(ns, "paths")
    result = writes_by_default(paths, _opt_str_list(ns, "fixture"), _opt_str_list(ns, "gate"))
    for row in result.rows:
        verdict = "WRITES" if row.writes else "inert"
        sys.stdout.write(f"writes {row.path}:{row.line} {verdict} {row.why}\n")
    writing = sum(row.writes for row in result.rows)
    sys.stdout.write(f"writes files={len(result.rows)} writing={writing}\n")
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


def _handle_header(ns: argparse.Namespace) -> int:
    """Check, or with --write complete, each file's licence header (W306).

    One tab-separated line per file that is not complete: state, path, detail. With --write, a
    missing or partial header is written and a wrong one is refused; then one `shebang` line per
    rewritten file that carries a shebang (EXE001 is the filesystem's to answer).

    Returns:
        0 when every file ends complete; 1 when one does not (unwritten, or a wrong id refused);
        2 when a file could not be read.

    """
    write = _flag(ns, "write")
    holder = _opt_str(ns, "holder")
    paths = _str_list(ns, "paths")
    skipped: list[tuple[str, str]] = []
    unfinished = 0
    for path in paths:
        try:
            text = Path(path).read_text(encoding="utf-8", newline="")
        except (OSError, UnicodeDecodeError) as exc:
            skipped.append(("unreadable", type(exc).__name__))
            continue
        result = header_plan(text, spdx=_str(ns, "spdx"), holder=holder, year=_int(ns, "year"))
        if result.state == COMPLETE:
            continue
        if write and result.state != WRONG:
            Path(path).write_text(result.text, encoding="utf-8", newline="")
            sys.stdout.write(f"wrote\t{path}\t{result.detail}\n")
            if result.shebang:
                sys.stdout.write(f"shebang\t{path}\n")
            continue
        unfinished += 1
        sys.stdout.write(f"{result.state}\t{path}\t{result.detail}\n")
    lines, code = report.incomplete(skipped, len(paths))
    _write_lines(lines)
    return code or (1 if unfinished else 0)


MODES = {
    "header": _handle_header,
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
    "forwards": _handle_forwards,
    "asserted": _handle_asserted,
    "values": _handle_values,
    "key-reads": _handle_key_reads,
    "literals": _handle_literals,
    "relname": _handle_relname,
    "bindings": _handle_bindings,
    "source-of": _handle_source_of,
    "alias-hint": _handle_alias_hint,
    "rivals": _handle_rivals,
    "resorts": _handle_resorts,
    "writes": _handle_writes,
    "aliases": _handle_aliases,
    "funcnames": _handle_funcnames,
    "size": _handle_size,
    "deps": _handle_deps,
    "crossings": _handle_crossings,
    "shapes": _handle_shapes,
    "commentary": _handle_commentary,
    "commentary-kinds": _handle_commentary_kinds,
    "commentary-blocks": _handle_commentary_blocks,
    "discards": _handle_discards,
    "control": _handle_control,
    "constructs": _handle_constructs,
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
    ("funcnames", "every func.<name>() call, graded generic or verbatim by SQLAlchemy"),
    ("interlock", "every except Exception whose try body calls a name that can exit"),
)


type _Make = Callable[[str, str], argparse.ArgumentParser]


def _add_scan_modes(make: _Make) -> None:
    calls = make("calls", "where a name is defined, called and used as a value")
    calls.add_argument("--target", default=None, help="a bare or dotted name; every name if unset")
    calls.add_argument("paths", nargs="+")
    grd = make("guarded", "calls under an if (with its tests) vs at the top")
    grd.add_argument("--target", default=None, help="a bare or dotted name; every name if unset")
    grd.add_argument("paths", nargs="+")
    fwd = make("forwards", "calls split by whether they pass a keyword, lack it, or hide it in **")
    fwd.add_argument("--target", default=None, help="a bare or dotted name; every name if unset")
    fwd.add_argument("keyword")
    fwd.add_argument("paths", nargs="+")
    ast_ = make("asserted", "calls passing a keyword, split by literal vs computed value")
    ast_.add_argument("--target", default=None, help="a bare or dotted name; every name if unset")
    ast_.add_argument("keyword")
    ast_.add_argument("paths", nargs="+")
    val = make("values", "the value each call of a name passes for one argument")
    val.add_argument("target", help="a bare or dotted callee name")
    val.add_argument("argument", help="a keyword, or an all-digit positional ordinal")
    val.add_argument("paths", nargs="+")
    make("dead", "defs nothing in the corpus calls or uses").add_argument("paths", nargs="+")
    rch = make("reaches", "target names reachable from a caller, same-file")
    rch.add_argument("--start", required=True, help="the caller, as PATH:SCOPE")
    rch.add_argument("--target", required=True, action="append", help="repeatable")
    rch.add_argument("--depth", type=int, default=DEPTH, help="hops to expand")
    rch.add_argument("paths", nargs="+")


def _add_named_modes(make: _Make) -> None:
    kr = make("key-reads", "every read and write of one string key")
    kr.add_argument("key")
    kr.add_argument("paths", nargs="+")
    lit = make("literals", "every string literal containing a text, with its role")
    lit.add_argument("text")
    lit.add_argument("paths", nargs="+")
    rel = make("relname", "every use of a name as a relation: a SQL literal or an exact string")
    rel.add_argument("name")
    rel.add_argument("paths", nargs="+")
    bnd = make("bindings", "every binding of a name, with the lines it is live")
    bnd.add_argument("name")
    bnd.add_argument("paths", nargs="+")
    src = make("source-of", "the source of every def or class with a bare name, decorators on")
    src.add_argument("name")
    src.add_argument("paths", nargs="+")
    hnt = make("alias-hint", "sites that reach a name through an aliased import")
    hnt.add_argument("name")
    hnt.add_argument(
        "--def",
        dest="defs",
        action="append",
        required=True,
        help="a file defining the name (repeatable)",
    )
    hnt.add_argument("paths", nargs="+")
    riv = make("rivals", "each `def NAME`: whether it delegates or reimplements")
    riv.add_argument("name")
    riv.add_argument("paths", nargs="+")
    rso = make("resorts", "sorted(f(...)) where f already returns a sorted collection")
    rso.add_argument("paths", nargs="+")
    wrt = make("writes", "whether a bare run of each file could write a real file")
    wrt.add_argument("--fixture", action="append", help="an inert function name (repeatable)")
    wrt.add_argument("--gate", action="append", help="a flag that gates writes (repeatable)")
    wrt.add_argument("paths", nargs="+")
    attr = make("attr-reads", "reads of `.name`, or `Recv.*` off `Recv`")
    attr.add_argument("query", help="`name`, or `Recv.*` for every attribute off Recv")
    attr.add_argument("paths", nargs="+")
    imp = make("importers", "every import of `module`, and the names taken")
    imp.add_argument("module")
    imp.add_argument("paths", nargs="+")
    dis = make("discards", "every call of a name, split by whether its value is dropped")
    dis.add_argument("name")
    dis.add_argument("paths", nargs="+")
    hdr = make("header", "check the SPDX/copyright header, or --write the missing lines")
    hdr.add_argument("--spdx", required=True, help="the SPDX id every file must declare")
    hdr.add_argument("--holder", default=None, help="write a copyright line for this holder")
    hdr.add_argument("--year", type=int, required=True, help="the year a new copyright line states")
    hdr.add_argument("--write", action="store_true", help="write missing lines; refuse wrong ids")
    hdr.add_argument("paths", nargs="+")
    shp = make("shapes", "every code line matching a regex (comments and docstrings excluded)")
    shp.add_argument("--anywhere", action="store_true", help="match comments and docstrings too")
    shp.add_argument("pattern")
    shp.add_argument("paths", nargs="+")


def _add_flagged_modes(make: _Make) -> None:
    als = make("aliases", "every import, graded by form")
    als.add_argument("--all-modules", action="store_true", help="not just local modules")
    als.add_argument("--local", action="append", help="an extra local head (repeatable)")
    als.add_argument("paths", nargs="+")
    siz = make("size", "every module's code lines against its cap")
    siz.add_argument("--base", type=int, default=OVERLARGE_LINES, help="the base cap")
    siz.add_argument("paths", nargs="+")
    dep = make("deps", "every top-level import, graded against a pyproject manifest")
    dep.add_argument("--manifest", required=True, help="the pyproject.toml to grade against")
    dep.add_argument("--vendored", action="append", help="a path fragment marking vendored")
    dep.add_argument("paths", nargs="+")
    cro = make("crossings", "every function that returns a container it built, classified")
    cro.add_argument(
        "--authority", action="append", help="a call name that enumerates a corpus (repeatable)"
    )
    cro.add_argument("paths", nargs="+")
    com = make("commentary", "marked lines per file, and every sentence found in two places")
    com.add_argument("--mark", action="append", help="a commentary mark (repeatable; default ⚑)")
    com.add_argument("paths", nargs="+")
    kin = make("commentary-kinds", "each marked line as comment, docstring or executable")
    kin.add_argument("--mark", action="append", help="a commentary mark (repeatable; default ⚑)")
    kin.add_argument("paths", nargs="+")
    blk = make("commentary-blocks", "each marked paragraph, its owner and what it cites")
    blk.add_argument("--mark", action="append", help="a commentary mark (repeatable; default ⚑)")
    blk.add_argument("paths", nargs="+")


def _add_rooted_modes(make: _Make) -> None:
    owes = make("owes", "uses of a name in files a revision did not touch")
    owes.add_argument("name")
    owes.add_argument("--rev", required=True, help="a git revision, or WORKING for the diff")
    owes.add_argument("--root", required=True, help="the repo root git resolves the revision in")
    owes.add_argument("paths", nargs="+")
    lost = make("commentary-lost", "marked sentences a split dropped")
    lost.add_argument("--rev", required=True, help="the baseline git revision")
    lost.add_argument("--root", required=True, help="the repo root the paths are under")
    lost.add_argument("paths", nargs="+")
    amb = make("ambient", "filesystem-resolving calls not anchored to a root")
    amb.add_argument("--root", required=True, help="the tree whose subtrees anchor paths")
    amb.add_argument("paths", nargs="+")


def _add_census_modes(make: _Make) -> None:
    for name, text in (
        ("control", "every control-flow site, typed by what a declarative engine could take"),
        ("constructs", "the control-flow roster tallied by group, zero rows shown"),
    ):
        cen = make(name, text)
        cen.add_argument("--readers", default=None, help="comma list: methods that read rows")
        cen.add_argument("--receivers", default=None, help="comma list: names readers run on")
        cen.add_argument("--connections", default=None, help="comma list: connection names")
        cen.add_argument("--boundary", default=None, help="the boundary to type against: python")
        cen.add_argument("paths", nargs="+")


_FAMILIES: tuple[Callable[[_Make], None], ...] = (
    _add_scan_modes,
    _add_named_modes,
    _add_flagged_modes,
    _add_rooted_modes,
    _add_census_modes,
)


def _build_parser() -> argparse.ArgumentParser:
    """Build the parser; each mode family adds its own subparsers, so no builder outgrows ruff.

    Returns:
        the parser.

    """
    parser = argparse.ArgumentParser(prog="mikemol-pycodemod")
    sub = parser.add_subparsers(dest="mode", required=True)

    def make(name: str, text: str) -> argparse.ArgumentParser:
        parser = sub.add_parser(name, help=text)
        parser.add_argument(
            "--include-worktrees",
            action="store_true",
            help="with a directory operand, also read registered git worktrees (default: skip)",
        )
        return parser

    for family in _FAMILIES:
        family(make)
    for name, text in _PATHS_ONLY:
        make(name, text).add_argument("paths", nargs="+")
    for name in (*RETIRED, *DO_NOT_PORT):
        sub.add_parser(name).add_argument("rest", nargs=argparse.REMAINDER)
    return parser


def _expand_operands(ns: argparse.Namespace) -> int | None:
    """Expand directory operands to files, printing what the expansion left out.

    ⚑ A DIRECTORY OPERAND PRINTS ITS SKIP, ZERO INCLUDED: "skipped N registered worktrees" counts
    the registered git worktrees other than the root own tree (none, with --include-worktrees).
    A refused symlink is counted, never followed. File operands are untouched.

    Returns:
        the refusal code when git could not list worktrees, else None.

    """
    try:
        got = expand(_str_list(ns, "paths"), include_worktrees=_flag(ns, "include_worktrees"))
    except WorktreeRefusedError as exc:
        sys.stdout.write(f"{exc}\n")
        return _REFUSED
    if got.directories:
        sys.stdout.write(f"skipped {got.worktrees} registered worktrees\n")
        sys.stdout.write(f"skipped {got.virtualenvs} virtualenvs\n")
        sys.stdout.write(f"refused {got.links} symlinks (not followed)\n")
        ns.paths = got.files
    return None


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
    refused = _expand_operands(ns)
    if refused is not None:
        return refused
    return MODES[mode](ns)


def _console() -> int:
    """Run `main` over the real argv, as the `mikemol-pycodemod` console-script entry point.

    Returns:
        the mode's exit code.

    """
    return main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(_console())
