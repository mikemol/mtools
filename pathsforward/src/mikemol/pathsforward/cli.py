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

import argparse
import json
import socket
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from mikemol.pathsforward import (
    admission,
    attach,
    behindopen,
    bulkblock,
    certify,
    delivered,
    dropto,
    embargo,
    foreign,
    gate,
    inbound,
    lease,
    lock,
    opa_eval,
    ops,
    outcomes,
    render,
    selftest,
    session,
    store,
    triage,
    vtodo,
)
from mikemol.pathsforward.advice import close_applied as close_advice
from mikemol.pathsforward.advice import counts as count_advice
from mikemol.pathsforward.advice import exclude as exclude_advice
from mikemol.pathsforward.advice import mark_applied as apply_advice
from mikemol.pathsforward.advice import reason_for as advice_reason
from mikemol.pathsforward.advice import reject as reject_advice
from mikemol.pathsforward.advice import upsert as upsert_advice
from mikemol.pathsforward.atomize import atomize
from mikemol.pathsforward.check import check, evidence_findings, unscored
from mikemol.pathsforward.closegate import judge as judge_close
from mikemol.pathsforward.closeumbrellas import apply as close_apply
from mikemol.pathsforward.closeumbrellas import plan as close_plan
from mikemol.pathsforward.commitmsg import draft
from mikemol.pathsforward.digest import Outcome, v2, verify
from mikemol.pathsforward.ledger import Entry, MalformedEntryError, append, line, read
from mikemol.pathsforward.lift import lift as lift_row
from mikemol.pathsforward.model import (
    BLOCKED_KINDS,
    NO_SYMBOL,
    STATUSES,
    Json,
    RefusedError,
    State,
    text,
)
from mikemol.pathsforward.overlap import overlaps
from mikemol.pathsforward.payload import PayloadOverBudgetError, Request, build
from mikemol.pathsforward.realizable import GATES
from mikemol.pathsforward.redact import REDACTED, digest, redact, scan
from mikemol.pathsforward.unlinked import report as unlinked_report

LIFT_ROW = lift_row
CLOSE_JUDGE = judge_close
REJECT_ADVICE = reject_advice
EXIT_OK = 0
EXIT_FAILED = 1
EXIT_REFUSED = 2
EXIT_LOCKED = 3
EXIT_DIVERGED = 4
Planned = tuple[str, str, str]


def _advise(
    ctx: "Ctx",
    state: State,
    spec: tuple[str, str],
    planned: Sequence[Planned],
    excluded: Mapping[str, str] | None = None,
) -> None:
    """Say a dry run's plan through the advice store, or close the advice a write applied (W1244).

    `spec` is (tool, rule) and each planned item is (subject, action, the WOULD line). On a dry
    run every item is upserted once: a rejected one prints its stated reason in place of the line,
    the rest print as before, rows no longer indicated close as applied, and the output ends with
    the counts of proposed, rejected and new. On `--write` the change is made by the caller, so
    the lines print as they did and the matching open rows are marked applied. ⚑ A rejection
    governs what a dry run PROPOSES; an explicit `--write` is the operator's own word and is not
    blocked by it.

    ⚑ `excluded` IS EACH `--except SYMBOL=REASON` OF THE CALL (W1158): it is stored as a row
    rejected with that reason, write or dry, so the decision outlives the command and a later dry
    run that would propose the card prints `EXCLUDED <card>: <reason>` for update-many. An
    exclusion with no reason is not stored: there is nothing to print.
    """
    tool, rule = spec
    for symbol, why in (excluded or {}).items():
        if why.strip():
            exclude_advice(state.doc, (tool, rule, symbol, f"update {symbol}"), why, ctx.stamp())
    subjects = {subject for subject, _, _ in planned}
    if ctx.opts.get("write"):
        for _, _, said in planned:
            _say(said)
        apply_advice(state.doc, tool, rule, subjects)
        return
    label = "EXCLUDED" if tool == "update-many" else "REJECTED"
    outcomes: list[str] = []
    for subject, action, said in planned:
        item = (tool, rule, subject, action)
        outcome = upsert_advice(state.doc, item, ctx.stamp())
        outcomes.append(outcome)
        rejected_line = f"{label} {subject}: {advice_reason(state.doc, item)}"
        _say(rejected_line if outcome == "rejected" else said)
    close_advice(state.doc, tool, rule, subjects)
    proposed, rejected, new = count_advice(outcomes)
    _say(f"advice: {proposed} proposed, {rejected} rejected, {new} new")


def _block_matching(ctx: "Ctx") -> int:
    """Block every ready card carrying a touches tag on one card; a dry run unless `--write`.

    ⚑ DRY RUN FIRST (mtools:W947): without `--write` nothing is saved and the lines say WOULD
    BLOCK. Cards that stay (already blocked, or working) are listed as KEPT with their reason.

    Returns:
        EXIT_OK.

    Raises:
        RefusedError: when `--on` is missing, or the plan refuses (see `bulkblock.plan`).

    """
    tag = ctx.get("block_matching") or ""
    target = ctx.get("on")
    if target is None:
        msg = "--block-matching needs --on SYMBOL, the card the matches wait on"
        raise RefusedError(msg)
    write = bool(ctx.opts.get("write"))

    def edit(state: State) -> int:
        found = bulkblock.plan(state, tag, target)
        verb = "BLOCKED" if write else "WOULD BLOCK"
        planned = [
            (sym, f"block {sym} on {target}", f"{verb} {sym} on {target}") for sym in found.moved
        ]
        _advise(ctx, state, ("block-matching", f"touches:{tag}"), planned)
        for sym, why in found.kept:
            _say(f"KEPT {sym} ({why})")
        if write:
            bulkblock.apply(state, found, target)
        return EXIT_OK

    return _mutate(ctx, edit)


def _freeze(ctx: "Ctx") -> int:
    """Block every ready or working card but the ask on the ask; a dry run unless `--write`.

    ⚑ DRY RUN FIRST, as `--block-matching`: without `--write` nothing is saved and the lines say
    WOULD BLOCK. A card already blocked is LISTED and keeps its blocker (mtools:W1397).

    Returns:
        EXIT_OK.

    """
    ask = ctx.get("freeze") or ""
    write = bool(ctx.opts.get("write"))

    def edit(state: State) -> int:
        found = bulkblock.freeze_plan(state, ask)
        verb = "BLOCKED" if write else "WOULD BLOCK"
        planned = [(sym, f"block {sym} on {ask}", f"{verb} {sym} on {ask}") for sym in found.moved]
        _advise(ctx, state, ("freeze", ask), planned)
        if ctx.opts.get("verbose"):
            for sym, why in found.kept:
                _say(f"KEPT {sym} ({why})")
        else:
            _say(f"KEPT {len(found.kept)} (already blocked; --verbose lists them)")
        if write:
            bulkblock.apply(state, found, ask)
        return EXIT_OK

    return _mutate(ctx, edit)


def _block_behind_open(ctx: "Ctx") -> int:
    """Block each ready card behind the open cards that enable it; a dry run unless `--write`.

    ⚑ DRY RUN FIRST, as `--block-matching`: without `--write` nothing is saved and the lines say
    WOULD BLOCK. A working card is LISTED with its enablers and left; a mutual pair is named and
    left, never deadlocked (mtools:W1131, nemik:W476).

    Returns:
        EXIT_OK.

    """
    write = bool(ctx.opts.get("write"))

    def edit(state: State) -> int:
        found = behindopen.plan(state)
        verb = "BLOCKED" if write else "WOULD BLOCK"
        planned = [
            (sym, f"block {sym} on {', '.join(behind)}", f"{verb} {sym} on {', '.join(behind)}")
            for sym, behind in found.moved
        ]
        _advise(ctx, state, ("block-behind-open", "behind-open"), planned)
        for sym, behind in found.working:
            _say(f"KEPT {sym} (working, behind {', '.join(behind)})")
        for sym, other in found.mutual:
            _say(f"KEPT {sym} (on an enabling cycle, through {other})")
        if write:
            behindopen.apply(state, found)
        return EXIT_OK

    return _mutate(ctx, edit)


def _close_umbrellas(ctx: "Ctx") -> int:
    """Mark done each open card whose local children are all done; a dry run unless `--write`.

    ⚑ DRY RUN FIRST, as `--block-behind-open`: without `--write` nothing is saved and the lines
    say WOULD CLOSE. A card that is not closed although its children are done is LISTED as KEPT
    with its reason (mtools:W1139, nemik:W488).

    Returns:
        EXIT_OK.

    """
    write = bool(ctx.opts.get("write"))

    def edit(state: State) -> int:
        found = close_plan(state)
        verb = "CLOSED" if write else "WOULD CLOSE"
        for sym, kids in found.closed:
            _say(f"{verb} {sym} (all children done: {', '.join(kids)})")
        for sym, why in found.kept:
            _say(f"KEPT {sym} ({why})")
        if write:
            close_apply(state, found, ctx.stamp())
        return EXIT_OK

    return _mutate(ctx, edit)


def _triage(ctx: "Ctx") -> int:
    """Propose the repairs that shrink the ready frontier; a dry run unless `--write` (W1332).

    ⚑ DRY RUN FIRST, as `--block-behind-open`, and through the same advice store so a host can
    apply a queue's proposals from a record. A card stored ready that still waits, an umbrella
    edge pointing at the child it minted, and a duplicate are proposed; nothing is closed as done
    and no dependency is invented (see `triage`).

    Returns:
        EXIT_OK.

    """
    write = bool(ctx.opts.get("write"))

    def edit(state: State) -> int:
        found = triage.plan(state)
        planned = [
            (
                item.symbol,
                f"{item.kind} {item.symbol}",
                item.said.replace("WOULD ", "DONE " if write else "WOULD "),
            )
            for item in found
        ]
        _advise(ctx, state, ("triage", "frontier"), planned)
        if write:
            triage.apply(state, found, ctx.stamp())
        return EXIT_OK

    return _mutate(ctx, edit)


