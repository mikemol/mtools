# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""Report a running //:hook's progress and its WINDOWED action rate, so a stall is named.

Ported from paperkit's `tools/buildpulse.py` (paperkit:W142); behaviour unchanged. The `pgrep`
probe goes through `proc` and the clock is a parameter, so a test drives every terminal state;
`--selftest` is kept, and its checks are a list of `(name, verdict)` pairs (paperkit's `check`
helper took a boolean positional, which the `# noqa: FBT001` waived).

THE HOOK HAS NO PROGRESS PULSE, AND THAT IS A RECORDED GAP (`tooling-self-regulates`): a
126k-action sweep prints a live action counter and nothing that says whether the counter is
MOVING.  Idle CPU with a slow wall clock is the lease queue behaving correctly; idle CPU with a
FROZEN counter is a stall.  The two look identical in a `tail`, and telling them apart takes two
samples separated in time - which is precisely the judgement that evaporates when a turn ends.

SO THE STATE IS PERSISTED, NOT HELD IN THE READER.  Each run appends a sample to a JSONL file
and reports the rate against the OLDEST sample still inside the window.  A monitor invoking this
every 15 minutes therefore gets a real actions-per-minute, and the verdict travels with the
artifact instead of being re-derived (differently) by whoever reads the log next.

SILENCE IS NOT SUCCESS.  The Monitor contract is explicit that a watcher which only matches the
happy path stays quiet through a crash.  This exits non-zero and says so when the build process is
GONE, when the counter has not moved for `--stall-after`, or when the log's tail carries a failure
signature - three distinct terminal states, each named, none of them a silent hang.  `--selftest`
proves each of those arms can FIRE; an alarm whose red path has never run is not a control.

IT WAS WRITTEN IN A SCRATCHPAD AND LANDED AFTERWARDS, WHICH IS THE POINT (quiesce).  Writing
it into the repo while a //:hook run was in flight would have invalidated that run - a sandboxed
cell whose input changes reds with `input dependency modified during execution`, which reads as an
engine defect rather than as interference.  The repo's own PreToolUse guard refused the write and
was right to; the tool lived outside the tree until the tree was quiet.

    python -m mikemol.buildtel.buildpulse --log <hook.output>     # one sample, human-readable
    python -m mikemol.buildtel.buildpulse --log <f> --window 3600 # rate over the last hour
    python -m mikemol.buildtel.buildpulse --selftest              # prove every arm can fire
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.buildtel import proc

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

# Bazel's progress line: "[39,547 / 116,688] eval ..."
PROGRESS = re.compile(r"\[([\d,]+)\s*/\s*([\d,]+)\]")
# Terminal-state signatures worth waking a reader for.  Deliberately broader than the failures
# seen so far: the Monitor contract says to widen rather than narrow when enumeration is uncertain.
TROUBLE = re.compile(
    r"\bFAIL(?:ED)?\b|\bERROR\b|Traceback|OutOfMemoryError|"
    r"input dependency modified during execution|Build did NOT complete",
)
# THE EXECUTABLE NAME, NOT THE COMMAND LINE (probe-self).  This read `pgrep -f "bazel test
# //:hook"`, and a watcher looping that predicate MATCHES ITSELF: the loop's own command line
# contains the literal, so it can never see the build as gone.  Measured - a monitor kept pulsing
# after a completed run, and the first fix (`installs/bazel/.*bazel test //:hook`) was wrong the
# same way.  `pgrep -x` matches the executable, which a shell cannot spoof.
BUILD_EXE = "bazel"

MINUTES_PER_HOUR = 60.0
SECONDS_PER_MINUTE = 60.0
PERCENT = 100.0
DAY_S = 86_400
PAIR = 2
DEFAULT_WINDOW = 3600.0  # seconds of history the rate is measured over
DEFAULT_STALL = 1800.0  # seconds with an unmoved counter before calling it a stall
EPS = 0.01
EXIT_NO_LOG = 2
TROUBLE_MAX = 160
PROGRESS_TAIL = 200_000
TROUBLE_TAIL = 20_000
SELFTEST_SIGNATURES = (
    "FAIL: @@x//:y (Exit 1)",
    "ERROR: Build did NOT complete successfully",
    "java.lang.OutOfMemoryError: Java heap space",
    "Traceback (most recent call last):",
    "err: input dependency modified during execution",
)
SIGNATURE_LABEL = 42


@dataclass(frozen=True)
class Sample:
    """One observation of the build's progress counter."""

    at: float
    done: int
    total: int


