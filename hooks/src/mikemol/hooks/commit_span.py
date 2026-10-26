# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Plan and start the spans of one commit: the commit, its wait for the lease, its gate (W1440).

⚑⚑ ONE COMMIT IS THREE SPANS IN ONE TRACE, because the operator's question is where the time went
(luthen-observability:W1193, per-phase panels): `commit` from submission to the verdict, with two
children, `commit.queued` (submission to the moment the lease was held) and `commit.gating` (the
lease held to the verdict). They are emitted AFTER the verdict, from three timestamps, so nothing
is held open across the commit and a crash loses a span, never a verdict.

⚑ EMITTING IS A DETACHED `mikemol-otlp trace` PER SPAN, NOT AN IMPORT: this dist stays
dependency-free (the protobuf wheel lives in `otlp`), the same shape as the paths-forward writer's
record. The child is found by `MIKEMOL_OTLP_BIN`, then PATH, then the mtools checkout under the
home directory's `github`; the store is the child's own concern (`MIKEMOL_ENDPOINTS` naming
`victoriatraces-http`). With no child or no `MIKEMOL_ENDPOINTS` this does nothing, and a failure to
start one is swallowed: the verdict is already printed.

⚑ THE VERDICT IS READ FROM THE OUTPUT'S OWN LINE (`verdictlog.events_of`), the same grammar the
log shipper reads, so a span and a log line cannot disagree about it. Only COMMITTED is OK;
REFUSED, NOT COMMITTED and RACED are ERROR. A block with no verdict line gets no span.

