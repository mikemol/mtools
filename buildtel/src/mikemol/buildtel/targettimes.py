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

⚑ A LOG IS DATA, NEVER A LINK: a path that is a symlink is refused, as every reader here refuses
one, and a log that names no invocation prints nothing and says so.

    python -m mikemol.buildtel.targettimes <commit-log>     # one JSON row per test target
"""

import json
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from mikemol.buildtel import bb_targets

EXIT_USAGE = 2
EXIT_UNREACHABLE = 3
USAGE = "targettimes <commit-log>"
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
    if len(args) != 1 or args[0].startswith("-"):
        sys.stderr.write(USAGE + "\n")
        return EXIT_USAGE
    path = Path(args[0])
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
            fields = {
                "invocation": row.invocation,
                "label": row.label,
                "status": row.status,
                "millis": row.millis,
                "complete": row.complete,
            }
            sys.stdout.write(json.dumps(fields) + "\n")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
