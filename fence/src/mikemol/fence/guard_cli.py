# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Run a command under the declared run-time guards: `python -m mikemol.fence.guard_cli -- CMD...`.

    guard_cli [--policy FILE] -- CMD [ARG...]

The launcher half of W916 (luthen-observability:W710). It reads the policy (`policy.py`), starts the
command as a child, runs one `watcher.Guard` per declared row beside it, and returns the child's own
exit status. `mikemol-commit` puts it between the repository's fence claim and the commit, so the
bazel client beneath the commit is what a trip interrupts.

⚑⚑ A BROKEN POLICY IS LOUD AND DOES NOT BLOCK THE COMMAND. A guard protects the machine, not the
commit's correctness: refusing every commit over a typo would turn a protective file into an
outage. Every problem is printed to stderr and the command runs UNGUARDED, saying so, so a green run
is never read as a guarded one. An ABSENT policy is silent: most hosts declare none. A policy file
named by `MIKEMOL_GUARDS` that does not exist is said once, because that is a misconfiguration.

⚑ THE POLICY'S DEFAULT HOME IS THE HOST'S, not the repository's: `~/.config/mikemol/guards.toml`, as
the katas policy lives under `~/.config/mikemol`. The limits are a host's judgement about its own
machine; a repository that carried them would carry one host's numbers to every other.

CONSUMED BY: `mikemol-commit` (`commit_kata.claim_of`).
"""

import os
import subprocess
import sys
from collections.abc import Mapping, Sequence
from contextlib import ExitStack
from datetime import UTC, datetime
from pathlib import Path

from mikemol.fence import triprecord
from mikemol.fence.policy import PolicyError, Spec, load
from mikemol.fence.reading import reader
from mikemol.fence.watcher import Guard

ENV = "MIKEMOL_GUARDS"
DEFAULT_POLICY = Path("~/.config/mikemol/guards.toml")
EXIT_USAGE = 2
_USAGE = "usage: guard_cli [--policy FILE] -- CMD [ARG...]\n"
_SIGNAL_BASE = 128
_POLICY_ARGS = 2


def policy_path(flag: str | None, environ: Mapping[str, str]) -> tuple[Path, bool]:
    """Choose the policy file: the flag, else the environment, else the host default.

    Returns:
        the path and whether it was named explicitly (so a missing one is worth saying).

    """
    named = flag or environ.get(ENV)
    if named:
        return Path(named).expanduser(), True
    return DEFAULT_POLICY.expanduser(), False


def exit_status(code: int) -> int:
    """Turn a child's wait status into a shell-style exit code.

    Returns:
        the code, or 128 plus the signal number when the child was killed by a signal.

    """
    return _SIGNAL_BASE - code if code < 0 else code


def _entries(spec: Spec, guard: Guard, command: Sequence[str], at: str) -> list[triprecord.Entry]:
    """Turn one guard's outcome into the record's entries (W2359).

    A freeze guard's events are its own (`freeze`, `resume:cleared`, `cap:resume`, `cap:kill`); a
    signalling guard that tripped with no event is one `trip` naming what it signalled.

    Returns:
        one entry per event, each with the run's peak reading; empty when nothing happened.

    """
    outcome = guard.outcome
    seen = [value for value in outcome.samples if value is not None]
    peak = max(seen) if seen else None
    named = [(event.kind, event.pids) for event in outcome.events]
    if outcome.tripped and not outcome.events:
        named = [("trip", tuple(outcome.signalled))]
    if guard.failed:
        named.append(("error", ()))
    return [
        triprecord.Entry(
            at=at,
            guard=spec.row.name,
            event=kind,
            pids=tuple(pids),
            repo=Path.cwd().name,
            command=" ".join(command),
            owner=os.getpid(),
            limit=spec.row.above,
            peak=peak,
        )
        for kind, pids in named
    ]


def _keep(entries: Sequence[triprecord.Entry], environ: Mapping[str, str]) -> None:
    """Append the entries to the trip record and refresh the counter; say so when it fails.

    ⚑ A RECORD THAT CANNOT BE WRITTEN NEVER CHANGES THE COMMAND'S STATUS: the guard protects the
    machine, and a full disk must not turn a finished gate into a failed one.
    """
    if not entries:
        return
    record = triprecord.record_path(environ)
    try:
        triprecord.append(record, entries)
        triprecord.write_counter(record)
    except OSError as fault:
        sys.stderr.write(f"guard: the trip record {record} was not written: {fault}\n")


def run(command: Sequence[str], specs: Sequence[Spec], environ: Mapping[str, str]) -> int:
    """Run `command` with one guard per spec beside it.

    Returns:
        the command's exit status.

    """
    child = subprocess.Popen(list(command))
    guards: list[Guard] = []
    with ExitStack() as stack:
        for spec in specs:
            read = reader(spec.endpoint, spec.query, environ)
            guards.append(stack.enter_context(Guard(spec.row, child.pid, read)))
        code = child.wait()
    at = datetime.now(UTC).isoformat(timespec="seconds")
    for spec, guard in zip(specs, guards, strict=True):
        _keep(_entries(spec, guard, command, at), environ)
        if guard.failed:
            sys.stderr.write(f"guard {spec.row.name}: FAILED {guard.failed}\n")
        for event in guard.outcome.events:
            sys.stderr.write(f"guard {spec.row.name}: {event.kind} {list(event.pids)}\n")
        if guard.outcome.tripped and not guard.outcome.events:
            sent = guard.outcome.signalled or f"nothing (no process named {spec.row.target})"
            sys.stderr.write(
                f"guard {spec.row.name}: TRIPPED over {spec.row.above:g} for "
                f"{spec.row.hold} samples; signalled {sent}\n"
            )
    return exit_status(code)


def parse(argv: Sequence[str]) -> tuple[str | None, list[str]] | None:
    """Split `[--policy FILE] -- CMD...`.

    Returns:
        the policy flag and the command, or None for a usage error.

    """
    args = list(argv)
    if "--" not in args:
        return None
    cut = args.index("--")
    head, command = args[:cut], args[cut + 1 :]
    flag: str | None = None
    if head[:1] == ["--policy"] and len(head) == _POLICY_ARGS:
        flag = head[1]
    elif head:
        return None
    return (flag, command) if command else None


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command under the guards the policy declares.

    Returns:
        the command's exit status; 2 for a usage error.

    """
    parsed = parse(sys.argv[1:] if argv is None else argv)
    if parsed is None:
        sys.stderr.write(_USAGE)
        return EXIT_USAGE
    flag, command = parsed
    path, explicit = policy_path(flag, os.environ)
    if explicit and not path.is_file():
        sys.stderr.write(f"guard_cli: policy {path} does not exist; running unguarded\n")
    try:
        specs = load(path)
    except PolicyError as problem:
        sys.stderr.write(f"guard_cli: policy {path} is wrong; running UNGUARDED:\n")
        sys.stderr.writelines(f"  {line}\n" for line in problem.problems)
        specs = []
    return run(command, specs, os.environ)


if __name__ == "__main__":
    sys.exit(main())