CONSUMED BY: `commit_kata.main` (W1441).
"""

import json
import re
import secrets
import shutil
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from mikemol.hooks import verdictlog
from mikemol.hooks.gatephase import Mark
from mikemol.hooks.gatephase import marks as _marks_of
from mikemol.hooks.vlogdetach import spawn_detached, spawn_with_stdin

BIN_ENV = "MIKEMOL_OTLP_BIN"
ENDPOINTS_ENV = "MIKEMOL_ENDPOINTS"
HOME_FILE = ".config/mikemol/endpoints.json"
SUBMIT_ENV = "MIKEMOL_COMMIT_SUBMITTED_NS"
SERVICE = "mikemol-commit"
ADMISSION_NAME = "mikemol.gate.admission_wait_seconds"
RUN_NAME = "mikemol.gate.run_seconds"
_OK = "COMMITTED"
_INVOCATION = re.compile(
    r"/invocation/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
)
_CARD = re.compile(r"^(W\d+)\b")
NS_PER_S = 1_000_000_000
NO_CARD = "-"
Spawn = Callable[[Sequence[str]], None]
TextSpawn = Callable[[Sequence[str], str], None]


def landing_records(text: str, gate_s: float) -> list[dict[str, str]]:
    """Make one landing record per COMMITTED line of a run's output (W1738).

    ⚑ A LOG RECORD, NOT A METRIC: the card and the sha are unbounded, so neither may be a metric
    label. `pushed` is the word the line carried in brackets, so a card that is done but not yet
    pushed reads differently from one that landed on the remote.

    Returns:
        the records, in order; the card is the subject's leading `W<n>`, or `-` when it has none.

    """
    records: list[dict[str, str]] = []
    for event in verdictlog.events_of(text):
        if event["verdict"] != _OK:
            continue
        card = _CARD.match(event.get("subject", ""))
        records.append(
            {
                "event": "landing",
                "repo": event["repo"],
                "sha": event["sha"],
                "card": card.group(1) if card else NO_CARD,
                "gate_s": f"{gate_s:.0f}",
                "pushed": event.get("pushed", ""),
                "verdict": _OK,
            }
        )
    return records


def emit_landings(
    text: str, gate_s: float, env: Mapping[str, str], spawn: TextSpawn = spawn_with_stdin
) -> int:
    """Ship each landing record as a log record, when a child and a store exist.

    Returns:
        how many were started: 0 with no binary or store; a failed start ends the run quietly.

    """
    program = binary(env)
    if program is None or not store_named(env):
        return 0
    started = 0
    for record in landing_records(text, gate_s):
        argv = [program, "log", "--service", SERVICE, "--namespace", record["repo"]]
        argv += ["--version", record["sha"], "--field", f"card={record['card']}"]
        argv += ["--field", f"pushed={record['pushed']}", "--field", f"gate_s={record['gate_s']}"]
        try:
            spawn(argv, json.dumps(record))
        except OSError:
            break
        started += 1
    return started


@dataclass(frozen=True, slots=True)
class Moments:
    """When the commit was submitted, got its lease, and reached its verdict (epoch ns)."""

    submit_ns: int
    lease_ns: int
    end_ns: int


@dataclass(frozen=True, slots=True)
class Ids:
    """The trace id (32 hex) and the three span ids (16 hex each) of one commit."""

    trace: str
    commit: str
    queued: str
    gating: str


@dataclass(frozen=True, slots=True)
class Piece:
    """One span of the trace: its name, window and place (its own id and its parent's, or empty)."""

    name: str
    start_ns: int
    end_ns: int
    span_id: str
    parent_id: str


def new_ids() -> Ids:
    """Draw the ids of one commit's trace.

    Returns:
        fresh random ids.

    """
    return Ids(
        secrets.token_hex(16), secrets.token_hex(8), secrets.token_hex(8), secrets.token_hex(8)
    )


def invocations_of(text: str) -> str:
    """Name the bazel invocations a gate's output prints, so a span can be joined to BuildBuddy.

    ⚑ THE SPAN CARRIES THE ID BECAUSE NOTHING ELSE PAIRS THE TWO (W1578, github-8f 2026-10-18): a
    gate runs more than one bazel call (the prebuild, the test run), each printing `Streaming build
    results to: <host>/invocation/<uuid>` into the output this module already reads, and the search
    RPC that would list invocations answers PermissionDenied. With the ids on the `commit.gating`
    span, a gate's wall time and its bazel invocations can be read side by side (W1572's table).

    Returns:
        each distinct uuid after `/invocation/`, in order, joined with commas; empty when none.

    """
    seen: dict[str, None] = {}
    for found in _INVOCATION.finditer(text):
        seen.setdefault(found.group(1))
    return ",".join(seen)


def verdict_of(text: str) -> dict[str, str] | None:
    """Read the commit's verdict event out of its output.

    Returns:
        the LAST verdict event (verdict, repo and the parts that line has) with the output's
        bazel `invocations` when it prints any, or None when the output holds no verdict.

    """
    names = {name for name, _ in verdictlog.VERDICTS}
    found = [e for e in verdictlog.events_of(text) if e["verdict"] in names]
    if not found:
        return None
    ids = invocations_of(text)
    return {**found[-1], "invocations": ids} if ids else found[-1]


def binary(env: Mapping[str, str]) -> str | None:
    """Find `mikemol-otlp`: the named binary, PATH, then the mtools checkout under ~/github.

    Returns:
        its path, or None when none exists.

    """
    named = env.get(BIN_ENV)
    if named:
        return named
    on_path = shutil.which("mikemol-otlp")
    if on_path:
        return on_path
    checkout = Path.home() / "github" / "mtools" / "otlp" / ".venv" / "bin" / "mikemol-otlp"
    return str(checkout) if checkout.is_file() else None


def store_named(env: Mapping[str, str]) -> bool:
    """Say whether a store can be named: the variable is set, or the host's file is under HOME.

    ⚑ A SESSION CARRIES NO `MIKEMOL_ENDPOINTS` (W1528), so the host's own file at
    `$HOME/.config/mikemol/endpoints.json` counts, the same fallback `mikemol-otlp` resolves
    through. This only decides whether to start the child; the child still fails silent.

    Returns:
        whether a send is worth starting.

    """
    if env.get(ENDPOINTS_ENV):
        return True
    home = env.get("HOME")
    if not home:
        return False
    return (Path(home) / HOME_FILE).is_file()


def pieces(
    moments: Moments, ids: Ids, root: str = "commit", phases: Sequence[Mark] = ()
) -> list[Piece]:
    """Lay out the three spans, then one child of `gating` per phase mark the gate printed.

    Returns:
        the whole first, so a reader meets the parent before its children; the phase spans last.

    """
    return [
        Piece(root, moments.submit_ns, moments.end_ns, ids.commit, ""),
        Piece(f"{root}.queued", moments.submit_ns, moments.lease_ns, ids.queued, ids.commit),
        Piece(f"{root}.gating", moments.lease_ns, moments.end_ns, ids.gating, ids.commit),
        *phase_pieces(moments, ids.gating, f"{root}.gating", phases),
    ]


def phase_pieces(moments: Moments, parent: str, prefix: str, phases: Sequence[Mark]) -> list[Piece]:
    """Turn phase marks into spans: each runs to the next mark, the last to the verdict (W1493).

    ⚑ A MARK OUTSIDE THE GATING WINDOW IS CLAMPED INTO IT, because the gate's clock and the lease
    are read by different processes and a phase must never start before its parent.

    Returns:
        one span per mark, named `<prefix>.<mark name>`, children of `parent`.

    """
    if not phases:
        return []
    edges = [*(m.at_ns for m in phases[1:]), moments.end_ns]
    found: list[Piece] = []
    for mark, end in zip(phases, edges, strict=True):
        start = min(max(mark.at_ns, moments.lease_ns), moments.end_ns)
        stop = min(max(end, start), moments.end_ns)
        found.append(Piece(f"{prefix}.{mark.name}", start, stop, secrets.token_hex(8), parent))
    return found


def plan(
    program: str, event: Mapping[str, str], waypoint: str, laid: tuple[Ids, list[Piece]]
) -> list[list[str]]:
    """Build one `mikemol-otlp trace` argv per piece.

    Returns:
        the argvs, in the order of the pieces.

    """
    ids, parts = laid
    repo = event.get("repo", "")
    status = "OK" if event["verdict"] == _OK else "ERROR"
    fields = {"repo": repo, "waypoint": waypoint, "sha": event.get("sha", "")}
    fields["verdict"] = event["verdict"]
    fields.update({key: event[key] for key in ("entries", "invocations") if key in event})
    shared = ["--service", SERVICE, "--namespace", repo, "--status", status]
    shared += ["--trace-id", ids.trace]
    for key, value in fields.items():
        shared += ["--field", f"{key}={value}"]
    argvs: list[list[str]] = []
    for part in parts:
        argv = [program, "trace", *shared, "--name", part.name, "--span-id", part.span_id]
        argv += ["--start-ns", str(part.start_ns), "--end-ns", str(part.end_ns)]
        argvs.append([*argv, *(["--parent-id", part.parent_id] if part.parent_id else [])])
    return argvs


def stack_event(text: str) -> dict[str, str] | None:
    """Fold the verdict lines of a stack run into ONE event: the run as a whole.

    ⚑ A STACK IS ONE GATE, SO IT IS ONE TRACE: the wait for the lease and the gate on the tip are
    shared by every entry, and one span per entry would count that gate N times in a panel. The
    verdict is COMMITTED only when every entry committed, else the first entry that did not; the
    shas are joined and `entries` says how many verdict lines there were.

    Returns:
        the event, or None when the output holds no verdict line.

    """
    names = {name for name, _ in verdictlog.VERDICTS}
    found = [e for e in verdictlog.events_of(text) if e["verdict"] in names]
    if not found:
        return None
    bad = next((e["verdict"] for e in found if e["verdict"] != _OK), _OK)
    shas = ",".join(e["sha"] for e in found if "sha" in e)
    event = {"verdict": bad, "repo": found[0]["repo"], "sha": shas, "entries": str(len(found))}
    ids = invocations_of(text)
    return {**event, "invocations": ids} if ids else event


def _start(
    what: tuple[Mapping[str, str] | None, str, str, Sequence[Mark]],
    moments: Moments,
    env: Mapping[str, str],
    spawn: Spawn,
) -> int:
    """Start the span children for one finished run, when a child and a store exist.

    `what` is (event, waypoint, root name of the trace, the gate's phase marks).

    Returns:
        how many were started, 0 when there is no event, binary or endpoints file, or the first
        start failed.

    """
    event, waypoint, root, phases = what
    program = binary(env)
    if event is None or program is None or not store_named(env):
        return 0
    ids = new_ids()
    started = 0
    for argv in plan(program, event, waypoint, (ids, pieces(moments, ids, root, phases))):
        try:
            spawn(argv)
        except OSError:
            break
        started += 1
    return started


def gate_series(moments: Moments) -> list[tuple[str, float]]:
    """Name the two figures of one gate: the wait for its turn and the run itself (W2053).

    ⚑ ADMISSION WAIT AND RUN TIME ARE DIFFERENT TERMS OF TIME-TO-LAND (github-8f 2026-10-26: a gate
    that took 116 minutes spent about 110 of them before its pre-commit started, and nothing
    measured it). The wait is the submit to the lease, the run is the lease to the verdict, both
    in seconds and neither below zero, so a clock that stepped back reads 0 and not a negative.

    Returns:
        `(mikemol.gate.admission_wait_seconds, wait)` and `(mikemol.gate.run_seconds, run)`.

    """
    wait = max(moments.lease_ns - moments.submit_ns, 0) / NS_PER_S
    run = max(moments.end_ns - moments.lease_ns, 0) / NS_PER_S
    return [(ADMISSION_NAME, wait), (RUN_NAME, run)]


def emit_series(
    repo: str, moments: Moments, env: Mapping[str, str], spawn: Spawn = spawn_detached
) -> int:
    """Start one `mikemol-otlp metric` child for each of the gate's two figures.

    Returns:
        how many were started: 0 with no binary or store; a failed start ends the run quietly.

    """
    program = binary(env)
    if program is None or not store_named(env):
        return 0
    shared = ["--service", SERVICE, "--namespace", repo, "--field", f"repo={repo}"]
    started = 0
    for name, value in gate_series(moments):
        try:
            spawn([program, "metric", *shared, "--name", name, "--value", f"{value:.3f}"])
        except OSError:
            break
        started += 1
    return started


def emit(
    text: str,
    moments: Moments,
    waypoint: str,
    env: Mapping[str, str],
    spawn: Spawn = spawn_detached,
) -> int:
    """Start the three span children for a finished commit, when a child and a store exist.

    Returns:
        how many were started: 0 when there is no verdict line, no binary, no endpoints file, or
        the first start failed; a failure never propagates.

    """
    event = verdict_of(text)
    if event is not None:
        emit_series(event["repo"], moments, env)
    return _start((event, waypoint, "commit", _marks_of(text)), moments, env, spawn)


def emit_stack(
    text: str,
    moments: Moments,
    waypoints: Sequence[str],
    env: Mapping[str, str],
    spawn: Spawn = spawn_detached,
) -> int:
    """Start the three span children for a finished stack run: `commit.stack` and its phases.

    Each landed card also gets a landing log record (W1738), its gate seconds the time from the
    lease to the verdict; that is a separate child and does not change the count returned.

    Returns:
        how many were started, as `emit`; the waypoint attribute is the entries' joined.

    """
    emit_landings(text, (moments.end_ns - moments.lease_ns) / NS_PER_S, env)
    found = _marks_of(text)
    event = stack_event(text)
    if event is not None:
        emit_series(event["repo"], moments, env)
    return _start((event, ",".join(waypoints), "commit.stack", found), moments, env, spawn)
