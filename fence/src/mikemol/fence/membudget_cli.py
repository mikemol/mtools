# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-membudget`: substrate's bash `membudget` surface, over `admit` and `label_lease`.

Designed in `.claude/swarm/cross-client.md` §5-§7. The verbs are bash's: `run MB [LABEL] -- CMD`,
`init [N]`, `init --reset N` and `status`; `lease` and `deadline` are `label_lease`'s modes, which
waited for this script (`label_lease`'s module docstring). The exit codes are bash's too: the
command's own code from `run` (a signal as 128 + its number), 1 when the ledger lock stays busy,
2 on a usage error, 3 when admission is refused or would wait under `MEMBUDGET_NOBLOCK` or past
`MEMBUDGET_TIMEOUT`, and 4 when the ledger itself says no.

⚑⚑ ONE LEDGER, TWO CLIENTS. Nothing here holds a rule of its own about the file: every write goes
through `admit`, whose rules already take bash's side where the two could differ, so this script
and bash's honour each other's leases (the cross-client arm in `tests/test_membudget_cli.py`).

⚑⚑ `run` DOES NOT CAP THE COMMAND. Bash launches it in a `MemoryMax` scope; this script admits,
runs and releases, and a cap is `mikemol-fence`'s job — composed as `run MB L -- mikemol-fence …`.

⚑ A SCRIPT OF ITS OWN, NOT A MODE OF `mikemol-fence`, for the reason `peaks` gives: that command
fences whatever follows its flags, so it cannot take a subcommand.

⚑ THE EFFECTFUL EDGE IS ONE FUNCTION PER VERB, and each reads the machine only through a `Context`
— the environment, `admit.Host` and the spawner — so no arm depends on the box's load or memory.
"""

from __future__ import annotations

import math
import os
import sys
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

from mikemol.fence import admit, label_lease

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

# Bash's exit codes that are not `admit`'s: a busy lock, and a malformed invocation.
EXIT_LOCK = 1
EXIT_USAGE = 2

# The shell's codes for a command that could not be run: not found, and not executable.
EXIT_NOT_FOUND = 127
EXIT_NOT_EXECUTABLE = 126

# A command killed by signal N exits 128 + N, as the shell reports it.
_SIGNAL_BASE = 128

# The variables bash reads that shape the wait and the lock.
ENV_LOCK_TIMEOUT = "MEMBUDGET_LOCK_TIMEOUT"
ENV_NOBLOCK = "MEMBUDGET_NOBLOCK"
ENV_TIMEOUT = "MEMBUDGET_TIMEOUT"
ENV_MAXLOAD = "MEMBUDGET_MAXLOAD"
ENV_POLL = "MEMBUDGET_POLL"
ENV_POLL_MAX = "MEMBUDGET_POLL_MAX"
ENV_GC_INTERVAL = "MEMBUDGET_GC_INTERVAL"

_SEPARATOR = "--"
_RESET = "--reset"
_RESET_ARGS = 2

USAGE = ("usage: mikemol-membudget {run MB [LABEL] -- CMD... | init [MB] | init --reset MB"
         " | status | lease LEDGER LABEL DEFAULT_MB CEILING_MB"
         " | deadline LEDGER LABEL DEFAULT_S CEILING_S}\n")


class UsageError(ValueError):
    """The invocation is malformed; the message says how."""


def spawn(command: Sequence[str], env: Mapping[str, str]) -> int:
    """Run `command` to completion with `env`, and return its exit code as a shell reports it.

    ⚑ AN ARGV LIST, NO SHELL: `posix_spawnp` searches `PATH` and execs; nothing is re-parsed.

    Returns:
        the command's code; 128 + N when signal N killed it; 127 or 126 when it could not start.

    """
    try:
        pid = os.posix_spawnp(command[0], list(command), dict(env))
    except FileNotFoundError:
        return EXIT_NOT_FOUND
    except PermissionError:
        return EXIT_NOT_EXECUTABLE
    code = os.waitstatus_to_exitcode(os.waitpid(pid, 0)[1])
    return _SIGNAL_BASE - code if code < 0 else code


def _environ() -> Mapping[str, str]:
    """Return the live process environment.

    Returns:
        `os.environ`.

    """
    return os.environ


@dataclass(frozen=True, slots=True)
class Context:
    """What a verb reads from the world: the environment, the host's facts, and the spawner."""

    env: Mapping[str, str] = field(default_factory=_environ)
    host: admit.Host = admit.HOST
    spawn: Callable[[Sequence[str], Mapping[str, str]], int] = spawn


# --- the pure half: arguments and environment, read into `admit`'s types ---

def _number(env: Mapping[str, str], name: str, default: float) -> float:
    """Return `env[name]` as a finite, non-negative number; unset or empty is `default`.

    Returns:
        the number.

    Raises:
        UsageError: the value is not a finite non-negative number.

    """
    raw = env.get(name)
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        value = math.nan
    if not math.isfinite(value) or value < 0:
        msg = f"{name} must be a non-negative number, got {raw!r}"
        raise UsageError(msg)
    return value


def store_of(env: Mapping[str, str]) -> admit.Store:
    """Return the ledger bash would use, with bash's lock bound.

    Returns:
        the store at `$MEMBUDGET_FILE` (else bash's default), bounded by `$MEMBUDGET_LOCK_TIMEOUT`.

    """
    return admit.Store(admit.default_path(env),
                       _number(env, ENV_LOCK_TIMEOUT, admit.LOCK_TIMEOUT_S))


def waiting_of(env: Mapping[str, str]) -> admit.Waiting:
    """Return how a blocked `run` waits, from the variables bash reads.

    ⚑ `NOBLOCK` IS ANY NON-EMPTY VALUE, as bash's `[ -n … ]`; the numbers fall back to `admit`'s.

    Returns:
        the waiting policy.

    """
    return admit.Waiting(
        noblock=bool(env.get(ENV_NOBLOCK)),
        timeout_s=_number(env, ENV_TIMEOUT, 0.0) if env.get(ENV_TIMEOUT) else None,
        maxload=_number(env, ENV_MAXLOAD, admit.MAXLOAD),
        poll_start_s=_number(env, ENV_POLL, admit.POLL_START_S),
        poll_max_s=_number(env, ENV_POLL_MAX, admit.POLL_MAX_S),
        gc_interval_s=_number(env, ENV_GC_INTERVAL, admit.GC_INTERVAL_S),
    )


def megabytes(raw: str, *, zero_ok: bool) -> int:
    """Return `raw` as whole MB — bash's `_valid_mb`, which admits no zero for a total.

    Returns:
        the number.

    Raises:
        UsageError: `raw` is not all digits, or is zero where zero is not allowed.

    """
    if not (raw.isascii() and raw.isdigit()) or (int(raw) == 0 and not zero_ok):
        msg = f"expected a {'non-negative' if zero_ok else 'positive'} MB, got {raw!r}"
        raise UsageError(msg)
    return int(raw)


@dataclass(frozen=True, slots=True)
class RunArgs:
    """`run`'s operands: the lease size, its label, and the command it runs."""

    mb: int
    label: str
    command: tuple[str, ...]

    @classmethod
    def parse(cls, args: Sequence[str]) -> RunArgs:
        """Read `MB [LABEL] -- CMD...`.

        ⚑ A ZERO LEASE IS ALLOWED: a claim needs no capacity (`admit.decide`). `auto` is NOT —
        bash sizes it from `labels.tsv`, and this script does not read that file yet.

        Returns:
            the operands.

        Raises:
            UsageError: no `--`, no command, a wrong operand count, or a bad MB.

        """
        if _SEPARATOR not in args:
            msg = "run needs `--` before the command"
            raise UsageError(msg)
        cut = list(args).index(_SEPARATOR)
        head, command = args[:cut], tuple(args[cut + 1:])
        if not command or len(head) not in {1, 2}:
            msg = "run takes MB [LABEL] -- CMD..."
            raise UsageError(msg)
        label = head[1] if len(head) > 1 else ""
        return cls(megabytes(head[0], zero_ok=True), label, command)


def request_of(call: RunArgs, env: Mapping[str, str]) -> admit.Request:
    """Return the admission request, nested under the lease the environment names.

    Returns:
        the request.

    Raises:
        UsageError: the label holds whitespace, which the shared ledger cannot carry.

    """
    try:
        return admit.Request(call.mb, call.label, admit.inherited_parent(env))
    except ValueError as exc:
        raise UsageError(str(exc)) from exc


def render_status(snap: admit.Ledger) -> str:
    """Render `status` as bash prints it: totals, then one line per lease.

    ⚑ `top-level-leased` IS BASH'S FIGURE — top-level leases only — kept so that one reader can
    parse both clients; nested leases still draw from the pool (`Ledger.used`), and admission counts
    them.

    Returns:
        the report.

    """
    top = sum(lease.mb for lease in snap.leases if lease.parent == admit.NO_PARENT)
    total = "" if snap.total_mb is None else str(snap.total_mb)
    free = (snap.total_mb or 0) - top
    lines = [f"membudget: TOTAL={total}MB top-level-leased={top}MB global-free={free}MB"]
    for lease in snap.leases:
        where = "top" if lease.parent == admit.NO_PARENT else f"under {lease.parent}"
        lines.append(f"  [{lease.lease_id}] {lease.mb}MB pid={lease.owner} ({where}) {lease.label}")
    if not snap.leases:
        lines.append("  (no active leases)")
    return "".join(f"{line}\n" for line in lines)


def resize(store: admit.Store, total_mb: int) -> admit.Ledger:
    """Set the ledger's total to `total_mb` in place, under the lock, keeping every lease.

    ⚑⚑ NEVER `rm`: the old bash `init` deleted the file and wiped a live lease (cross-client §5).
    The rewrite is `admit.Store.rewrite` — a sibling renamed over the ledger — so a lock-free
    reader sees the old file or the new one, never none.

    Returns:
        the snapshot as written.

    Raises:
        RefusedError: the ledger declares its total more than once; nothing is guessed.

    """
    with store.locked():
        snap = store.read()
        if snap.ambiguous:
            raise admit.RefusedError(admit.Verdict.AMBIGUOUS_TOTAL, admit.EXIT_LEDGER,
                                     f"{store.path} has {snap.total_lines} TOTAL_MB lines")
        sized = replace(snap, total_mb=total_mb, total_lines=1)
        store.rewrite(sized)
        return sized


# --- the effectful half: one function per verb ---

def _say(text: str) -> None:
    """Write one line of narration to stderr."""
    sys.stderr.write(f"membudget: {text}\n")


def cmd_run(args: Sequence[str], ctx: Context) -> int:
    """`run MB [LABEL] -- CMD...`: admit, run the command under its lease, release.

    Returns:
        the command's exit code.

    """
    call = RunArgs.parse(args)
    request = request_of(call, ctx.env)
    store = store_of(ctx.env)
    with admit.admit(store, request, waiting_of(ctx.env), ctx.host) as lease:
        where = "TOP" if request.parent == admit.NO_PARENT else f"SUB under {request.parent}"
        _say(f"{where} lease {call.mb}MB [{call.label}] id={lease.lease_id}")
        return ctx.spawn(call.command, {**ctx.env, admit.ENV_PARENT: lease.lease_id})


def cmd_status(args: Sequence[str], ctx: Context) -> int:
    """`status`: create the ledger if absent, reap the dead, and report.

    Returns:
        0.

    Raises:
        UsageError: `status` was given operands.

    """
    if args:
        msg = "status takes no operands"
        raise UsageError(msg)
    store = store_of(ctx.env)
    admit.ensure(store, ctx.host.default_total())
    sys.stdout.write(render_status(admit.reap(store, ctx.host.is_alive)))
    return 0


def cmd_init(args: Sequence[str], ctx: Context) -> int:
    """`init [MB]` declares a missing total and changes nothing else; `init --reset MB` resizes.

    Returns:
        `status`'s code.

    Raises:
        UsageError: a wrong operand count, or a bad MB.

    """
    store = store_of(ctx.env)
    if args[:1] == [_RESET]:
        if len(args) != _RESET_ARGS:
            msg = "init --reset needs a positive MB, e.g. init --reset 8192"
            raise UsageError(msg)
        sized = resize(store, megabytes(args[1], zero_ok=False))
        if sized.used > (sized.total_mb or 0):
            _say(f"total {sized.total_mb}MB is below the {sized.used}MB leased — over-subscribed "
                 "until leases drain; admission blocks meanwhile")
    else:
        if len(args) > 1:
            msg = "init takes at most one MB"
            raise UsageError(msg)
        total = megabytes(args[0], zero_ok=False) if args else ctx.host.default_total()
        if not admit.init(store, total):
            sys.stdout.write("membudget: ledger exists with a total — init changes nothing (to "
                             "resize, keeping live leases: membudget init --reset N)\n")
    return cmd_status([], ctx)


def cmd_lease(args: Sequence[str], _ctx: Context) -> int:
    """`lease LEDGER LABEL DEFAULT_MB CEILING_MB`, answered by `label_lease`.

    Returns:
        `label_lease.main`'s code.

    """
    return label_lease.main(["lease", *args])


def cmd_deadline(args: Sequence[str], _ctx: Context) -> int:
    """`deadline LEDGER LABEL DEFAULT_S CEILING_S`, answered by `label_lease`.

    Returns:
        `label_lease.main`'s code.

    """
    return label_lease.main(["deadline", *args])


VERBS: dict[str, Callable[[Sequence[str], Context], int]] = {
    "run": cmd_run,
    "init": cmd_init,
    "status": cmd_status,
    "lease": cmd_lease,
    "deadline": cmd_deadline,
}


def main(argv: list[str] | None = None, ctx: Context | None = None) -> int:
    """Dispatch one verb, mapping `admit`'s failures onto bash's exit codes.

    Returns:
        the verb's code; 1 on a busy lock, 2 on a usage error, 3 or 4 on a refusal.

    """
    args = sys.argv[1:] if argv is None else argv
    verb = VERBS.get(args[0]) if args else None
    if verb is None:
        sys.stderr.write(USAGE)
        return EXIT_USAGE
    try:
        return verb(args[1:], Context() if ctx is None else ctx)
    except UsageError as exc:
        _say(str(exc))
        sys.stderr.write(USAGE)
        return EXIT_USAGE
    except admit.RefusedError as exc:
        _say(f"REFUSED — {exc}")
        return exc.code
    except admit.LockTimeoutError as exc:
        _say(f"lock busy — {exc}")
        return EXIT_LOCK


if __name__ == "__main__":
    sys.exit(main())