def _lift(ctx: "Ctx") -> int:
    """Lift the one held row a signed operator ruling names (W1277, W1194).

    ⚑ THE SIGNATURE IS THE ONLY AUTHORITY: `--lift JWS --jwk FILE` verifies the compact JWS against
    the operator's public key through the pinned opa and changes exactly the row its signed payload
    names, and only when that row is held on the operator (see `lift`). Anything else, including a
    missing or unreadable key, an absent opa, a bad signature or a row that is not held, is refused
    with nothing saved; an opa that cannot run is a refusal, never a pass.

    Returns:
        EXIT_OK after the lift.

    Raises:
        RefusedError: on a missing or non-regular key file, no usable opa, or any refusal of
            `lift`.

    """
    named = ctx.get("jwk")
    if named is None:
        msg = "--lift needs --jwk FILE, the operator's public key"
        raise RefusedError(msg)
    key = Path(named)
    if key.is_symlink() or not key.is_file():
        msg = f"--jwk {named} is not a regular file"
        raise RefusedError(msg)
    jwk = key.read_text(encoding="utf-8")
    try:
        opa = opa_eval.resolve()
    except opa_eval.OpaUnavailableError as exc:
        raise RefusedError(str(exc)) from exc

    def verify(token: str, public: str) -> bool:
        try:
            return opa_eval.verify_eddsa(token, public, opa)
        except opa_eval.OpaUnavailableError as exc:
            raise RefusedError(str(exc)) from exc

    def edit(state: State) -> int:
        sym = LIFT_ROW(state, ctx.get("lift") or "", jwk, verify, ctx.stamp())
        _say(f"LIFTED {sym}")
        return EXIT_OK

    return _mutate(ctx, edit)


def _pinned(upd: ops.Update, root: Path, path: str | None) -> ops.Update:
    """Give an update the (path, sha256) of the file `--attach` names, resolved under the root.

    Returns:
        the update unchanged when nothing is attached; otherwise a copy carrying the pin.

    """
    return upd if path is None else replace(upd, attachment=attach.resolve(root, path))


_SUMMARY = "summary"
_FLAGS = (
    "hash",
    "render",
    "payload",
    "queue",
    "check",
    "check_evidence",
    "selftest",
    "bump_blocked",
    "prune_landed",
    "block_behind_open",
    "close_umbrellas",
    "triage",
    "inbound",
    "preamble_clear",
    "outcomes_clear",
    "init",
    "overlaps",
    "ics",
    "unlinked",
    "delivered",
    "close_gate",
)
_VALUED = (
    "verify",
    "lock",
    "unlock",
    "tick_open",
    "tick_close",
    "armed",
    "update",
    "add",
    "drop",
    "ledger",
    "show",
    "preamble_set",
    "standing_set",
    "weights_from",
    "vectors_from",
    "repair_counter",
    "scan_literal",
    "commit_message",
    "embargo",
    "lift_embargo",
    "reject_advice",
    "outcomes_set",
    "certify",
    "mint_residue",
    "skip",
    "gate_red",
    "gate_green",
    "gate_note",
    "block_matching",
    "freeze",
    "update_many",
    "lift",
)
_LEDGER_ARGS = ("SYMBOL", "OUTCOME", "MECHANISM", "NOTE")
# ⚑⚑ `-`, NOT A BARE `--`: NO_SYMBOL (model.py) is literally "--", and argparse consumes a bare
# `--` as its own end-of-options marker before nargs ever sees it as a value — "expected 4
# arguments" (nemik AND rosettapkg, 2026-09-26, both hit this live). `-` is not argparse-special
# and is translated to NO_SYMBOL in `_ledger_mode`, so the ledger's own format never changes.
_QUEUE_SYMBOL = "-"
_DEFAULT_KIND = "tick"

# ⚑⚑ EACH MODE NAMES THE FIELD FLAGS IT READS, AND ANY OTHER IS REFUSED (nemik, 2026-09-25).
# `--update W49 --enables W46 W35` exited 0 and printed "W49 updated" while never reading enables:
# a flag accepted in silence is a write the caller believes happened. A mode absent here reads
# no field flag at all.
_FIELDS = (
    "status",
    "blocked_on",
    "blocked_kind",
    "next",
    "title",
    "evidence_append",
    "evidence_redact",
    "replacement",
    "ticks_blocked",
    "enables",
    "add_enables",
    "attach",
    "touches",
    "caused_by",
    "exclude",
    "kind",
    "evidence",
    "blocked_by",
    "reason",
    "promote",
    "weight",
    "witness",
    "witness_lang",
    "jwk",
    "vector",
    "vector_source",
    "dtstart",
    "due",
    "alarm",
    "rrule",
    "exdate",
    "complete_occurrence",
    "reopen_occurrence",
    "unchanged",
    "rejected",
    "consumers",
    "reference_arm",
    "command",
    "population",
    "deferred",
    "facts",
    "admit",
    "gate",
    "root",
    "all",
    "on",
    "write",
    "verbose",
)
_APPLIES: dict[str, frozenset[str]] = {
    "update": frozenset(
        {
            "status",
            "blocked_on",
            "blocked_kind",
            "next",
            "title",
            "evidence_append",
            "evidence_redact",
            "replacement",
            "ticks_blocked",
            "enables",
            "add_enables",
            "attach",
            "weight",
            "touches",
            "witness",
            "witness_lang",
            "vector",
            "vector_source",
            "caused_by",
            "dtstart",
            "due",
            "alarm",
            "rrule",
            "exdate",
            "complete_occurrence",
            "reopen_occurrence",
            "unchanged",
            "rejected",
            "consumers",
            "reference_arm",
            "command",
            "population",
            "deferred",
            "admit",
            "root",
        }
    ),
    "add": frozenset(
        {"next", "enables", "touches", "caused_by", "witness", "witness_lang", "admit", "root"}
    ),
    "drop": frozenset({"admit", "gate", "reference_arm", "root", "on", "write"}),
    "bump_blocked": frozenset({"exclude", "verbose"}),
    "block_matching": frozenset({"on", "write"}),
    "freeze": frozenset({"write", "verbose"}),
    # ⚑ THE FIELDS OF `--update` EXCEPT `status` (a status change takes a lease, once per card) and
    # `attach` (one file pinned to many cards is a different act), plus `--write`.
    "update_many": frozenset(
        {
            "blocked_on",
            "blocked_kind",
            "next",
            "title",
            "evidence_append",
            "ticks_blocked",
            "enables",
            "add_enables",
            "weight",
            "touches",
            "witness",
            "witness_lang",
            "vector",
            "vector_source",
            "caused_by",
            "write",
            "exclude",
        }
    ),
    "prune_landed": frozenset({"root"}),
    "block_behind_open": frozenset({"write"}),
    "close_umbrellas": frozenset({"write"}),
    "triage": frozenset({"write"}),
    "inbound": frozenset({"root", "all"}),
    "tick_open": frozenset({"root", "exclude", "verbose"}),
    "tick_close": frozenset({"kind", "evidence", "blocked_by", "reason", "promote"}),
    "close_gate": frozenset({"blocked_by", "reason"}),
    "lift": frozenset({"jwk"}),
    "payload": frozenset({"root"}),
    "ledger": frozenset({"kind", "evidence"}),
    "certify": frozenset({"root", "facts"}),
    "mint_residue": frozenset({"root"}),
    "gate_red": frozenset({"next", "blocked_on", "exclude"}),
}


def stray_flags(mode: str, opts: dict[str, object]) -> list[str]:
    """Name the field flags given that `mode` does not read.

    Returns:
        each such flag, spelled as typed (`--enables`).

    """
    applies = _APPLIES.get(mode, frozenset())
    return [
        "--" + f.replace("_", "-").replace("exclude", "except")
        for f in _FIELDS
        if opts.get(f) is not None and f not in applies
    ]


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


def _add_run_fields(ap: argparse.ArgumentParser) -> None:
    """Add the flags that shape one run: `--except`, `--root` and the ledger columns.

    ⚑ SPLIT OUT OF `_parser` (W538): that function sits at ruff's 50-statement limit, and the
    fix for a parser that outgrew its budget is another function, never a waiver.
    """
    ap.add_argument("--except", dest="exclude", nargs="+", metavar="SYMBOL")
    ap.add_argument(
        "--root",
        metavar="PATH",
        help="--prune-landed, --inbound, --payload: the directory holding the repos "
        "(default: ~/github)",
    )
    ap.add_argument(
        "--all",
        action="store_true",
        default=None,
        help="--inbound: also print the CLAIMED rows (default: only the UNCLAIMED ones)",
    )
    ap.add_argument(
        "--on",
        "--onto",
        dest="on",
        metavar="SYMBOL",
        help="--block-matching: the card the matches wait on; --drop: the survivor to repoint to",
    )
    ap.add_argument(
        "--write",
        action="store_true",
        default=None,
        help="--block-matching: apply the block (default: a dry run that saves nothing)",
    )
    ap.add_argument(
        "--verbose",
        action="store_true",
        default=None,
        help="--bump-blocked: one row per blocked card (default: counts and external parties)",
    )
    ap.add_argument("--kind", help="the ledger line's kind column (default: tick)")
    ap.add_argument("--evidence", metavar="TEXT", help="the ledger line's evidence column")
    ap.add_argument(
        "--blocked-by",
        metavar="SYMBOL",
        help="W1203: --tick-close with ready cards left: the card that is the real block",
    )
    ap.add_argument(
        "--reason",
        metavar="TEXT",
        help="W1203: --tick-close with ready cards left: why, citing a card of this queue",
    )
    ap.add_argument(
        "--promote",
        metavar="SYMBOL",
        help="W1245: --tick-close: set this ready card working, refused while another is",
    )
    _add_realizable_fields(ap)
    _add_signoff_fields(ap)


def _add_signoff_fields(ap: argparse.ArgumentParser) -> None:
    """Add the flags that declare a witness's language and name the operator's public key."""
    ap.add_argument(
        "--witness-lang",
        metavar="LANG",
        help="--add/--update: the witness's language, declared: rego or promql (W1260)",
    )
    ap.add_argument(
        "--jwk",
        metavar="FILE",
        help="W1277: --lift: the operator's public key as a JWK file (OKP, Ed25519)",
    )


