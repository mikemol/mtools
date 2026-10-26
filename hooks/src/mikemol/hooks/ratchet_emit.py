# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Ship a repository's own ratchet census as a gauge on each gate run (W1909, W1923).

    mikemol-ratchet-emit NAME DIR

The operator's ruling (host transcript 695f3e0a, lines 92679 and 93406): a nonzero ratchet is a
priority marker and a paydown rate needs teeth, so each ratchet's value has to be a series. One
`mikemol.ratchet.value` gauge per ratchet file per gate run, labelled `{repo, ratchet, kind}`, makes
the rate computable (nemik:W987, W991).

⚑ THE LABEL IS THE REPOSITORY'S NAME, NOT ITS DIRECTORY'S BASENAME. The gate runs inside
mikemol-commit's isolated snapshot, whose directory is named `tree`, so a name taken from the path
labelled every series `tree` (luthen's reading, 2026-10-24; the same defect the gate-target emit
had before W1793). The caller passes the name it already has (`basename $tools`) and the census
directory separately.

⚑ A GATE EMITS ITS OWN REPOSITORY AND NO OTHER (W1923; the operator's ruling, host transcript
695f3e0a line 84035: repos must not be aware that sibling checkouts exist). The sample then lands
at that repository's own landing, which is what the pace is keyed to, and nothing here reads a
sibling. Fleet coverage comes from each repository adopting the hook.

⚑ THE CENSUS IS READ, NOT RECOMPUTED HERE. `mikemol-ratchet census --repo REPO` (W1907) owns which
files are ratchets and what each records; this reads its lines through the transcript reader's
pattern (`hold_lift.run_reader`), so the hooks distribution does not import the ratchet one.

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
import shutil
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from mikemol.hooks.commit_span import binary, store_named
from mikemol.hooks.hold_lift import run_reader
from mikemol.hooks.vlogdetach import spawn_with_stdin

SERVICE = "mikemol-gate"
VALUE = "mikemol.ratchet.value"
SUM = "mikemol.ratchet.sum"
CHUNK = 100
EXIT_USAGE = 2
ARGUMENTS = 2
READER_ENV = "RATCHET_BIN"
_LINE = re.compile(
    r"^(?P<repo>\S+) (?P<path>\S+) (?P<kind>\S+) value=(?P<value>\d+) floor=\d+"
    r"(?: sum=(?P<sum>\d+))?(?: guessed=(?P<guessed>[01]))?$"
)

type Row = dict[str, object]
type Entry = tuple[str, str, str, int, int | None, bool | None]
type Spawn = Callable[[Sequence[str], str], None]
type Run = Callable[[Sequence[str]], tuple[int, str]]


def parse_census(text: str) -> list[Entry]:
    """Read the census lines that carry a value.

    Returns:
        `(repo, ratchet, kind, value, sum, guessed)` for each line, the sum None when the line
        has none and guessed None when it does not say (an older census); a comment, an UNREAD
        line and any line of another shape are left out.

    """
    found: list[Entry] = []
    for line in text.splitlines():
        match = _LINE.match(line)
        if match is not None:
            total, flag = match["sum"], match["guessed"]
            entry = (match["repo"], match["path"], match["kind"], int(match["value"]))
            guessed = None if flag is None else str(flag) == "1"
            found.append((*entry, None if total is None else int(total), guessed))
    return found


def rows_of(census: Sequence[Entry], now_ns: int) -> list[Row]:
    """Turn census entries into gauge rows: the entry count, and the sum where there is one.

    ⚑ THE SUM IS A SECOND SERIES (W1922, asked for by nemik:W991): a count falling inside a key
    leaves the entry count flat, so a baseline of the file-rule-count shape also sends
    `mikemol.ratchet.sum`; any other baseline sends the entry count alone.

    Returns:
        rows named `mikemol.ratchet.value`, and `mikemol.ratchet.sum` for entries with a sum,
        with the labels `repo`, `ratchet` and `kind`, and `guessed` (true when the row came from
        the name classifier, false when declared) only where the census said so (W1958).

    """
    rows: list[Row] = []
    for repo, ratchet, kind, value, total, guessed in census:
        fields = {"repo": repo, "ratchet": ratchet, "kind": kind}
        if guessed is not None:
            fields["guessed"] = "true" if guessed else "false"
        rows.append({"name": VALUE, "value": value, "time_ns": now_ns, "fields": fields})
        if total is not None:
            rows.append({"name": SUM, "value": total, "time_ns": now_ns, "fields": fields})
    return rows


def plan(
    program: str, rows: Sequence[Row], namespace: str = "ratchet"
) -> list[tuple[list[str], str]]:
    """Build the children a run starts, each with the JSON lines for its stdin.

    Returns:
        one `mikemol-otlp metrics` argv and its text per chunk of `CHUNK` rows.

    """
    argv = [program, "metrics", "--service", SERVICE, "--namespace", namespace]
    chunks = [rows[i : i + CHUNK] for i in range(0, len(rows), CHUNK)]
    return [(argv, "".join(json.dumps(row) + "\n" for row in chunk)) for chunk in chunks]


def emit(
    rows: Sequence[Row],
    env: Mapping[str, str],
    spawn: Spawn = spawn_with_stdin,
    namespace: str = "ratchet",
) -> bool:
    """Start the children for a census, when a binary and a store exist.

    Returns:
        whether every child was started; False with no binary or store, or a failed spawn.

    """
    program = binary(env)
    if program is None or not store_named(env):
        return False
    try:
        for argv, text in plan(program, rows, namespace):
            spawn(argv, text)
    except OSError:
        return False
    return True


def reader_path(env: Mapping[str, str]) -> str | None:
    """Find the ratchet tool: the env override, then PATH.

    ⚑ NO SIBLING CHECKOUT (W1927; the operator's ruling, host transcript 695f3e0a line 84035): an
    adopting repository installs `mikemol-ratchet` as a dependency or names it in RATCHET_BIN, and
    this knows no path under another checkout.

    Returns:
        its path, or None when neither names an existing file.

    """
    named = env.get(READER_ENV)
    if named and Path(named).is_file():
        return named
    return shutil.which("mikemol-ratchet", path=env.get("PATH", ""))


def main(
    argv: Sequence[str] | None = None,
    spawn: Spawn = spawn_with_stdin,
    run: Run = run_reader,
) -> int:
    """Read the census of one repository directory and ship its values under a name.

    Returns:
        0 once the arguments are right (a send that cannot start changes nothing); 2 with usage.

    """
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != ARGUMENTS:
        sys.stderr.write("usage: mikemol-ratchet-emit NAME DIR\n")
        return EXIT_USAGE
    tool = reader_path(os.environ)
    if tool is None:
        sys.stdout.write("ratchet emit: no mikemol-ratchet found; nothing sent\n")
        return 0
    code, said = run([tool, "census", "--repo", args[1]])
    if code != 0:
        sys.stdout.write(f"ratchet emit: the census exited {code}; nothing sent\n")
        return 0
    named = [
        (args[0], path, kind, value, total, guessed)
        for _repo, path, kind, value, total, guessed in parse_census(said)
    ]
    rows = rows_of(named, time.time_ns())
    sent = emit(rows, os.environ, spawn)
    sys.stdout.write(f"ratchet emit: {len(rows)} ratchet(s), sent={sent}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
