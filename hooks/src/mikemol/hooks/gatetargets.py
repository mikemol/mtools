# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-gate-targets REPO BEP TESTLOGS`: a gate's per-target measurements, to the metrics store.

W1783, W1735. The operator's ruling (2026-10-20, line 88070 of the host transcript): luthen collects
metrics into victoria and trains the model on the history; the budgets and the SMT knee come back as
series. This is mtools' side, the emit, to the contract luthen fixed on luthen-observability:W1463:

    mikemol.gate.target.cpu.seconds | .wall.seconds | .children
        {target, kind, repo}, kind in mutants|pytest|other, at the time the test finished
    mikemol.gate.run.emitted{repo}   the number of targets emitted in this run, 0 when all cached
    mikemol.gate.target.failed {target, kind, repo}   1 when the final attempt did not pass, else 0

⚑ THE FAILED SAMPLE IS THE TARGET HALF OF A FAILURE HISTORY (W1800, W1719): a target's record over
prior runs is then a metrics query, and needs no key to the build event service (a BuildBuddy search
answers 403 without one, W1715). Every fresh result whose events carry a status is a sample, passing
ones as 0, because a history with only the failures in it cannot say whether the target ran.

⚑ A CACHED RESULT IS NOT EMITTED. Bazel replays an old test's result with its old log, so sending it
would put a measurement from an earlier run at today's time. Only a result that ran in this
invocation is a sample. The count of those, including zero, is `mikemol.gate.run.emitted`, so a
fully cached gate, a day with no gate and a dead emitter are three different readings.

⚑ THE BUILD EVENTS GIVE THE LABEL, STATUS, WALL TIME AND WHEN; THE LOG GIVES THE CPU. The BEP's log
URIs are remote `bytestream://` blobs, not local files, so the shard line (`shard cpu=S children=K
idle_wall=W`, W1769) is read from the local testlogs directory, which `bazel info bazel-testlogs`
prints as a real path. Retired instructions and cycles are not emitted yet: nothing records them
per target (W1779).

⚑ THE SEND IS A BATCH, NOT A PROCESS PER SAMPLE (`mikemol-otlp metrics`, W1784), in chunks of
`CHUNK` rows so each fits an OS pipe without blocking. BEST EFFORT, NEVER CHANGING A VERDICT: no
binary or store, or a failed spawn, means nothing is sent and the exit is still 0.
"""

import json
import os
import re
import sys
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from mikemol.hooks.commit_span import binary, store_named
from mikemol.hooks.vlogdetach import spawn_with_stdin

SERVICE = "mikemol-gate"
CPU = "mikemol.gate.target.cpu.seconds"
WALL = "mikemol.gate.target.wall.seconds"
CHILDREN = "mikemol.gate.target.children"
FAILED = "mikemol.gate.target.failed"
RUN_SECONDS = "mikemol.gate.run.seconds"
PASSED = "PASSED"
EMITTED = "mikemol.gate.run.emitted"
MUTANTS = "mutants"
PYTEST = "pytest"
OTHER = "other"
CHUNK = 100
MILLIS = 1_000_000
EXIT_USAGE = 2
ARGUMENTS = 3
_LABEL = re.compile(r"//[A-Za-z0-9_./-]*:[A-Za-z0-9_.+/-]+")
_SHARD = re.compile(r"shard cpu=([0-9.]+)s children=(\d+) idle_wall=[0-9.]+s")

type Row = dict[str, object]
type Spawn = Callable[[Sequence[str], str], None]
type Reader = Callable[[str], str | None]


@dataclass(frozen=True, slots=True)
class Result:
    """One test target's result in this invocation, as the build events state it."""

    label: str
    wall_s: float
    cached: bool
    finished_ns: int
    status: str = ""