def _add_realizable_fields(ap: argparse.ArgumentParser) -> None:
    """Add the flags for the fields the realizability policy reads (W849).

    ⚑ FORM IS CHECKED IN `realizable`, NEVER HERE: these only collect the words.
    """
    for name in ("reference-arm", "command"):
        ap.add_argument(
            f"--{name}", metavar="TEXT", help=f"--update: the realizability {name}; '' clears"
        )
    ap.add_argument(
        "--population",
        nargs="*",
        metavar="SOURCE_OR_BOUND",
        help="--update: SOURCE [BOUND], a named finite source and its size or 'unbounded'; "
        "bare clears",
    )
    ap.add_argument(
        "--deferred",
        nargs="*",
        metavar="ENTRY",
        help="--update: the whole list of gate|reference_arm|what|closes_by[|closes_ref]; "
        "bare clears. There is no waiver field.",
    )
    ap.add_argument(
        "--admit",
        action="store_true",
        default=None,
        help="--add/--update/--drop: judge the transition through the realizability policy "
        "after saving, print its coordinate and append a mark; a drop must also give "
        "--gate and --reference-arm",
    )
    ap.add_argument(
        "--gate",
        choices=GATES,
        help="--drop with --admit: the gate the waypoint died at",
    )
    ap.add_argument(
        "--facts",
        metavar="FILE",
        help="--certify: a JSON object {name: {value, as_of, gate, waypoints} | {unreadable: "
        "true, gate, waypoints}}; read, never run",
    )


def _parser() -> argparse.ArgumentParser:
    """Build the argument parser: one optional mode, and the typed fields modes read.

    Returns:
        the parser.

    """
    ap = argparse.ArgumentParser(
        prog="mikemol-paths-forward",
        allow_abbrev=False,
        description=(__doc__ or "").splitlines()[0],
    )
    ap.add_argument("--state", metavar="PATH", help="the state file (required; no default)")
    mode = ap.add_mutually_exclusive_group()
    for flag in _FLAGS:
        mode.add_argument(f"--{flag.replace('_', '-')}", action="store_true")
    # ⚑ ONE TABLE FOR THE ONE-VALUE MODES: `_parser` sits at ruff's 50-statement limit (W538), and
    # a new mode (W850's --certify) is room made here, never a waiver.
    for flag, metavar, text_help in (
        ("--verify", "HASH", "compare a payload's state_hash"),
        ("--lock", "HOLDER", "take the tick lock (exit 3 if held)"),
        ("--unlock", "HOLDER", "release the tick lock"),
        (
            "--tick-open",
            "HOLDER",
            (
                "W1078: take the lock as HOLDER, then bump-blocked, inbound and check, and print "
                "the close command with the same HOLDER"
            ),
        ),
        ("--armed", "JOB_ID", "record job_id and heartbeat"),
        ("--update", "SYMBOL", "set typed fields on a waypoint"),
        ("--add", "TITLE", "mint the next W<n> as ready"),
        (
            "--block-matching",
            "TAG",
            "W947: block every ready card touching TAG on --on SYMBOL; a dry run without --write",
        ),
        (
            "--freeze",
            "SYMBOL",
            (
                "W1397: block every ready or working card but SYMBOL on SYMBOL (the operator's "
                "unfreeze ask); blocked cards keep their blocker; a dry run without --write"
            ),
        ),
        (
            "--gate-red",
            "REASON",
            (
                "W870: this repo's commit gate is red: mint or reuse the card, block the open "
                "ledger on it; needs --next STEP, optional --blocked-on OPERATOR_ASK, --except "
                "REPAIRS"
            ),
        ),
        (
            "--gate-green",
            "EVIDENCE",
            "W870: the gate is green: mark the card done and lift what waited only on it",
        ),
        (
            "--gate-note",
            "EVIDENCE",
            "W830: append evidence to the open gate card; never mints one, no-op when none is open",
        ),
    ):
        mode.add_argument(flag, metavar=metavar, help=text_help)
    mode.add_argument(
        "--update-many",
        nargs="+",
        metavar="SYMBOL_OR_SELECTOR",
        help="W974: the --update field flags applied to many waypoints, all or none; operands "
        "are symbols, `unscored` or `open` (every card not done; --except SYMBOL[=REASON] skips "
        "cards and prints each reason); a dry run without --write",
    )
    mode.add_argument(
        "--certify",
        nargs="+",
        metavar="SYMBOL",
        help="W850: each waypoint's realizability verdict {ref, level, reference_arm, residue}, "
        "one JSON line each, judged by the pinned opa; reads, never writes",
    )
    # ⚑ ONE TABLE FOR THE FIXED-ARITY MODES, for the same reason as the one-value table above:
    # `--tick-close` (W1079) is room made here, never a waiver.
    for flag, names, text_help in (
        ("--drop", ("SYMBOL", "REASON"), "move to residue"),
        (
            "--skip",
            ("SYMBOL", "REASON"),
            "W847: record a symbol the counter issued that no waypoint or residue holds",
        ),
        (
            "--mint-residue",
            ("SYMBOL", "GATE"),
            (
                "W853: mint one claimable card from SYMBOL's residue at GATE, caused by SYMBOL; "
                "a rerun finds the card and mints nothing"
            ),
        ),
        (
            "--tick-close",
            ("HOLDER", "SYMBOL", "OUTCOME", "MECHANISM", "NOTE"),
            "W1079: the --ledger line, then --render, --check and --unlock HOLDER, in one verb",
        ),
    ):
        mode.add_argument(flag, nargs=len(names), metavar=names, help=text_help)
    mode.add_argument(
        "--embargo",
        nargs=2,
        metavar=("PATH", "REASON"),
        help="W511: forbid edits to a project-relative PATH while a freeze holds (rule 6)",
    )
    mode.add_argument("--lift-embargo", metavar="PATH", help="W511: remove PATH's embargo")
    mode.add_argument(
        "--reject-advice",
        nargs=3,
        metavar=("TOOL", "RULE", "REASON"),
        help=(
            "W1243: reject every open piece of TOOL's recorded dry-run advice under RULE; "
            "the next dry run prints REASON instead of re-proposing it"
        ),
    )
    mode.add_argument(
        "--outcomes-set",
        nargs=2,
        metavar=("ADVANCE_CSV", "OTHER_CSV"),
        help="W533: declare the OUTCOME words --ledger accepts on tick/interrupt lines",
    )
    mode.add_argument(
        "--ledger",
        nargs=len(_LEDGER_ARGS),
        metavar=_LEDGER_ARGS,
        help=f"SYMBOL is a waypoint, or {_QUEUE_SYMBOL!r} for a queue-level line (not a bare --,"
        " which argparse consumes as end-of-options)",
    )
    mode.add_argument(
        "--show", nargs="+", metavar="SYMBOL", help="what is W<n>; several symbols print in order"
    )
    mode.add_argument(
        "--lift",
        metavar="JWS",
        help="W1277: lift the one held row a signed operator ruling names; needs --jwk FILE",
    )
    mode.add_argument(
        "--commit-message",
        metavar="SYMBOL",
        help="print a draft commit message for a live waypoint (W493); writes nothing",
    )
    mode.add_argument(
        "--scan-literal",
        metavar="PATTERN",
        help="where a literal still appears: waypoints, residue, ledger, mirror (exit 1 on a hit)",
    )
    mode.add_argument("--preamble-set", metavar="FILE", help="store FILE's lines as preamble")
    mode.add_argument(
        "--standing-set",
        metavar="FILE",
        help="W862: store FILE's non-blank lines as the whole standing list, one rule per line",
    )
    mode.add_argument(
        "--weights-from",
        metavar="FILE",
        help="store [{symbol, weight}] from a JSON file, all or nothing",
    )
    mode.add_argument(
        "--vectors-from",
        metavar="FILE",
        help="store [{symbol, vector, vector_source}] from a JSON file, all or nothing",
    )
    mode.add_argument(
        "--repair-counter",
        metavar="REASON",
        help="raise a counter lagging a claimed symbol up to it (never lower); ledgered",
    )
    ap.add_argument("--status", choices=STATUSES)
    ap.add_argument("--blocked-on", action="extend", nargs="*", metavar="WHO")
    ap.add_argument("--blocked-kind", choices=BLOCKED_KINDS)
    ap.add_argument("--next", metavar="TEXT")
    ap.add_argument("--title", metavar="TEXT", help="--update: replace a stale one-line title")
    ap.add_argument("--evidence-append", metavar="TEXT")
    ap.add_argument(
        "--evidence-redact",
        metavar="PATTERN",
        help="--update: replace a literal in evidence, next and title; ledgered by hash",
    )
    ap.add_argument(
        "--replacement", metavar="TEXT", help=f"--evidence-redact's (default {REDACTED})"
    )
    ap.add_argument("--ticks-blocked", type=int, metavar="N")
    ap.add_argument(
        "--weight", type=int, metavar="N", help="--update: store a priority; higher sorts first"
    )
    # ⚑ `nargs="*"`, LIKE `--blocked-on` (nemik AND mtools, 2026-09-26): the bare flag now means
    # CLEAR. `ctx.many` already returns `None` only when the flag is absent, and `Update.enables` /
    # `_set_given` already treat `()` as "set to empty"; `+` was the one thing blocking it.
    ap.add_argument("--enables", action="extend", nargs="*", metavar="SYMBOL")
    ap.add_argument(
        "--add-enables",
        action="extend",
        nargs="+",
        metavar="SYMBOL",
        help="--update: append to the edges already there (--enables sets the whole list)",
    )
    ap.add_argument(
        "--attach",
        metavar="PATH",
        help="--update: pin a repo-relative file to the waypoint by its sha256 (nemik:W276)",
    )
    # ⚑ A REPEATED LIST FLAG ACCUMULATES (W995): argparse's default `store` kept only the LAST
    # `--touches`, so `--touches hooks --touches locks` stored [locks] with no word said and the
    # work-claims hook claimed one of two tags. `extend` appends each occurrence; a bare `--enables`
    # or `--blocked-on` still clears, as `extend` of nothing onto an absent flag yields `[]`.
    ap.add_argument("--touches", action="extend", nargs="+", metavar="TAG")
    ap.add_argument(
        "--witness", metavar="QUERY", help="--add/--update: a one-line query, stored unread"
    )
    ap.add_argument(
        "--vector", metavar="WV", help="--update: a WV:1 vector (W248); with --vector-source"
    )
    ap.add_argument(
        "--vector-source",
        choices=("default", "signal", "agent"),
        help="--update: who set the vector; required with --vector",
    )
    ap.add_argument(
        "--caused-by",
        metavar="REF",
        help="--add/--update: letter path, peer, operator, W<n>; '' clears on --update",
    )
    ap.add_argument(
        "--dtstart",
        metavar="RFC5545",
        help="--update: 20261001, 20261001T203000Z or TZID=Zone/Name:20261001T163000; '' clears",
    )
    ap.add_argument(
        "--due",
        metavar="RFC5545",
        help="--update: as --dtstart; a floating time (no Z, no TZID) is refused; '' clears",
    )
    ap.add_argument(
        "--alarm",
        action="extend",
        nargs="*",
        metavar="TRIGGER",
        help="--update: the whole VALARM list, e.g. -PT15M RELATED=END:-PT2H "
        "VALUE=DATE-TIME:20261001T200000Z; bare --alarm clears",
    )
    ap.add_argument(
        "--rrule",
        metavar="RRULE",
        help="--update: an RFC 5545 RRULE, e.g. FREQ=MONTHLY;BYMONTHDAY=1 (quote it); needs a "
        "DTSTART; '' clears",
    )
    ap.add_argument(
        "--exdate",
        action="extend",
        nargs="*",
        metavar="RFC5545",
        help="--update: the whole EXDATE list, each as --dtstart; needs an RRULE; bare clears",
    )
    ap.add_argument(
        "--complete-occurrence",
        metavar="RECURRENCE-ID",
        help="--update: stamp one occurrence of the RRULE COMPLETED (same form as DTSTART)",
    )
    ap.add_argument(
        "--reopen-occurrence",
        metavar="RECURRENCE-ID",
        help="--update: remove one completed occurrence's stamp",
    )
    for l2 in ("unchanged", "rejected", "consumers"):
        ap.add_argument(
            f"--{l2}", metavar="TEXT", help=f"--update: append one entry to the {l2} list"
        )
    _add_run_fields(ap)
    return ap