def _tail(path: Path, nbytes: int) -> str:
    """Read the last `nbytes` of a file as text.

    ⚑ ONLY THE TAIL, DELIBERATELY.  A //:hook log reaches hundreds of MB and every answer here is
    at the end.  Reading the whole file to find the last line is the shape that put a 4.45 GB
    execution log in RAM (execlog-leak) - the same lesson, on the reading side.

    Returns:
        the tail, undecodable bytes replaced.

    """
    size = path.stat().st_size
    with path.open("rb") as fh:
        fh.seek(max(0, size - nbytes))
        return fh.read().decode("utf-8", "replace")


def read_progress(log: Path, tail_bytes: int = PROGRESS_TAIL) -> tuple[int, int]:
    """Read the most recent [done / total] the log carries, or (0, 0) when there is none.

    ⚑ The `findall` Any is narrowed HERE, at the seam, so callers see concrete ints.

    Returns:
        `(done, total)`.

    """
    hits: object = PROGRESS.findall(_tail(log, tail_bytes))
    if not isinstance(hits, list) or not hits:
        return (0, 0)
    last: object = hits[-1]
    if not isinstance(last, tuple) or len(last) != PAIR:
        return (0, 0)
    done, total = str(last[0]), str(last[1])
    return (int(done.replace(",", "")), int(total.replace(",", "")))


def read_trouble(log: Path, tail_bytes: int = TROUBLE_TAIL) -> str:
    """Return the newest line matching a failure signature, or "" when the tail is clean.

    Returns:
        the line, clipped to 160 characters, or "".

    """
    hits = [ln for ln in _tail(log, tail_bytes).splitlines() if TROUBLE.search(ln)]
    return hits[-1][:TROUBLE_MAX] if hits else ""


def build_alive(run: proc.Runner = proc.capture) -> bool:
    """Report whether the //:hook build process is still running.

    Returns:
        True when `pgrep -x bazel` finds one.

    """
    status, _out, _err = run(["pgrep", "-x", BUILD_EXE])
    return status == 0


def load(state: Path) -> list[Sample]:
    """Read the samples recorded so far, skipping any line that is not one.

    Returns:
        the samples, in file order.

    """
    if not state.exists():
        return []
    out: list[Sample] = []
    for ln in state.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        try:
            rec: object = json.loads(ln)
        except ValueError:
            continue
        if not isinstance(rec, dict):
            continue
        at: object = rec.get("at")
        done: object = rec.get("done")
        total: object = rec.get("total")
        if isinstance(at, float) and isinstance(done, float) and isinstance(total, float):
            out.append(Sample(at=at, done=int(done), total=int(total)))
    return out


def append(state: Path, s: Sample) -> None:
    """Append one sample to the state file."""
    rec: dict[str, float] = {"at": s.at, "done": float(s.done), "total": float(s.total)}
    with state.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")


def rate(now: Sample, past: list[Sample], window: float) -> tuple[float, float]:
    """Actions per minute against the oldest sample inside `window`, with that span in minutes.

    Returns (0, 0) when there is no earlier sample to measure against - an honest "not yet known"
    rather than a zero that reads as a stall on the very first call.

    Returns:
        `(actions per minute, span in minutes)`.

    """
    inside = [p for p in past if now.at - p.at <= window]
    if not inside:
        return (0.0, 0.0)
    ref = inside[0]
    if now.at <= ref.at:
        return (0.0, 0.0)
    mins = (now.at - ref.at) / SECONDS_PER_MINUTE
    return ((now.done - ref.done) / mins, mins)


def stalled(now: Sample, past: list[Sample], stall_after: float) -> float:
    """Minutes the counter has been frozen, or 0.0 when it has moved (or nothing to compare).

    One function so the predicate has ONE definition - the selftest asserts against the same code
    the reporting path runs, not a restatement of it.

    ⚑ THE WINDOW IS A FLOOR ON THE AGE, NOT A CEILING - AND THE FIRST CUT HAD IT BACKWARDS.  It
    kept only samples NEWER than `stall_after`, so a counter frozen for LONGER than the window
    left the set empty and reported NO STALL: the alarm went silent exactly as the outage got
    worse, which is the `silence is not success` failure committed by the thing built to prevent
    it.  Caught by --selftest on its first run, not by a build.

    The correct predicate: find the OLDEST sample that still agrees with the current count and has
    no DISAGREEING sample after it, then report how long ago it was.  A sample with a different
    count means the counter moved at that point, so the freeze can only have run since then.

    Returns:
        the minutes frozen, or 0.0.

    """
    if not past:
        return 0.0
    moved = [p.at for p in past if p.done != now.done]
    since = max(moved) if moved else None
    agreeing = [p.at for p in past if p.done == now.done and (since is None or p.at > since)]
    if not agreeing:
        return 0.0
    held = (now.at - min(agreeing)) / SECONDS_PER_MINUTE
    return held if held * SECONDS_PER_MINUTE >= stall_after else 0.0


