# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Gate outcome ledger: measured pass/fail rates, and the fail-fast order (W303).

Ported from substrate's `scripts/gate_ledger.py`, which el-openglo borrowed by symlink. A
pre-commit runs its gates in a hand-chosen order, so a gate that fails half the time can sit
behind five that never do. Ordering by MEASURED failure rate makes the loop fail fast.

⚑⚑ THE LEDGER PATH IS AN ARGUMENT, NEVER DERIVED (el-openglo:W140, the defect this port closes).
The original computed `<this script's repo>/scripts/.gate-outcomes.tsv`. el-openglo's hook wrote
`<repo>/.gate-outcomes.tsv`, so `--report` printed "no outcomes recorded yet" over a ledger that
had been filling for days, and nobody could measure which gates held the commit. An installed
tool has no repo of its own to derive from. So `--ledger PATH` is required on every mode, and the
hook passes the one LEDGER variable it writes to, to `--record` and to `--report` alike: the
writer and the reader cannot disagree.

The ledger is append-only TSV, one row per gate run:

    iso8601 <TAB> gate <TAB> status <TAB> seconds

`status` is `pass` or `fail`. Rates are over each gate's last K runs, so a gate that was fixed
stops ranking first once its recent history is clean.

⚑ IT REPORTS THE OBSERVED POPULATION, NEVER THE DECLARED ONE. A gate that never ran has no rows
and is invisible here. The report says how many gates it saw, and never claims that is all of
them.

    mikemol-gate-ledger --ledger PATH --record GATE pass|fail SECONDS
    mikemol-gate-ledger --ledger PATH --order     # gate names, worst first
    mikemol-gate-ledger --ledger PATH [--report]  # rates and timings
"""

from __future__ import annotations

import argparse
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import cast

K = 20  # the window: each gate's rate is over its last K runs
_FIELDS = 4


@dataclass(frozen=True, slots=True)
class Stat:
    """One gate's recent record: failure rate, runs counted, and median seconds."""

    rate: float
    runs: int
    median: float


def record(ledger: Path, gate: str, status: str, seconds: str) -> None:
    """Append one outcome, never raising.

    ⚑ A ledger failure must not break the gate it measures: the instrument must not become a
    new failure mode.
    """
    try:
        with ledger.open("a", encoding="utf-8") as fh:
            fh.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')}\t{gate}\t{status}\t{seconds}\n")
    except OSError:
        return


def read(ledger: Path) -> dict[str, list[tuple[str, float]]]:
    """Read every gate's history, oldest first. A short row is skipped, a bad number reads 0.

    Returns:
        gate -> [(status, seconds)].

    """
    history: dict[str, list[tuple[str, float]]] = defaultdict(list)
    try:
        lines = ledger.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    for line in lines:
        fields = line.split("\t")
        if len(fields) < _FIELDS:
            continue
        try:
            seconds = float(fields[3])
        except ValueError:
            seconds = 0.0
        history[fields[1]].append((fields[2], seconds))
    return dict(history)


def stats(history: dict[str, list[tuple[str, float]]]) -> dict[str, Stat]:
    """Summarize each gate over its last K runs.

    Returns:
        gate -> its Stat.

    """
    out: dict[str, Stat] = {}
    for gate, rows in history.items():
        recent = rows[-K:]
        fails = sum(1 for status, _ in recent if status == "fail")
        times = sorted(seconds for _, seconds in recent)
        out[gate] = Stat(fails / len(recent), len(recent), times[len(times) // 2])
    return out


def order(ledger: Path) -> list[str]:
    """Rank the gates worst first: highest failure rate, then the CHEAPEST first.

    ⚑ Among gates that fail equally often, running the cheap one first costs less per rejected
    attempt: fail-fast is about time to rejection, not position alone.

    Returns:
        gate names, worst first.

    """
    ranked = sorted(stats(read(ledger)).items(), key=_worst_first)
    return [gate for gate, _ in ranked]


def _worst_first(item: tuple[str, Stat]) -> tuple[float, float]:
    """Key a gate by failure rate (descending), then median seconds (ascending).

    Returns:
        the sort key.

    """
    return (-item[1].rate, item[1].median)


def report(ledger: Path) -> str:
    """Write the rates and timings, worst first, naming the file read.

    Returns:
        the report text.

    """
    table = stats(read(ledger))
    if not table:
        return f"gate-ledger: no outcomes recorded yet in {ledger}"
    lines = [f"{'gate':<34} {'fail%':>6} {'n':>4} {'med_s':>7}", "-" * 54]
    for gate in order(ledger):
        stat = table[gate]
        lines.append(f"{gate:<34} {stat.rate * 100:>5.0f}% {stat.runs:>4} {stat.median:>7.1f}")
    failing = sum(1 for stat in table.values() if stat.rate > 0)
    lines += [
        "",
        f"{failing} of the {len(table)} gates seen in {ledger} failed in their last {K} runs.",
        "Fail-fast order = this listing, top to bottom.",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Run one mode. A misspelled flag is refused by argparse, never read as --report.

    Returns:
        0, or 2 on a usage error.

    """
    ap = argparse.ArgumentParser(prog="mikemol-gate-ledger", allow_abbrev=False)
    ap.add_argument("--ledger", required=True, metavar="PATH")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--record", nargs=3, metavar=("GATE", "STATUS", "SECONDS"))
    mode.add_argument("--order", action="store_true")
    mode.add_argument("--report", action="store_true")
    opts: dict[str, object] = vars(ap.parse_args(sys.argv[1:] if argv is None else argv))
    ledger = Path(str(opts["ledger"]))
    given = opts["record"]
    if isinstance(given, list):
        gate, status, seconds = (str(part) for part in cast("list[object]", given))
        record(ledger, gate, status, seconds)
    elif opts["order"] is True:
        sys.stdout.write("".join(f"{gate}\n" for gate in order(ledger)))
    else:
        sys.stdout.write(report(ledger) + "\n")
    return 0
