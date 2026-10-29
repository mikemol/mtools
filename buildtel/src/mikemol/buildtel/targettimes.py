# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W1572: the per-target run-time table, filled from the invocations a gate log names.

A gate's bazel invocation id is printed into the commit's own output as
`Streaming build results to: <host>/invocation/<uuid>` (github-8f, 2026-10-18), and the search RPC
that would list invocations answers PermissionDenied, so the ids come from a log. For each id this
reads the invocation with `bb_targets` (every group's pages followed) and emits ONE ROW PER TEST
TARGET: the invocation, the label, its status, its run time in milliseconds, and whether that
invocation's listing was COMPLETE.

⚑ A ROW CARRIES ITS INVOCATION'S COVERAGE. A table built from partial listings would let a reader
read a maximum off rows that were never the whole run; `complete` is false on every row of an
invocation `bb_targets` calls INCOMPLETE, and a consumer (the shard planner, W1573) filters on it
or says what it did not see.

⚑ A ROW MAY CARRY ITS OWN CPU (W1895): `--cpu FILE` takes the output of
`mikemol-otlp query-metrics 'last_over_time(mikemol.gate.target.cpu.seconds{...}[3d])'`, one sample
per line, and a row whose label has a sample gains `cpu_s`. The planner reads that column when it is
there and its wall time when it is not, so a target never measured keeps no invented figure. This
reads a FILE, never the store: the query is the caller's.

⚑ A LOG IS DATA, NEVER A LINK: a path that is a symlink is refused, as every reader here refuses
one, and a log that names no invocation prints nothing and says so.

    python -m mikemol.buildtel.targettimes <commit-log> [--cpu FILE]
"""

import json
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from mikemol.buildtel import bb_targets

EXIT_USAGE = 2
EXIT_UNREACHABLE = 3
USAGE = "targettimes <commit-log> [--cpu FILE]"
_WITH_CPU = 3
_INVOCATION = re.compile(
    r"/invocation/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
)


@dataclass(frozen=True)
class Row:
    """One test target of one invocation, with how complete that invocation's listing was."""

    invocation: str
    label: str
    status: str
    millis: int
    complete: bool


def invocation_ids(text: str) -> list[str]:
    """Take the bazel invocation ids a log names, in order of first appearance.

    Returns:
        each distinct uuid that follows `/invocation/`, once.

    """
    seen: dict[str, None] = {}
    for found in _INVOCATION.finditer(text):
        seen.setdefault(found.group(1))
    return list(seen)


def cpu_samples(text: str) -> dict[str, float]:
    """Read `mikemol-otlp query-metrics` lines into target -> CPU seconds.

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


def fields_of(row: Row, cpu: Mapping[str, float]) -> dict[str, object]:
    """Spell one row as its output fields, with `cpu_s` only when the label has a sample.

    Returns:
        the fields, in the order the table has always printed them, then `cpu_s` if measured.

    """
    fields: dict[str, object] = {
        "invocation": row.invocation,
        "label": row.label,
        "status": row.status,
        "millis": row.millis,
        "complete": row.complete,
    }
    if row.label in cpu:
        fields["cpu_s"] = cpu[row.label]
    return fields


def rows_of(invocation: str, report: bb_targets.Report) -> list[Row]:
    """Turn one invocation's report into table rows, every test and the report's coverage.

    Returns:
        a row per test target, longest first, each marked with whether the listing was complete.

    """
    whole = report.complete()
    return [Row(invocation, t.label, t.status, t.millis, whole) for t in report.tests]


def read(invocation: str, fetch: bb_targets.Fetch, more: bb_targets.Page) -> list[Row]:
    """Read one invocation from the service into rows, following its pages.

    Returns:
        the invocation's rows.

    """
    return rows_of(invocation, bb_targets.parse(fetch(invocation), more, invocation))


def _cpu_of(args: list[str]) -> tuple[str, dict[str, float]] | None:
    # The log path and the CPU samples of `--cpu FILE`; None for a usage error or an unreadable or
    # linked samples file.
    if len(args) == _WITH_CPU and args[1] == "--cpu":
        samples = Path(args[2])
        if samples.is_symlink():
            sys.stderr.write(f"targettimes: {samples} is a symlink; refused\n")
            return None
        try:
            return args[0], cpu_samples(samples.read_text(encoding="utf-8", errors="replace"))
        except OSError as err:
            sys.stderr.write(f"targettimes: {samples}: {err}\n")
            return None
    return (args[0], {}) if len(args) == 1 else None


def main(
    argv: Sequence[str] | None = None,
    fetch: bb_targets.Fetch = bb_targets.post,
    more: bb_targets.Page = bb_targets.post_page,
) -> int:
    """Print the table rows for every invocation a commit log names, one JSON line each.

    Returns:
        0 on success, 2 for a usage error or a log that is a link or unreadable, 3 when the
        service could not be reached for some invocation (the others are still printed).

    """
    args = sys.argv[1:] if argv is None else list(argv)
    parsed = None if not args or args[0].startswith("-") else _cpu_of(args)
    if parsed is None:
        sys.stderr.write(USAGE + "\n")
        return EXIT_USAGE
    path, cpu = Path(parsed[0]), parsed[1]
    if path.is_symlink():
        sys.stderr.write(f"targettimes: {path} is a symlink; refused\n")
        return EXIT_USAGE
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as err:
        sys.stderr.write(f"targettimes: {path}: {err}\n")
        return EXIT_USAGE
    ids = invocation_ids(text)
    if not ids:
        sys.stderr.write(f"targettimes: {path} names no invocation\n")
    code = 0
    for invocation in ids:
        try:
            rows = read(invocation, fetch, more)
        except OSError as err:
            sys.stderr.write(f"targettimes: {invocation} unreachable: {err}\n")
            code = EXIT_UNREACHABLE
            continue
        for row in rows:
            sys.stdout.write(json.dumps(fields_of(row, cpu)) + "\n")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
