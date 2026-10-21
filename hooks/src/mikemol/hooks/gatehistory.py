# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Each gate step's failure history over prior train rounds, newest first (W1719).

A red round names the checks the gate's own summary listed as failed (W1728, recorded on the round's
span by W1715). Whether `//hooks:test_x` failing now is NEW or the fifth red round in a row is
a question of its history, and the history is already in the trace store: this reads the round
spans `mikemol-otlp query-traces --service mikemol-train --name train.round` prints (W1799) and
gives each check its pass and fail record, so the answer is a lookup and not a guess.

⚑ A ROUND SAYS SOMETHING ABOUT A STEP ONLY WHEN IT RAN THE STEP. `green` ran every check and each
passed. `red` with named checks ran them and exactly those failed. A `red` round with no label (the
gate stopped before its summary), an `unbuilt` one and a `raced` one are not evidence for or against
any step, so they are left out rather than counted as passes: a step is never reported healthy on a
round that did not look at it.

⚑ NEWEST FIRST, BY THE SPAN'S OWN START TIME, never by round number: a round number restarts with
every train, so two trains' round 1 are different rounds.

⚑ THE SCOPE IS ONE REPO'S ROUNDS: the spans of every repo share a service, so `report` takes the
repo whose rounds it reads and a step of another repo's gate is not in it.

THIS READS STEPS, the labels the summary prints. A bazel TARGET inside a step lives in the gate's
build event stream, which needs the invocation each round recorded and a key the host does not hand
this session; that half is its own card.

CONSUMED BY: the `mikemol-gate-history` console script, which reads the search's lines on stdin.
"""

import json
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import TextIO, cast

GREEN = "green"
RED = "red"
NONE = "-"
SEPARATOR = "; "
EXIT_OK = 0
EXIT_USAGE = 2


@dataclass(frozen=True, slots=True)
class Round:
    """One train round that looked at the gate's steps."""

    repo: str
    start_us: int
    verdict: str
    failed: tuple[str, ...]


def _fields(record: Mapping[str, object]) -> dict[str, str]:
    # A search line's attribute object as strings; empty when it has none.
    raw = record.get("fields")
    if not isinstance(raw, dict):
        return {}
    return {str(key): str(value) for key, value in cast("dict[object, object]", raw).items()}


def _round_of(line: str) -> Round | None:
    # One search line as a round that ran its steps, or None for anything that says nothing of them.
    try:
        parsed = cast("object", json.loads(line))
    except ValueError:
        return None
    if not isinstance(parsed, dict):
        return None
    record = cast("dict[str, object]", parsed)
    fields = _fields(record)
    verdict = fields.get("verdict", "")
    shown = fields.get("failed", NONE)
    failed = tuple(label for label in shown.split(SEPARATOR) if label and label != NONE)
    start = record.get("start_us")
    if not isinstance(start, int) or verdict not in {GREEN, RED}:
        return None
    if (verdict == RED) != bool(failed):
        return None
    return Round(fields.get("repo", ""), start, verdict, failed)


def _started(round_: Round) -> int:
    # The sort key: when the round began.
    return round_.start_us


def rounds_of(lines: Iterable[str], repo: str) -> list[Round]:
    """Read the rounds of `repo` that ran their steps out of the search's lines.

    Returns:
        the rounds, newest first; lines that are not JSON, not a round span, of another repo or that
        name no verdict about the steps are left out.

    """
    found = [round_ for line in lines if (round_ := _round_of(line)) is not None]
    return sorted((r for r in found if r.repo == repo), key=_started, reverse=True)


def history(rounds: Sequence[Round]) -> dict[str, tuple[bool, ...]]:
    """Give each step that ever failed in `rounds` its record, True where it failed.

    Returns:
        label to one flag per round, in the order the rounds were given (newest first), so a step
        that failed only in the oldest round reads (False, False, True).

    """
    labels = sorted({label for r in rounds for label in r.failed})
    return {label: tuple(label in r.failed for r in rounds) for label in labels}


def streak(record: Sequence[bool]) -> int:
    """Count the failures at the newest end of a record.

    Returns:
        how many rounds in a row, newest first, the step has failed; 0 when the newest passed.

    """
    count = 0
    for failed in record:
        if not failed:
            break
        count += 1
    return count


def describe(label: str, record: Sequence[bool]) -> str:
    """Say one step's record in a line.

    Returns:
        the label, how many of the rounds it failed in and the current streak.

    """
    return f"{label}: failed {sum(record)} of {len(record)} rounds, streak {streak(record)}"


def report(lines: Iterable[str], repo: str) -> list[str]:
    """Build the report for `repo` from the search's lines.

    Returns:
        one line per step that ever failed, the currently-failing first and then by label; a single
        line saying so when no round ran its steps or none failed a step.

    """
    rounds = rounds_of(lines, repo)
    if not rounds:
        return [f"no round of {repo} that ran its steps"]
    records = history(rounds)
    order = sorted((-streak(record), label) for label, record in records.items())
    return [describe(label, records[label]) for _, label in order] or [
        f"{len(rounds)} rounds of {repo}, none failed a step"
    ]


def main(argv: Sequence[str] | None = None, stdin: TextIO | None = None) -> int:
    """Print each step's failure history for the repo named on the command line.

    Returns:
        `EXIT_OK` with the report printed, `EXIT_USAGE` when the one argument (the repo) is missing.

    """
    args = sys.argv[1:] if argv is None else list(argv)
    if len(args) != 1:
        sys.stderr.write("usage: mikemol-gate-history REPO < query-traces-lines\n")
        return EXIT_USAGE
    source = cast("TextIO", sys.stdin) if stdin is None else stdin
    sys.stdout.writelines(f"{line}\n" for line in report(source.read().splitlines(), args[0]))
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