def _ledger(ctx: Ctx, entry: Entry) -> None:
    """Append one structured line to the ledger beside the state file."""
    append(store.sibling(ctx.path, store.LEDGER), line(entry, ctx.stamp()))


def _atomize_line(ctx: Ctx, state: State) -> str | None:
    """Read the ledger beside the state file and name a top waypoint that is owed a split.

    ⚑ AN ABSENT LEDGER IS AN EMPTY ONE: a fresh `--init` has advanced nothing, so nothing is owed.

    Returns:
        the `ATOMIZE W<n> ...` line, or None.

    """
    path = store.sibling(ctx.path, store.LEDGER)
    # ⚑ A queue that declared `ledger_outcomes` (W533) counts ONLY its advance set (W539); one that
    # did not is counted by the deny-list, exactly as before.
    sets = outcomes.declared(state)
    counted = frozenset(sets[0]) if sets else None
    return atomize(state.waypoints, read(path) if path.is_file() else [], counted)


_UNLOCKED = "(unlocked)"
_NO_SHA = "unknown"
_WORKING = "working"


def _head_sha(root: Path) -> str:
    """Read HEAD's commit from `.git` files, without running git.

    ⚑ NO SUBPROCESS: the CLI stays a file reader. A worktree (`.git` is a file), a detached or
    packed ref the reader cannot resolve, and a missing repo all read as `unknown`, which renew()
    then reports as a moved tree rather than hiding.

    Returns:
        the 40-hex sha, or `unknown`.

    """
    git = root / ".git"
    head = git / "HEAD"
    if not head.is_file():
        return _NO_SHA
    ref = head.read_text(encoding="utf-8").strip()
    if not ref.startswith("ref: "):
        return ref or _NO_SHA
    name = ref.removeprefix("ref: ")
    loose = git / name
    if loose.is_file():
        return loose.read_text(encoding="utf-8").strip() or _NO_SHA
    packed = git / "packed-refs"
    if packed.is_file():
        for row in packed.read_text(encoding="utf-8").splitlines():
            sha, _, refname = row.partition(" ")
            if refname == name:
                return sha
    return _NO_SHA


def _claimant(ctx: Ctx, state: State) -> lease.Claimant:
    """Name who is taking a lease: the lock's holder, the project's HEAD, and now.

    Returns:
        the Claimant.

    """
    held = lock.current(state)
    root = attach.project_path(text(state.doc, "project_root") or str(ctx.path.parent.parent))
    return lease.Claimant(held[0] if held else _UNLOCKED, _head_sha(root), ctx.now)


def _lease_for_status(ctx: Ctx, state: State, sym: str, status: str | None) -> int:
    """Take leases when a waypoint becomes `working`; release them when it becomes anything else.

    Returns:
        EXIT_OK, or EXIT_REFUSED naming each conflict (the caller then saves nothing).

    """
    if status is None:
        return EXIT_OK
    if status != _WORKING:
        dropped = lease.release(state, sym)
        if dropped:
            _say(f"{sym} released {dropped} lease(s)")
        return EXIT_OK
    touches = ops.find(state, sym).get("touches")
    tags = [str(t) for t in cast("list[object]", touches)] if isinstance(touches, list) else []
    conflicts = lease.take(state, sym, tags, _claimant(ctx, state))
    for c in conflicts:
        _warn(f"REFUSED: {sym} cannot lease {c.tag}: {c.waypoint} holds it (holder={c.holder})")
    return EXIT_REFUSED if conflicts else EXIT_OK


def _lapsed_lines(ctx: Ctx, state: State) -> None:
    """Print one grep-stable `LAPSED` line per lease past its expiry (W119 point 6); advisory."""
    for x in lease.lapsed(state, ctx.now):
        _say(
            f"LAPSED {text(x, 'waypoint')} {text(x, 'tag')} "
            f"holder={text(x, 'holder')} base={text(x, 'base_sha')}"
        )


def _mutate(
    ctx: Ctx,
    edit: Callable[[State], int],
    after: Callable[[State], None] | None = None,
) -> int:
    """Run one read-modify-write under the flock, saving only when the edit succeeded.

    ⚑ `after` RUNS ONLY ONCE THE STATE IS SAVED, still under the flock (W851): a mark is never
    written for a transition the queue does not hold.

    Returns:
        the edit's exit code.

    """
    with store.exclusive(ctx.path):
        state = store.load(ctx.path)
        code = edit(state)
        if code == EXIT_OK:
            store.save(ctx.path, state)
            if after is not None:
                after(state)
    return code


def _admit_after(ctx: Ctx, op: str, sym: str) -> Callable[[State], None] | None:
    """Build the post-save judging step for `--admit`, or None when it was not asked for.

    Returns:
        a callable that judges `sym` in the saved state and says its coordinate.

    """
    if not ctx.opts.get("admit"):
        return None

    def after(state: State) -> None:
        _say(admission.admit(state, op, sym, admission.Site(ctx.path, _root(ctx), ctx.stamp())))

    return after


def _summary(ctx: Ctx) -> int:
    """Print the cheap one-line summary.

    Returns:
        EXIT_OK.

    """
    state = store.load(ctx.path)
    held = lock.current(state)
    _say(
        f"counter={state.counter} state_hash={v2(state.waypoints)} "
        f"live={len(state.waypoints)} residue={len(state.residue)} "
        f"lock={held[0] if held else '-'}"
    )
    return EXIT_OK


def _hash(ctx: Ctx) -> int:
    """Print the v2 hash.

    Returns:
        EXIT_OK.

    """
    _say(v2(store.load(ctx.path).waypoints))
    return EXIT_OK


def _overlaps(ctx: Ctx) -> int:
    """Print one OVERLAP line per tag two or more live waypoints declare; advisory.

    Returns:
        EXIT_OK, with or without lines.

    """
    for found in overlaps(store.load(ctx.path).waypoints):
        _say(found)
    return EXIT_OK


def _unlinked(ctx: Ctx) -> int:
    """Print `n of m live waypoints linked`, then one UNLINKED line per isolated waypoint.

    Returns:
        EXIT_OK (unlinked waypoints are a reading, not a failure), or EXIT_REFUSED when no
        waypoint is live.

    """
    lines = unlinked_report(store.load(ctx.path).waypoints)
    if lines is None:
        _warn("REFUSED: no live waypoint, so there is no linkage to report")
        return EXIT_REFUSED
    for found in lines:
        _say(found)
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
        state = store.load(ctx.path)
        owed = _atomize_line(ctx, state)
        found = inbound.census(_root(ctx), inbound.repo_name(ctx.path), state)
        lines = inbound.payload_lines(found)
        _say(build(Request(state, ctx.path, ctx.stamp(), atomize=owed, inbound=lines)))
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


def _ics(ctx: Ctx) -> int:
    """Print the queue as an iCalendar file, one VTODO per waypoint (W313).

    ⚑ READ-ONLY: nothing is written, and no lock is taken. The repo in each UID is the state's
    project_root directory name, the name nemik cites it by; the host makes the UID unique.

    Returns:
        EXIT_OK.

    """
    state = store.load(ctx.path)
    repo = Path(text(state.doc, "project_root") or str(ctx.path.parent.parent)).name
    stamp = ctx.stamp().replace("-", "").replace(":", "")
    sys.stdout.write(vtodo.calendar(state, repo=repo, host=socket.gethostname(), stamp=stamp))
    return EXIT_OK


def _report(state: State, findings: list[str], owed: str | None = None) -> int:
    """Print a check's findings, then the ATOMIZE line when one is owed.

    ⚑ ATOMIZE IS ADVICE, NOT A FINDING: a coarse top waypoint is a fact about the WORK, not a
    defect in the file, so it never changes the exit code. It prints last, on its own line, so
    `grep ^ATOMIZE` finds it whatever the check said.

    Returns:
        EXIT_OK when there are no findings, else EXIT_REFUSED.

    """
    if not findings:
        _say(
            f"check: OK — {state.counter} of {state.counter} symbols resolve; "
            f"state_hash={v2(state.waypoints)}"
        )
        # ⚑ A CENSUS, NOT A FINDING (W257): unscored waypoints never change the exit code;
        # the line is grep-stable so nemik and luthen can count them.
        _say(f"UNSCORED {unscored(state)}")
        if owed:
            _say(owed)
        return EXIT_OK
    _say(f"check: REFUSED — {len(findings)} finding(s):")
    for finding in findings:
        _say(f"    {finding}")
    if owed:
        _say(owed)
    return EXIT_REFUSED


