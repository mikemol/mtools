# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Ship the fleet ratchet census as a gauge on each gate run (W1909, github:W42 piece (a)).

    mikemol-ratchet-emit ROOT

The operator's ruling (host transcript 695f3e0a, lines 92679 and 93406): a nonzero ratchet is a
priority marker and a paydown rate needs teeth, so each ratchet's value has to be a series. One
`mikemol.ratchet.value` gauge per ratchet file per gate run, labelled `{repo, ratchet, kind}`, makes
the rate computable (nemik:W987, W991).

⚑ THE CENSUS IS READ, NOT RECOMPUTED HERE. `mikemol-ratchet census ROOT` (W1907) owns which files
are ratchets and what each records; this reads its lines through the transcript reader's pattern
(`hold_lift.run_reader`), so the hooks distribution does not import the ratchet one.

⚑ THE `repo` LABEL IS THE RATCHET'S OWN REPOSITORY, not the repository whose gate ran: a gate in
mtools reports luthen's baseline as luthen's. (`gatetargets.plan` overwrites that label with the
emitting repo and so cannot be reused for these rows.)

⚑ AN UNREAD RATCHET SENDS NOTHING: a value of UNREAD is not 0, and a gauge of 0 for a baseline that
failed to parse would show debt paid down by breaking the file. Best effort, as every send here:
no binary or store, or a failed spawn, changes nothing and the exit is still 0.
"""

import json
import os
import re
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from mikemol.hooks.commit_span import binary, store_named
from mikemol.hooks.hold_lift import run_reader
from mikemol.hooks.vlogdetach import spawn_with_stdin

SERVICE = "mikemol-gate"
VALUE = "mikemol.ratchet.value"
CHUNK = 100
EXIT_USAGE = 2
READER_ENV = "RATCHET_BIN"
_CHECKOUT = ("github", "mtools", "ratchet", ".venv", "bin", "mikemol-ratchet")
_LINE = re.compile(r"^(?P<repo>\S+) (?P<path>\S+) (?P<kind>\S+) value=(?P<value>\d+) floor=\d+$")

type Row = dict[str, object]
type Spawn = Callable[[Sequence[str], str], None]
type Run = Callable[[Sequence[str]], tuple[int, str]]


def parse_census(text: str) -> list[tuple[str, str, str, int]]:
    """Read the census lines that carry a value.

    Returns:
        `(repo, ratchet, kind, value)` for each line; a comment, an UNREAD line and any line of
        another shape are left out.

    """
    found: list[tuple[str, str, str, int]] = []
    for line in text.splitlines():
        match = _LINE.match(line)
        if match is not None:
            found.append((match["repo"], match["path"], match["kind"], int(match["value"])))
    return found


def rows_of(census: Sequence[tuple[str, str, str, int]], now_ns: int) -> list[Row]:
    """Turn census entries into gauge rows, one per ratchet.

    Returns:
        rows named `mikemol.ratchet.value` with the labels `repo`, `ratchet` and `kind`.

    """
    return [
        {
            "name": VALUE,
            "value": value,
            "time_ns": now_ns,
            "fields": {"repo": repo, "ratchet": ratchet, "kind": kind},
        }
        for repo, ratchet, kind, value in census
    ]


def plan(program: str, rows: Sequence[Row]) -> list[tuple[list[str], str]]:
    """Build the children a run starts, each with the JSON lines for its stdin.

    Returns:
        one `mikemol-otlp metrics` argv and its text per chunk of `CHUNK` rows.

    """
    argv = [program, "metrics", "--service", SERVICE, "--namespace", "ratchet"]
    chunks = [rows[i : i + CHUNK] for i in range(0, len(rows), CHUNK)]
    return [(argv, "".join(json.dumps(row) + "\n" for row in chunk)) for chunk in chunks]


def emit(rows: Sequence[Row], env: Mapping[str, str], spawn: Spawn = spawn_with_stdin) -> bool:
    """Start the children for a census, when a binary and a store exist.

    Returns:
        whether every child was started; False with no binary or store, or a failed spawn.

    """
    program = binary(env)
    if program is None or not store_named(env):
        return False
    try:
        for argv, text in plan(program, rows):
            spawn(argv, text)
    except OSError:
        return False
    return True


def reader_path(env: Mapping[str, str]) -> str | None:
    """Find the ratchet tool: the env override, then the mtools checkout.

    Returns:
        its path, or None when neither exists.

    """
    named = env.get(READER_ENV)
    candidates = [Path(named)] if named else []
    candidates.append(Path.home().joinpath(*_CHECKOUT))
    return next((str(c) for c in candidates if c.is_file()), None)


def main(
    argv: Sequence[str] | None = None,
    spawn: Spawn = spawn_with_stdin,
    run: Run = run_reader,
) -> int:
    """Read the census under a root and ship its values.

    Returns:
        0 once the arguments are right (a send that cannot start changes nothing); 2 with usage.

    """
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        sys.stderr.write("usage: mikemol-ratchet-emit ROOT\n")
        return EXIT_USAGE
    tool = reader_path(os.environ)
    if tool is None:
        sys.stdout.write("ratchet emit: no mikemol-ratchet found; nothing sent\n")
        return 0
    code, said = run([tool, "census", args[0]])
    if code != 0:
        sys.stdout.write(f"ratchet emit: the census exited {code}; nothing sent\n")
        return 0
    rows = rows_of(parse_census(said), time.time_ns())
    sent = emit(rows, os.environ, spawn)
    sys.stdout.write(f"ratchet emit: {len(rows)} ratchet(s), sent={sent}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
