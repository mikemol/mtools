# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""SQL literals a real engine rejects, judged by an INJECTED probe; no database is opened here.

Cleanroomed from substrate's `scratch/_pycodemod_sql.py` (`portable_sites`, `_pg_*`,
`pg_probe_status`; W608). The origin asks a live postgres through connections it opens itself. Here
the caller supplies the judgement and this module only routes statements to it and classifies what
comes back.

⚑⚑ THE SEAM IS CALLABLES, NOT A PROTOCOL. A `Probe` is a frozen record of two optional functions and
a reason string. A Protocol's methods are bodiless def-sites no test can exercise, so the seam is
`Judge = Callable[[str], Verdict]`, and the connection adapter takes the three callables it needs
(`transaction`, `execute`, `ddl_execute`) rather than a connection object.

⚑⚑ THE VERDICT IS A SQLSTATE, NOT AN EXCEPTION TYPE. `42P01` (undefined table), `42P07` (duplicate
table) and `42710` (duplicate object) mean the engine PARSED the statement and the fact is about the
store, so they are `parsed_absent`. Any other SQLSTATE is an `error`. An error with NO SQLSTATE (a
dropped socket) is not a verdict about the SQL and is re-raised, never classified.

⚑ AN UNREACHABLE PROBE CARRIES ITS CAUSE. `Probe.reason` is the positive control: a zero from a
probe that never ran must read differently from a zero from one that did.
`PortableReport.degraded` is that reason.

⚑ DDL IS EXECUTED ONLY WHEN THE CALLER NAMES A SANDBOX HANDLE. `connection_probe` has no default for
`ddl_execute`; without it DDL is graded by pattern and tagged `pattern/ddl`, never executed.

⚑ NOTHING IS SWALLOWED. Unreadable, undecodable and unparseable files are returned as skips, and a
generated file (the marker in its first 400 bytes) is listed under `generated`, not dropped.
`core_built` is a field of the returned report, so one file's SQLAlchemy `func.<name>` calls cannot
be carried to the next file by construction.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, cast

from mikemol.pycodemod.core import Skip

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from contextlib import AbstractContextManager

OK = "ok"
ABSENT = "parsed_absent"
ERROR = "error"
PATTERN = "pattern"
PATTERN_DDL = "pattern/ddl"
NO_REMEDY = "(no known remedy — read the engine's message)"
_HEAD_BYTES = 400
_RECEIVER = "func"
_DDL_HEADS = frozenset({"CREATE", "DROP", "ALTER", "VACUUM", "ATTACH", "PRAGMA"})
_ABSENT_EXPLAIN = frozenset({"42P01"})
_ABSENT_DDL = frozenset({"42P01", "42P07", "42710"})
DEFAULT_REMEDIES: tuple[tuple[str, str], ...] = (
    (r"\bINSERT\s+OR\s+(?:IGNORE|REPLACE)\b", "use the dialect's upsert"),
    (r"\bsqlite_master\b", "use the catalog the target engine offers"),
    (r"\bPRAGMA\b", "sqlite-only: guard, or drop"),
    (r"\browid\b", "use a real key"),
    (r"\bGROUP_CONCAT\b", "use string_agg"),
    (r"(?<![%\w])\?", "use the driver's paramstyle"),
)
DEFAULT_GENERATED = r"^#\s*GENERATED\b"


@dataclass(frozen=True, slots=True)
class Verdict:
    """What the engine said about one statement: ok, parsed_absent, or error of a kind."""

    status: str
    kind: str = ""


type Judge = Callable[[str], Verdict]
type Literals = Callable[[str], Sequence[tuple[int, str]]]


@dataclass(frozen=True, slots=True)
class Probe:
    """Two optional judges and the cause of any absence; an absent judge degrades to patterns."""

    explain: Judge | None = None
    execute_ddl: Judge | None = None
    reason: str = ""


@dataclass(frozen=True, slots=True)
class PortConfig:
    """The caller's remedy text and generated-file marker; defaults are generic SQL grammar."""

    remedies: tuple[tuple[str, str], ...] = DEFAULT_REMEDIES
    generated_marker: str = DEFAULT_GENERATED


@dataclass(frozen=True, slots=True, order=True)
class Blocker:
    """One SQL literal the engine (or a pattern) rejects, with the remedy."""

    path: str
    line: int
    blocker: str
    remedy: str
    snippet: str


@dataclass(frozen=True, slots=True)
class PortableReport:
    """Blockers, what could not be judged, and why the probe was absent when it was."""

    blockers: list[Blocker] = field(default_factory=list)
    core_built: dict[str, list[tuple[int, str]]] = field(default_factory=dict)
    generated: list[str] = field(default_factory=list)
    skipped: list[Skip] = field(default_factory=list)
    degraded: str = ""


