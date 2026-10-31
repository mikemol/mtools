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
import os
import shutil
import socket
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from mikemol.pathsforward import (
    admission,
    attach,
    beat,
    behindopen,
    blockedlist,
    bulkblock,
    certify,
    delivered,
    dropto,
    embargo,
    foreign,
    gate,
    generated,
    ghosts,
    idle,
    inbound,
    lease,
    lock,
    manifest,
    manifestsfile,
    opa_eval,
    ops,
    outcomes,
    promptwatch,
    readyolder,
    refusal_record,
    regressions,
    render,
    retros,
    selftest,
    session,
    standing,
    store,
    tickhooks,
    triage,
    vtodo,
    warrant,
    watchdogcmd,
    wholelist,
)
from mikemol.pathsforward.advice import close_applied as close_advice
from mikemol.pathsforward.advice import counts as count_advice
from mikemol.pathsforward.advice import exclude as exclude_advice
from mikemol.pathsforward.advice import mark_applied as apply_advice
from mikemol.pathsforward.advice import reason_for as advice_reason
from mikemol.pathsforward.advice import reject as reject_advice
from mikemol.pathsforward.advice import upsert as upsert_advice
from mikemol.pathsforward.atomize import atomize
from mikemol.pathsforward.blockerwatch import SEEN_NAME as _BLOCKERS_SEEN
from mikemol.pathsforward.blockerwatch import notice as blocker_notice
from mikemol.pathsforward.check import check, evidence_findings, unscored
from mikemol.pathsforward.closegate import (
    Verdict,
    judge_reviewing,
    open_line,
    rank_check,
    roll_note,
    top_ranked,
)
from mikemol.pathsforward.closegate import handoff_line as handoff_of
from mikemol.pathsforward.closegate import judge as judge_close
from mikemol.pathsforward.closeumbrellas import apply as close_apply
from mikemol.pathsforward.closeumbrellas import plan as close_plan
from mikemol.pathsforward.commitmsg import draft
from mikemol.pathsforward.digest import Outcome, v2, verify
from mikemol.pathsforward.landedblock import refuse_landed
from mikemol.pathsforward.ledger import (
    Entry,
    MalformedEntryError,
    actor_of,
    append,
    own_line,
    read,
)
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
from mikemol.pathsforward.mutations import snapshot as field_snapshot
from mikemol.pathsforward.mutations_ship import KINDS as INTERVENTION_KINDS
from mikemol.pathsforward.mutations_ship import ship as ship_mutation
from mikemol.pathsforward.mutations_ship import ship_intervention
from mikemol.pathsforward.overlap import overlaps
from mikemol.pathsforward.payload import PayloadOverBudgetError, Request, build
from mikemol.pathsforward.pruned import edges_of, ledger_line, removed
from mikemol.pathsforward.pruned import said as pruned_said
from mikemol.pathsforward.realizable import GATES
from mikemol.pathsforward.reconcilecmd import run as reconcile_run
from mikemol.pathsforward.redact import REDACTED, digest, redact, scan
from mikemol.pathsforward.subagents import running as running_subagents
from mikemol.pathsforward.tickjson import capture as capture_open
from mikemol.pathsforward.tickjson import document as open_document
from mikemol.pathsforward.tickjson import utc_stamp
from mikemol.pathsforward.transitions import lines as transition_lines
from mikemol.pathsforward.transitions import snapshot as status_snapshot
from mikemol.pathsforward.unlinked import report as unlinked_report

HANDOFF_LINE = handoff_of
CAPTURE_OPEN = capture_open
OPEN_DOCUMENT = open_document
UTC_STAMP = utc_stamp
RECONCILE = reconcile_run
PRUNE_EDGES = edges_of
PRUNE_REMOVED = removed
PRUNE_SAID = pruned_said
PRUNE_LEDGER = ledger_line
TRANSITION_LINES = transition_lines
STATUS_SNAPSHOT = status_snapshot
FIELD_SNAPSHOT = field_snapshot
SHIP_MUTATION = ship_mutation
SHIP_INTERVENTION = ship_intervention
INTERVENTIONS = INTERVENTION_KINDS
REFUSE_LANDED = refuse_landed
BLOCKERS_SEEN = _BLOCKERS_SEEN
BLOCKER_NOTICE = blocker_notice
LIFT_ROW = lift_row
CLOSE_JUDGE = judge_close
ROLL_NOTE = roll_note
REJECT_ADVICE = reject_advice
EXIT_OK = 0
EXIT_FAILED = 1
EXIT_REFUSED = 4
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


def _warrant(ctx: "Ctx") -> int:
    """Attach a PROV-O warrant to a card after reading the transcript record it cites (W1384).

    ⚑ THE RECORD IS READ BEFORE THE QUEUE IS LOCKED AND A REFUSAL CHANGES NOTHING: the reader's own
    reason is the message, so a forged citation is named, not silently dropped.

    Returns:
        EXIT_OK.

    Raises:
        RefusedError: when the citation is incomplete or the reader refuses the record.

    """
    symbol = ctx.get("warrant") or ""
    where, uuid, claim = ctx.get("transcript"), ctx.get("uuid"), ctx.get("claim")
    if not where or not uuid or not claim:
        msg = (
            "--warrant needs --transcript PATH, --uuid UUID and --claim SPEAKER, "
            "the record it cites and whose words it rests on"
        )
        raise RefusedError(msg)
    cited = warrant.Citation(Path(where), uuid, claim, ctx.number("line"))
    reader = warrant.resolve(ctx.get("reader"), _root(ctx), os.environ)
    verdict, argv = warrant.read(cited, reader)
    reason = ctx.get("reason") or ""
    said = f" ({reason})" if reason else ""
    if ctx.opts.get("dry_run"):
        _say(
            f"WOULD ATTACH to {symbol}: record {uuid}, speaker {verdict.get('kind')}, "
            f"line {verdict.get('line')}, at {verdict.get('timestamp')}{said}"
        )
        return EXIT_OK

    def edit(state: State) -> int:
        card = f"urn:nemik:{ctx.path.resolve().parent.parent.name}/{symbol}"
        built = warrant.build(card, cited, verdict, argv, reason)
        added = warrant.attach(state, symbol, built)
        _say(f"WARRANT {'attached to' if added else 'already on'} {symbol}{said}")
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
        repo = attach.project_path(text(state.doc, "project_root") or str(ctx.path.parent.parent))
        found = close_plan(state, repo)
        verb = "CLOSED" if write else "WOULD CLOSE"
        for sym, kids in found.closed:
            _say(f"{verb} {sym} (all children done: {', '.join(kids)})")
        for sym, why in found.kept:
            _say(f"KEPT {sym} ({why})")
        if write:
            close_apply(state, found, ctx.stamp())
        return EXIT_OK

    return _mutate(ctx, edit)


