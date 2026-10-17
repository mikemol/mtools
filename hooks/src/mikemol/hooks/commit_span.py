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

import secrets
import shutil
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from mikemol.hooks import verdictlog
from mikemol.hooks.vlogdetach import spawn_detached

BIN_ENV = "MIKEMOL_OTLP_BIN"
ENDPOINTS_ENV = "MIKEMOL_ENDPOINTS"
SUBMIT_ENV = "MIKEMOL_COMMIT_SUBMITTED_NS"
SERVICE = "mikemol-commit"
_OK = "COMMITTED"
Spawn = Callable[[Sequence[str]], None]


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


def verdict_of(text: str) -> dict[str, str] | None:
    """Read the commit's verdict event out of its output.

    Returns:
        the LAST verdict event (verdict, repo and the parts that line has), or None when the
        output holds none.

    """
    names = {name for name, _ in verdictlog.VERDICTS}
    found = [e for e in verdictlog.events_of(text) if e["verdict"] in names]
    return found[-1] if found else None


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


def pieces(moments: Moments, ids: Ids, root: str = "commit") -> list[Piece]:
    """Lay out the three spans: the whole named `root`, then its two phases as children.

    Returns:
        the whole first, so a reader meets the parent before its children.

    """
    return [
        Piece(root, moments.submit_ns, moments.end_ns, ids.commit, ""),
        Piece(f"{root}.queued", moments.submit_ns, moments.lease_ns, ids.queued, ids.commit),
        Piece(f"{root}.gating", moments.lease_ns, moments.end_ns, ids.gating, ids.commit),
    ]


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
    fields.update({key: event[key] for key in ("entries",) if key in event})
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
    return {"verdict": bad, "repo": found[0]["repo"], "sha": shas, "entries": str(len(found))}


def _start(
    what: tuple[Mapping[str, str] | None, str, str],
    moments: Moments,
    env: Mapping[str, str],
    spawn: Spawn,
) -> int:
    """Start the span children for one finished run, when a child and a store exist.

    `what` is (event, waypoint, root name of the trace).

    Returns:
        how many were started, 0 when there is no event, binary or endpoints file, or the first
        start failed.

    """
    event, waypoint, root = what
    program = binary(env)
    if event is None or program is None or not env.get(ENDPOINTS_ENV):
        return 0
    ids = new_ids()
    started = 0
    for argv in plan(program, event, waypoint, (ids, pieces(moments, ids, root))):
        try:
            spawn(argv)
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
    return _start((verdict_of(text), waypoint, "commit"), moments, env, spawn)


def emit_stack(
    text: str,
    moments: Moments,
    waypoints: Sequence[str],
    env: Mapping[str, str],
    spawn: Spawn = spawn_detached,
) -> int:
    """Start the three span children for a finished stack run: `commit.stack` and its phases.

    Returns:
        how many were started, as `emit`; the waypoint attribute is the entries' joined.

    """
    return _start((stack_event(text), ",".join(waypoints), "commit.stack"), moments, env, spawn)