def _check(ctx: Ctx) -> int:
    """Run the cheap check.

    Returns:
        see `_report`.

    """
    state = store.load(ctx.path)
    code = _report(state, check(state), _atomize_line(ctx, state))
    _lapsed_lines(ctx, state)
    return code


def _check_evidence(ctx: Ctx) -> int:
    """Run the check plus the opt-in evidence read.

    Returns:
        see `_report`.

    """
    state = store.load(ctx.path)
    code = _report(state, check(state) + evidence_findings(state), _atomize_line(ctx, state))
    _lapsed_lines(ctx, state)
    return code


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


_LAPSE_LEDGERED = "lapse_ledgered"


def _tend_leases(ctx: Ctx, state: State, holder: str) -> None:
    """Renew `holder`'s leases, then ledger each lapsed lease exactly once (W119 points 5-6).

    ⚑ NEVER A SILENT RELEASE: a lapsed lease stays in the file, so --check keeps printing its
    `LAPSED` line until its waypoint leaves `working`; the ledger line is written once, marked on
    the record, so a stuck lapse does not repeat every tick. A `MOVED` line names each renewed
    tag whose base commit is no longer HEAD: reported, never refused.
    """
    root = attach.project_path(text(state.doc, "project_root") or str(ctx.path.parent.parent))
    for tag in lease.renew(state, holder, _head_sha(root), ctx.now):
        _say(f"MOVED {tag}: base is not HEAD; re-read before writing")
    for x in lease.lapsed(state, ctx.now):
        if x.get(_LAPSE_LEDGERED) is True:
            continue
        note = f"lease on {text(x, 'tag')} held by {text(x, 'holder')} lapsed unrenewed"
        _ledger(ctx, Entry("lease", text(x, "waypoint"), "lapsed", NO_SYMBOL, note))
        x[_LAPSE_LEDGERED] = True


def _lock(ctx: Ctx) -> int:
    """Take the tick lock, ledgering a takeover.

    Returns:
        EXIT_OK, or EXIT_LOCKED when another holder has it.

    """

    def edit(state: State) -> int:
        result = lock.acquire(state, ctx.get("lock") or "", ctx.now, session.own())
        if result.outcome is lock.Outcome.HELD:
            _say(f"locked by {result.previous} ({result.age_s:.0f}s); skip this tick")
            return EXIT_LOCKED
        if result.outcome is lock.Outcome.TAKEOVER:
            note = (
                f"stale lock from {result.previous} ({result.age_s:.0f}s) taken by "
                f"{result.holder}; re-read evidence"
            )
            _ledger(ctx, Entry("lock", NO_SYMBOL, "takeover", NO_SYMBOL, note))
        _say(f"{result.outcome} by {result.holder}")
        _tend_leases(ctx, state, result.holder)
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


def _tick_open(ctx: Ctx) -> int:
    """Open a tick as HOLDER in one verb: take the lock, bump blocked, inbound, check (W1078).

    ⚑ ONE NAME FOR BEGIN AND END. A host kata took the lock as its own holder while the stop hook
    asked for `--unlock mtools-tick-opus`, and the two never matched. This takes the lock as the
    holder it is given, runs the other opening steps under that same context, and ENDS by printing
    the unlock command with the same holder, so the name is carried by the tool and not retyped.
    A held lock stops it before any other step runs (exit 3, as `--lock`).

    Returns:
        EXIT_OK, EXIT_LOCKED when another holder has the lock, or the first failing step's status.

    """
    holder = ctx.get("tick_open") or ""
    held = replace(ctx, opts={**ctx.opts, "lock": holder})
    code = _lock(held)
    if code != EXIT_OK:
        return code
    for step in (_bump_blocked, _inbound, _check):
        code = max(code, step(held))
    _say(f"tick open as {holder}; close: --ledger ..., --render, --check, --unlock {holder}")
    return code


def _tick_close(ctx: Ctx) -> int:
    """Close a tick in one verb: ledger line, prune landed blockers, render, check, unlock (W1079).

    ⚑ THE CHECK COMES AFTER THE PRUNE (W1112, gabion:W1079). A tick that completes a card other
    cards wait on closed with `check: REFUSED: Wn blocked on Wm, which is done`, because only the
    open pruned. The close now does the same idempotent prune first and prints what it freed.

    ⚑ THE UNLOCK IS NOT CONDITIONAL ON THE REST. A ledger line refused for an unlisted outcome, or
    a check that fails, still ends the tick, and a lock nobody releases makes the next tick wait
    it out; so the unlock runs last whatever the earlier steps did, and the first failure is the
    status.

    Returns:
        EXIT_OK, or the first failing step's status (a refused ledger line is EXIT_REFUSED).

    """
    holder, *entry = ctx.many("tick_close") or ("", "", "", "", "")
    # ⚑ W1203: A TICK IS A LOOP CYCLE, NOT A CARD. Read the queue before anything is written; with a
    # ready, unblocked card and no named block the close is REFUSED and the lock stays held.
    worked = entry[0] if entry else None
    when = (ctx.get("blocked_by"), ctx.get("reason"), worked)
    verdict = CLOSE_JUDGE(store.load(ctx.path), *when, store.sibling(ctx.path, store.LEDGER))
    for said in verdict.lines:
        _say(said)
    if verdict.refused:
        return EXIT_REFUSED
    if verdict.note:
        entry[-1] = f"{entry[-1]} [{verdict.note}]"
    closing = replace(ctx, opts={**ctx.opts, "ledger": tuple(entry), "unlock": holder})
    code = EXIT_OK
    try:
        code = _ledger_mode(closing)
    except ops.RefusedError as exc:
        _warn(f"not ledgered: {exc}")
        code = EXIT_REFUSED
    for step in (_promote, _prune_landed, _render, _check, _unlock):
        result = step(closing)
        code = code or result
    return code


def _promote(ctx: Ctx) -> int:
    """Set the card `--promote` names working, as part of the close (W1245, W1080).

    ⚑ ONE WORKING CARD: nemik warns on none and on two, so the close that frees the lock also names
    the next card. It is refused while another card is working (finish or mark that one first), and
    for a card that is not ready: promoting a blocked card would work what cannot be worked.

    Returns:
        EXIT_OK (also when `--promote` is not given), or EXIT_REFUSED.

    """
    sym = ctx.get("promote")
    if sym is None:
        return EXIT_OK

    def edit(state: State) -> int:
        busy = [
            text(w, "symbol")
            for w in state.waypoints
            if text(w, "status") == _WORKING and text(w, "symbol") != sym
        ]
        if busy:
            msg = f"--promote {sym}: {', '.join(busy)} is already working"
            raise RefusedError(msg)
        status = text(ops.find(state, sym), "status")
        if status not in {"ready", _WORKING}:
            msg = f"--promote {sym}: it is {status}, not ready"
            raise RefusedError(msg)
        ops.update(state, sym, ops.Update(status=_WORKING), ctx.stamp())
        _say(f"PROMOTED {sym} to working")
        return EXIT_OK

    try:
        return _mutate(ctx, edit)
    except RefusedError as exc:
        _warn(f"not promoted: {exc}")
        return EXIT_REFUSED


def _close_gate(ctx: Ctx) -> int:
    """Say whether a tick may close, without closing it (W1202).

    ⚑ THE READ HALF OF `--tick-close`, for a caller that closes the tick itself (the katas `tick
    end` writes its own note and flushes its own commits) and must still refuse while a ready,
    unblocked card exists. Same verdict, same lines, nothing written.

    Returns:
        EXIT_OK when the tick may close, EXIT_REFUSED when it may not.

    """
    when = (ctx.get("blocked_by"), ctx.get("reason"), None)
    verdict = CLOSE_JUDGE(store.load(ctx.path), *when, store.sibling(ctx.path, store.LEDGER))
    for said in verdict.lines:
        _say(said)
    return EXIT_REFUSED if verdict.refused else EXIT_OK


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


def _fields_of(ctx: Ctx) -> ops.Update:
    """Read the field flags of an `--update` or `--update-many` into one Update.

    Returns:
        the Update the flags describe.

    """
    return ops.Update(
        status=ctx.get("status"),
        blocked_on=ctx.many("blocked_on"),
        blocked_kind=ctx.get("blocked_kind"),
        next_step=ctx.get("next"),
        evidence_append=ctx.get("evidence_append"),
        ticks_blocked=ctx.number("ticks_blocked"),
        title=ctx.get("title"),
        enables=ctx.many("enables"),
        add_enables=ctx.many("add_enables"),
        weight=ctx.number("weight"),
        touches=ctx.many("touches"),
        witness=ctx.get("witness"),
        witness_lang=ctx.get("witness_lang"),
        vector=ctx.get("vector"),
        vector_source=ctx.get("vector_source"),
        caused_by=ctx.get("caused_by"),
        dtstart=ctx.get("dtstart"),
        due=ctx.get("due"),
        alarms=ctx.many("alarm"),
        rrule=ctx.get("rrule"),
        exdates=ctx.many("exdate"),
        complete_occurrence=ctx.get("complete_occurrence"),
        reopen_occurrence=ctx.get("reopen_occurrence"),
        unchanged=ctx.get("unchanged"),
        rejected=ctx.get("rejected"),
        consumers=ctx.get("consumers"),
        reference_arm=ctx.get("reference_arm"),
        command=ctx.get("command"),
        population=ctx.many("population"),
        deferred=ctx.many("deferred"),
    )