def eta(now: Sample, per_min: float) -> str:
    """Render a remaining-time estimate, or "" when the rate cannot support one.

    ⚑ AN ESTIMATE, AND LABELLED AS ONE.  The grid's cells are not uniform and the aggregation
    phases come last, so a linear extrapolation is a floor on the honest answer rather than a
    prediction.  It is printed because "is this minutes or hours away" is the actual question,
    and withheld entirely when the rate is zero rather than rendered as infinity.

    Returns:
        the estimate text (leading separator included), or "".

    """
    if per_min <= 0 or now.total <= now.done:
        return ""
    mins = (now.total - now.done) / per_min
    if mins >= MINUTES_PER_HOUR:
        return f" · ~{mins / MINUTES_PER_HOUR:.1f}h left at this rate (linear est.)"
    return f" · ~{mins:.0f}m left at this rate (linear est.)"


def selftest_cases(d: Path) -> list[tuple[str, bool]]:
    """Construct each failure on synthetic inputs in `d` and say whether the arm names it.

    ⚑ AN ALARM WHOSE RED PATH HAS NEVER RUN IS NOT A CONTROL (instrument-vs-gate).  The Monitor
    contract's own warning is that silence looks identical to "still running", so the question
    that matters is not "does it print a percentage" but "would it emit anything if the build died
    right now".  Each case constructs the failure and asserts the arm names it.

    ⚑⚑ AND THE STALL CASE SEEDS ITS CLOCK rather than waiting on one.  A probe that must sleep 30
    minutes to exercise its 30-minute predicate never gets run, and a predicate that is never run
    is the one that is wrong.

    Returns:
        `(name, verdict)` for every case, in order.

    """
    cases: list[tuple[str, bool]] = []

    # a healthy tail parses and stays quiet
    good = d / "good.log"
    good.write_text("[42,387 / 120,269] eval something; 1s linux-sandbox\n")
    cases.extend(
        [
            ("progress parses a comma-formatted counter", read_progress(good) == (42387, 120269)),
            ("a clean tail yields no failure signature", not read_trouble(good)),
        ]
    )

    # every failure signature is caught
    for sig in SELFTEST_SIGNATURES:
        f = d / "f.log"
        f.write_text(f"[1 / 2] fine\n{sig}\n")
        cases.append((f"caught: {sig[:SIGNATURE_LABEL]}", bool(read_trouble(f))))

    # a frozen counter across the window is a STALL, and one action clears it
    st = d / "s.pulse"
    old = time.time() - DEFAULT_WINDOW
    seed: dict[str, float] = {"at": old, "done": 42.0, "total": 100.0}
    st.write_text(json.dumps(seed) + "\n")
    past = load(st)
    cases.append(("a seeded sample round-trips through load()", len(past) == 1))
    now = Sample(at=time.time(), done=42, total=100)
    cases.append(
        ("F - a frozen counter is reported as a stall", stalled(now, past, DEFAULT_STALL) > 0)
    )
    moved = Sample(at=now.at, done=43, total=100)
    cases.append(
        (
            "delta - ONE action of progress clears the stall verdict",
            not stalled(moved, past, DEFAULT_STALL),
        )
    )

    # ⚑ THE REGRESSION THIS SELFTEST ALREADY CAUGHT ONCE: a freeze LONGER than the window.
    # The first predicate kept only samples newer than stall_after, so the longer the outage
    # ran the more certainly it reported nothing.  A day-old frozen sample must still stall.
    far = Sample(at=old - DAY_S, done=42, total=100)
    cases.append(
        (
            "F - a freeze OLDER than the window still stalls (not silence)",
            stalled(now, [far, *past], DEFAULT_STALL) > 0,
        )
    )

    # a counter that moved recently is not a stall, even with old agreeing samples
    recent = [far, Sample(at=old + 1, done=98, total=100)]
    advanced = Sample(at=now.at, done=99, total=100)
    cases.append(
        (
            "P - a counter that moved since the old sample is not a stall",
            not stalled(advanced, recent, DEFAULT_STALL),
        )
    )

    # the rate is withheld until there is something to measure against
    cases.extend(
        [
            (
                "no prior sample => rate (0,0), never a false stall",
                rate(now, [], DEFAULT_WINDOW) == (0.0, 0.0),
            ),
            ("no prior sample => no stall verdict either", not stalled(now, [], DEFAULT_STALL)),
        ]
    )
    r, span = rate(
        Sample(at=old + 600, done=142, total=1000),
        [Sample(at=old, done=42, total=1000)],
        DEFAULT_WINDOW,
    )
    cases.append(
        ("100 actions in 10m reads as 10/min", abs(r - 10.0) < EPS and abs(span - 10.0) < EPS)
    )
    return cases