def _reconcile(ctx: "Ctx") -> int:
    """Judge every working card against the gate and the log; a dry run unless `--write` (W1639).

    ⚑ DRY RUN FIRST, as `--close-umbrellas`: each line says what is true of the card (GATING,
    LANDED or STALE) and what `--write` would set. A gate map that cannot be read refuses.

    Returns:
        EXIT_OK.

    """
    write = bool(ctx.opts.get("write"))

    def edit(state: State) -> int:
        root = attach.project_path(text(state.doc, "project_root") or str(ctx.path.parent.parent))
        for line in RECONCILE(state, root, write=write):
            _say(line)
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
EXPORT_SUFFIX = store.EXPORT
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
    "reconcile",
    "triage",
    "inbound",
    "preamble_clear",
    "outcomes_clear",
    "init",
    "overlaps",
    "ics",
    "export",
    "unlinked",
    "delivered",
    "close_gate",
    "standing",
    "ready_count",
    "ghosts",
    "watchdog_line",
    "prompt_ack",
    "migrate_retros",
)
_VALUED = (
    "verify",
    "lock",
    "unlock",
    "tick_open",
    "tick_close",
    "tick_roll",
    "armed",
    "update",
    "add",
    "drop",
    "ledger",
    "show",
    "blocked_on_list",
    "ready_older_than",
    "retros",
    "preamble_set",
    "standing_set",
    "tick_hooks_set",
    "weights_from",
    "vectors_from",
    "manifests_from",
    "add_retro",
    "regressions",
    "repair_counter",
    "scan_literal",
    "commit_message",
    "embargo",
    "lift_embargo",
    "intervention",
    "reject_advice",
    "outcomes_set",
    "certify",
    "atomize",
    "mint_residue",
    "skip",
    "gate_red",
    "gate_green",
    "gate_note",
    "block_matching",
    "freeze",
    "warrant",
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
# ⚑ THE ONLY STATUSES A BULK CALL SETS (W1520): ready to blocked and blocked to ready, with the
# blocker named.
# `done` needs each card's own evidence and `working` comes per card from the mechanical marks, so
# neither belongs in a call that changes many cards at once.
_BULK_STATUSES = frozenset({"blocked", "ready"})

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
    "add_blocker",
    "attach",
    "touches",
    "caused_by",
    "exclude",
    "kind",
    "evidence",
    "blocked_by",
    "reason",
    "reviewing",
    "rank_from",
    "promote",
    "weight",
    "witness",
    "witness_lang",
    "jwk",
    "vector",
    "vector_source",
    "dtstart",
    "due",
    "location",
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
    "manifest",
    "size",
    "acceptable_suppliers",
    "want",
    "facts",
    "admit",
    "gate",
    "root",
    "all",
    "on",
    "write",
    "verbose",
    "count_tick",
    "transcript",
    "uuid",
    "claim",
    "line",
    "reader",
    "dry_run",
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
            "add_blocker",
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
            "location",
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
            "manifest",
            "size",
            "acceptable_suppliers",
            "want",
            "admit",
            "root",
        }
    ),
    "add": frozenset(
        {"next", "enables", "touches", "caused_by", "witness", "witness_lang", "admit", "root"}
    ),
    "drop": frozenset({"admit", "gate", "reference_arm", "root", "on", "write"}),
    "bump_blocked": frozenset({"exclude", "verbose", "root", "count_tick"}),
    "block_matching": frozenset({"on", "write"}),
    "freeze": frozenset({"write", "verbose"}),
    "manifests_from": frozenset({"write"}),
    "add_retro": frozenset(),
    "retros": frozenset(),
    "migrate_retros": frozenset({"dry_run"}),
    "regressions": frozenset(),
    "warrant": frozenset(
        {"transcript", "uuid", "claim", "line", "reader", "root", "reason", "dry_run"}
    ),
    # ⚑ THE FIELDS OF `--update` EXCEPT `attach` (one file pinned to many cards is a different act),
    # plus `--write`. `status` is here since W1520 but only ready or blocked (`_BULK_STATUSES`).
    "update_many": frozenset(
        {
            "status",
            "blocked_on",
            "blocked_kind",
            "next",
            "title",
            "evidence_append",
            "ticks_blocked",
            "enables",
            "add_enables",
            "add_blocker",
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
    "reconcile": frozenset({"write", "root"}),
    "triage": frozenset({"write"}),
    "inbound": frozenset({"root", "all"}),
    "blocked_on_list": frozenset({"all"}),
    "tick_open": frozenset({"root", "exclude", "verbose", "json"}),
    "tick_close": frozenset(
        {
            "kind",
            "evidence",
            "blocked_by",
            "reason",
            "reviewing",
            "transcript",
            "promote",
            "rank_from",
        }
    ),
    "tick_roll": frozenset({"kind", "evidence"}),
    "close_gate": frozenset({"blocked_by", "reason", "rank_from"}),
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
        "--add-blocker",
        metavar="SYMBOL",
        help="W2178: --update: hold the card behind SYMBOL, keeping its other blockers; its "
        "status is restored when the last blocker goes",
    )
    ap.add_argument(
        "--retires",
        nargs="+",
        metavar="WORD",
        help="--outcomes-set: stored outcome words this declaration drops on purpose (W2058)",
    )
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
        help="W1203: --tick-close with ready cards left: why, citing a card of this queue; "
        "W1860: --warrant: the operator record this sanctions, printed and stored",
    )
    ap.add_argument(
        "--reviewing",
        metavar="AGENT-ID",
        help="W2038: --tick-close with ready cards left: the reviewer subagent it idles for; "
        "accepted only while --transcript PATH's session lists it as running",
    )
    ap.add_argument(
        "--rank-from",
        metavar="FILE",
        help="W1368: --tick-close and --close-gate: nemik-rank --json for this repo; refuse "
        "a close that skipped the top ready card unless it is named",
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


def _add_manifest_fields(ap: argparse.ArgumentParser) -> None:
    """Add the flags for a card's manifest and size class (W1426); checked in `manifest.check`."""
    ap.add_argument(
        "--manifest",
        action="extend",
        nargs="*",
        metavar="PATH",
        help="--update: the whole list of exact repo-relative files this card will create or "
        "edit (no directory, glob or link); bare --manifest clears",
    )
    ap.add_argument(
        "--size",
        choices=(*manifest.SIZES, ""),
        help="--update: the card's size class, small (~50 lines), medium (~300) or large "
        "(atomize); '' clears",
    )


def _add_supplier_fields(ap: argparse.ArgumentParser) -> None:
    """Add the flags for a waiting card's fallback suppliers (W1511); checked in `suppliers`."""
    ap.add_argument(
        "--acceptable-suppliers",
        action="extend",
        nargs="*",
        metavar="REF",
        help="--update: the WHOLE list of other waypoints (W<n> or repo:W<n>) that could supply "
        "what this card waits for; a fallback, never a second block; bare flag clears",
    )
    ap.add_argument(
        "--want",
        metavar="TEXT",
        help="--update: one line naming the asset this card waits for; '' clears",
    )


def _flag(value: str | None) -> bool | None:
    """Read a true or false flag word.

    Returns:
        True or False for those words, None when the flag was not given.

    """
    return None if value is None else value == "true"


def _add_deploys_field(ap: argparse.ArgumentParser) -> None:
    """Add the flag saying whether a card's change ships as a deployment (W1814)."""
    ap.add_argument(
        "--deploys",
        choices=("true", "false"),
        help="--update: true when the change ships as a deployment, so landing sends the card to "
        "landed and only its witness makes it done; false when it deploys nothing",
    )


def _add_withheld_field(ap: argparse.ArgumentParser) -> None:
    """Add the flag keeping a card out of this repo's export (W1836, nemik:W516)."""
    ap.add_argument(
        "--withheld",
        choices=("true", "false"),
        help="--update: true keeps the card out of the repo's export, whole, as a bare ref; "
        "false (the default) publishes it",
    )


def _add_realizable_fields(ap: argparse.ArgumentParser) -> None:
    """Add the flags for the fields the realizability policy reads (W849).

    ⚑ FORM IS CHECKED IN `realizable`, NEVER HERE: these only collect the words.
    """
    _add_manifest_fields(ap)
    _add_supplier_fields(ap)
    _add_deploys_field(ap)
    _add_withheld_field(ap)
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
        "--count-tick",
        action="store_true",
        default=None,
        help="--bump-blocked: also count a blocked tick on each blocked card (tick-open does)",
    )
    ap.add_argument("--transcript", metavar="PATH", help="--warrant: the transcript JSONL cited")
    ap.add_argument("--uuid", metavar="UUID", help="--warrant: the cited record's uuid")
    ap.add_argument("--claim", help="--warrant: the speaker claimed (`operator` needs a human)")
    ap.add_argument("--line", type=int, help="--warrant: the line the citation names")
    ap.add_argument("--reader", metavar="CMD", help="--warrant: the transcript reader to run")
    ap.add_argument(
        "--dry-run",
        action="store_true",
        default=None,
        help="W1860: --warrant: verify the cited record and print what would be attached, "
        "saving nothing",
    )
    ap.add_argument(
        "--json",
        action="store_true",
        default=None,
        help="W2169: --tick-open: print one JSON document (holder, exit, hooks with their UTC read "
        "times, and the open's lines) instead of the text",
    )
    ap.add_argument(
        "--facts",
        metavar="FILE",
        help="--certify: a JSON object {name: {value, as_of, gate, waypoints} | {unreadable: "
        "true, gate, waypoints}}; read, never run",
    )