def classify_state(state: str, name: str, *, ddl: bool) -> Verdict:
    """Classify an engine error by its SQLSTATE.

    Returns:
        parsed_absent for the object-existence states, else an error named by the exception type.

    """
    if state in (_ABSENT_DDL if ddl else _ABSENT_EXPLAIN):
        return Verdict(ABSENT, state)
    return Verdict(ERROR, name.replace("Error", ""))


def _sqlstate(exc: Exception) -> str | None:
    return cast("str | None", getattr(exc, "sqlstate", None))


def _explain(
    transaction: Callable[[], AbstractContextManager[object]],
    execute: Callable[[str], object],
    text: str,
) -> Verdict:
    try:
        with transaction():
            execute("EXPLAIN " + text)
    except Exception as exc:
        state = _sqlstate(exc)
        if state is None:
            raise
        return classify_state(state, type(exc).__name__, ddl=False)
    return Verdict(OK)


def _run_ddl(execute: Callable[[str], object], text: str) -> Verdict:
    try:
        execute(text)
    except Exception as exc:
        state = _sqlstate(exc)
        if state is None:
            raise
        return classify_state(state, type(exc).__name__, ddl=True)
    return Verdict(OK)


def connection_probe(
    transaction: Callable[[], AbstractContextManager[object]],
    execute: Callable[[str], object],
    ddl_execute: Callable[[str], object] | None = None,
) -> Probe:
    """Adapt a connection's callables to a probe.

    Each EXPLAIN runs inside its own `transaction()` so one rejection cannot poison later sites.
    DDL runs through `ddl_execute` only, which the caller must name; never the EXPLAIN handle.

    Returns:
        a connected probe with an empty reason.

    """
    ddl = None if ddl_execute is None else partial(_run_ddl, ddl_execute)
    return Probe(partial(_explain, transaction, execute), ddl, "")


def _remedy(config: PortConfig, snippet: str) -> str | None:
    for rx, text in config.remedies:
        if re.search(rx, snippet, re.IGNORECASE):
            return text
    return None


def _read(path: str) -> str | Skip:
    try:
        return Path(path).read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        return Skip(path, "undecodable", type(exc).__name__)
    except OSError as exc:
        return Skip(path, "unreadable", type(exc).__name__)


def _is_core_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == _RECEIVER
    )


def _core_sites(tree: ast.Module) -> list[tuple[int, str]]:
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and _is_core_call(n)]
    return sorted({(c.lineno, c.func.attr) for c in calls if isinstance(c.func, ast.Attribute)})


def _judge(probe: Probe, config: PortConfig, path: str, row: tuple[int, str]) -> Blocker | None:
    line, snippet = row
    words = snippet.split(None, 1)
    ddl = bool(words) and words[0].upper() in _DDL_HEADS
    judge = probe.execute_ddl if ddl else probe.explain
    pattern = _remedy(config, snippet)
    if judge is None:
        if pattern is None:
            return None
        tag = PATTERN_DDL if ddl and probe.explain else PATTERN
        return Blocker(path, line, tag, pattern, snippet)
    verdict = judge(snippet)
    if verdict.status != ERROR:
        return None
    return Blocker(path, line, verdict.kind, pattern or NO_REMEDY, snippet)


def portable_sites(
    paths: Sequence[str],
    literals: Literals,
    probe: Probe,
    config: PortConfig | None = None,
) -> PortableReport:
    """List SQL literals the probe's engine rejects, with a remedy.

    `literals` maps a path to its `(line, snippet)` SQL literals; the caller owns that definition.

    Returns:
        the report; a probe with no explain judge yields pattern verdicts and names its reason.

    """
    cfg = config or PortConfig()
    report = PortableReport(degraded="" if probe.explain else probe.reason or "not attempted")
    for path in paths:
        text = _read(path)
        if isinstance(text, Skip):
            report.skipped.append(text)
            continue
        if re.search(cfg.generated_marker, text[:_HEAD_BYTES], re.MULTILINE):
            report.generated.append(path)
            continue
        try:
            tree = ast.parse(text, filename=path)
        except SyntaxError as exc:
            report.skipped.append(Skip(path, "unparseable", type(exc).__name__))
            continue
        report.core_built[path] = _core_sites(tree)
        for row in literals(path):
            found = _judge(probe, cfg, path, row)
            if found is not None:
                report.blockers.append(found)
    report.blockers.sort()
    return report
