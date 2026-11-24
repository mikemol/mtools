# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The plan-admit-apply flow and its exit codes (W1855).

Ported from luthen's `checks/opa_plan.py` (lines 540-571, 618-646, 899-981), behind `PlanConfig`,
`Tools` and the consumer's `Seams`. The pieces it joins are the other plan modules: `planplan`
(plan and record), `planeval` (judge), `planverdict` (admit), `planledger` (record the apply),
`planwitness` and `planprecond` (prove what came before and after).

⚑ THE EXIT CODES ARE LUTHEN'S CONTRACT, NOT THE FLEET TABLE'S (corpus/exit-table.json reads CANNOT
as 7 and HELD as 6, while luthen's units and scripts read 2 and 3): 0 admitted or applied and
witnessed, 1 a rule measured a defect (DENY), 2 the question could not be asked or the act was
refused (STOPPED, named so the table's CANNOT is not claimed), 3 a check could not be
measured or a precondition is unproven (WITHHELD), 4 the apply HAPPENED and its witness failed or
could not run (WITNESS). Unmeasured is never a pass.

⚑ `confirm_and_apply` IS THE ONLY CALL SITE OF `tofu apply`: the verdict must be 0 for THESE bytes
and THIS root, the judged resource set must be unchanged, every precondition proven, and then
(unless `assume_yes`) one y/N on a terminal. `assume_yes` replaces the human and never the verdict.

⚑ THE APPLY IS RECORDED EVEN WHEN IT FAILED, AND A LEDGER THAT COULD NOT BE WRITTEN IS LOUD: the
apply happened, so the message says so and the exit is the witness code after a success.

⚑ THE CONSUMER'S SEAMS ARE ALL IN `Seams`: where output goes, the clock, extra policy data, a
pre-plan check of its own (luthen's portage dry run), the run-record fields, the effective uid,
the rerun hint, whether a terminal is there to ask, the answer, and a guard held around the apply
(luthen ignores SIGHUP there). Each defaults to the plain behaviour.
"""

import sys
from collections.abc import Callable, Mapping, Sequence
from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass, field
from pathlib import Path

from mikemol.waldo.planconfig import PlanConfig
from mikemol.waldo.planeval import Evidence, evaluate, refuse_unless, reported_of
from mikemol.waldo.planjson import Json, as_object, list_at, parse_object
from mikemol.waldo.planledger import append_ledger, current_applier, repo_commit
from mikemol.waldo.planplan import (
    UndecidablePlanError,
    exclude_refusal,
    plan_and_show,
    plan_changes,
    plan_flags,
    plan_has_work,
    record_verdict,
    unheld_excludes,
)
from mikemol.waldo.planprecond import fired_names, unmet_preconditions
from mikemol.waldo.planreading import READ, Prior
from mikemol.waldo.plantools import Tools
from mikemol.waldo.planverdict import load_verdict
from mikemol.waldo.planwitness import run_witness, store_witness, take_reading

EXIT_OK = 0
EXIT_DENY = 1
EXIT_STOPPED = 2
EXIT_WITHHELD = 3
EXIT_WITNESS = 4
WITNESS_OK = ("pass", "none-declared")


def exclude_stopped(seams: "Seams", tofu: Path, excludes: tuple[str, ...]) -> int | None:
    """Stop a plan that excludes addresses when this tofu cannot, naming why (W2872).

    Returns:
        the STOPPED exit code with the reason said, or None when there is no exclude or the tofu
        can plan with it.

    """
    reason = exclude_refusal(seams.tools, tofu) if excludes else None
    if reason is None:
        return None
    seams.out(f"opa_plan A: {reason}\n")
    return seams.exits.stopped


def unheld_stopped(seams: "Seams", shown_json: Path, excludes: tuple[str, ...]) -> int | None:
    """Stop a plan whose excluded addresses name nothing it holds, one line each (W2872).

    Returns:
        the STOPPED exit code with every unheld address said, or None when all are held.

    """
    plan = as_object(parse_object(shown_json.read_text(encoding="utf-8")))
    problems = unheld_excludes(plan, excludes)
    if not problems:
        return None
    seams.out("".join(f"opa_plan A: exclude {line}\n" for line in problems))
    return seams.exits.stopped


@dataclass(frozen=True, slots=True)
class ExitCodes:
    """The failing exit numbers of plan admission, as the consumer's tools spell them (W1858).

    Success is 0 for everyone: admission reads a recorded verdict of exit 0, so OK is not here.
    `deny` is a rule that measured a defect and also a failed apply; `stopped` is a run that
    could not be judged or was not confirmed; `withheld` is a check that could not be measured
    or a precondition not proven; `witness` is an apply that happened but whose witness or
    ledger did not pass.
    """

    deny: int = EXIT_DENY
    stopped: int = EXIT_STOPPED
    withheld: int = EXIT_WITHHELD
    witness: int = EXIT_WITNESS


LUTHEN = ExitCodes()


def say(text: str) -> None:
    """Write and flush `text` to stdout, surviving a gone terminal.

    After an ssh drop stdout is a dead tty or a closed pipe and the write raises; the apply and its
    ledger line must not die on that (luthen W353).
    """
    try:
        sys.stdout.write(text)
        sys.stdout.flush()
    except (OSError, ValueError):
        return


def _no_pre_plan(_root: Path) -> int | None:
    # The default pre-plan check: none.
    return None


def _no_data() -> AbstractContextManager[Sequence[Path]]:
    # The default extra policy data: none.
    return nullcontext(())


def _no_fields() -> Json:
    # The default run-record fields: none.
    return {}


def _no_guard() -> AbstractContextManager[None]:
    # The default guard held around the apply: none.
    return nullcontext()


def _no_answer() -> str:
    # The default answer to the confirmation: none.
    return ""


@dataclass(frozen=True)
class Seams:
    """Everything the flow takes from its consumer, each defaulting to the plain behaviour."""

    tools: Tools
    config: PlanConfig
    now: Callable[[], str]
    euid: int
    rerun_hint: str = ""
    out: Callable[[str], None] = say
    declarations: Mapping[str, str] = field(default_factory=dict)
    data: Callable[[], AbstractContextManager[Sequence[Path]]] = _no_data
    pre_plan: Callable[[Path], int | None] = _no_pre_plan
    run_fields: Callable[[], Json] = _no_fields
    guard: Callable[[], AbstractContextManager[None]] = _no_guard
    interactive: bool = False
    answer: Callable[[], str] = _no_answer
    exits: ExitCodes = LUTHEN


def judge(
    seams: Seams,
    binaries: tuple[Path, Path],
    root: Path,
    planfile: Path,
    flags: tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]],
) -> int:
    """Plan to `planfile`, evaluate the policy, record the verdict.

    `binaries` is (tofu, opa); `flags` is (replace, target, exclude addresses). An exclude is
    DEFERRED (W2872): recorded by address in the verdict, never read as installed or clean.

    Returns:
        the verdict's exit code: OK, DENY, WITHHELD, or CANNOT when it could not be judged.

    """
    targets, excludes = flags[1], flags[2]
    config, out = seams.config, seams.out
    if (stopped := exclude_stopped(seams, binaries[0], excludes)) is not None:
        return stopped
    shown_json = plan_and_show(seams.tools, binaries[0], planfile, root, plan_flags(*flags))
    if isinstance(shown_json, str):
        out(f"opa_plan A: {shown_json}\n")
        return seams.exits.stopped
    if (unheld := unheld_stopped(seams, shown_json, excludes)) is not None:
        return unheld
    with seams.data() as data:
        verdict = evaluate(
            seams.tools, config, binaries[1], Evidence(shown_json, targets, tuple(data), excludes)
        )
    if isinstance(verdict, str):
        out(f"opa_plan A: {verdict}\n")
        return seams.exits.stopped
    deny, withheld = verdict
    shown = as_object(parse_object(shown_json.read_text(encoding="utf-8")))
    changes = plan_changes(shown)
    withheld = [*withheld, *unmet_preconditions(seams.tools, config, root.name, changes)]
    out("".join(f"  DENY  {m}\n" for m in deny) + "".join(f"  HELD  {m}\n" for m in withheld))
    reported = reported_of(shown_json)
    out("".join(f"  NOTE  {m}\n" for m in reported))
    code = seams.exits.deny if deny else (seams.exits.withheld if withheld else EXIT_OK)
    extra: Json = {
        "root": root.name,
        "changes": changes,
        "targets": list(targets),
        "deferred": list(excludes),
        "reported": reported,
    }
    record_verdict(config, planfile, (code, deny, withheld), extra, seams.declarations)
    out(f"opa_plan R: {len(deny)} deny, {len(withheld)} withheld over {planfile}\n")
    return code


def refusal(seams: Seams, root: Path, planfile: Path) -> Json | None:
    """Admit a planfile for a root.

    Returns:
        the verdict when this planfile may be applied to this root, else None (the reason is said).

    """
    doc = load_verdict(seams.config, planfile, seams.declarations)
    if isinstance(doc, str):
        seams.out(f"opa_plan --apply: REFUSED -- {doc}\n")
        return None
    if doc.get("root") != root.name:
        seams.out(
            f"opa_plan --apply: REFUSED -- {planfile} was judged for root "
            f"{doc.get('root')!r}, not {root.name!r}\n"
        )
        return None
    return doc


class PlanRefusedError(Exception):
    """A planfile that may not be applied; `message` is what to say, empty when already said."""

    def __init__(self, message: str) -> None:
        """Carry the refusal's message."""
        super().__init__(message)
        self.message = message


@dataclass(frozen=True, slots=True)
class Judged:
    """A planfile read once: its JSON and whether applying it would change anything."""

    plan: Json
    has_work: bool


def admitted(seams: Seams, root: Path, planfile: Path) -> Json:
    """Admit a planfile for a root, as `refusal` does, but by raising.

    Returns:
        the verdict.

    Raises:
        PlanRefusedError: when it may not be applied (the reason is already said).

    """
    doc = refusal(seams, root, planfile)
    if doc is None:
        already_said = ""
        raise PlanRefusedError(already_said)
    return doc


def judged_plan(seams: Seams, tofu: Path, root: Path, planfile: Path, doc: Json) -> Judged:
    """Read the planfile on disk once, and check it still acts on exactly the judged resource set.

    Returns:
        the plan's JSON and its work decision, both from the one read.

    Raises:
        PlanRefusedError: when the set moved, the JSON is unreadable, or it has no
            `resource_changes` list.

    """
    shown = seams.tools.run(tofu, f"-chdir={root}", "show", "-json", str(planfile))
    parsed = parse_object(shown.stdout)
    now = ["(unreadable)"] if parsed is None else plan_changes(parsed)
    if parsed is None or shown.returncode != 0 or now != doc.get("changes"):
        msg = (
            f"opa_plan --apply: REFUSED -- the planfile's resource set {now} is not the judged "
            f"set {doc.get('changes')}"
        )
        raise PlanRefusedError(msg)
    try:
        return Judged(parsed, plan_has_work(parsed))
    except UndecidablePlanError as exc:
        msg = f"opa_plan --apply: REFUSED -- {exc}"
        raise PlanRefusedError(msg) from exc


def ledger_entry(seams: Seams, root: Path, doc: Json, apply_rc: int, witness: Json) -> Json:
    """Assemble the ledger entry for one apply.

    Returns:
        who, when, what, under which policy, witnessed.

    """
    return {
        "when": seams.now(),
        **seams.run_fields(),
        **current_applier(),
        "root": root.name,
        "planfile_sha256": doc.get("sha256"),
        "policy_sha256": doc.get("policy_sha256"),
        "destroys_sha256": doc.get("destroys_sha256"),
        "changes": doc.get("changes"),
        "preconditions": fired_names(seams.config, root.name, doc),
        **repo_commit(seams.tools, seams.config),
        "apply_exit": apply_rc,
        "witness": {k: witness.get(k) for k in ("status", "exit", "why")},
    }


def after_apply(seams: Seams, root: Path, doc: Json, apply_rc: int, prior: Prior) -> int:
    """Witness, then write the ledger entry.

    A failed apply is DENY, no witness runs (nothing to witness), and the ledger still records the
    attempt. After a successful apply, a witness that failed or could not run, or a ledger that
    could not be written, is WITNESS, loudly: the apply happened.

    Returns:
        the process exit code.

    """
    config, out = seams.config, seams.out
    witness: Json = {"status": "not-run", "why": "the apply failed"}
    if apply_rc == 0:
        witness = run_witness(seams.tools, config, root.name, seams.now(), prior)
        store_witness(config, root.name, str(doc["sha256"]), witness)
    try:
        where = append_ledger(config, root.name, ledger_entry(seams, root, doc, apply_rc, witness))
    except OSError as exc:
        out(f"opa_plan ledger: NOT WRITTEN ({exc}) -- THE APPLY HAPPENED\n")
        return seams.exits.deny if apply_rc != 0 else seams.exits.witness
    out(f"opa_plan ledger: appended to {where}\n")
    if apply_rc != 0:
        return seams.exits.deny
    status = witness["status"]
    if status in WITNESS_OK:
        out(f"opa_plan witness: {status} {witness.get('why', '')}\n")
        return EXIT_OK
    out(
        f"opa_plan witness: {str(status).upper()} -- THE APPLY HAPPENED but its witness did not "
        f"pass: {witness.get('why') or witness.get('stdout_tail')}\n"
    )
    return seams.exits.witness


def _confirmed(seams: Seams) -> int | None:
    # Ask once on a terminal. None when confirmed, else the exit code that stops the run.
    if not seams.interactive:
        seams.out("opa_plan --apply: no terminal to confirm on; not applied\n")
        return seams.exits.stopped
    seams.out("opa_plan --apply: apply exactly this plan? [y/N] ")
    if seams.answer() != "y":
        seams.out("opa_plan --apply: not applied\n")
        return seams.exits.stopped
    return None


def confirm_and_apply(
    seams: Seams, tofu: Path, root: Path, planfile: Path, *, assume_yes: bool = False
) -> int:
    """Apply exactly an admitted planfile: THE ONLY CALL SITE OF `tofu apply`.

    Verdict 0 for these bytes and this root, the judged resource set unchanged, every precondition
    proven, then (unless `assume_yes`) one y/N on a terminal.

    Returns:
        the process exit code.

    """
    try:
        doc = admitted(seams, root, planfile)
        judged = judged_plan(seams, tofu, root, planfile, doc)
    except PlanRefusedError as exc:
        if exc.message:
            seams.out(exc.message + "\n")
        return seams.exits.stopped
    unmet = unmet_preconditions(
        seams.tools, seams.config, root.name, [str(c) for c in list_at(doc, "changes")]
    )
    if unmet:
        seams.out("".join(f"  HELD  {m}\n" for m in unmet))
        seams.out("opa_plan --apply: REFUSED -- a declared precondition is not proven\n")
        return seams.exits.withheld
    show = seams.tools.run(tofu, f"-chdir={root}", "show", "-no-color", str(planfile))
    seams.out(show.stdout)
    if not judged.has_work:
        seams.out("opa_plan --apply: nothing to apply\n")
        return EXIT_OK
    stopped = None if assume_yes else _confirmed(seams)
    if stopped is not None:
        return stopped
    changes = [str(c) for c in list_at(doc, "changes")]
    addresses = tuple(change.rpartition(":")[0] or change for change in changes)
    before = take_reading(seams.tools, seams.config, root.name, addresses)
    if before is not None and before.get("status") != READ:
        seams.out(f"opa_plan --apply: not applied -- {before.get('why')}\n")
        return seams.exits.withheld
    prior = Prior(before, seams.now(), addresses)
    with seams.guard():
        done = seams.tools.run(tofu, f"-chdir={root}", "apply", "-no-color", str(planfile))
        seams.out(done.stdout + done.stderr)
        return after_apply(seams, root, doc, done.returncode, prior)


def preflight(seams: Seams, root: Path) -> tuple[Path, Path] | int:
    """Check the tools, the root and the consumer's own pre-plan check.

    Returns:
        (tofu, opa) when the root may be planned, else the exit code that stops the run.

    """
    tools = refuse_unless(
        seams.tools, seams.config, root, euid=seams.euid, rerun_hint=seams.rerun_hint
    )
    if isinstance(tools, str):
        seams.out(f"opa_plan S: REFUSED -- {tools}\n")
        return seams.exits.stopped
    held = seams.pre_plan(root)
    return tools if held is None else held