def selftest() -> int:
    """Prove each arm can FIRE, on synthetic inputs with known contents.

    Returns:
        0 when every case holds, 1 otherwise.

    """
    with tempfile.TemporaryDirectory() as td:
        cases = selftest_cases(Path(td))
    bad: list[str] = []
    for name, cond in cases:
        if not cond:
            bad.append(name)
        sys.stdout.write(f"  {'ok' if cond else 'XX'} {name}\n")
    sys.stdout.write(f"\nbuildpulse selftest: {len(cases) - len(bad)}/{len(cases)}\n")
    return 1 if bad else 0


def parse_args(argv: Sequence[str]) -> tuple[Path, Path, float, float, bool]:
    """Read the command line into concrete types (a Namespace attribute is Any).

    Returns:
        `(log, state, window, stall_after, selftest)`; `state` defaults to `<log>.pulse`.

    """
    ap = argparse.ArgumentParser(description="Report a running build's progress and action rate.")
    ap.add_argument("--log", default="", help="the build's output file")
    ap.add_argument("--state", default="", help="where samples accumulate (default: <log>.pulse)")
    ap.add_argument(
        "--window",
        type=float,
        default=DEFAULT_WINDOW,
        help="seconds of history the rate is measured over",
    )
    ap.add_argument(
        "--stall-after",
        type=float,
        default=DEFAULT_STALL,
        help="seconds with an unmoved counter before calling it a STALL",
    )
    ap.add_argument("--selftest", action="store_true", help="prove every arm can fire, then exit")
    ns = ap.parse_args(list(argv))
    log: str = ns.log
    state: str = ns.state
    window: float = ns.window
    stall_after: float = ns.stall_after
    run_selftest: bool = ns.selftest
    return (
        Path(log),
        Path(state) if state else Path(log + ".pulse"),
        window,
        stall_after,
        run_selftest,
    )


def main(
    argv: Sequence[str] | None = None,
    *,
    is_alive: Callable[[], bool] = build_alive,
    clock: Callable[[], float] = time.time,
) -> int:
    """Sample the build once, report progress + windowed rate, and name any terminal state.

    Returns:
        0 while the build is alive and moving; 1 for a failure signature, a gone build or a
        stall; 2 when there is no log.

    """
    log, state, window, stall_after, run_selftest = parse_args(
        sys.argv[1:] if argv is None else argv
    )
    if run_selftest:
        return selftest()

    if not log.name or not log.exists():
        sys.stdout.write(f"pulse: no log at {log}\n")
        return EXIT_NO_LOG

    done, total = read_progress(log)
    now = Sample(at=clock(), done=done, total=total)
    past = load(state)
    append(state, now)

    per_min, span = rate(now, past, window)
    pct = (PERCENT * done / total) if total else 0.0

    line = f"pulse: {done:,}/{total:,} ({pct:.1f}%)"
    if span:
        line += f" · {per_min:,.0f} actions/min over {span:.0f}m" + eta(now, per_min)
    else:
        line += " · rate: first sample"
    sys.stdout.write(line + "\n")

    # terminal states, each named
    trouble = read_trouble(log)
    if trouble:
        sys.stdout.write(f"  ⚑ FAILURE SIGNATURE in the log tail: {trouble}\n")
        return 1

    if not is_alive():
        sys.stdout.write(
            "  ⚑ the //:hook build process is GONE — finished, or killed.  Read the log's "
            "tail for its verdict; a pulse cannot tell a green exit from a kill.\n"
        )
        return 1

    held = stalled(now, past, stall_after)
    if held:
        sys.stdout.write(
            f"  ⚑ STALL: the action counter has not moved in {held:.0f}m "
            f"(still {done:,}).  Alive but not progressing.\n"
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
