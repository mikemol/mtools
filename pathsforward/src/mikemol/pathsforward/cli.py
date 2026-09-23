# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""mikemol-paths-forward: the one reader and writer of a paths-forward state file.

⚑⚑ `--state PATH` IS REQUIRED AND THERE IS NO DEFAULT ROOT. sre's and gabion's tools hardcoded
`/home/mikemol/github/<repo>`, so a copy of the tool edited the original repo's file. The mirror,
the ledger and the flock sidecar all sit beside the path given.

⚑ THE BARE INVOCATION IS THE CHEAP READ: `--state PATH` alone prints one summary line. Every
write is a named mode, and the one read that stats the filesystem per waypoint is
`--check-evidence`, never the bare `--check`.

Exit codes: 0 ok · 1 payload over budget · 2 refused (unreadable file, a failed check, a refused
edit, bad arguments) · 3 lock held by another · 4 hash divergence (the FILE wins).
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, cast

from mikemol.pathsforward import lock, ops, render, selftest, store
from mikemol.pathsforward.check import check, evidence_findings
from mikemol.pathsforward.digest import Outcome, v2, verify
from mikemol.pathsforward.ledger import Entry, MalformedEntryError, append, line
from mikemol.pathsforward.model import BLOCKED_KINDS, NO_SYMBOL, STATUSES, text
from mikemol.pathsforward.payload import PayloadOverBudgetError, Request, build

if TYPE_CHECKING:
    from collections.abc import Callable

    from mikemol.pathsforward.model import Json, State

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_REFUSED = 2
EXIT_LOCKED = 3
EXIT_DIVERGED = 4

_SUMMARY = "summary"
_FLAGS = ("hash", "render", "payload", "queue", "check", "check_evidence", "selftest",
          "bump_blocked", "preamble_clear")
_VALUED = ("verify", "lock", "unlock", "armed", "update", "add", "drop", "ledger", "show",
           "preamble_set")
_LEDGER_ARGS = ("SYMBOL", "OUTCOME", "MECHANISM", "NOTE")


@dataclass(frozen=True)
class Ctx:
    """One invocation: its parsed options, the state path, and the clock read once."""

    opts: dict[str, object]
    path: Path
    now: datetime

    def get(self, key: str) -> str | None:
        """Read a string option.

        Returns:
            the value, or None when unset.

        """
        value = self.opts.get(key)
        return None if value is None else str(value)

    def many(self, key: str) -> tuple[str, ...] | None:
        """Read a list option.

        Returns:
            the values, or None when unset.

        """
        value = self.opts.get(key)
        if value is None:
            return None
        return tuple(str(v) for v in cast("list[object]", value))

    def number(self, key: str) -> int | None:
        """Read an integer option.

        Returns:
            the value, or None when unset.

        """
        value = self.opts.get(key)
        return value if isinstance(value, int) else None

    def stamp(self) -> str:
        """Format the invocation's clock.

        Returns:
            the stamp.

        """
        return lock.stamp(self.now)


def _say(message: str) -> None:
    """Write one line to stdout."""
    sys.stdout.write(message + "\n")


def _warn(message: str) -> None:
    """Write one line to stderr."""
    sys.stderr.write(message + "\n")