def _update_many(ctx: Ctx) -> int:
    """Apply one set of field flags to many waypoints, all or none; a dry run unless `--write`.

    ⚑ ALL OR NONE (mtools:W974, el-openglo:W484). Every update is applied to a copy of the queue
    first, so a refusal on the last symbol changes nothing and names it, and the dry run reports
    exactly what `--write` would do. Operands are symbols or the selector `unscored`.

    Returns:
        EXIT_OK.

    """
    write = bool(ctx.opts.get("write"))
    upd = _fields_of(ctx)

    skipped: dict[str, str] = {}
    for item in ctx.many("exclude") or ():
        name, _, reason = item.partition("=")
        skipped[name] = reason

    def plan(state: State) -> list[Planned]:
        chosen = bulkblock.select_symbols(state, list(ctx.many("update_many") or ()), skipped)
        for sym, reason in skipped.items():
            _say(f"EXCLUDED {sym}" + (f" ({reason})" if reason else ""))
        for sym in chosen:
            ops.update(state, sym, upd, ctx.stamp())
        verb = "UPDATED" if write else "WOULD UPDATE"
        return [(sym, f"update {sym}", f"{verb} {sym}") for sym in chosen]

    spec = ("update-many", "update-many")
    if write:

        def edit(state: State) -> int:
            _advise(ctx, state, spec, plan(state), skipped)
            return EXIT_OK

        return _mutate(ctx, edit)
    # ⚑ A DRY RUN APPLIES THE UPDATES TO A THROWAWAY LOAD, then records only the advice: the queue
    # it saves is a second load that has had no update applied to it.
    planned = plan(store.load(ctx.path))

    def record(state: State) -> int:
        _advise(ctx, state, spec, planned, skipped)
        return EXIT_OK

    return _mutate(ctx, record)


def _update(ctx: Ctx) -> int:
    """Set typed fields on a waypoint, or redact a literal from it.

    Returns:
        EXIT_OK.

    """
    if ctx.get("evidence_redact") is not None or ctx.get("replacement") is not None:
        return _redact(ctx)
    upd = _fields_of(ctx)

    def edit(state: State) -> int:
        sym = ctx.get("update") or ""
        root = attach.project_path(text(state.doc, "project_root") or str(ctx.path.parent.parent))
        pinned = _pinned(upd, root, ctx.get("attach"))
        ops.update(state, sym, pinned, ctx.stamp())
        code = _lease_for_status(ctx, state, sym, upd.status)
        if code == EXIT_OK and upd.status == "done":
            # ⚑ A DONE CARD LEAVES NO STALE BLOCKER (W1215): marking it done prunes it from its
            # dependents in the same write, so a reader between ticks never finds a card blocked
            # on one that has landed.
            for freed in ops.prune_done(state):
                _say(f"UNBLOCKED {freed} (every local blocker is done)")
        if code == EXIT_OK:
            _say(f"{sym} updated; state_hash={v2(state.waypoints)}")
        return code

    return _mutate(ctx, edit, _admit_after(ctx, "update", ctx.get("update") or ""))


def _redact(ctx: Ctx) -> int:
    """Replace a literal in one waypoint's free text, then ledger it by the pattern's hash.

    ⚑ A REDACTION IS ITS OWN WRITE: combined with other fields, a refusal of either would leave the
    caller unsure which half landed. ⚑ THE LEDGER LINE IS WRITTEN ONLY AFTER THE SAVE, so the
    ledger never records a redaction the state does not hold.

    Returns:
        EXIT_OK, or EXIT_REFUSED when combined with another field or given `--replacement` alone.

    """
    sym = ctx.get("update") or ""
    pattern = ctx.get("evidence_redact")
    if pattern is None:
        _warn("REFUSED: --replacement needs --evidence-redact PATTERN")
        return EXIT_REFUSED
    others = [f for f in _APPLIES["update"] - {"evidence_redact", "replacement"} if ctx.opts.get(f)]
    if others:
        _warn(f"REFUSED: --evidence-redact is its own write; drop {', '.join(sorted(others))}")
        return EXIT_REFUSED
    replacement = ctx.get("replacement")
    counted: list[int] = []

    def edit(state: State) -> int:
        counted.append(
            redact(ops.find(state, sym), pattern, REDACTED if replacement is None else replacement)
        )
        return EXIT_OK

    code = _mutate(ctx, edit)
    if code == EXIT_OK:
        note = f"{digest(pattern)} n={counted[0]}"
        _ledger(ctx, Entry("redact", sym, "redacted", NO_SYMBOL, note))
        _say(f"{sym} redacted {note}; run --render, then --scan-literal to confirm")
    return code


def _scan_literal(ctx: Ctx) -> int:
    """Report every place a literal still appears, never the literal itself.

    Returns:
        EXIT_OK when it appears nowhere, EXIT_FAILED on any hit, EXIT_REFUSED on an empty pattern.

    """
    pattern = ctx.get("scan_literal") or ""
    if not pattern:
        _warn("REFUSED: --scan-literal needs a non-empty pattern")
        return EXIT_REFUSED
    state = store.load(ctx.path)
    ledger_path = store.sibling(ctx.path, store.LEDGER)
    mirror_path = store.sibling(ctx.path, store.MIRROR)
    ledger_lines = (
        ledger_path.read_text(encoding="utf-8").splitlines() if ledger_path.is_file() else []
    )
    hits = scan([*state.waypoints, *state.residue], ledger_lines, pattern)
    if mirror_path.is_file():
        for i, raw in enumerate(mirror_path.read_text(encoding="utf-8").splitlines(), 1):
            if pattern in raw:
                hits.append(f"mirror line {i} n={raw.count(pattern)}")
    for hit in hits:
        _say(f"  {hit}")
    _say(f"scan-literal: {digest(pattern)} {len(hits)} hit(s)")
    return EXIT_FAILED if hits else EXIT_OK


def _add(ctx: Ctx) -> int:
    """Mint a waypoint.

    Returns:
        EXIT_OK.

    """
    draft = ops.Draft(
        ctx.get("add") or "",
        ctx.get("next") or "",
        ctx.many("enables") or (),
        ctx.many("touches") or (),
        ctx.get("caused_by") or "",
        ctx.get("witness") or "",
        ctx.get("witness_lang") or "",
    )

    # ⚑ ORDER (W534): the line is FORMATTED before anything is saved, so a malformed one (a
    # multi-line title) refuses with nothing minted; it is APPENDED only AFTER the state save, so
    # a crash can lose a `minted` line but never leave one for a waypoint that was never saved.
    with store.exclusive(ctx.path):
        state = store.load(ctx.path)
        now = ctx.stamp()
        sym = ops.add(state, draft, now)
        mint = state.waypoints[-1]
        minted = line(
            Entry(text(mint, "minted_during"), sym, "minted", "-", draft.title, draft.caused_by),
            now,
        )
        store.save(ctx.path, state)
        append(store.sibling(ctx.path, store.LEDGER), minted)
        judge = _admit_after(ctx, "add", sym)
        if judge is not None:
            judge(state)
    _say(f"{sym} added; state_hash={v2(state.waypoints)}")
    return EXIT_OK


def _drop(ctx: Ctx) -> int:
    """Move a waypoint to residue; with `--on SURVIVOR` repoint its edges first, dry run first.

    ⚑ `--on` (also `--onto`) NAMES THE CARD THAT SURVIVES THE DROPPED ONE (mtools:W1333): every
    `blocked_on` and `enables` naming the dropped card is moved to the survivor, so the drop leaves
    no `--check` finding behind. Without `--write` the repoints are only listed and nothing is
    dropped; a plain `--drop` with no `--on` is unchanged and already written.

    Returns:
        EXIT_OK.

    Raises:
        RefusedError: on `--write` with no `--on`.

    """
    sym, reason = ctx.many("drop") or ("", "")
    if ctx.opts.get("write") and ctx.get("on") is None:
        msg = "--drop: --write belongs to --on SURVIVOR; a plain drop is already written"
        raise RefusedError(msg)
    # ⚑ UNDER --admit A DROP MUST SAY WHERE IT DIED (W851), checked BEFORE anything moves so a
    # refused drop leaves the waypoint live; without --admit the old two-operand drop is unchanged.
    account = (
        admission.died(ctx.get("gate"), ctx.get("reference_arm"), reason)
        if ctx.opts.get("admit")
        else None
    )

    survivor = ctx.get("on")
    write = bool(ctx.opts.get("write"))

    def edit(state: State) -> int:
        if survivor is not None:
            found = dropto.plan(state, sym, survivor)
            verb = "REPOINTED" if write else "WOULD REPOINT"
            planned = [
                (
                    f"{r.card}.{r.field}",
                    f"repoint {r.card} {r.field} {sym}",
                    f"{verb} {r.card} {r.field}: {sym} -> {'(removed)' if r.removed else survivor}",
                )
                for r in found
            ]
            _advise(ctx, state, ("drop-onto", f"{sym}->{survivor}"), planned)
            if not write:
                _say(f"WOULD DROP {sym} onto {survivor}; nothing is dropped without --write")
                return EXIT_OK
            dropto.apply(state, found, sym, survivor)
        ops.drop(state, sym, reason, ctx.stamp(), account)
        _say(f"{sym} -> residue; state_hash={v2(state.waypoints)}")
        return EXIT_OK

    def after(_state: State) -> None:
        if account is not None:
            site = admission.Site(ctx.path, _root(ctx), ctx.stamp())
            admission.mark_drop(site, sym, reason, account)

    return _mutate(ctx, edit, after)


def _delivered(ctx: Ctx) -> int:
    """Print the queue's delivered version, `0.0.<highest done number>` (W803); reads only.

    Returns:
        EXIT_OK.

    """
    _say(delivered.version(store.load(ctx.path)))
    return EXIT_OK


def _skip(ctx: Ctx) -> int:
    """Record a skipped symbol in residue, with its reason (W847).

    Returns:
        EXIT_OK.

    """
    sym, reason = ctx.many("skip") or ("", "")

    def edit(state: State) -> int:
        ops.skip(state, sym, reason, ctx.stamp())
        _say(f"{sym} -> residue (skipped); state_hash={v2(state.waypoints)}")
        return EXIT_OK

    return _mutate(ctx, edit)


def _gate_red(ctx: Ctx) -> int:
    """Mint or reuse this repo's gate card and block the open ledger behind it (W870).

    Returns:
        EXIT_OK.

    """
    spec = gate.Red(
        reason=ctx.get("gate_red") or "",
        step=ctx.get("next") or "",
        human=" ".join(ctx.many("blocked_on") or ()),
        repairs=ctx.many("exclude") or (),
    )
    repo = inbound.repo_name(ctx.path)

    def edit(state: State) -> int:
        out = gate.red(state, repo, spec, ctx.stamp())
        _say(f"{out.card} gate card; {out.blocked} waypoint(s) newly blocked on it")
        return EXIT_OK

    return _mutate(ctx, edit)


