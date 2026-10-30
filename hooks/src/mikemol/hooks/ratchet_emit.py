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
STAGES = ("staged", "landed")
"""The stage a run may name as its third word; `landed` marks a row read after the push (W2171)."""
READER_ENV = "RATCHET_BIN"
_LINE = re.compile(
    r"^(?P<repo>\S+) (?P<path>\S+) (?P<kind>\S+) value=(?P<value>\d+) floor=\d+"
    r"(?: sum=(?P<sum>\d+))?(?: guessed=(?P<guessed>[01]))?$"
)

RETIRED = "mikemol.ratchet.retired"
_TOMBSTONE = re.compile(
    r"^(?P<repo>\S+) (?P<path>\S+) retired reason=(?P<reason>\S+) sha=\S+(?: to=\S+)?$"
)

type Row = dict[str, object]
type Tombstone = tuple[str, str, str]
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


def parse_tombstones(text: str) -> list[Tombstone]:
    """Read the census lines that say a ratchet was retired (W1963).

    Returns:
        `(repo, ratchet, reason)` for each tombstone line; a ratchet row, a comment and any line of
        another shape are left out.

    """
    found: list[Tombstone] = []
    for line in text.splitlines():
        match = _TOMBSTONE.match(line)
        if match is not None:
            found.append((str(match["repo"]), str(match["path"]), str(match["reason"])))
    return found


def retired_rows(tombstones: Sequence[Tombstone], now_ns: int) -> list[Row]:
    """Turn tombstones into gauge rows: `mikemol.ratchet.retired` is 1 for each, every run.

    ⚑ RETIRED IS WRITTEN, NEVER INFERRED FROM SILENCE (the operator, host line 96701; W1964): a
    series that stops reporting could be a ratchet paid off, a rename or a broken census, so a
    retirement is sent as its own series for as long as the declaration lists it.

    Returns:
        rows named `mikemol.ratchet.retired`, value 1, with the labels `repo`, `ratchet`, `reason`.

    """
    return [
        {
            "name": RETIRED,
            "value": 1,
            "time_ns": now_ns,
            "fields": {"repo": repo, "ratchet": ratchet, "reason": reason},
        }
        for repo, ratchet, reason in tombstones
    ]


def rows_of(census: Sequence[Entry], now_ns: int, stage: str = "") -> list[Row]:
    """Turn census entries into gauge rows: the entry count, and the sum where there is one.

    ⚑ THE SUM IS A SECOND SERIES (W1922, asked for by nemik:W991): a count falling inside a key
    leaves the entry count flat, so a baseline of the file-rule-count shape also sends
    `mikemol.ratchet.sum`; any other baseline sends the entry count alone.

    ⚑ `stage` SEPARATES A GATE-TIME SAMPLE FROM A LANDED ONE (W2171, nemik:W1179): the gate emits
    before its verdict, so a refused stack left numbers the pace counted as landings (nemik's
    stacks 703 and 704, codon 146 to 145 and 144, read as a fall that never landed). A row sent
    after a push carries `stage=landed`; the gate's own rows carry no `stage` label, as before, so
    the existing series stands as unlabeled history and a reader that wants landings selects
    `stage="landed"`.

    Returns:
        rows named `mikemol.ratchet.value`, and `mikemol.ratchet.sum` for entries with a sum,
        with the labels `repo`, `ratchet` and `kind`, `guessed` (true when the row came from the
        name classifier, false when declared) only where the census said so (W1958), and `stage`
        only when one is given.

    """
    rows: list[Row] = []
    for repo, ratchet, kind, value, total, guessed in census:
        fields = {"repo": repo, "ratchet": ratchet, "kind": kind}
        if guessed is not None:
            fields["guessed"] = "true" if guessed else "false"
        if stage:
            fields["stage"] = stage
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

    ⚑ `sent=` IS A COUNT OF ROWS STARTED, NOT A BOOLEAN (W2018): `0 ratchet(s), sent=True` read as
    success while nothing was published (summit, 2026-10-25). A run whose census held no ratchet
    for a directory that declares some (a `ratchets.json`) exits 1, so the gate's own `|| echo`
    says so; a send that cannot start for want of a binary or a store still changes nothing.

    Returns:
        0 once the arguments are right and rows were found or none are declared; 1 when none were
        found for a directory that declares ratchets; 2 with usage.

    """
    args = list(sys.argv[1:] if argv is None else argv)
    stage = _stage_of(args)
    if stage is None:
        sys.stderr.write("usage: mikemol-ratchet-emit NAME DIR [staged|landed]\n")
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
    now = time.time_ns()
    dead = [(args[0], path, reason) for _repo, path, reason in parse_tombstones(said)]
    rows = [*rows_of(named, now, stage), *retired_rows(dead, now)]
    sent = len(rows) if emit(rows, os.environ, spawn) else 0
    sys.stdout.write(f"ratchet emit: {len(rows)} ratchet(s), sent={sent}\n")
    declared = (Path(args[1]) / "ratchets.json").is_file()
    return 1 if declared and not rows else 0


def _stage_of(args: Sequence[str]) -> str | None:
    # The stage the words name: "" for NAME DIR, the third word when it is a known stage, and None
    # for any other count or an unknown stage (the caller answers usage).
    if len(args) == ARGUMENTS:
        return ""
    if len(args) == ARGUMENTS + 1 and args[ARGUMENTS] in STAGES:
        return args[ARGUMENTS]
    return None


if __name__ == "__main__":
    sys.exit(main())
