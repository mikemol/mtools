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

from __future__ import annotations

import os
import subprocess
import sys
from contextlib import ExitStack
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.fence.policy import PolicyError, load
from mikemol.fence.reading import reader
from mikemol.fence.watcher import Guard

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from mikemol.fence.policy import Spec

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
    for spec, guard in zip(specs, guards, strict=True):
        if guard.outcome.tripped:
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