def _parser() -> argparse.ArgumentParser:
    """Build the argument parser: one optional mode, and the typed fields modes read.

    Returns:
        the parser.

    """
    ap = argparse.ArgumentParser(prog="mikemol-paths-forward", allow_abbrev=False,
                                 description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--state", metavar="PATH", help="the state file (required; no default)")
    mode = ap.add_mutually_exclusive_group()
    for flag in _FLAGS:
        mode.add_argument(f"--{flag.replace('_', '-')}", action="store_true")
    mode.add_argument("--verify", metavar="HASH", help="compare a payload's state_hash")
    mode.add_argument("--lock", metavar="HOLDER", help="take the tick lock (exit 3 if held)")
    mode.add_argument("--unlock", metavar="HOLDER", help="release the tick lock")
    mode.add_argument("--armed", metavar="JOB_ID", help="record job_id and heartbeat")
    mode.add_argument("--update", metavar="SYMBOL", help="set typed fields on a waypoint")
    mode.add_argument("--add", metavar="TITLE", help="mint the next W<n> as ready")
    mode.add_argument("--drop", nargs=2, metavar=("SYMBOL", "REASON"), help="move to residue")
    mode.add_argument("--ledger", nargs=len(_LEDGER_ARGS), metavar=_LEDGER_ARGS)
    mode.add_argument("--show", metavar="SYMBOL", help="what is W<n>")
    mode.add_argument("--preamble-set", metavar="FILE", help="store FILE's lines as preamble")
    ap.add_argument("--status", choices=STATUSES)
    ap.add_argument("--blocked-on", nargs="*", metavar="WHO")
    ap.add_argument("--blocked-kind", choices=BLOCKED_KINDS)
    ap.add_argument("--next", metavar="TEXT")
    ap.add_argument("--title", metavar="TEXT", help="--update: replace a stale one-line title")
    ap.add_argument("--evidence-append", metavar="TEXT")
    ap.add_argument("--ticks-blocked", type=int, metavar="N")
    ap.add_argument("--enables", nargs="+", metavar="SYMBOL")
    ap.add_argument("--touches", nargs="+", metavar="TAG")
    ap.add_argument("--except", dest="exclude", nargs="+", metavar="SYMBOL")
    ap.add_argument("--kind", default="tick", help="the ledger line's kind column")
    ap.add_argument("--evidence", metavar="TEXT", help="the ledger line's evidence column")
    return ap


def _ledger(ctx: Ctx, entry: Entry) -> None:
    """Append one structured line to the ledger beside the state file."""
    append(store.sibling(ctx.path, store.LEDGER), line(entry, ctx.stamp()))


def _mutate(ctx: Ctx, edit: Callable[[State], int]) -> int:
    """Run one read-modify-write under the flock, saving only when the edit succeeded.

    Returns:
        the edit's exit code.

    """
    with store.exclusive(ctx.path):
        state = store.load(ctx.path)
        code = edit(state)
        if code == EXIT_OK:
            store.save(ctx.path, state)
    return code


def _summary(ctx: Ctx) -> int:
    """Print the cheap one-line summary.

    Returns:
        EXIT_OK.

    """
    state = store.load(ctx.path)
    held = lock.current(state)
    _say(f"counter={state.counter} state_hash={v2(state.waypoints)} "
         f"live={len(state.waypoints)} residue={len(state.residue)} "
         f"lock={held[0] if held else '-'}")
    return EXIT_OK


def _hash(ctx: Ctx) -> int:
    """Print the v2 hash.

    Returns:
        EXIT_OK.

    """
    _say(v2(store.load(ctx.path).waypoints))
    return EXIT_OK


def _verify(ctx: Ctx) -> int:
    """Compare a claimed hash; ledger a transition or a divergence.

    Returns:
        EXIT_OK on a match or transition, EXIT_DIVERGED, or EXIT_REFUSED when malformed.

    """
    claimed = ctx.get("verify") or ""
    verdict = verify(store.load(ctx.path).waypoints, claimed)
    forms = ",".join(verdict.forms)
    if verdict.outcome is Outcome.MALFORMED:
        _warn(f"REFUSED: {claimed!r} is neither v2:<16 hex> nor 12-64 legacy hex")
        return EXIT_REFUSED
    if verdict.outcome is Outcome.MATCH:
        _say(f"match {verdict.current}")
        return EXIT_OK
    if verdict.outcome is Outcome.TRANSITION:
        note = f"hash-scheme transition (legacy={forms}) {claimed} -> {verdict.current}"
        _ledger(ctx, Entry("hash", NO_SYMBOL, "transition", NO_SYMBOL, note))
        _say(f"transition legacy={forms} claimed={claimed} current={verdict.current}")
        return EXIT_OK
    note = f"divergence: payload {claimed}, file {verdict.current}; the FILE wins"
    _ledger(ctx, Entry("hash", NO_SYMBOL, "diverged", NO_SYMBOL, note))
    _say(note)
    return EXIT_DIVERGED


def _render(ctx: Ctx) -> int:
    """Write the mirror beside the state file.

    Returns:
        EXIT_OK.

    """
    target = store.sibling(ctx.path, store.MIRROR)
    store.write_atomic(target, render.mirror(store.load(ctx.path), ctx.path))
    _say(f"rendered {target}")
    return EXIT_OK


def _payload(ctx: Ctx) -> int:
    """Print the payload, or refuse it.

    Returns:
        EXIT_OK, or EXIT_FAILED when it cannot fit.

    """
    try:
        _say(build(Request(store.load(ctx.path), ctx.path, ctx.stamp())))
    except PayloadOverBudgetError as exc:
        _warn(f"PayloadOverBudget: {exc}")
        return EXIT_FAILED
    return EXIT_OK


def _queue(ctx: Ctx) -> int:
    """Print the queue.

    Returns:
        EXIT_OK.

    """
    _say(render.queue(store.load(ctx.path)))
    return EXIT_OK


def _report(state: State, findings: list[str]) -> int:
    """Print a check's findings.

    Returns:
        EXIT_OK when there are none, else EXIT_REFUSED.

    """
    if not findings:
        _say(f"check: OK — {state.counter} of {state.counter} symbols resolve; "
             f"state_hash={v2(state.waypoints)}")
        return EXIT_OK
    _say(f"check: REFUSED — {len(findings)} finding(s):")
    for finding in findings:
        _say(f"    {finding}")
    return EXIT_REFUSED


def _check(ctx: Ctx) -> int:
    """Run the cheap check.

    Returns:
        see `_report`.

    """
    state = store.load(ctx.path)
    return _report(state, check(state))


def _check_evidence(ctx: Ctx) -> int:
    """Run the check plus the opt-in evidence read.

    Returns:
        see `_report`.

    """
    state = store.load(ctx.path)
    return _report(state, check(state) + evidence_findings(state))


def _selftest() -> int:
    """Run the built-in arms.

    Returns:
        EXIT_OK when every arm held, else EXIT_FAILED.

    """
    held, missed = selftest.run()
    for label in missed:
        _say(f"  MISS {label}")
    _say(f"selftest: {held} of {held + len(missed)} arm(s) hold")
    return EXIT_FAILED if missed else EXIT_OK


def _lock(ctx: Ctx) -> int:
    """Take the tick lock, ledgering a takeover.

    Returns:
        EXIT_OK, or EXIT_LOCKED when another holder has it.

    """
    def edit(state: State) -> int:
        result = lock.acquire(state, ctx.get("lock") or "", ctx.now)
        if result.outcome is lock.Outcome.HELD:
            _say(f"locked by {result.previous} ({result.age_s:.0f}s); skip this tick")
            return EXIT_LOCKED
        if result.outcome is lock.Outcome.TAKEOVER:
            note = (f"stale lock from {result.previous} ({result.age_s:.0f}s) taken by "
                    f"{result.holder}; re-read evidence")
            _ledger(ctx, Entry("lock", NO_SYMBOL, "takeover", NO_SYMBOL, note))
        _say(f"{result.outcome} by {result.holder}")
        return EXIT_OK

    return _mutate(ctx, edit)


def _unlock(ctx: Ctx) -> int:
    """Release the tick lock.

    Returns:
        EXIT_OK, or EXIT_LOCKED when another holder has it.

    """
    def edit(state: State) -> int:
        result = lock.release(state, ctx.get("unlock") or "")
        if result.outcome is lock.Outcome.NOT_HOLDER:
            _warn(f"not released: held by {result.previous}")
            return EXIT_LOCKED
        _say("unlocked")
        return EXIT_OK

    return _mutate(ctx, edit)


def _armed(ctx: Ctx) -> int:
    """Record the job id and heartbeat.

    Returns:
        EXIT_OK.

    """
    def edit(state: State) -> int:
        ops.arm(state, ctx.get("armed") or "", ctx.stamp())
        _say(f"armed job_id={ctx.get('armed')}")
        return EXIT_OK

    return _mutate(ctx, edit)


def _update(ctx: Ctx) -> int:
    """Set typed fields on a waypoint.

    Returns:
        EXIT_OK.

    """
    upd = ops.Update(status=ctx.get("status"), blocked_on=ctx.many("blocked_on"),
                     blocked_kind=ctx.get("blocked_kind"), next_step=ctx.get("next"),
                     evidence_append=ctx.get("evidence_append"),
                     ticks_blocked=ctx.number("ticks_blocked"), title=ctx.get("title"))

    def edit(state: State) -> int:
        sym = ctx.get("update") or ""
        ops.update(state, sym, upd, ctx.stamp())
        _say(f"{sym} updated; state_hash={v2(state.waypoints)}")
        return EXIT_OK

    return _mutate(ctx, edit)


def _add(ctx: Ctx) -> int:
    """Mint a waypoint.

    Returns:
        EXIT_OK.

    """
    draft = ops.Draft(ctx.get("add") or "", ctx.get("next") or "",
                      ctx.many("enables") or (), ctx.many("touches") or ())

    def edit(state: State) -> int:
        sym = ops.add(state, draft, ctx.stamp())
        _say(f"{sym} added; state_hash={v2(state.waypoints)}")
        return EXIT_OK

    return _mutate(ctx, edit)


def _drop(ctx: Ctx) -> int:
    """Move a waypoint to residue.

    Returns:
        EXIT_OK.

    """
    sym, reason = ctx.many("drop") or ("", "")

    def edit(state: State) -> int:
        ops.drop(state, sym, reason, ctx.stamp())
        _say(f"{sym} -> residue; state_hash={v2(state.waypoints)}")
        return EXIT_OK

    return _mutate(ctx, edit)


def _bump_blocked(ctx: Ctx) -> int:
    """Count a blocked tick on every blocked waypoint and say who is owed a nudge.

    Returns:
        EXIT_OK.

    """
    exclude = frozenset(ctx.many("exclude") or ())

    def edit(state: State) -> int:
        for n in ops.bump_blocked(state, exclude):
            owed = "" if n.action is ops.Action.QUIET else f"  {n.action}"
            _say(f"{n.symbol} ticks_blocked={n.ticks} on={','.join(n.blocked_on)}"
                 f"({n.kind}){owed}")
        return EXIT_OK

    return _mutate(ctx, edit)


def _ledger_mode(ctx: Ctx) -> int:
    """Append a structured ledger line.

    Returns:
        EXIT_OK.

    """
    sym, outcome, mechanism, note = ctx.many("ledger") or ("", "", "", "")
    entry = Entry(ctx.get("kind") or "", sym, outcome, mechanism, note, ctx.get("evidence") or "")
    text_line = line(entry, ctx.stamp())
    append(store.sibling(ctx.path, store.LEDGER), text_line)
    _say(text_line)
    return EXIT_OK


def _show(ctx: Ctx) -> int:
    """Say what a symbol is: live, residue, or never issued.

    Returns:
        EXIT_OK when it resolves, else EXIT_REFUSED.

    """
    state = store.load(ctx.path)
    sym = ctx.get("show") or ""
    found: list[Json] = [r for r in (*state.waypoints, *state.residue) if text(r, "symbol") == sym]
    if not found:
        _warn(f"{sym}: in neither waypoints nor residue (counter={state.counter})")
        return EXIT_REFUSED
    for rec in found:
        _say(json.dumps(rec, indent=2, ensure_ascii=False))
    return EXIT_OK


def _preamble_set(ctx: Ctx) -> int:
    """Store a file's lines as the preamble.

    Returns:
        EXIT_OK.

    """
    lines = Path(ctx.get("preamble_set") or "").read_text(encoding="utf-8").splitlines()

    def edit(state: State) -> int:
        ops.set_preamble(state, lines)
        _say(f"preamble set: {len(lines)} line(s)")
        return EXIT_OK

    return _mutate(ctx, edit)


def _preamble_clear(ctx: Ctx) -> int:
    """Remove the preamble.

    Returns:
        EXIT_OK.

    """
    def edit(state: State) -> int:
        _say(f"preamble cleared ({ops.clear_preamble(state)} line(s) removed)")
        return EXIT_OK

    return _mutate(ctx, edit)


_HANDLERS: dict[str, Callable[[Ctx], int]] = {
    _SUMMARY: _summary, "hash": _hash, "verify": _verify, "render": _render,
    "payload": _payload, "queue": _queue, "check": _check, "check_evidence": _check_evidence,
    "lock": _lock, "unlock": _unlock, "armed": _armed, "update": _update, "add": _add,
    "drop": _drop, "bump_blocked": _bump_blocked, "ledger": _ledger_mode, "show": _show,
    "preamble_set": _preamble_set, "preamble_clear": _preamble_clear,
}


def mode_of(opts: dict[str, object]) -> str:
    """Name the mode an invocation selected.

    Returns:
        the mode, or the summary when none was given.

    """
    chosen = [m for m in _FLAGS if opts.get(m) is True]
    chosen += [m for m in _VALUED if opts.get(m) is not None]
    return chosen[0] if chosen else _SUMMARY


def main(argv: list[str] | None = None) -> int:
    """Run one invocation.

    Returns:
        the exit code (see the module docstring).

    """
    opts: dict[str, object] = vars(_parser().parse_args(sys.argv[1:] if argv is None else argv))
    mode = mode_of(opts)
    if mode == "selftest":
        return _selftest()
    state = opts.get("state")
    if not state:
        _warn("REFUSED: --state PATH is required; there is no default root")
        return EXIT_REFUSED
    ctx = Ctx(opts, Path(str(state)).absolute(), datetime.now(UTC))
    try:
        return _HANDLERS[mode](ctx)
    except (store.UnreadableStateError, ops.RefusedError, MalformedEntryError, OSError) as exc:
        _warn(f"REFUSED: {exc}")
        return EXIT_REFUSED
