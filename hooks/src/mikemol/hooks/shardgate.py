# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Refuse a stack that touches a mutants grid already past half of its CPU budget (W1602).

⚑ THE RULE IS THE OPERATOR'S (2026-10-18, 695f3e0a line 80168): "If something takes longer than 50%
of a wall timeout, it should be sharded before its next run. We spend a lot on waiting-for-failure."
And its unit (2026-10-20, line 87670): the fraction is measured in whatever unit the failure
threshold is measured in. A mutants grid is bounded by CPU seconds (`cpu_budget` in its dist's
BUILD file since W1778), so the figure compared is a shard's CPU, from the series
`mikemol.gate.target.cpu.seconds` that every gate sends (W1785).

⚑ THE LATEST READING, NOT THE LARGEST (`last_over_time`): a reshard changes what the next run
reads, and a window maximum would go on refusing for days after the fix landed.

⚑ A READING OLDER THAN THE DIST'S LAST BUILD CHANGE IS ABOUT A GRID THAT IS GONE. Resharding lands
a BUILD change, and no gate has run since, so the latest reading is still the old grid's; without
this every stack touching the dist would be refused until a gate ran, which a refused stack cannot
make happen. The reading's time (`tlast_over_time`, seconds) is compared with the commit time of
the dist's BUILD file, and an older reading is not judged.

⚑ NO READING IS NOT A REFUSAL. With no store, no `mikemol-otlp`, or an unreadable answer, nothing is
refused and nothing is said: this gate stops a known-slow grid, it does not guess at an unknown one.

⚑ THE ANSWER NAMES A NUMBER: the grid's work divides evenly across its shards, so a worst shard at
`cpu` of a `budget` with `shards` shards needs about `shards * cpu / (TARGET * budget)` to read at
`TARGET` of the budget, rounded up. It is always more than the grid has: a shard is named only past
`FRACTION` of the budget, and `FRACTION` is above `TARGET`, so the ratio exceeds one.

CONSUMED BY: `commit_kata.submit_problem`, at submit, beside the import and build-file refusals.
"""

import json
import math
import re
from collections.abc import Callable, Collection, Mapping
from pathlib import Path
from typing import cast

from mikemol.hooks.commit_span import binary, store_named
from mikemol.hooks.presubmit import dists_of
from mikemol.hooks.runproc import run_process
from mikemol.hooks.stackrun import items_of

FRACTION = 0.5
TARGET = 0.4
SERIES = "mikemol.gate.target.cpu.seconds"
_LABEL = re.compile(r"^//(?P<dist>[^:]+):mutants_[0-9]+$")
_BUDGET = re.compile(r"\bcpu_budget\s*=\s*(?P<v>[0-9]+)")
_SHARDS = re.compile(r"\bshards\s*=\s*(?P<v>[0-9]+)")

type Reading = tuple[float, float]
"""A shard's latest CPU seconds and the time of that sample, in epoch seconds."""

ReadBuild = Callable[[str], str | None]
ChangedAt = Callable[[str], float | None]
Run = Callable[[list[str], Path], tuple[int, str]]


def query(repo: str, function: str = "last_over_time") -> str:
    """Build the PromQL for one reading of every mutants shard of a repo.

    Returns:
        the query text: the latest value by default, `tlast_over_time` for the sample's time.

    """
    return f'{function}({SERIES}{{kind="mutants",repo="{repo}"}}[3d])'


def samples(text: str) -> dict[str, float]:
    """Read `mikemol-otlp query-metrics` lines into target -> value.

    Returns:
        the values; a line that is not a sample of a labelled target is skipped.

    """
    found: dict[str, float] = {}
    for line in text.splitlines():
        try:
            row = cast("dict[str, object]", json.loads(line))
            metric = cast("dict[str, object]", row["metric"])
            value = cast("list[object]", row["value"])
            found[str(metric["target"])] = float(str(value[1]))
        except (ValueError, KeyError, IndexError, TypeError):
            continue
    return found