def _gate_green(ctx: Ctx) -> int:
    """Mark this repo's gate card done and lift what waited only on it (W870).

    Returns:
        EXIT_OK.

    """
    repo = inbound.repo_name(ctx.path)

    def edit(state: State) -> int:
        card, freed = gate.green(state, repo, ctx.get("gate_green") or "", ctx.stamp())
        if not card:
            _say(f"{repo}: no open gate card")
            return EXIT_OK
        _say(f"{card} done; {len(freed)} waypoint(s) unblocked: {', '.join(freed) or 'none'}")
        return EXIT_OK

    return _mutate(ctx, edit)


def _gate_note(ctx: Ctx) -> int:
    """Append evidence to this repo's open gate card, if there is one (W830).

    Returns:
        EXIT_OK, whether or not a card was open.

    """
    repo = inbound.repo_name(ctx.path)

    def edit(state: State) -> int:
        card = gate.note(state, repo, ctx.get("gate_note") or "", ctx.stamp())
        _say(f"{card} evidence appended" if card else f"{repo}: no open gate card")
        return EXIT_OK

    return _mutate(ctx, edit)


def _embargo(ctx: Ctx) -> int:
    """Record one embargoed path (W511), and ledger it.

    Returns:
        EXIT_OK.

    """
    path, reason = ctx.many("embargo") or ("", "")

    def edit(state: State) -> int:
        rel = embargo.embargo(state, path, reason, ctx.stamp())
        _ledger(ctx, Entry("embargo", NO_SYMBOL, "set", "embargo", f"{rel}: {reason}"))
        _say(f"embargoed {rel}")
        return EXIT_OK

    return _mutate(ctx, edit)


def _reject_advice(ctx: Ctx) -> int:
    """Reject every open piece of one tool's advice under one rule, with a reason (W1243).

    ⚑ ONE COMMAND REJECTS A WHOLE SELECTOR: a session that declines the advice of a dry run says so
    here, with the reason the next dry run prints in place of the advice, instead of silently not
    running `--write`. An empty reason, or no open advice to reject, is refused and changes
    nothing: a rejection the caller believes happened and did not is the silence this verb exists
    to remove.

    Returns:
        EXIT_OK.

    """
    tool, rule, reason = ctx.many("reject_advice") or ("", "", "")

    def edit(state: State) -> int:
        try:
            changed = REJECT_ADVICE(state.doc, tool, rule, reason)
        except ValueError as exc:
            raise RefusedError(str(exc)) from exc
        if changed == 0:
            msg = f"no open advice from {tool} under rule {rule}: nothing to reject"
            raise RefusedError(msg)
        _ledger(ctx, Entry("advice", NO_SYMBOL, "rejected", "advice", f"{tool} {rule}: {reason}"))
        _say(f"rejected {changed} piece(s) of advice from {tool} under {rule}")
        return EXIT_OK

    return _mutate(ctx, edit)


def _lift_embargo(ctx: Ctx) -> int:
    """Remove one embargo record (W511), and ledger it.

    Returns:
        EXIT_OK.

    """
    path = ctx.get("lift_embargo") or ""

    def edit(state: State) -> int:
        rel = embargo.lift(state, path)
        _ledger(ctx, Entry("embargo", NO_SYMBOL, "lifted", "embargo", rel))
        _say(f"embargo lifted: {rel}")
        return EXIT_OK

    return _mutate(ctx, edit)


def _outcomes_set(ctx: Ctx) -> int:
    """Declare the ledger outcome sets (W533), and ledger it.

    Returns:
        EXIT_OK.

    """
    advance, other = ctx.many("outcomes_set") or ("", "")

    def edit(state: State) -> int:
        outcomes.set_sets(state, advance, other)
        _ledger(ctx, Entry("outcomes", NO_SYMBOL, "set", "outcomes", f"{advance} | {other}"))
        _say("ledger outcomes declared")
        return EXIT_OK

    return _mutate(ctx, edit)


def _outcomes_clear(ctx: Ctx) -> int:
    """Remove the ledger outcome sets (W533), and ledger it.

    Returns:
        EXIT_OK.

    """

    def edit(state: State) -> int:
        outcomes.clear(state)
        _ledger(ctx, Entry("outcomes", NO_SYMBOL, "cleared", "outcomes", "ledger_outcomes"))
        _say("ledger outcomes cleared")
        return EXIT_OK

    return _mutate(ctx, edit)


def _root(ctx: Ctx) -> Path:
    """Name the directory holding the repos: `--root`, or `~/github`.

    Returns:
        the root.

    """
    return Path(ctx.get("root") or foreign.default_root())


def _prune_landed(ctx: Ctx) -> int:
    """Drop landed local blockers and say which waypoints that frees, counting nothing.

    ⚑ THE IDEMPOTENT HALF OF `--bump-blocked` (luthen-observability, mtools:W537). `--bump-blocked`
    also advances the nudge back-off counter, so run from a hook on every tool use it would drive
    every blocked card to ESCALATE_TICK in minutes. This only prunes, so running it twice changes
    nothing, and it is safe from a hook. A foreign `repo:W<n>` is resolved by reading that repo's
    queue under `--root` (W538); one that stays is named, one line each.

    Returns:
        EXIT_OK.

    """
    root = _root(ctx)

    def edit(state: State) -> int:
        for sym in ops.prune_done(state):
            _say(f"UNBLOCKED {sym} (every local blocker is done)")
        pruned = foreign.prune_foreign(state, root)
        for sym in pruned.freed:
            _say(f"UNBLOCKED {sym} (every blocker is done)")
        for note in pruned.kept:
            _say(note)
        return EXIT_OK

    return _mutate(ctx, edit)


def _inbound(ctx: Ctx) -> int:
    """Print the peer cards blocked on this repo that no local waypoint claims, read-only.

    ⚑ ONE LINE PER UNCLAIMED ROW, `UNCLAIMED <peer>:W<n> :: <title> :: <claim command>`, and
    nothing for a claimed one unless `--all` asks (then `CLAIMED ... by ...`). A peer queue that
    cannot be read is named on an `UNREADABLE` line. The exit is 0 either way (W577).

    Returns:
        EXIT_OK.

    """
    found = inbound.census(_root(ctx), inbound.repo_name(ctx.path), store.load(ctx.path))
    shown = [ask for ask in found.asks if not ask.claimed_by or ctx.opts.get("all")]
    for ask in shown:
        _say(inbound.ask_line(ctx.path, ask))
    for entry in found.unreadable:
        _say(f"UNREADABLE {entry}")
    # ⚑ W1111: under --tick-open every step speaks, so an empty inbound reads as a reading.
    if ctx.get("tick_open") and not shown and not found.unreadable:
        _say("inbound: no unclaimed asks")
    return EXIT_OK


def _bump_blocked(ctx: Ctx) -> int:
    """Prune landed blockers, then count a blocked tick on every blocked waypoint.

    Returns:
        EXIT_OK.

    """
    exclude = frozenset(ctx.many("exclude") or ())

    def edit(state: State) -> int:
        for sym in ops.prune_done(state):
            _say(f"UNBLOCKED {sym} (every local blocker is done)")
        bumped = ops.bump_blocked(state, exclude)
        if not ctx.opts.get("verbose"):
            for report_line in ops.nudge_summary(bumped):
                _say(report_line)
            return EXIT_OK
        for n in bumped:
            owed = "" if n.action is ops.Action.QUIET else f"  {n.action}"
            _say(f"{n.symbol} ticks_blocked={n.ticks} on={','.join(n.blocked_on)}({n.kind}){owed}")
        return EXIT_OK

    return _mutate(ctx, edit)


def _ledger_mode(ctx: Ctx) -> int:
    """Append a structured ledger line; a declared outcome set (W533) refuses an unlisted word.

    Returns:
        EXIT_OK.

    Raises:
        RefusedError: on a tick/interrupt OUTCOME in neither declared set.

    """
    sym, outcome, mechanism, note = ctx.many("ledger") or ("", "", "", "")
    if sym == _QUEUE_SYMBOL:
        sym = NO_SYMBOL
    kind = ctx.get("kind") or _DEFAULT_KIND
    refused = outcomes.refusal(store.load(ctx.path), kind, outcome)
    if refused:
        raise ops.RefusedError(refused)
    entry = Entry(kind, sym, outcome, mechanism, note, ctx.get("evidence") or "")
    text_line = line(entry, ctx.stamp())
    append(store.sibling(ctx.path, store.LEDGER), text_line)
    _say(text_line)
    return EXIT_OK


def _show(ctx: Ctx) -> int:
    """Say what each named symbol is: live, residue, or never issued (mtools:W1335).

    ⚑ One record is printed per symbol, in the order given. A symbol that resolves to nothing is
    named on stderr in its place, the rest still print, and the exit is a refusal.

    Returns:
        EXIT_OK when every symbol resolves, else EXIT_REFUSED.

    """
    state = store.load(ctx.path)
    missing = 0
    for sym in ctx.many("show") or ("",):
        found: list[Json] = [
            r for r in (*state.waypoints, *state.residue) if text(r, "symbol") == sym
        ]
        if not found:
            _warn(f"{sym}: in neither waypoints nor residue (counter={state.counter})")
            missing += 1
        for rec in found:
            _say(json.dumps(rec, indent=2, ensure_ascii=False))
    return EXIT_REFUSED if missing else EXIT_OK


def _commit_message(ctx: Ctx) -> int:
    """Print a draft commit message for one live waypoint; the state is only read.

    Returns:
        EXIT_OK.

    """
    sys.stdout.write(draft(ops.find(store.load(ctx.path), ctx.get("commit_message") or "")))
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


def _standing_set(ctx: Ctx) -> int:
    """Store a file's non-blank lines as the standing list, replacing it whole (W862).

    Returns:
        EXIT_OK.

    """
    lines = Path(ctx.get("standing_set") or "").read_text(encoding="utf-8").splitlines()

    def edit(state: State) -> int:
        _say(f"standing set: {ops.set_standing(state, lines)} rule(s)")
        return EXIT_OK

    return _mutate(ctx, edit)