def _add_file_modes(mode: argparse._MutuallyExclusiveGroup) -> None:
    """Register the modes that store a file's lines into the queue state.

    ⚑ ONE HELPER, BECAUSE `_parser` IS AT THE STATEMENT LIMIT: `--preamble-set`, `--standing-set`
    and `--tick-hooks-set` (W1348) have one shape, FILE in and a list stored. `--blocked-on-list`
    (W2184) rides here for the same reason, the parser having no statement left for it.
    """
    mode.add_argument(
        "--blocked-on-list",
        metavar="SYMBOL",
        help="W2184: the open cards blocked on SYMBOL, newest first, 50 at most (--all: every one)",
    )
    mode.add_argument(
        "--ready-older-than",
        metavar="DAYS",
        help="W2118: the ready cards issued more than DAYS days ago (2.2 is allowed), oldest "
        "first, as '<symbol> <age>d <next step>', then a count",
    )
    mode.add_argument("--preamble-set", metavar="FILE", help="store FILE's lines as preamble")
    mode.add_argument(
        "--standing-set",
        metavar="FILE",
        help="W862: store FILE's non-blank lines as the whole standing list, one rule per line",
    )
    mode.add_argument(
        "--tick-hooks-set",
        metavar="FILE",
        help="W1348: store FILE's commands (one per non-blank, non-# line) for --tick-open to run; "
        "an empty file clears",
    )
    mode.add_argument(
        "--manifests-from",
        metavar="FILE",
        help="W1453: store [{symbol, manifest, size}] from a JSON file, all or nothing; "
        "a dry run unless --write",
    )
    mode.add_argument(
        "--regressions",
        metavar="FILE",
        help="W1930: compare this queue with the queue document in FILE (HEAD's copy) and refuse "
        "a done card reopened, a residue card gone, or evidence shortened without a redaction",
    )
    mode.add_argument(
        "--retros",
        nargs="*",
        metavar="Rn",
        help="W2088: print the retro records in full (every field and finding), all of them or "
        "the named <repo>:R<n> / R<n>; an unknown id is named and refused",
    )
    mode.add_argument(
        "--add-retro",
        metavar="FILE",
        help="W1918: add the retro record in a JSON file to the queue's retros list, minting "
        "the next <repo>:R<n>; a finding with no card or certify_change, or a card without "
        "owner, due date or witness, is refused (nemik:W982)",
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
            "--warrant",
            "SYMBOL",
            (
                "W1384: attach a PROV-O warrant to SYMBOL after reading the transcript record it "
                "cites (--transcript PATH --uuid UUID [--claim operator] [--line N] "
                "[--reader CMD]). mikemol-transcriptstruct --human REGEX prints each row's uuid "
                "and timestamp"
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
        "are symbols or a selector: `unscored`, `unmanifested` (every ready card with no "
        "manifest) or `open` (every card not done); --except SYMBOL[=REASON] skips cards and "
        "prints each reason; a dry run without --write",
    )
    for flag, metavar, text_help in (
        (
            "--certify",
            "SYMBOL",
            (
                "W850: each waypoint's realizability verdict {ref, level, reference_arm, "
                "residue}, one JSON line each, judged by the pinned opa; reads, never writes"
            ),
        ),
        (
            "--atomize",
            "PARENT_THEN_TITLES",
            (
                "W1089: PARENT, then one child title per operand: mint each child (ready, "
                "enabling and caused by PARENT) and block PARENT on them"
            ),
        ),
    ):
        mode.add_argument(flag, nargs="+", metavar=metavar, help=text_help)
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
        (
            "--tick-roll",
            ("HOLDER", "SYMBOL", "OUTCOME", "MECHANISM", "NOTE"),
            (
                "W1589: close the tick and open the next in one step, always allowed: the "
                "--tick-close line without the refusal or the unlock, HOLDER keeping the lock"
            ),
        ),
        (
            "--intervention",
            ("KIND", "NOTE"),
            (
                "W1739: send a card-less intervention event (station fleet:intervention), KIND "
                "one of atomize, stack, shard, repin, other, with the writer's own session, actor "
                "and clock; changes no card"
            ),
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
    _add_file_modes(mode)
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
        "--location",
        metavar="ADDRESS",
        help="--update: where the work happens, one line, an iCalendar LOCATION; '' clears",
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
    append(store.sibling(ctx.path, store.LEDGER), own_line(entry, ctx.stamp()))


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
    return atomize(
        state.waypoints, read(path) if path.is_file() else [], counted, root=ctx.path.parent.parent
    )


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
    root = attach.project_path(text(state.doc, "project_root") or str(ctx.path.parent.parent))
    # ⚑ A GENERATED FILE IS NOT AN EXCLUSIVE WRITE (W1468): the repo's list leaves them out.
    tags = generated.leased(tags, generated.paths(root))
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
        before = STATUS_SNAPSHOT(state)
        fields = FIELD_SNAPSHOT(state)
        code = edit(state)
        if code == EXIT_OK:
            store.save(ctx.path, state)
            # ⚑ EVERY STATUS A CARD CHANGES IS LEDGERED HERE, whichever verb changed it (W1372); a
            # ledger that cannot be written never fails an edit that is already saved.
            ledger_path = store.sibling(ctx.path, store.LEDGER)
            try:
                for said in TRANSITION_LINES(before, state, ctx.stamp(), actor_of(ctx.opts)):
                    append(ledger_path, said)
            except (OSError, MalformedEntryError) as exc:
                _warn(f"status transitions not ledgered: {exc}")
            # ⚑ EVERY FIELD A CARD CHANGES IS SHIPPED HERE TOO, one event per field (W1742); a
            # send that cannot start never fails an edit that is already saved.
            SHIP_MUTATION(ctx.path, fields, state, (mode_of(ctx.opts), ctx.now))
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


def _export(ctx: Ctx) -> int:
    """Write this repo's version-2 export beside the state file (W1838, nemik:W516).

    ⚑ WITHHELD WHOLE OR NOT AT ALL: the file holds every unflagged live card exactly as it is and
    only a bare ref for each flagged one (`export.build`), and it replaces the old file atomically,
    so a reader never sees half an export. The queue and the state file are not touched.

    Returns:
        EXIT_OK.

    """
    built = store.write_export(ctx.path, store.load(ctx.path))
    target = ctx.path.with_suffix(EXPORT_SUFFIX)
    shown = len(cast("list[object]", built["cards"]))
    held = len(cast("list[object]", built["withheld"]))
    _say(f"exported {target}: {shown} card(s), {held} withheld")
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


def _hook_lines(ctx: Ctx, root: Path) -> list[str]:
    """Run the stored tick hooks and describe them; with a `hook_records` sink, keep the records.

    The sink is the JSON open's (W2169): when it is there each hook is read with a UTC stamp taken
    as that hook finishes and its record is appended; the lines are the same either way.

    Returns:
        the `HOOK <line> exit N` lines `--tick-open` prints.

    """
    stored = tickhooks.stored(store.load(ctx.path).doc)
    sink = ctx.opts.get("hook_records")
    if not isinstance(sink, list):
        return tickhooks.run_all(stored, root)
    found = tickhooks.records(stored, root, UTC_STAMP)
    cast("list[dict[str, object]]", sink).extend(found)
    return tickhooks.describe(found)


def _tick_open_json(ctx: Ctx) -> int:
    """Open the tick as `_tick_open` does, and print ONE JSON document instead of the text (W2169).

    ⚑ THE OPEN RUNS UNCHANGED UNDER A CAPTURE: its text is kept whole in `lines`, and the hooks'
    own records (command, exit, UTC read time, output) arrive through `hook_records`, so a reader
    gets each hook's time without parsing the text.

    Returns:
        the open's own status.

    """
    sink: list[dict[str, object]] = []
    inner = replace(ctx, opts={**ctx.opts, "json": False, "hook_records": sink})
    code, lines = CAPTURE_OPEN(lambda: _tick_open(inner))
    _say(OPEN_DOCUMENT(ctx.get("tick_open") or "", code, lines, sink))
    return code


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
    if ctx.opts.get("json") is True:
        return _tick_open_json(ctx)
    holder = ctx.get("tick_open") or ""
    held = replace(ctx, opts={**ctx.opts, "lock": holder, "count_tick": True})
    code = _lock(held)
    if code != EXIT_OK:
        _watchdog_line(ctx)
        return code
    root = ctx.path.parent.parent
    # ⚑ THE BLOCKERS' STATES ARE READ BEFORE THE PRUNE (W1597): a blocker that landed is pruned by
    # the next step, and its change would go unsaid if the snapshot were taken after.
    blocker_seen = root / ".git" / "mtools" / BLOCKERS_SEEN
    notices = list(BLOCKER_NOTICE(store.load(ctx.path), blocker_seen, _root(ctx)))
    # ⚑ A CARD THE PRUNE FREED IS NAMED FIRST, AS READY WORK (W1598, operator ruling via github-8f
    # 2026-10-18): the idempotent prune runs before anything else is printed, so each `UNBLOCKED
    # <card>` line opens the output instead of sitting under a long list of blocker changes. The
    # blockers' states were read above, before the prune, as W1597 needs; only their printing waits.
    code = max(code, _prune_landed(held))
    for said in notices:
        _say(said)
    for step in (_bump_blocked, _inbound, _check):
        code = max(code, step(held))
    _say(open_line(store.load(ctx.path)))
    # ⚑ THE ACUTE RECONCILER'S PLAN IS PRINTED AT OPEN, DRY (W1640): a working card whose commit has
    # landed, or whose gate is gone, is said here with what `--reconcile --write` would set, so a
    # tick does not begin on a card the log already finished. Never written from the open.
    # A reconciler that cannot read the gate map REFUSES (its own rule, W1639); at open that is said
    # and the open goes on, because a refusal here must not stop a tick from starting.
    try:
        code = max(code, _reconcile(replace(held, opts={**held.opts, "write": False})))
    except ops.RefusedError as refused:
        _say(f"reconcile: not run ({refused})")
    for said in _hook_lines(ctx, root):
        _say(said)
    for said in standing.lines(store.load(ctx.path).doc):
        _say(said)
    _say(watchdogcmd.tick_line(ctx.path, sys.argv[0], Path.home(), shutil.which))
    seen = root / ".git" / "mtools" / promptwatch.SEEN_NAME
    for said in promptwatch.notice(promptwatch.prompt_of(root), seen):
        _say(said)
    _say(f"tick open as {holder}; close: --ledger ..., --render, --check, --unlock {holder}")
    return code


def _top_of(ctx: Ctx) -> str | None:
    """Read the top ranked card off `--rank-from`, or nothing when no file is given (W1368).

    Returns:
        the top card's symbol, or None without the flag (so no new refusal) or for an empty list.

    Raises:
        RefusedError: when the file is not JSON, not a list, or its first record has no symbol.

    """
    given = ctx.get("rank_from")
    if given is None:
        return None
    doc = _json_file(Path(given))
    try:
        return top_ranked(doc)
    except (TypeError, ValueError) as exc:
        msg = f"{given}: {exc}"
        raise ops.RefusedError(msg) from exc


def _say_handoff(ctx: Ctx) -> None:
    """Print the hand-off header for the tick just ledgered, as the last line of a close (W2154).

    The time on it is the ledger line's own, so a reviewer hand-off pastes the tool's reading and
    not one typed by hand; an unreadable ledger or one with no tick line prints nothing.
    """
    ledger = store.sibling(ctx.path, store.LEDGER)
    try:
        body = ledger.read_text(encoding="utf-8")
    except OSError:
        return
    line = HANDOFF_LINE(body, ctx.path.resolve().parent.parent.name)
    if line:
        _say(line)


def review_wait(ctx: Ctx, state: State, verdict: Verdict) -> Verdict:
    """Let a refused close idle for a reviewer the session lists as running (W2038).

    ⚑ A TYPED NAME IS NOT A BLOCK: `--reviewing AGENT-ID` is accepted only while the harness's
    own subagent transcripts, found from `--transcript PATH`, list that agent as running.

    Returns:
        the verdict unchanged unless the close was refused and names a running reviewer.

    """
    reviewer, transcript = ctx.get("reviewing"), ctx.get("transcript")
    if reviewer is None or not verdict.refused:
        return verdict
    if transcript is None:
        _warn("--reviewing needs --transcript PATH (the session transcript)")
        return verdict
    alive = running_subagents(Path(transcript), time.time())
    return judge_reviewing(state, reviewer, alive, store.sibling(ctx.path, store.LEDGER))


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
    state = store.load(ctx.path)
    verdict = CLOSE_JUDGE(state, *when, store.sibling(ctx.path, store.LEDGER))
    verdict = review_wait(ctx, state, verdict)
    verdict = rank_check(verdict, state, _top_of(ctx), when)
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
    _say_handoff(closing)
    return code


def _tick_roll(ctx: Ctx) -> int:
    """Close this tick and open the next in one step, always allowed (W1589, github-8f).

    ⚑ A ROLL IS A CYCLE BOUNDARY, NOT A STOP. `--tick-close` refuses while a ready card exists
    because it ends the loop's turn; a session that never stops (nemik held one tick for 26 hours,
    with 85 cards advanced) could never close it. The roll writes the same ledger line, prunes,
    renders and checks, but keeps the lock for the same holder (re-acquired first, so another
    holder's lock refuses it), so the next tick has begun when it returns. No threshold: a typed
    number is what the autocalibrate rule rules out, and `--tick-close` keeps its refusal. The line
    carries `rolled; advanced N`, so a roll that advanced nothing reads `advanced 0`.

    Returns:
        EXIT_OK, EXIT_LOCKED when another holder has the lock, or the first failing step's status.

    """
    holder, *entry = ctx.many("tick_roll") or ("", "", "", "", "")
    rolling = replace(ctx, opts={**ctx.opts, "lock": holder})
    code = _lock(rolling)
    if code != EXIT_OK:
        return code
    state = store.load(ctx.path)
    ledger = store.sibling(ctx.path, store.LEDGER)
    for said in CLOSE_JUDGE(state, None, None, entry[0] if entry else None, ledger).lines:
        _say(said)
    entry[-1] = f"{entry[-1]} [{ROLL_NOTE(state, ledger)}]"
    rolling = replace(rolling, opts={**rolling.opts, "ledger": tuple(entry)})
    try:
        code = _ledger_mode(rolling)
    except ops.RefusedError as exc:
        _warn(f"not ledgered: {exc}")
        code = EXIT_REFUSED
    for step in (_prune_landed, _render, _check):
        code = code or step(rolling)
    code = code or _chronic_reconcile(rolling)
    _say(f"rolled: {holder} keeps the lock and the next tick has begun")
    _say_handoff(rolling)
    return code


def _chronic_reconcile(ctx: Ctx) -> int:
    """Run the reconciler on a roll's cadence, dry, and name the cards it cannot decide (W1641).

    ⚑ A TICK THAT NEVER STOPS NEVER REOPENS (nemik held one for 26 hours), so the open's pass
    (W1640) is not enough; the roll is the cadence. The reconciler judges each working card
    GATING, LANDED or STALE from the live-commit map and the log. When it cannot read the map it
    refuses, and judging nothing is not the same as there being nothing to judge: the roll says
    which working cards were left undecided, so none reads as settled by silence. Never written.

    Returns:
        EXIT_OK, or the reconciler's own status when it ran.

    """
    try:
        return _reconcile(replace(ctx, opts={**ctx.opts, "write": False}))
    except ops.RefusedError as refused:
        cards = store.load(ctx.path).waypoints
        working = [text(w, "symbol") for w in cards if text(w, "status") == "working"]
        _say(f"reconcile: cannot decide {', '.join(working) or 'no working card'} ({refused})")
        return EXIT_OK


def _promote(ctx: Ctx) -> int:
    """Set the card `--promote` names working, as part of the close (W1245, W1080).

    ⚑ MORE THAN ONE WORKING CARD IS NORMAL (operator 2026-10-15, W1468): anything in a stack,
    building, queued or gating, is working, so a second working card no longer refuses this. It is
    refused for a card that is not ready: promoting a blocked card would work what cannot be worked.

    Returns:
        EXIT_OK (also when `--promote` is not given), or EXIT_REFUSED.

    """
    sym = ctx.get("promote")
    if sym is None:
        return EXIT_OK

    def edit(state: State) -> int:
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
    state = store.load(ctx.path)
    verdict = CLOSE_JUDGE(state, *when, store.sibling(ctx.path, store.LEDGER))
    verdict = rank_check(verdict, state, _top_of(ctx), when)
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

    ⚑ AN EMPTY BLOCKER IS NOT A BLOCKER (W2041, the host's W52 carried `blocked_on [""]`): a blank
    or whitespace-only `--blocked-on` value is refused; a bare `--blocked-on` clears.

    Returns:
        the Update the flags describe.

    Raises:
        RefusedError: when a `--blocked-on` value is empty or only whitespace.

    """
    blockers = ctx.many("blocked_on")
    if blockers is not None and not all(b.strip() for b in blockers):
        msg = "--blocked-on: an empty or whitespace blocker is refused; a bare --blocked-on clears"
        raise ops.RefusedError(msg)
    tags = ctx.many("touches")
    if tags is not None and not all(t.strip() for t in tags):
        msg = "--touches: an empty or whitespace tag is refused (W2041)"
        raise ops.RefusedError(msg)
    return ops.Update(
        status=ctx.get("status"),
        blocked_on=blockers,
        blocked_kind=ctx.get("blocked_kind"),
        next_step=ctx.get("next"),
        evidence_append=ctx.get("evidence_append"),
        ticks_blocked=ctx.number("ticks_blocked"),
        title=ctx.get("title"),
        enables=ctx.many("enables"),
        add_enables=ctx.many("add_enables"),
        add_blocker=ctx.get("add_blocker"),
        weight=ctx.number("weight"),
        touches=ctx.many("touches"),
        witness=ctx.get("witness"),
        witness_lang=ctx.get("witness_lang"),
        vector=ctx.get("vector"),
        vector_source=ctx.get("vector_source"),
        caused_by=ctx.get("caused_by"),
        dtstart=ctx.get("dtstart"),
        due=ctx.get("due"),
        location=ctx.get("location"),
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
        manifest=ctx.many("manifest"),
        size_class=ctx.get("size"),
        acceptable_suppliers=ctx.many("acceptable_suppliers"),
        want=ctx.get("want"),
        deploys=_flag(ctx.get("deploys")),
        withheld=_flag(ctx.get("withheld")),
    )


def _named_blockers(upd: ops.Update) -> tuple[str, ...]:
    """List every blocker an update names: the set `--blocked-on` and the added `--add-blocker`.

    Returns:
        the blockers a landed card must not be among (W2178: an added blocker is judged too).

    """
    return (*(upd.blocked_on or ()), *((upd.add_blocker,) if upd.add_blocker else ()))


def _update_many(ctx: Ctx) -> int:
    """Apply one set of field flags to many waypoints, all or none; a dry run unless `--write`.

    ⚑ ALL OR NONE (mtools:W974, el-openglo:W484). Every update is applied to a copy of the queue
    first, so a refusal on the last symbol changes nothing and names it, and the dry run reports
    exactly what `--write` would do. Operands are symbols or a selector: `unscored`,
    `unmanifested` or `open`.

    Returns:
        EXIT_OK.

    Raises:
        RefusedError: when `--status` is neither ready nor blocked.

    """
    write = bool(ctx.opts.get("write"))
    upd = _fields_of(ctx)
    if upd.status is not None and upd.status not in _BULK_STATUSES:
        msg = (
            f"--update-many sets only {' or '.join(sorted(_BULK_STATUSES))}, not {upd.status}: "
            "done needs each card's own evidence and working comes per card from the marks"
        )
        raise ops.RefusedError(msg)

    skipped: dict[str, str] = {}
    for item in ctx.many("exclude") or ():
        name, _, reason = item.partition("=")
        skipped[name] = reason

    def plan(state: State) -> list[Planned]:
        chosen = bulkblock.select_symbols(state, list(ctx.many("update_many") or ()), skipped)
        for sym, reason in skipped.items():
            _say(f"EXCLUDED {sym}" + (f" ({reason})" if reason else ""))
        for sym in chosen:
            REFUSE_LANDED(state, sym, _named_blockers(upd), _root(ctx))
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
        manifest.check(upd.manifest or (), root)
        REFUSE_LANDED(state, sym, _named_blockers(upd), _root(ctx))
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


def _standing_hits(doc: Json, pattern: str) -> list[str]:
    """Find the stored standing rules that still hold a literal (W2160).

    Returns:
        one `standing rule <i> n=<count>` per rule holding it, empty when none does.

    """
    return [
        f"standing rule {i} n={rule.count(pattern)}"
        for i, rule in enumerate(standing.rules(doc), 1)
        if pattern in rule
    ]


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
    hits += _standing_hits(state.doc, pattern)
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

    Raises:
        RefusedError: when a `--touches` value is empty or only whitespace (W2041).

    """
    tags = ctx.many("touches") or ()
    if not all(t.strip() for t in tags):
        msg = "--touches: an empty or whitespace tag is refused (W2041)"
        raise ops.RefusedError(msg)
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
        minted = own_line(
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


def _atomize(ctx: Ctx) -> int:
    """Mint a child card per title under PARENT and block PARENT on them (W1089).

    Returns:
        EXIT_OK.

    """
    parent, *titles = ctx.many("atomize") or ("",)
    with store.exclusive(ctx.path):
        state = store.load(ctx.path)
        now = ctx.stamp()
        children = ops.atomize(state, parent, titles, now)
        minted = [
            own_line(
                Entry(text(mint, "minted_during"), sym, "minted", "-", text(mint, "title"), parent),
                now,
            )
            for sym, mint in ((s, ops.find(state, s)) for s in children)
        ]
        store.save(ctx.path, state)
        for line in minted:
            append(store.sibling(ctx.path, store.LEDGER), line)
    for sym in children:
        _say(f"{sym} added under {parent}")
    _say(f"{parent} blocked on {', '.join(children)}; state_hash={v2(state.waypoints)}")
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
        released = dropto.release(state, sym) if survivor is None else []
        if released:
            _say(f"{sym} removed from the blocked_on of {', '.join(released)}")
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


def _intervention(ctx: Ctx) -> int:
    """Send a card-less intervention event, changing no card (W1739).

    Returns:
        EXIT_OK; EXIT_REFUSED for a kind outside the fixed set, which would otherwise become an
        unbounded metric label.

    """
    kind, note = ctx.many("intervention") or ("", "")
    if kind not in INTERVENTIONS:
        _warn(f"--intervention KIND is one of {', '.join(INTERVENTIONS)}, not {kind!r}")
        return EXIT_REFUSED
    state = store.load(ctx.path)
    # ⚑ THE LEDGER LINE IS THE RECORD THAT CANNOT FAIL SILENTLY (W1887, nemik:W750): the event's
    # children are detached with their output discarded, so "started" is all the writer can say of
    # them, and a lost send leaves nothing here. The line is written whatever became of the send.
    _ledger(ctx, Entry("intervention", NO_SYMBOL, kind, "intervention", note))
    started = SHIP_INTERVENTION(ctx.path, (kind, note), state, (mode_of(ctx.opts), ctx.now))
    _say(f"intervention {kind} {'started' if started else 'not sent (no binary or store)'}")
    return EXIT_OK


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
    retired = list(ctx.many("retires") or ())

    def edit(state: State) -> int:
        lost = outcomes.dropped(state, advance, other, retired)
        if lost:
            return _refuse_dropped(lost, "outcome word", "declare each with --retires WORD")
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


def _report_pruned(ctx: Ctx, before: set[tuple[str, str]], state: State) -> None:
    """Print and ledger every blocker edge a prune removed, with the card it was on (W1599).

    ⚑ A BLOCKER REMOVED FROM A CARD THAT KEEPS OTHERS WAS SILENT (operator, 2026-10-18): only a card
    freed outright was named. Each removed edge is a `PRUNED card <- blocker` line and a `prune`
    ledger line; a ledger that cannot be written is said and never fails the prune.
    """
    ledger_path = store.sibling(ctx.path, store.LEDGER)
    for card, blocker in PRUNE_REMOVED(before, state):
        _say(PRUNE_SAID(card, blocker))
        try:
            append(ledger_path, PRUNE_LEDGER(card, blocker, ctx.stamp()))
        except (OSError, MalformedEntryError) as exc:
            _warn(f"pruned edge not ledgered: {exc}")


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
        before = PRUNE_EDGES(state)
        for sym in ops.prune_done(state):
            _say(f"UNBLOCKED {sym} (every local blocker is done)")
        pruned = foreign.prune_foreign(state, root)
        for sym in pruned.freed:
            _say(f"UNBLOCKED {sym} (every blocker is done)")
        for note in pruned.kept:
            _say(note)
        _report_pruned(ctx, before, state)
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
    """Prune landed blockers, and with `--count-tick` count a blocked tick on every blocked card.

    ⚑ COUNTING IS EXPLICIT (W1420, github-8f 2026-10-17): twice a session ran `--bump-blocked` to
    clear a landed-blocker warning and inflated `ticks_blocked` on 243 and 229 cards, because the
    verb that prunes also advanced the nudge back-off. Without `--count-tick` it now only prunes
    (exactly `--prune-landed`) and says so; `--tick-open` passes the flag itself, since a tick is
    what the count is of.

    Returns:
        EXIT_OK.

    """
    exclude = frozenset(ctx.many("exclude") or ())
    root = _root(ctx)
    counting = bool(ctx.opts.get("count_tick"))

    def edit(state: State) -> int:
        before = PRUNE_EDGES(state)
        for sym in ops.prune_done(state):
            _say(f"UNBLOCKED {sym} (every local blocker is done)")
        for sym in foreign.prune_foreign(state, root).freed:
            _say(f"UNBLOCKED {sym} (every blocker is done)")
        _report_pruned(ctx, before, state)
        if not counting:
            _say("pruned only: no tick was counted (pass --count-tick inside a tick-open)")
            return EXIT_OK
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
    text_line = own_line(entry, ctx.stamp())
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


def _blocked_on_list(ctx: Ctx) -> int:
    """Print the open cards blocked on one card, then how many there are (W2184).

    ⚑ A READING, NOT A WRITE: it asks the queue and changes nothing, so it leaves no beat.

    Returns:
        EXIT_OK always; the last line counts every blocked card, listed or not.

    """
    symbol = ctx.get("blocked_on_list") or ""
    limit = None if ctx.opts.get("all") is True else blockedlist.LIMIT
    for found in blockedlist.report(store.load(ctx.path), symbol, ctx.now, limit):
        _say(found)
    return EXIT_OK


def _ready_older_than(ctx: Ctx) -> int:
    """Print the ready cards older than a bound, oldest first, then how many there are (W2118).

    ⚑ A READING, NOT A WRITE: it asks the queue and changes nothing, so it leaves no beat.

    Returns:
        EXIT_OK; EXIT_REFUSED when the bound is not a non-negative number.

    """
    given = ctx.get("ready_older_than") or ""
    days = readyolder.parse_days(given)
    if days is None:
        _warn(f"REFUSED: --ready-older-than wants a number of days, not {given!r}")
        return EXIT_REFUSED
    for found in readyolder.report(store.load(ctx.path), days, ctx.now):
        _say(found)
    return EXIT_OK


def _retros(ctx: Ctx) -> int:
    """Print the retro records in full, all of them or the ones named (W2088).

    ⚑ A reviewer re-spawned from the queue reads its subtracted set here: `--export` carries no
    retros and `--render` prints a summary line. The state is only read; an id no retro carries is
    named on stderr and the exit is a refusal.

    Returns:
        EXIT_OK when every named id resolves (or none is named), else EXIT_REFUSED.

    """
    lines, unknown = retros.render_full(store.load(ctx.path).doc, list(ctx.many("retros") or ()))
    for line in lines:
        _say(line)
    for ident in unknown:
        _warn(f"{ident}: no retro with that id")
    return EXIT_REFUSED if unknown else EXIT_OK


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
    text = Path(ctx.get("preamble_set") or "").read_text(encoding="utf-8")
    lines, _gone = wholelist.split(text)

    def edit(state: State) -> int:
        lost = wholelist.lost(wholelist.stored(state.doc, "preamble"), text)
        if lost:
            return _refuse_dropped(lost, "preamble line")
        ops.set_preamble(state, lines)
        _say(f"preamble set: {len(lines)} line(s)")
        return EXIT_OK

    return _mutate(ctx, edit)


def _standing_set(ctx: Ctx) -> int:
    """Store a file's non-blank lines as the standing list, replacing it whole (W862).

    Returns:
        EXIT_OK.

    """
    text = Path(ctx.get("standing_set") or "").read_text(encoding="utf-8")
    lines, _gone = wholelist.split(text)

    def edit(state: State) -> int:
        # An empty file is `set_standing`'s own refusal (0 non-blank lines), not a drop to name.
        keeps = any(line.strip() for line in lines)
        lost = wholelist.lost(wholelist.stored(state.doc, "standing"), text) if keeps else []
        if lost:
            return _refuse_dropped(lost, "standing rule")
        _say(f"standing set: {ops.set_standing(state, lines)} rule(s)")
        return EXIT_OK

    return _mutate(ctx, edit)


def _ghosts(ctx: Ctx) -> int:
    """Print each ready card whose symbol leads a landed commit's subject, with its markers (W2033).

    ⚑ A LIST FOR THE READER, NEVER A CLOSE: the markers a subject uses to say a part is still open
    vary, so a card with a landing commit is a candidate and nothing here changes it.

    Returns:
        EXIT_OK, or EXIT_REFUSED when the git log cannot be read.

    """
    state = store.load(ctx.path)
    root = attach.project_path(text(state.doc, "project_root") or str(ctx.path.parent.parent))
    try:
        lines = ghosts.report(state, root)
    except RefusedError as caught:
        _warn(f"REFUSED: {caught}")
        return EXIT_REFUSED
    for found in lines:
        _say(found)
    return EXIT_OK


def _ready_count(ctx: Ctx) -> int:
    """Print how many unblocked ready cards the queue holds, for the idle watchdog (W1474).

    Returns:
        EXIT_OK.

    """
    _say(str(idle.ready_count(store.load(ctx.path))))
    return EXIT_OK


def _standing(ctx: Ctx) -> int:
    """Print the standing rules alone, one numbered line each (W1470).

    Returns:
        EXIT_OK.

    """
    for said in standing.lines(store.load(ctx.path).doc):
        _say(said)
    return EXIT_OK


def _watchdog_line(ctx: Ctx) -> int:
    """Print the watchdog start line alone, whatever the tick lock says (W1540, nemik).

    ⚑ A TICK THAT STAYS OPEN NEVER SEES THE LINE FROM `--tick-open` (it stops at a held lock), so
    a session whose lock is held by its own earlier open had no way to read how to arm the
    watchdog. This reads nothing but the queue's path and the host, takes no lock and does not beat.

    Returns:
        EXIT_OK.

    """
    _say(watchdogcmd.tick_line(ctx.path, sys.argv[0], Path.home(), shutil.which))
    return EXIT_OK


def _prompt_ack(ctx: Ctx) -> int:
    """Record that the session has read the canonical loop prompt as it stands (W1562, github-8f).

    ⚑ "THE CRON READS IT EVERY TICK" IS NOT A READING BY THE SESSION: a rule was loaded and never
    noticed. This is the session saying it read the lines `--tick-open` showed, by name, once.

    Returns:
        EXIT_OK, or EXIT_REFUSED when there is no prompt to acknowledge or the record did not take.

    """
    root = ctx.path.parent.parent
    prompt = promptwatch.prompt_of(root)
    taken = promptwatch.acknowledge(prompt, root / ".git" / "mtools" / promptwatch.SEEN_NAME)
    if taken is None:
        _warn(f"REFUSED: no loop prompt at {prompt}, or the acknowledgement was not recorded")
        return EXIT_REFUSED
    _say(f"loop prompt acknowledged: {prompt} ({taken} lines)")
    return EXIT_OK


def _refuse_dropped(lost: list[str], what: str, how: str = "") -> int:
    """Refuse a whole-list setter that drops stored lines, naming each (W2058, of W1930 and W862).

    Returns:
        EXIT_REFUSED after one REFUSED line per dropped line and how to declare it (`how`, else
        the `# replaces:` comment a file can carry).

    """
    for line in lost:
        _warn(f"REFUSED: the new list drops the {what} {line!r}")
    _warn(how or "declare each with '# replaces: <line>' (or '# retires: <line>') in the file")
    return EXIT_REFUSED


def _tick_hooks_set(ctx: Ctx) -> int:
    """Store a file's commands as the tick hooks, replacing them whole (W1348, nemik:W450).

    Returns:
        EXIT_OK.

    """
    text = Path(ctx.get("tick_hooks_set") or "").read_text(encoding="utf-8")
    lines = tickhooks.lines_of(text)

    def edit(state: State) -> int:
        lost = tickhooks.dropped(tickhooks.stored(state.doc), text)
        if lost:
            return _refuse_dropped(lost, "tick hook")
        state.doc[tickhooks.KEY] = lines
        _say(f"tick hooks set: {len(lines)} command(s)")
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


def _manifests_from(ctx: Ctx) -> int:
    """Store a file's manifests in one write, or refuse the whole file; a dry run without --write.

    ⚑ PARSED BEFORE THE LOCK, JUDGED WHOLE UNDER IT (W1453): a malformed file is refused without
    touching the state, and a well-formed one is checked against the live queue and the repo's
    files before the first card is written. Without `--write` the changes are printed, none saved.

    Returns:
        EXIT_OK.

    """
    entries = manifestsfile.parse(_json_file(Path(ctx.get("manifests_from") or "")))
    if not ctx.opts.get("write"):
        state = store.load(ctx.path)
        root = attach.project_path(text(state.doc, "project_root") or str(ctx.path.parent.parent))
        for line in manifestsfile.plan(state, entries, root):
            _say(line)
        _say(f"dry run: {len(entries)} manifest(s) would be stored; add --write to store them")
        return EXIT_OK

    def edit(state: State) -> int:
        root = attach.project_path(text(state.doc, "project_root") or str(ctx.path.parent.parent))
        count = manifestsfile.store(state, entries, root, ctx.stamp())
        _say(f"manifests set: {count}; state_hash={v2(state.waypoints)}")
        return EXIT_OK

    return _mutate(ctx, edit)


def _regressions(ctx: Ctx) -> int:
    """Refuse a queue that lost a finished card or evidence relative to another copy (W1930).

    Returns:
        EXIT_OK when nothing was lost; EXIT_REFUSED, with each loss on stderr, when something was
        or when the file is not one queue document.

    """
    raw = _json_file(Path(ctx.get("regressions") or ""))
    if not isinstance(raw, dict):
        _warn("--regressions FILE holds one queue document")
        return EXIT_REFUSED
    found = regressions.lost(cast("dict[str, object]", raw), store.load(ctx.path).doc)
    for line in found:
        _warn(line)
    return EXIT_REFUSED if found else EXIT_OK


def _add_retro(ctx: Ctx) -> int:
    """Add one retro record from a JSON file, minting its id (W1918, nemik:W982).

    Returns:
        EXIT_OK; EXIT_REFUSED when the file is not one object or the record fails
        `retros.retro_refusals`, which is said on stderr and changes nothing.

    """
    raw = _json_file(Path(ctx.get("add_retro") or ""))
    if not isinstance(raw, dict):
        _warn("--add-retro FILE holds one JSON object")
        return EXIT_REFUSED
    retro = cast("dict[str, object]", raw)
    repo = inbound.repo_name(ctx.path)

    def edit(state: State) -> int:
        try:
            ident = retros.add_retro(state.doc, repo, retro)
        except ValueError as refusal:
            _warn(f"--add-retro refused: {refusal}")
            return EXIT_REFUSED
        _say(f"{ident} added")
        return EXIT_OK

    return _mutate(ctx, edit)


def _migrate_retros(ctx: Ctx) -> int:
    """Rename `cause` to `root` on host-schema retros, or say which would change (W2091).

    Returns:
        EXIT_OK; with --dry-run nothing is saved and the ids that would change are listed.

    """
    if ctx.opts.get("dry_run"):
        scratch = cast("dict[str, object]", json.loads(json.dumps(store.load(ctx.path).doc)))
        _say(f"WOULD MIGRATE {' '.join(retros.migrate(scratch)) or 'none'}")
        return EXIT_OK

    def edit(state: State) -> int:
        _say(f"MIGRATED {' '.join(retros.migrate(state.doc)) or 'none'}")
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
    except Exception as exc:
        if not isinstance(
            exc, (ops.RefusedError, opa_eval.OpaUnavailableError, OSError, ValueError)
        ):
            raise
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
            append(store.sibling(ctx.path, store.LEDGER), own_line(mint, site.now))
            return said, new

    try:
        said, new = locked()
    except Exception as exc:
        if not isinstance(exc, (ops.RefusedError, opa_eval.OpaUnavailableError, ValueError)):
            raise
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
    "tick_roll": _tick_roll,
    "armed": _armed,
    "update": _update,
    "update_many": _update_many,
    "add": _add,
    "drop": _drop,
    "embargo": _embargo,
    "lift_embargo": _lift_embargo,
    "intervention": _intervention,
    "reject_advice": _reject_advice,
    "outcomes_set": _outcomes_set,
    "outcomes_clear": _outcomes_clear,
    "bump_blocked": _bump_blocked,
    "block_matching": _block_matching,
    "freeze": _freeze,
    "warrant": _warrant,
    "prune_landed": _prune_landed,
    "block_behind_open": _block_behind_open,
    "close_umbrellas": _close_umbrellas,
    "reconcile": _reconcile,
    "triage": _triage,
    "lift": _lift,
    "inbound": _inbound,
    "ledger": _ledger_mode,
    "show": _show,
    "blocked_on_list": _blocked_on_list,
    "ready_older_than": _ready_older_than,
    "retros": _retros,
    "commit_message": _commit_message,
    "scan_literal": _scan_literal,
    "preamble_set": _preamble_set,
    "standing": _standing,
    "watchdog_line": _watchdog_line,
    "prompt_ack": _prompt_ack,
    "atomize": _atomize,
    "ready_count": _ready_count,
    "ghosts": _ghosts,
    "standing_set": _standing_set,
    "tick_hooks_set": _tick_hooks_set,
    "preamble_clear": _preamble_clear,
    "init": _init,
    "weights_from": _weights_from,
    "vectors_from": _vectors_from,
    "manifests_from": _manifests_from,
    "add_retro": _add_retro,
    "regressions": _regressions,
    "migrate_retros": _migrate_retros,
    "repair_counter": _repair_counter,
    "overlaps": _overlaps,
    "ics": _ics,
    "export": _export,
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


def _refuse(message: str, args: list[str], opts: dict[str, object]) -> int:
    """Print a usage refusal and ship it as an OTLP record when a sink is configured (W1248).

    Returns:
        EXIT_REFUSED; shipping is best effort and never changes the answer.

    """
    _warn(message)
    state = opts.get("state")
    if state:
        refusal_record.emit(message, args, Path(str(state)).absolute())
    return EXIT_REFUSED


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
        return _refuse(
            f"REFUSED: {', '.join(stray)} does not apply to --{mode.replace('_', '-')}", args, opts
        )
    if mode == "selftest":
        return _selftest()
    state = opts.get("state")
    if not state:
        _warn("REFUSED: --state PATH is required; there is no default root")
        return EXIT_REFUSED
    ctx = Ctx(opts, Path(str(state)).absolute(), datetime.now(UTC))
    if mode not in {"ready_count", "watchdog_line", "show", "blocked_on_list", "ready_older_than"}:
        beat.try_beat(ctx.path, time.time_ns())
    try:
        code = _HANDLERS[mode](ctx)
    except Exception as exc:
        if not isinstance(
            exc, (store.UnreadableStateError, ops.RefusedError, MalformedEntryError, OSError)
        ):
            raise
        return _refuse(f"REFUSED: {exc}", args, opts)
    else:
        if code == EXIT_OK:
            refusal_record.emit_accepted(mode, args, ctx.path)
        return code