def readings(cpu_text: str, time_text: str) -> dict[str, Reading]:
    """Join the CPU samples and the sample times by target.

    Returns:
        target -> (CPU seconds, epoch seconds); a target with no time is left out, since a reading
        of unknown age cannot be told from one about a grid that is gone.

    """
    times = samples(time_text)
    return {t: (cpu, times[t]) for t, cpu in samples(cpu_text).items() if t in times}


def _number(pattern: re.Pattern[str], build: str) -> int | None:
    found = pattern.search(build)
    return int(found.group("v")) if found else None


def findings(
    read: Mapping[str, Reading],
    dists: Collection[str],
    builds: tuple[ReadBuild, ChangedAt],
) -> list[str]:
    """Name each touched dist's worst current shard that is past half of the dist's CPU budget.

    `builds` is the reader of a dist's BUILD text and the epoch second it last changed.

    Returns:
        one line per dist, with the proposed shard count; empty when nothing is past the line.

    """
    text_of, changed_at = builds
    worst: dict[str, tuple[str, float]] = {}
    for label, (cpu, at) in read.items():
        matched = _LABEL.match(label)
        dist = matched.group("dist") if matched else ""
        changed = changed_at(dist) if dist in dists else None
        current = dist in dists and (changed is None or at > changed)
        if current and cpu > worst.get(dist, ("", 0.0))[1]:
            worst[dist] = (label, cpu)
    lines: list[str] = []
    for dist, (label, cpu) in sorted(worst.items()):
        build = text_of(dist) or ""
        budget, shards = _number(_BUDGET, build), _number(_SHARDS, build)
        if not budget or not shards or cpu <= FRACTION * budget:
            continue
        proposed = math.ceil(shards * cpu / (TARGET * budget))
        lines.append(
            f"{label} used {cpu:.0f} CPU s of {budget} ({100 * cpu / budget:.0f}%), past half: "
            f"set shards = {proposed} (now {shards}) in {dist}/BUILD.bazel before this stack"
        )
    return lines


def _text_of(root: Path) -> ReadBuild:
    def build(dist: str) -> str | None:
        try:
            return (root / dist / "BUILD.bazel").read_text(encoding="utf-8")
        except OSError:
            return None

    return build


def _changed_at(root: Path, run: Run) -> ChangedAt:
    def changed(dist: str) -> float | None:
        status, out = run(["git", "log", "-1", "--format=%ct", "--", f"{dist}/BUILD.bazel"], root)
        return float(out.strip()) if status == 0 and out.strip().isdecimal() else None

    return changed


def refusal(
    root: Path, stack_file: Path, env: Mapping[str, str], run: Run = run_process
) -> str | None:
    """Judge a submitted stack against the latest shard readings.

    Returns:
        the findings, one per line, or None when nothing is past the line or nothing could be read
        (no stack file, no store, no `mikemol-otlp`, an unreadable answer).

    """
    items = items_of(stack_file)
    program = binary(env)
    if isinstance(items, str) or program is None or not store_named(env):
        return None
    cpu_status, cpu = run([program, "query-metrics", query(root.name)], root)
    time_status, when = run([program, "query-metrics", query(root.name, "tlast_over_time")], root)
    if cpu_status != 0 or time_status != 0:
        return None
    paths = [path for item in items for path in item.paths]
    # ⚑ A STACK THAT CARRIES THE DIST'S BUILD FILE IS THE REPAIR AND IS NOT JUDGED (found by the
    # first real refusal, 2026-10-22): the reading is about the grid as committed, while the shard
    # count is read from the tree this stack changes, so the proposal came out against the wrong
    # count (80 measured, 102 set, 130 demanded). The next gate's measurement judges the new value.
    carried = {path.removesuffix("/BUILD.bazel") for path in paths if path.endswith("/BUILD.bazel")}
    dists = [dist for dist in dists_of(paths) if dist not in carried]
    found = findings(readings(cpu, when), dists, (_text_of(root), _changed_at(root, run)))
    return "\n".join(found) if found else None