def _result_of(event: object) -> Result | None:
    """Read one event as a test result.

    Returns:
        the Result, or None when it is not a well-formed test-result event.

    """
    if not isinstance(event, dict):
        return None
    ident, body = event.get("id"), event.get("testResult")
    if not isinstance(ident, dict) or not isinstance(body, dict):
        return None
    key = ident.get("testResult")
    label = key.get("label") if isinstance(key, dict) else None
    if not isinstance(label, str) or not _LABEL.fullmatch(label):
        return None
    try:
        wall_ms = int(body["testAttemptDurationMillis"])
        start_ms = int(body["testAttemptStartMillisEpoch"])
    except (KeyError, ValueError, TypeError):
        return None
    info = body.get("executionInfo")
    remote = isinstance(info, dict) and bool(info.get("cachedRemotely"))
    cached = bool(body.get("cachedLocally")) or remote
    status = body.get("status")
    finished_ns = (start_ms + wall_ms) * MILLIS
    return Result(
        label, wall_ms / 1000.0, cached, finished_ns, status if isinstance(status, str) else ""
    )


def results_of(lines: Iterable[str]) -> list[Result]:
    """Read the test results out of a build-event JSON file, one per target.

    ⚑ THE LAST ATTEMPT OF A TARGET WINS (a retried flaky test is one measurement, its final one),
    and a line that is not JSON, or an event that is not a test result, is skipped: the file is
    bazel's, and a gate must not fail because it is read.

    Returns:
        one Result per target, in first-seen order.

    """
    found: dict[str, Result] = {}
    for line in lines:
        try:
            event: object = json.loads(line)
        except ValueError:
            continue
        made = _result_of(event)
        if made is not None:
            found[made.label] = made
    return list(found.values())


def _millis(event: object, section: str, field: str) -> int | None:
    # One int64 millisecond field of a build event's body, which JSON spells as a string.
    if not isinstance(event, dict):
        return None
    body = event.get(section)
    raw = body.get(field) if isinstance(body, dict) else None
    try:
        return int(raw) if isinstance(raw, str | int) else None
    except ValueError:
        return None


def run_seconds(lines: Iterable[str]) -> float | None:
    """Read the build's own wall time out of its started and finished events (W1801).

    ⚑ THE WHOLE-GATE SERIES THE MEDIAN AND THE FRESHNESS ALERT NEED (W1748, W1781): per-target
    samples cannot say how long the gate took. The two events carry the build's start and finish in
    milliseconds, so the difference is the bazel run, not the hook around it.

    Returns:
        the seconds between the started and the finished event, or None when either is absent or
        the finish precedes the start.

    """
    start = finish = None
    for line in lines:
        try:
            event: object = json.loads(line)
        except ValueError:
            continue
        start = _millis(event, "started", "startTimeMillis") or start
        finish = _millis(event, "finished", "finishTimeMillis") or finish
    if start is None or finish is None or finish < start:
        return None
    return (finish - start) / 1000.0


def kind_of(label: str) -> str:
    """Name what sort of target this is.

    Returns:
        `mutants` for a `:mutants` target or shard, `pytest` for a `:test_*` one, else `other`.

    """
    name = label.rsplit(":", 1)[-1]
    if name == "mutants" or name.startswith("mutants_"):
        return MUTANTS
    return PYTEST if name.startswith("test_") else OTHER


def shard_line(text: str) -> tuple[float, int] | None:
    """Read the runner's CPU line out of a test log (W1769).

    Returns:
        (CPU seconds, children), or None when the log carries no such line.

    """
    found = _SHARD.search(text)
    return (float(found.group(1)), int(found.group(2))) if found else None


def log_reader(testlogs: Path) -> Reader:
    """Build the reader of a target's `test.log` under a testlogs directory.

    Returns:
        a function from a label to the log's text, or None when the log is unreadable.

    """

    def read(label: str) -> str | None:
        package, _, name = label.removeprefix("//").partition(":")
        try:
            return (testlogs / package / name / "test.log").read_text(
                encoding="utf-8", errors="replace"
            )
        except OSError:
            return None

    return read


def _row(name: str, value: float, time_ns: int, fields: Mapping[str, str]) -> Row:
    return {"name": name, "value": value, "time_ns": time_ns, "fields": dict(fields)}


