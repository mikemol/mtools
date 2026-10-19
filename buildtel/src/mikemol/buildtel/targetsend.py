# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W1579: send the per-target run-time rows to the log store, so the table is read from a service.

    python -m mikemol.buildtel.targettimes <commit-log> > rows.jsonl
    python -m mikemol.buildtel.targetsend rows.jsonl <repo>

⚑ ONE OTLP LOG RECORD PER ROW THROUGH THE SHARED EMITTER (operator, 2026-10-18, 695f3e0a line
80168: every gate's test targets are recorded against their limits so a 50% rule can act before the
next run): the rows `targettimes` prints are piped line by line into `mikemol-otlp log`, one call
per bazel invocation, with the invocation id, the repo and `kind=target-time` as fields, so a panel
or the planner (W1573) reads them from the store and not from gate logs.

⚑ BEST EFFORT, AND SAID SO: a missing `mikemol-otlp` or an unreachable store is exit 3 with the
reason, and the rows were already printed by `targettimes`, so nothing is lost. The emitter is
`$MIKEMOL_OTLP_BIN`, else `mikemol-otlp` on PATH, else the mtools checkout's. The child is started
by `proc.feed`, the one place this dist starts one.
"""

import json
import os
import shutil
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from mikemol.buildtel import proc

EXIT_USAGE = 2
EXIT_NOT_SENT = 3
SERVICE = "mikemol-gate-targets"
BIN_ENV = "MIKEMOL_OTLP_BIN"
_ARGC = 2
Run = Callable[[Sequence[str], str], int]
Row = dict[str, object]


def emitter(env: Mapping[str, str]) -> str | None:
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


def by_invocation(rows: Sequence[Row]) -> dict[str, list[Row]]:
    """Group rows by the invocation they came from, in order of first appearance.

    Returns:
        invocation id mapped to its rows; a row with no invocation is left out.

    """
    groups: dict[str, list[Row]] = {}
    for row in rows:
        invocation = str(row.get("invocation", ""))
        if invocation:
            groups.setdefault(invocation, []).append(row)
    return groups


def argv_for(program: str, repo: str, invocation: str) -> list[str]:
    """Build the `mikemol-otlp log` call for one invocation's rows.

    Returns:
        the argv; the rows go on its stdin, one JSON line each.

    """
    shared = ["--service", SERVICE, "--namespace", repo]
    fields = ["--field", f"invocation={invocation}", "--field", "kind=target-time"]
    return [program, "log", *shared, *fields]


def send(rows: Sequence[Row], repo: str, program: str, run: Run) -> int:
    """Send every invocation's rows, one emitter call each.

    Returns:
        how many invocations the emitter accepted.

    """
    sent = 0
    for invocation, group in by_invocation(rows).items():
        body = "\n".join(json.dumps(row) for row in group) + "\n"
        sent += run(argv_for(program, repo, invocation), body) == 0
    return sent


def _read_rows(path: Path) -> list[Row]:
    rows: list[Row] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        row: object = json.loads(raw)
        if isinstance(row, dict):
            rows.append({str(k): v for k, v in row.items()})
    return rows


def main(argv: Sequence[str] | None = None, run: Run = proc.feed) -> int:
    """Send a rows file to the log store.

    Returns:
        0 when every invocation was accepted, 2 for a usage error or an unreadable rows file or a
        link, 3 when no emitter exists or some invocation was not accepted.

    """
    args = sys.argv[1:] if argv is None else list(argv)
    if len(args) != _ARGC:
        sys.stderr.write("targetsend <rows.jsonl> <repo>\n")
        return EXIT_USAGE
    path, repo = Path(args[0]), args[1]
    if path.is_symlink():
        sys.stderr.write(f"targetsend: {path} is a symlink; refused\n")
        return EXIT_USAGE
    try:
        rows = _read_rows(path)
    except (OSError, ValueError) as err:
        sys.stderr.write(f"targetsend: {path}: {err}\n")
        return EXIT_USAGE
    program = emitter(os.environ)
    if program is None:
        sys.stderr.write("targetsend: no mikemol-otlp found; nothing sent\n")
        return EXIT_NOT_SENT
    groups = by_invocation(rows)
    sent = send(rows, repo, program, run)
    sys.stdout.write(f"targetsend: {sent} of {len(groups)} invocation(s) sent\n")
    return 0 if sent == len(groups) else EXIT_NOT_SENT


if __name__ == "__main__":
    raise SystemExit(main())
