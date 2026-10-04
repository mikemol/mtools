# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The mutation contract: state `--apply` or `--dry-run`, never default, and snapshot on apply.

Ported from paperkit's `tools/edit_snapshot.py`. A tool that rewrites files must STATE its intent,
and the statement is read once, where the operator's request is read, then asked of the context by
every frame below it.

NO DEFAULT IN EITHER DIRECTION (operator, 2026-08-18: "no default-dry, no default-apply, only
explicit behavior"). Both defaults fail SILENTLY and in opposite directions: default-dry does
nothing when the caller meant to write and the caller reads "no changes" as "nothing to change";
default-apply writes when the caller meant to look. Which one you get is a property of whichever
tool you happened to invoke, so the caller cannot carry a habit across tools; the decision has to
be at the call site every time, which means the tool must refuse to guess.

ENFORCED HERE BECAUSE THIS IS WHERE EVERY WRITER ALREADY PASSES. The guard is the one call a rewrite
tool makes before its first write. Putting the check in each tool's main is the many-call-site edit
this code base keeps retiring; putting it at the shared chokepoint means a writer added next month
inherits it without knowing.

IT REFUSES BY DEFAULT AS OF 2026-08-25. An earlier cut was advisory: "flipping this to a hard
refusal in one commit would break every in-flight repair loop, so warn now, measure the population,
refuse when it is paid down." That argument was weighed and REJECTED, kept as residue rather than
forgotten, because the ratchet framing was the wrong shape for this debt. A paydown converges only
if the population SHRINKS; this one grows, since every new writer inherits the guard and, under an
advisory, inherits the lesson that the contract is optional. "Breaks every in-flight repair loop"
reads a refusal as damage when it is the deliverable: the loop's owner states the flag once and
continues. WHAT REPLACES THE RATCHET IS THE ESCAPE HATCH, NOT A GRACE PERIOD: the environment
variable SUBSTRATE_EXPLICIT_MUTATION set to 0 restores the advisory and SAYS SO ON EVERY RUN. A
grace path that warns loudly with a deadline was proposed and rejected: that is the advisory state
renamed, and a deadline in a comment is not a mechanism. The off-switch must announce itself,
because an escape hatch that restores the old behaviour silently is indistinguishable, in any log
read later, from a compliant run, which is how a bypass becomes permanent.

THE THIRD SPELLING IS A HAZARD, NOT A SYNONYM. Three tools spelled no-write as `--dry` and all
three WRITE when it is absent, and none validated argv, so a typo of the dry-run flag fell through
to the writing branch. That is one-spelling census drift in the mutation family: the guard reads
one spelling, the tool dispatches on another, and the gap between them is silent. A near miss is
recognised here so it can be REFUSED WITH A SUCCESSOR, never blessed as an alias: accepting it
would freeze the divergence into the shared authority.

THE RULE FOR WHERE A REFUSAL MAY EXIT, mechanical rather than remembered: inside `cli_main`, or
lexically in an entry point, it may exit; anywhere else it must raise. `require_at_entry` is named
for a POSITION (an entry point, which owns the pid, so it renders and exits 2) and `guard` is named
for an ACT a library performs (which does not own the pid, so it raises). Whoever is on the
command-line side says so in the name they call. Measured, not assumed: the entry-point callers are
bare statements at the top of a tool's own main with no enclosing handler, so an unrendered
exception there would dump a traceback and exit 1 where a clean message and exit 2 used to be, and
in a hook whose stderr is discarded it would degrade to no diagnostic at all.
"""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

from mikemol.treeio.context import (
    INTENT,
    SNAPSHOT_STATE,
    SnapshotState,
    bind_intent,
    resolve_intent,
)
from mikemol.treeio.errors import MutationContractError
from mikemol.treeio.layout import layout
from mikemol.treeio.snapshot import announce, copy_untracked, snapshot

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path

NEAR_MISS_SPELLINGS = {
    "--dry": "--dry-run",
    "--dryrun": "--dry-run",
    "--dry_run": "--dry-run",
    "--apply-all": "--apply",
    "--no-dry-run": "--apply",
    "--write": "--apply",
    "--force": "--apply",
}
"""Spellings recognised so they can be refused with a successor, never accepted as an alias."""

_FLAGS = ("--apply", "--dry-run")
_EXIT_REFUSED = 2


def _unstated_message(label: str, argv: Sequence[str]) -> str:
    """Compose the refusal for an invocation that stated neither flag.

    A REFUSAL MUST NAME ITS SUCCESSOR. A bare "state one" is half a gate: the caller who typed
    `--dry` already believes they stated an intent, and telling them the contract without telling
    them the WORD sends them back to guess again. When a near miss is present the message leads
    with the exact substitution.

    Returns:
        The refusal text.

    """
    msg = (
        f"⚑ {label}: neither --apply nor --dry-run was given.\n"
        "  A mutating tool must not GUESS: default-dry silently does nothing when you "
        "meant to write,\n  default-apply silently writes when you meant to look. "
        "State one."
    )
    near = [a for a in argv if a in NEAR_MISS_SPELLINGS]
    if near:
        sub = "\n".join(f"      {a}  →  {NEAR_MISS_SPELLINGS[a]}" for a in near)
        msg += (
            "\n  ⚑ you typed a NEAR MISS — this tool does not accept it as a "
            f"statement of intent:\n{sub}\n"
            "    the two words the convention declares are `--apply` and "
            "`--dry-run`; there is no third."
        )
    return msg


def require_explicit_mutation(
    label: str, argv: Sequence[str] | None = None, intent: str | None = None
) -> str | None:
    """REFUSE unless the caller stated `--apply` or `--dry-run`. Exactly one, always.

    `intent` states it IN CODE instead of on the command line, for a fixture driving the write path
    against a temp directory, where the process argv carries a selftest flag and the operator asked
    for no mutation at all. It is STILL an explicit statement; what it is not is a reading of the
    wrong argv. An unknown intent is a refusal, never a pass: accepting any truthy value would make
    a typo satisfy the contract silently. The stated intent is resolved against the ambient context,
    not accepted on sight, so a parameter anyone can address positionally becomes a claim checked
    against the invocation.

    A statement on the command line BECOMES the ambient intent for this invocation: argv is read
    ONCE, here, where the operator's request is actually being read, and every callee below asks
    the context instead of re-reading an argv that may be describing another tool's request.
    A flag that merely CONTAINS the word, such as `--apply-all`, does not satisfy it: reading it as
    consent is the substring defect this code base has recorded on operand handling.

    Returns:
        None when an intent was stated, or advisory when the environment off-switch downgraded a
        refusal to a warning.

    Raises:
        MutationContractError: when neither or both flags were stated and the contract is armed.

    """
    if intent is not None:
        resolve_intent(label, stated=intent)
        return None
    given = sys.argv if argv is None else argv
    stated = [f for f in _FLAGS if f in given]
    if len(stated) == 1:
        if INTENT.get() is None:
            value = "apply" if stated[0] == "--apply" else "dry-run"
            bind_intent(value, f"argv at {label} ({stated[0]})")
        return None
    if len(stated) > 1:
        msg = (
            f"⚑ {label}: BOTH --apply and --dry-run given — they are mutually "
            "exclusive. Refusing rather than picking one."
        )
        raise MutationContractError(msg)
    msg = _unstated_message(label, given)
    if os.environ.get("SUBSTRATE_EXPLICIT_MUTATION") != "0":
        raise MutationContractError(msg)
    sys.stderr.write(
        msg + "\n  ⚑ RUNNING UNARMED: SUBSTRATE_EXPLICIT_MUTATION=0 downgraded this "
        "REFUSAL to a warning.\n    This tool may now write without either "
        "--apply or --dry-run having been stated.\n"
    )
    return "advisory"


def guard(
    label: str,
    paths: Sequence[str | Path] = (),
    intent: str | None = None,
    root: str | Path | None = None,
) -> str | None:
    """Check the mutation contract, snapshot, and announce: the one call a writer needs.

    The intent is checked here because this is the one call every writer already makes.

    `intent` is THE FIXTURE ESCAPE, AND IT IS NOT A LOOPHOLE. A fixture drives the write path
    against a TEMP DIRECTORY, so the write is the thing under test rather than a thing the
    operator asked for, and the process argv legitimately carries a selftest flag and neither
    mutation flag. Reading the CALLER'S argv there answers a question nobody asked. The escape is
    `intent="apply"` STATED AT THE CALL SITE, the same contract one level in: a fixture that writes
    still has to SAY it writes. Defaulting the parameter to "assume test" would re-create the
    silent default this exists to remove, in the one place where a wrong guess is invisible.

    `guard` IS ON THE LIBRARY SIDE OF THE LINE AND THEREFORE RAISES. It is named for an ACT a
    library performs, so it never ends a pid it does not own. WHAT THIS MEANS FOR A CALLER THAT
    WRAPS THIS CALL IN AN except CLAUSE FOR Exception, which was the shape of thirty-one measured
    call sites: that handler means "a snapshot is best-effort", is RIGHT about that, and is wrong
    only about a MUTATION-CONTRACT refusal, which is not a failed snapshot. `MutationContractError`
    derives from BaseException precisely so those handlers keep containing what they meant to
    contain: the refusal passes through and the write does not happen. A caller that genuinely
    wants to contain one names it, which is a statement, not an accident.

    Returns:
        The snapshot sha, or None when there is no snapshot to be had.

    """
    require_explicit_mutation(label, intent=intent)
    sha = snapshot(label, paths, root)
    announce(sha, label)
    return sha


def snapshot_once(
    label: str,
    paths: Sequence[str | Path] = (),
    intent: str | None = None,
    root: str | Path | None = None,
) -> str | None:
    """Take the worktree sha once per invocation, but COPY EVERY untracked path.

    This replaces the hand-rolled once-per-run helpers, and it is not a rename. Each of those was a
    latch over a module-level list, which arms on file one and does nothing after. That is right
    for the stash (whole-worktree, so a second one is waste) and WRONG for the per-path copy of
    untracked files: files two to N of every multi-file run were never copied aside. The two halves
    have different arities and the latch could only express one of them. So the state is split by
    kind: the sha is taken once and the copies accumulate.

    PER-INVOCATION, NOT PER-PROCESS. A module global survives across an in-process second run (a
    library caller, a selftest sweep) and silently suppresses its snapshot entirely; a ContextVar
    unwinds with the scope that set it.

    IT CHECKS THE MUTATION CONTRACT, AND WITHOUT THIS IT WAS A SILENT DOWNGRADE. Every hand-rolled
    helper called the guard, which is the contract check plus a snapshot plus the announcement.
    Calling the snapshot directly would have removed the stated-intent check from every writer at
    the moment they were consolidated: a deduplication that silently deletes a contract is the
    regression shape that looks like progress. The check is per-INVOCATION like the sha, since it
    is a question about how the process was invoked.

    `intent` exists because one caller genuinely needs it: its polarity is inverted (the flagged
    check is the read and the bare invocation is the writer), and a hook invokes the check, so an
    argv-reading guard would refuse and abort every commit.

    Returns:
        The snapshot sha, or None when there is no snapshot to be had.

    """
    require_explicit_mutation(label, intent=intent)
    state = SNAPSHOT_STATE.get()
    if state is None:
        state = SnapshotState(sha=None, label=label)
        SNAPSHOT_STATE.set(state)
    if state.sha is None:
        state.sha = snapshot(label, paths, root) or ""
        announce(state.sha or None, label)
    elif paths:
        copy_untracked(layout(root), paths)
    return state.sha or None


def require_at_entry(
    label: str,
    argv: Sequence[str] | None = None,
    intent: str | None = None,
    paths: Sequence[str | Path] = (),
    *,
    store: bool = False,
) -> str | None:
    """State the intent BEFORE any dispatch; on `--apply`, take the snapshot in the same act.

    THE BINDING IS THE POINT (operator, 2026-08-25): "the snapshot device [should] be mandatory
    every time a non-dry-run is performed on something other than a database. (And it needs to be
    triggered at the same place as the gate for live vs dry, else it will get missed downstream for
    the same reason the gate was.)" The parenthetical is the whole design.

    Until then they were two calls with two placements and nothing bound them, and that decoupling
    was the recurrence vector. A census found EIGHT tools split: each had paid down the entry-point
    gate by moving its intent check to entry while still snapshotting at the first pending write, so
    they read compliant and were unprotected in practice. A read-only mode, a dry run that restores,
    or a run that finds nothing to change never reaches a snapshot placed at the write. The guard
    was consulted at the write, and the question is asked at the INVOCATION. And the placement is
    the judgement being eliminated: a guard at the write encodes the tool author's one-time
    decision about which paths are read-only, which every caller inherits silently forever. At
    entry the caller states it, per invocation, out loud, including for an invocation that would
    only have read, so there is deliberately NO read-path exemption.

    `paths` is what a snapshot would copy. `store=True` declares that this tool's writes land in the
    STORE, where a file snapshot is NOT APPLICABLE, and the notice says so instead of claiming one:
    printing "snapshot taken" there would be a FALSE ASSURANCE, strictly worse than silence, because
    the operator reads it as recoverable and it is not. Naming the substitute is the other half.

    It is not a fourth body: it delegates to `require_explicit_mutation`, the one authority, and to
    `guard`, the one snapshot, and adds only the SELFTEST CARVE-OUT, a fact about ORDER rather than
    about intent. A selftest invocation exits before dispatch, so a guard placed ahead of it would
    refuse the one invocation that asks the tool to check itself. If moving a guard breaks a
    selftest, the guard is too early, and this is where that lives, once. An explicit intent still
    wins over the carve-out: a fixture that writes must still say it writes.

    THIS FRAME IS THE COMMAND-LINE BOUNDARY, and the one place in the contract that may still exit.
    It renders only this package's own stated refusals, so a bug in the body still surfaces as a
    traceback.

    Returns:
        selftest for the carve-out, otherwise the verdict of the contract check: None, or advisory.

    """
    given = sys.argv if argv is None else argv
    if intent is None and "--selftest" in given:
        return "selftest"
    try:
        verdict = require_explicit_mutation(label, argv=given, intent=intent)
    except MutationContractError as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(_EXIT_REFUSED)
    stated_apply = intent == "apply" or (intent is None and "--apply" in given)
    if not stated_apply:
        return verdict
    if store:
        sys.stderr.write(
            f"   ⚑ {label}: snapshot NOT APPLICABLE — this tool's writes land in the "
            "STORE, not the filesystem.\n"
            "     A file copy cannot capture them. Its protection is the stated "
            "--dry-run plus the\n"
            "     transaction boundary; there is no snapshot to recover from.\n"
        )
        return verdict
    guard(label, paths=paths, intent=intent or "apply")
    return verdict


def cli_main(fn: Callable[[], int | None]) -> int | None:
    """Run `fn` at the command-line boundary: the ONE place a refusal becomes an exit code.

    Everything above raises; this renders. It catches `MutationContractError`, NOT Exception, so a
    genuine bug in the body still surfaces as a traceback and only this package's own stated
    refusals are rendered. Rendering the message and returning 2 reproduces the exit-and-message
    behaviour at a command-line boundary, while a LIBRARY caller gets an exception it can contain
    instead of a dead interpreter. A tool whose main dispatches into work that calls the guard wraps
    that dispatch: `sys.exit(cli_main(run) or 0)`. Unlike paperkit's version it takes a callable of
    no arguments, since a strictly typed signature cannot forward positional and keyword arguments.

    Returns:
        What `fn` returns, or 2 after writing the refusal to stderr.

    """
    try:
        return fn()
    except MutationContractError as e:
        sys.stderr.write(str(e) + "\n")
        return _EXIT_REFUSED
