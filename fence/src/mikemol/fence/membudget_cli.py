# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-membudget`: substrate's bash `membudget` surface, over `admit` and `label_lease`.

Designed in `.claude/swarm/cross-client.md` §5-§7. The verbs are bash's: `run MB|auto [LABEL] --
CMD`, `init [N]`, `init --reset N` and `status`; `lease` and `deadline` are `label_lease`'s modes,
which waited for this script (`label_lease`'s module docstring). The exit codes are bash's too: the
command's own code from `run` (a signal as 128 + its number, so a cap's kill is 137), 1 when the
ledger lock stays busy, 2 on a usage error, 3 when admission is refused or would wait under
`MEMBUDGET_NOBLOCK` or past `MEMBUDGET_TIMEOUT` — or when no memory cap can be applied — and 4 when
the ledger itself says no.

⚑⚑ ONE LEDGER, TWO CLIENTS. Nothing here holds a rule of its own about the file: every write goes
through `admit`, whose rules already take bash's side where the two could differ, so this script
and bash's honour each other's leases (the cross-client arm in `tests/test_membudget_cli.py`).

⚑⚑ `run` CAPS THE COMMAND AT ITS LEASE, AS BASH'S `MemoryMax` SCOPE DOES. The cap is
`autosize.rung_caps` — the lease itself, swap forbidden — run by `autosize.climb`; nothing about
the cap is restated here. ⚑ NO FENCE IS A REFUSAL (3), NEVER AN UNCAPPED RUN: bash's `none`
backend refuses for the same reason — an uncapped payload is the OOM the lease exists to prevent.

⚑⚑ `MEMBUDGET_RETRY_OOM` CLIMBS. Set non-empty (bash's `[ -n … ]`), a rung the cap kills is
released and the next power-of-two rung admitted, up to the one cap; the last rung's code is the
outcome. It is `autosize.climb` — one lease at a time, each under the ORIGINAL parent.

⚑⚑ `auto` IS `label_lease` OVER THE RUN'S `History`, WITH THE CEILING PASSED. A command naming a
module sizes from that module's own ledger; any other from its label's. Bash's label arm hands
`label_lease` its default only, so `AGDA_MB_MAX` never reached it (A1 of the label-lease letter);
here both variables reach the one sizing rule, and a clamp says so on stderr.

⚑ A SCRIPT OF ITS OWN, NOT A MODE OF `mikemol-fence`, for the reason `peaks` gives: that command
fences whatever follows its flags, so it cannot take a subcommand.

⚑ THE EFFECTFUL EDGE IS ONE FUNCTION PER VERB, and each reads the machine only through a `Context`
— the environment, `admit.Host` and the fencer — so no arm depends on the box's load or memory.
"""

from __future__ import annotations

import math
import os
import sys
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.fence import admit, autosize, core, label_lease, ledger
from mikemol.fence.cgroup import FenceUnavailableError

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

# Bash's exit codes that are not `admit`'s: a busy lock, and a malformed invocation.
EXIT_LOCK = 1
EXIT_USAGE = 2

# Bash's code when no memory-cap backend exists: `_launch_scope`'s `none` arm returns 3.
EXIT_NO_CAP = 3

# The variables bash reads that shape the wait and the lock.
ENV_LOCK_TIMEOUT = "MEMBUDGET_LOCK_TIMEOUT"
ENV_NOBLOCK = "MEMBUDGET_NOBLOCK"
ENV_TIMEOUT = "MEMBUDGET_TIMEOUT"
ENV_MAXLOAD = "MEMBUDGET_MAXLOAD"
ENV_POLL = "MEMBUDGET_POLL"
ENV_POLL_MAX = "MEMBUDGET_POLL_MAX"
ENV_GC_INTERVAL = "MEMBUDGET_GC_INTERVAL"

# The variables bash's `_auto_mb` and `_record_time` read: the size with no history, the ceiling on
# an extrapolation from history, the run ledger's path, and the opt-out from recording to it.
ENV_DEFAULT_MB = "AGDA_MB_DEFAULT"
ENV_CEILING_MB = "AGDA_MB_MAX"
ENV_LABEL_LEDGER = "MEMBUDGET_LABEL_LEDGER"
ENV_NOLABELLEDGER = "MEMBUDGET_NOLABELLEDGER"

# The caller's declaration that its command re-runs cleanly, so a cap kill may climb (bash's
# retry block in `cmd_run`; substrate's agda shim sets it on every compile).
ENV_RETRY_OOM = "MEMBUDGET_RETRY_OOM"

# Bash's values when those are unset — substrate-tuned, and the operator's to override.
DEFAULT_MB = 192
CEILING_MB = 384

# The run ledger's name beside the budget ledger, and the label bash records an unlabelled run as.
LABEL_LEDGER_NAME = "labels.tsv"
UNLABELLED = "?"

_AUTO = "auto"
_SEPARATOR = "--"
_RESET = "--reset"
_RESET_ARGS = 2

USAGE = ("usage: mikemol-membudget {run MB|auto [LABEL] -- CMD... | init [MB] | init --reset MB"
         " | status | lease LEDGER LABEL DEFAULT_MB CEILING_MB"
         " | deadline LEDGER LABEL DEFAULT_S CEILING_S}\n")


class UsageError(ValueError):
    """The invocation is malformed; the message says how."""


def fence(command: Sequence[str], env: Mapping[str, str], caps: core.Caps) -> core.Result:
    """Run `command` in `env` inside a fence capped by `caps` — `core.run_once`, nothing added.

    Returns:
        what the run consumed, its exit code as a shell reports it, and which cap bound.

    """
    return core.run_once(command, caps, env)


def _environ() -> Mapping[str, str]:
    """Return the live process environment.

    Returns:
        `os.environ`.

    """
    return os.environ


@dataclass(frozen=True, slots=True)
class Context:
    """What a verb reads from the world: the environment, the host's facts, and the fencer."""

    env: Mapping[str, str] = field(default_factory=_environ)
    host: admit.Host = admit.HOST
    fence: Callable[[Sequence[str], Mapping[str, str], core.Caps], core.Result] = fence


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


def label_ledger_of(env: Mapping[str, str]) -> Path:
    """Return the run ledger bash would use: `$MEMBUDGET_LABEL_LEDGER`, else beside the budget.

    Returns:
        the path; an empty variable counts as unset, as bash's `${…:-}` does.

    """
    named = env.get(ENV_LABEL_LEDGER)
    return Path(named) if named else admit.default_path(env).parent / LABEL_LEDGER_NAME


@dataclass(frozen=True, slots=True)
class History:
    """Where a run's history is read and recorded: the ledger, the key, and the module if any.

    ⚑⚑ TWO KEYS, AS BASH HAS: a command naming a module (`label_lease.module_of`) keys on THAT
    MODULE's basename, in the ledger beside it; any other keys on its label, in the run ledger. A
    label-only ledger would put every agda compile on one label's max.
    """

    runs: Path
    key: str
    module: Path | None = None

    @classmethod
    def of(cls, command: Sequence[str], label: str, env: Mapping[str, str]) -> History:
        """Return the history `command` run under `label` reads and writes.

        Returns:
            the module's history when an argument names one, else the label's.

        """
        module = label_lease.module_of(command)
        if module is None:
            return cls(label_ledger_of(env), label)
        return cls(label_lease.module_ledger(module), module.name, module)

    def record(self, result: core.Result, env: Mapping[str, str]) -> None:
        """Append the row `result` earns, as bash's `_record_time` does.

        ⚑ `MEMBUDGET_NOLABELLEDGER` GATES THE LABEL LEDGER ONLY: bash writes a module's row before
        it reads that variable, so a module's history is always kept.
        """
        if self.module is not None:
            ledger.record(self.runs, self.key, result)
        elif not env.get(ENV_NOLABELLEDGER):
            ledger.record(self.runs, self.key or UNLABELLED, result)


@dataclass(frozen=True, slots=True)
class AutoSize:
    """What `auto` sizes from and a climb stops at: the default with no history, and the ceiling."""

    default_mb: int
    ceiling_mb: int

    @classmethod
    def of(cls, env: Mapping[str, str]) -> AutoSize:
        """Read `AGDA_MB_DEFAULT` and `AGDA_MB_MAX`; unset or empty is bash's value.

        ⚑ EACH MUST BE A POSITIVE WHOLE MB, or `megabytes` raises the usage error.

        Returns:
            the sizing inputs.

        """
        default = env.get(ENV_DEFAULT_MB)
        ceiling = env.get(ENV_CEILING_MB)
        return cls(megabytes(default, zero_ok=False) if default else DEFAULT_MB,
                   megabytes(ceiling, zero_ok=False) if ceiling else CEILING_MB)

    def lease(self, history: History) -> autosize.Sizing:
        """Return the lease `history` earns — its module's own peaks, else its label's.

        Returns:
            the sizing, `clamped_from` set when the one cap cut it.

        """
        if history.module is not None:
            return label_lease.module_lease(history.module, default_mb=self.default_mb,
                                            ceiling_mb=self.ceiling_mb)
        return label_lease.lease(label_lease.read_rows(history.runs), history.key,
                                 default_mb=self.default_mb, ceiling_mb=self.ceiling_mb)

    @property
    def cap(self) -> int:
        """The one cap the sizing and the climb obey: the ceiling, raised by a larger default."""
        return autosize.cap_of(self.ceiling_mb, self.default_mb)


@dataclass(frozen=True, slots=True)
class RunArgs:
    """`run`'s operands: the lease size (None for `auto`), its label, and the command it runs."""

    mb: int | None
    label: str
    command: tuple[str, ...]

    @classmethod
    def parse(cls, args: Sequence[str]) -> RunArgs:
        """Read `MB|auto [LABEL] -- CMD...`.

        ⚑ A ZERO LEASE IS ALLOWED: a claim needs no capacity (`admit.decide`) — but it is also a
        zero memory cap, as bash's `MemoryMax=0M` is, so its command cannot run.

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
        mb = None if head[0] == _AUTO else megabytes(head[0], zero_ok=True)
        return cls(mb, label, command)


def request_of(call: RunArgs, env: Mapping[str, str]) -> admit.Request:
    """Return the admission request for a sized call, nested under the lease the env names.

    Returns:
        the request.

    Raises:
        UsageError: the label holds whitespace, which the shared ledger cannot carry.

    """
    try:
        return admit.Request(call.mb or 0, call.label, admit.inherited_parent(env))
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


def sized_call(call: RunArgs, history: History, auto: AutoSize) -> RunArgs:
    """Return `call` with `auto` replaced by the lease its history earns.

    ⚑ A CLAMP IS LOUD: the warning `autosize.clamp_warning` owes goes to stderr, never stdout.

    Returns:
        the call with a size.

    """
    if call.mb is not None:
        return call
    got = auto.lease(history)
    warning = autosize.clamp_warning(history.key, got, auto.cap)
    if warning is not None:
        sys.stderr.write(warning + "\n")
    return replace(call, mb=got.mb)


def _announcer(label: str) -> Callable[[admit.Request, admit.Lease], None]:
    """Return the narration each admitted rung gets: TOP or SUB, its size, its lease id.

    Returns:
        the callback `autosize.Rig.announce` takes.

    """
    def announce(rung: admit.Request, lease: admit.Lease) -> None:
        where = "TOP" if rung.parent == admit.NO_PARENT else f"SUB under {rung.parent}"
        _say(f"{where} lease {rung.mb}MB [{label}] id={lease.lease_id} → MemoryMax={rung.mb}M")

    return announce


def _narrate_kills(label: str, results: Sequence[core.Result]) -> None:
    """Say, for each rung the cap killed, where it died and — when it climbed — where to."""
    for rung, result in enumerate(results):
        if not autosize.killed_by_cap(result):
            continue
        then = ""
        if rung + 1 < len(results):
            then = f" — retrying at {results[rung + 1].caps.mem}B (idempotent)"
        _say(f"OOM-killed at {result.caps.mem}B [{label}] — {'; '.join(result.bound_by)}{then}")


def cmd_run(args: Sequence[str], ctx: Context) -> int:
    """`run MB|auto [LABEL] -- CMD...`: admit, run capped at the lease, climb, release, record.

    ⚑ ONLY A CLEAN RUN IS RECORDED (`ledger.row_of`): a killed run's peak is the cap it hit — so
    of a climb, only the rung that finished can earn a row.

    Returns:
        the last rung's exit code — 137 when the cap killed it; 3 when no cap could be applied.

    """
    call = RunArgs.parse(args)
    history = History.of(call.command, call.label, ctx.env)
    auto = AutoSize.of(ctx.env)
    call = sized_call(call, history, auto)
    request = request_of(call, ctx.env)
    plan = autosize.Plan(request.mb, auto.cap, retry=bool(ctx.env.get(ENV_RETRY_OOM)),
                         request=request)
    rig = autosize.Rig(waiting_of(ctx.env), ctx.host, ctx.env, ctx.fence, _announcer(call.label))
    try:
        results = autosize.climb(store_of(ctx.env), call.command, plan, rig)
    except FenceUnavailableError as exc:
        _say(f"REFUSED [{call.label}] — no memory cap can be applied: {exc}")
        return EXIT_NO_CAP
    _narrate_kills(call.label, results)
    result = results[-1]
    history.record(result, ctx.env)
    return core.EXIT_HARNESS if result.exit_code is None else result.exit_code


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