def _json_file(source: Path) -> object:
    """Read a JSON file a bulk mode applies.

    Returns:
        the parsed document, unchecked.

    Raises:
        RefusedError: on a file that is not JSON.

    """
    try:
        return cast("object", json.loads(source.read_text(encoding="utf-8")))
    except json.JSONDecodeError as exc:
        msg = f"{source}: not JSON ({exc.msg}, line {exc.lineno})"
        raise ops.RefusedError(msg) from exc


def _vectors_from(ctx: Ctx) -> int:
    """Store a file's WV:1 vectors in one write, or refuse the whole file (W354).

    ⚑ PARSED AND CHECKED BEFORE THE LOCK, as `--weights-from`: every vector's grammar and source
    are judged before the state is opened, and the symbols against the live queue under it.

    Returns:
        EXIT_OK.

    """
    triples = ops.vectors_from(_json_file(Path(ctx.get("vectors_from") or "")))

    def edit(state: State) -> int:
        count = ops.set_vectors(state, triples, ctx.stamp())
        _say(f"vectors set: {count}; state_hash={v2(state.waypoints)}")
        return EXIT_OK

    return _mutate(ctx, edit)


def _repair_counter(ctx: Ctx) -> int:
    """Raise a lagging counter to the highest claimed symbol, and ledger the repair (W355).

    Returns:
        EXIT_OK.

    """
    reason = ctx.get("repair_counter") or ""

    def edit(state: State) -> int:
        old, new = ops.repair_counter(state)
        note = f"counter {old}->{new}: {reason}"
        _ledger(ctx, Entry("repair", f"W{new}", "counter", "raised", note))
        _say(f"counter repaired: {old}->{new}")
        return EXIT_OK

    return _mutate(ctx, edit)


def _weights_from(ctx: Ctx) -> int:
    """Store a file's weights in one write, or refuse the whole file.

    ⚑ PARSED BEFORE THE LOCK, APPLIED UNDER IT: a malformed file is refused without ever
    touching the state, and a well-formed one is still judged whole against the live queue.

    Returns:
        EXIT_OK.

    """
    pairs = ops.weights_from(_json_file(Path(ctx.get("weights_from") or "")))

    def edit(state: State) -> int:
        count = ops.set_weights(state, pairs, ctx.stamp())
        _say(f"weights set: {count}; state_hash={v2(state.waypoints)}")
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


def _init(ctx: Ctx) -> int:
    """Create a fresh, empty state file at `ctx.path` — refused if one already exists.

    ⚑⚑ REFUSED, NEVER OVERWRITTEN: an existing state file is a repo's live queue, and a second
    `--init` over it would silently reset the counter and drop every waypoint. Reported
    independently by nemik and rosettapkg (2026-09-26): both had hand-written their first state
    for want of this mode, the pattern that later broke substrate's and aeternum's counters.

    Returns:
        EXIT_OK, or EXIT_REFUSED when a state file is already there.

    """
    with store.exclusive(ctx.path):
        if ctx.path.exists():
            _warn(f"REFUSED: {ctx.path} already exists; --init never overwrites a live state")
            return EXIT_REFUSED
        doc: Json = {
            "version": 1,
            "project_root": str(ctx.path.parent.parent),
            "counter": 0,
            "waypoints": [],
            "residue": [],
        }
        store.write_atomic(ctx.path, json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    _say(f"initialized {ctx.path}; counter=0")
    return EXIT_OK


def _certify(ctx: Ctx) -> int:
    """Print each named waypoint's realizability verdict, one JSON line each (W850).

    ⚑ READS, NEVER WRITES, AND NEVER THROUGH THE WRITER: the queue is loaded, the policy judges
    it under the pinned opa, and nothing is saved. `--root` names where peer queues live, so a
    cited `repo:W<n>` resolves against its owner's queue.

    ⚑ THREE ANSWERS: 0 when every verdict is runtime-valid (coverable, no residue), 1 when any
    carries residue, 2 when nothing could be judged (a symbol not live here, or no pinned opa).
    Not checked never reads as clean.

    Returns:
        EXIT_OK, EXIT_FAILED or EXIT_REFUSED.

    """
    state = store.load(ctx.path)
    symbols = ctx.many("certify") or ()
    where = certify.Where(inbound.repo_name(ctx.path), _root(ctx))
    source = ctx.get("facts")
    try:
        facts = (
            certify.parse_facts(cast("object", json.loads(Path(source).read_text("utf-8"))))
            if source
            else {}
        )
        built = certify.items(state, symbols, where, ctx.stamp(), facts)
        found = opa_eval.verdicts(built, opa_eval.resolve())
    except (ops.RefusedError, opa_eval.OpaUnavailableError, OSError, ValueError) as exc:
        _warn(f"not certified: {exc}")
        return EXIT_REFUSED
    valid = [v for v in found if v.get("level") == "coverable" and not v.get("residue")]
    for verdict in found:
        _say(json.dumps(verdict, ensure_ascii=False, sort_keys=True))
    _warn(f"certified {len(found)}: {len(valid)} runtime-valid, {len(found) - len(valid)} residue")
    return EXIT_OK if len(valid) == len(found) else EXIT_FAILED


def _mint_residue(ctx: Ctx) -> int:
    """Mint one claimable card from a waypoint's residue at a gate (W853).

    ⚑ ONE CARD PER WAYPOINT AND GATE, JUDGED UNDER THE FLOCK: the policy judges the saved state,
    the card is drafted from the residue entry's `closes_by`, minted caused by the waypoint, and
    saved; a card that already exists is found, not duplicated. Nothing is minted unjudged, so no
    pinned opa is exit 2.

    Returns:
        EXIT_OK after minting or finding the card, EXIT_REFUSED when it cannot be judged or
        there is no residue at the gate.

    """
    sym, gate = ctx.many("mint_residue") or ("", "")
    site = admission.Site(ctx.path, _root(ctx), ctx.stamp())

    def locked() -> tuple[str, str | None]:
        with store.exclusive(ctx.path):
            state = store.load(ctx.path)
            said, draft = admission.card_for(state, sym, gate, site)
            if draft is None:
                return said, None
            new = ops.add(state, draft, site.now)
            mint = Entry(
                text(state.waypoints[-1], "minted_during"),
                new,
                "minted",
                "-",
                draft.title,
                draft.caused_by,
            )
            store.save(ctx.path, state)
            append(store.sibling(ctx.path, store.LEDGER), line(mint, site.now))
            return said, new

    try:
        said, new = locked()
    except (ops.RefusedError, opa_eval.OpaUnavailableError, ValueError) as exc:
        _warn(f"not minted: {exc}")
        return EXIT_REFUSED
    _say(said if new is None else f"{said} -> {new}")
    return EXIT_OK


_HANDLERS: dict[str, Callable[[Ctx], int]] = {
    _SUMMARY: _summary,
    "hash": _hash,
    "verify": _verify,
    "render": _render,
    "payload": _payload,
    "queue": _queue,
    "check": _check,
    "check_evidence": _check_evidence,
    "lock": _lock,
    "unlock": _unlock,
    "tick_open": _tick_open,
    "tick_close": _tick_close,
    "armed": _armed,
    "update": _update,
    "update_many": _update_many,
    "add": _add,
    "drop": _drop,
    "embargo": _embargo,
    "lift_embargo": _lift_embargo,
    "reject_advice": _reject_advice,
    "outcomes_set": _outcomes_set,
    "outcomes_clear": _outcomes_clear,
    "bump_blocked": _bump_blocked,
    "block_matching": _block_matching,
    "freeze": _freeze,
    "prune_landed": _prune_landed,
    "block_behind_open": _block_behind_open,
    "close_umbrellas": _close_umbrellas,
    "triage": _triage,
    "lift": _lift,
    "inbound": _inbound,
    "ledger": _ledger_mode,
    "show": _show,
    "commit_message": _commit_message,
    "scan_literal": _scan_literal,
    "preamble_set": _preamble_set,
    "standing_set": _standing_set,
    "preamble_clear": _preamble_clear,
    "init": _init,
    "weights_from": _weights_from,
    "vectors_from": _vectors_from,
    "repair_counter": _repair_counter,
    "overlaps": _overlaps,
    "ics": _ics,
    "unlinked": _unlinked,
    "certify": _certify,
    "mint_residue": _mint_residue,
    "skip": _skip,
    "gate_red": _gate_red,
    "gate_green": _gate_green,
    "gate_note": _gate_note,
    "delivered": _delivered,
    "close_gate": _close_gate,
}


def mode_of(opts: dict[str, object]) -> str:
    """Name the mode an invocation selected.

    Returns:
        the mode, or the summary when none was given.

    """
    chosen = [m for m in _FLAGS if opts.get(m) is True]
    chosen += [m for m in _VALUED if opts.get(m) is not None]
    return chosen[0] if chosen else _SUMMARY


_ALARM = "--alarm"


def bind_alarms(argv: list[str]) -> list[str]:
    """Spell each value after `--alarm` as `--alarm=VALUE`, so `-PT1H` is not read as an option.

    ⚑ "Before" is the common alarm, and every one starts with "-" (life-21, 2026-10-01: the first
    natural spelling, `--alarm -PT1H`, failed). A value runs until the next argument that starts
    with "-" and is not a duration ("-P..."); `--alarm` uses action="extend", so the rewrite is the
    same list, and a bare `--alarm` still clears.

    Returns:
        argv with every alarm value bound to its own `--alarm=`.

    """
    out: list[str] = []
    in_alarms = False
    for arg in argv:
        if arg == _ALARM:
            in_alarms = True
            out.append(arg)
        elif in_alarms and (not arg.startswith("-") or arg.startswith("-P")):
            out.append(f"{_ALARM}={arg}")
        else:
            in_alarms = False
            out.append(arg)
    return out


def main(argv: list[str] | None = None) -> int:
    """Run one invocation.

    Returns:
        the exit code (see the module docstring).

    """
    args = bind_alarms(sys.argv[1:] if argv is None else argv)
    opts: dict[str, object] = vars(_parser().parse_args(args))
    mode = mode_of(opts)
    stray = stray_flags(mode, opts)
    if stray:
        _warn(f"REFUSED: {', '.join(stray)} does not apply to --{mode.replace('_', '-')}")
        return EXIT_REFUSED
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