def _rows_of_result(result: Result, read: Reader) -> list[Row]:
    """Turn one fresh result into its gauge rows.

    Returns:
        the wall row, and the CPU and children rows when a mutants or pytest log has the shard line.

    """
    kind = kind_of(result.label)
    fields = {"target": result.label, "kind": kind}
    rows = [_row(WALL, result.wall_s, result.finished_ns, fields)]
    if result.status:
        failed = 0.0 if result.status == PASSED else 1.0
        rows.append(_row(FAILED, failed, result.finished_ns, fields))
    text = read(result.label) if kind in {MUTANTS, PYTEST} else None
    shard = shard_line(text) if text else None
    if shard is not None:
        rows.extend(
            [
                _row(CPU, shard[0], result.finished_ns, fields),
                _row(CHILDREN, shard[1], result.finished_ns, fields),
            ]
        )
    return rows


def rows_of(results: Iterable[Result], read: Reader, now_ns: int) -> list[Row]:
    """Turn the fresh results into gauge rows, led by the per-run count.

    Returns:
        the `run.emitted` row (a value of 0 when every result was cached), then each uncached
        target's rows, every one `{name, value, time_ns, fields}`.

    """
    fresh = [result for result in results if not result.cached]
    rows = [_row(EMITTED, len(fresh), now_ns, {})]
    for result in fresh:
        rows.extend(_rows_of_result(result, read))
    return rows


def plan(program: str, repo: str, rows: Sequence[Row]) -> list[tuple[list[str], str]]:
    """Build the children a run starts, each with the JSON lines for its stdin.

    ⚑ EVERY ROW CARRIES THE `repo` LABEL, as the contract's labels are `{target, kind, repo}` and
    `run.emitted` has `repo` alone.

    Returns:
        one `mikemol-otlp metrics` argv and its text per chunk of `CHUNK` rows.

    """
    argv = [program, "metrics", "--service", SERVICE, "--namespace", repo]
    labelled = [{**row, "fields": {**_fields_of(row), "repo": repo}} for row in rows]
    chunks = [labelled[i : i + CHUNK] for i in range(0, len(labelled), CHUNK)]
    return [(argv, "".join(json.dumps(row) + "\n" for row in chunk)) for chunk in chunks]


def _fields_of(row: Row) -> dict[str, str]:
    fields = row["fields"]
    return {str(k): str(v) for k, v in fields.items()} if isinstance(fields, dict) else {}


def emit(
    repo: str,
    rows: Sequence[Row],
    env: Mapping[str, str],
    spawn: Spawn = spawn_with_stdin,
) -> bool:
    """Start the children for a finished gate, when a binary and a store exist.

    Returns:
        whether every child was started; False with no binary or store, or a failed spawn.

    """
    program = binary(env)
    if program is None or not store_named(env):
        return False
    try:
        for argv, text in plan(program, repo, rows):
            spawn(argv, text)
    except OSError:
        return False
    return True


def main(argv: Sequence[str] | None = None, spawn: Spawn = spawn_with_stdin) -> int:
    """Read a gate's build events and test logs and ship the fresh targets' measurements.

    Returns:
        0 once the arguments are right (a send that cannot start changes nothing), or 2 with
        usage when REPO, BEP and TESTLOGS are not all given or the BEP file cannot be read.

    """
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != ARGUMENTS:
        sys.stderr.write("usage: mikemol-gate-targets REPO BEP-FILE TESTLOGS-DIR\n")
        return EXIT_USAGE
    repo, bep, testlogs = args
    try:
        lines = Path(bep).read_text(encoding="utf-8").splitlines()
    except OSError as err:
        sys.stderr.write(f"mikemol-gate-targets: cannot read {bep}: {err}\n")
        return EXIT_USAGE
    results = results_of(lines)
    now_ns = time.time_ns()
    rows = rows_of(results, log_reader(Path(testlogs)), now_ns)
    elapsed = run_seconds(lines)
    if elapsed is not None:
        rows.append(_row(RUN_SECONDS, elapsed, now_ns, {}))
    sent = emit(repo, rows, os.environ, spawn)
    sys.stdout.write(f"gate targets: {rows[0]['value']} fresh of {len(results)}, sent={sent}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
