# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-landing-cost`: what landing a card's manifest costs in CPU seconds (W1997, github:W50).

`cost` finds the tests a manifest reruns from a dist's committed `graph.json`; `series` turns
luthen's three per-target series into the table `cost.price` reads. This is the command line that
joins them:

    mikemol-landing-cost --dist hooks --repo mtools --otlp PATH FILE...

and prints how many tests the manifest reruns, the manifest paths the graph does not name (the
count is then a floor), the summed median and 90th-percentile CPU seconds of the measured tests
with the smallest sample count among them, and the tests that have no measurement.

⚑ CPU SECONDS, NEVER WALL, AND AN UNKNOWN STAYS UNKNOWN (luthen W1645, nemik W1056): an unmeasured
test is named and adds nothing, so a total over a partly measured set reads as a floor.
⚑ THE STORE IS ASKED THROUGH `mikemol-otlp query-metrics`, which prints one JSON object per
series; the lines are wrapped into the response shape `series.table` reads, and a query that fails
or prints nothing gives an empty table, so every test is then listed unmeasured and nothing is
invented.
"""

import argparse
import json
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TextIO, cast

from mikemol.importdag import cost, series

MEDIAN = 'gate:luthen_gate_target_cpu_seconds:median7d{{repo="{repo}"}}'
P90 = 'gate:luthen_gate_target_cpu_seconds:p90_7d{{repo="{repo}"}}'
SAMPLES = 'gate:luthen_gate_target_cpu_samples:count7d{{repo="{repo}"}}'
Query = Callable[[str], str]


def response_of(text: str) -> dict[str, object]:
    """Wrap `mikemol-otlp query-metrics` output into a Prometheus-shaped response.

    Returns:
        `{"data": {"result": [row, ...]}}` with one row per JSON line; a line that is not a JSON
        object is skipped.

    """
    rows: list[object] = []
    for line in text.splitlines():
        try:
            row = cast("object", json.loads(line))
        except ValueError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return {"data": {"result": rows}}


def run_query(otlp: str) -> Query:
    """Build the function that asks the store one question.

    Returns:
        a function from PromQL to the command's output; empty when it cannot run or fails.

    """

    def ask(promql: str) -> str:
        try:
            done = subprocess.run(
                [otlp, "query-metrics", promql], capture_output=True, text=True, check=False
            )
        except OSError:
            return ""
        return done.stdout if done.returncode == 0 else ""

    return ask


def report(graph: dict[str, object], manifest: Sequence[str], repo: str, query: Query) -> list[str]:
    """Price a manifest against the graph and the store's three series.

    Returns:
        the lines of the report.

    """
    tests = cost.affected(graph, manifest)
    gaps = cost.unnamed(graph, manifest)
    table = series.table(
        repo,
        response_of(query(MEDIAN.format(repo=repo))),
        response_of(query(P90.format(repo=repo))),
        response_of(query(SAMPLES.format(repo=repo))),
    )
    priced = cost.price(tests, table)
    lines = [f"tests rerun: {len(tests)}"]
    if gaps:
        lines.append(f"not in the graph (the count is a floor): {', '.join(gaps)}")
    measured = len(tests) - len(priced.unknown)
    fewest = priced.fewest if priced.fewest is not None else "none"
    lines.append(
        f"cpu: median {priced.median_s:.1f} s, p90 {priced.p90_s:.1f} s over {measured} measured "
        f"test(s); fewest samples {fewest}"
    )
    if priced.unknown:
        lines.append(f"unmeasured ({len(priced.unknown)}): {', '.join(priced.unknown)}")
    return lines


def _options(argv: Sequence[str] | None) -> dict[str, object]:
    parser = argparse.ArgumentParser(prog="mikemol-landing-cost")
    parser.add_argument("--dist", required=True, help="the distribution whose graph.json prices it")
    parser.add_argument("--repo", required=True, help="the repository the series are labelled by")
    parser.add_argument("--otlp", default="mikemol-otlp", help="the mikemol-otlp binary")
    parser.add_argument("--root", default=".", help="the checkout holding the dist")
    parser.add_argument("manifest", nargs="+", help="the files the card will edit")
    opts: dict[str, object] = vars(parser.parse_args(list(sys.argv[1:] if argv is None else argv)))
    return opts


def main(
    argv: Sequence[str] | None = None, out: TextIO = sys.stdout, query: Query | None = None
) -> int:
    """Run the command.

    Returns:
        0 after the report; 2 when the graph file cannot be read.

    """
    opts = _options(argv)
    dist = str(opts["dist"])
    path = Path(str(opts["root"])) / dist / "graph.json"
    try:
        graph = cast("dict[str, object]", json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError) as caught:
        sys.stderr.write(f"mikemol-landing-cost: {path}: {caught}\n")
        return 2
    named = cast("list[str]", opts["manifest"])
    manifest = [m.removeprefix(f"{dist}/") for m in named if m.startswith(f"{dist}/")]
    asker = query or run_query(str(opts["otlp"]))
    out.writelines(f"{line}\n" for line in report(graph, manifest, str(opts["repo"]), asker))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
