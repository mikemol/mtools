# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The waldo pipeline: lint, precondition, plan, compare, apply the SAME plan, witness (W1059).

Lifted from luthen-observability's `checks/apply_set.py::execute`, with the seams named so a third
waldo supplies only what is its own: how to plan, how to read the plan's changes, how to apply that
plan, and how to run a witness command. The steps, in order, each stopping the run at its failure:

    0. lint the contract; an unsound contract (a witness that cannot fail) is exit 7
    1. `before` witnesses (STAR-S); any failing refuses the run, exit 4
    2. plan FRESH inside the command and keep the artifact; a plan that is not admitted is exit 4
    3. read the plan's changes; unreadable is exit 7
    4. compare with the declared sets; outside `allowed` or missing a `required` row prints the diff
       and the planned rows, applies NOTHING, exit 4
    5. dry run stops here with `matches`
    6. apply the SAME artifact that was compared (skipped for an empty plan: `converged`)
    7. `after` witnesses; the state names the act and whether a witness failed

Exit 0 matched, applied or converged, witnessed; 1 the apply failed; 4 refused (a precondition, the
declared set, or a witness that failed); 7 cannot run (unsound or unreadable, or a witness that
could not be evaluated).

⚑ THE VERDICT IS ONE JSON OBJECT with a fixed state vocabulary, and every tail of command output in
it passes through `scrub` for the secrets the caller holds, so a secret echoed by a command cannot
reach the queue.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from mikemol.waldo.compare import Change, changes_from, compare, render, shown
from mikemol.waldo.contract import lint
from mikemol.waldo.custody import scrub
from mikemol.waldo.witness import capture_before, run_all

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from mikemol.waldo.contract import Contract
    from mikemol.waldo.custody import Secret
    from mikemol.waldo.witness import Result, Run

type Artifact = str
type Verdict = dict[str, object]

# ⚑ THE FLEET EXIT TABLE (corpus/exit-table.json, W1310): a step that RAN AND BROKE is FAILED 1, a
# verdict on the subject (a precondition, the declared set, a witness that failed) is REFUSED 4, and
# anything that could not be evaluated is CANNOT 7, an instrument fault that is never read as
# success and never retried as a deferral. Waldo's old 1 and 2 are read by luthen's apply family.
EXIT_OK = 0
EXIT_FAILED = 1
EXIT_REFUSED = 4
EXIT_CANNOT = 7


@dataclass(frozen=True)
class Seams:
    """What a waldo supplies: plan, read the plan, apply it, run a witness, tell the time."""

    plan: Callable[[Contract], tuple[Artifact | None, str]]
    summarize: Callable[[Artifact, Contract], object]
    apply: Callable[[Artifact, Contract], tuple[int, str]]
    run: Run
    clock: Callable[[], float]
    # ⚑ WHICH NON-ZERO WITNESS RUNS MEASURED NOTHING (W1272): the waldo's own classifier of
    # (exit code, output), written from the environment faults it knows; None means every non-zero
    # exit is a failure, as before.
    unevaluated: Callable[[int, str], bool] | None = None


@dataclass(frozen=True)
class Stop:
    """A run that ends before its end: the exit code and the verdict that says why."""

    code: int
    verdict: Verdict


@dataclass(frozen=True)
class Planned:
    """A plan that is within the declared set: the artifact to apply and its changes."""

    artifact: Artifact
    changes: frozenset[Change]
    rows: list[str]


def verdict_line(verdict: Verdict) -> str:
    """Give the verdict as the one JSON line a caller reads.

    Returns:
        the line, without a newline.

    """
    return json.dumps(verdict, sort_keys=False)


def _results(results: Sequence[Result], secrets: Sequence[Secret]) -> list[Verdict]:
    """Turn witness results into verdict rows, tails scrubbed.

    Returns:
        one row per result.

    """
    return [
        {
            "name": r.name,
            "rc": r.rc,
            "unmet": list(r.unmet),
            "tail": [scrub(line, *secrets) for line in r.tail],
            **({"unevaluated": True} if r.unevaluated else {}),
        }
        for r in results
    ]


def _gate(
    contract: Contract, seams: Seams, started: float, secrets: Sequence[Secret]
) -> Stop | None:
    """Lint the contract and run its preconditions.

    Returns:
        a Stop when the contract is unsound or a precondition failed, else None.

    """
    findings = lint(contract)
    if findings:
        why = "the contract is unsound"
        return Stop(EXIT_CANNOT, {"state": "cannot-run", "why": why, "findings": findings})
    results = run_all(contract.before, seams.run, started=started, unevaluated=seams.unevaluated)
    failed = [r for r in results if r.rc != 0 and not r.unevaluated]
    if failed:
        refusal: Verdict = {"state": "refused", "why": "a precondition failed"}
        return Stop(EXIT_REFUSED, {**refusal, "before": _results(failed, secrets)})
    blind = [r for r in results if r.unevaluated]
    if blind:
        # ⚑ NOTHING WAS APPLIED, AND NOTHING WAS MEASURED: an environment fault in a precondition is
        # "cannot run", not a precondition that failed, so the caller fixes the environment.
        why = "a precondition could not be evaluated"
        unread: Verdict = {"state": "cannot-run", "why": why}
        return Stop(EXIT_CANNOT, {**unread, "before": _results(blind, secrets)})
    return None


def _plan(contract: Contract, seams: Seams, secrets: Sequence[Secret]) -> Planned | Stop:
    """Plan fresh, read the plan, and compare it with the declared sets.

    Returns:
        the Planned artifact when it is within the set, else a Stop.

    """
    artifact, tail = seams.plan(contract)
    if artifact is None:
        refusal: Verdict = {"state": "refused", "why": "the plan was not admitted"}
        return Stop(EXIT_REFUSED, {**refusal, "tail": [scrub(tail, *secrets)]})
    try:
        planned = changes_from(seams.summarize(artifact, contract), "plan")
    except ValueError as problem:
        why = f"cannot read the plan: {problem}"
        return Stop(EXIT_CANNOT, {"state": "cannot-run", "why": why})
    diff = compare(set(contract.allowed), set(contract.required), planned)
    rows = shown(planned)
    if not diff.clean():
        why = "the plan is not within the declared set"
        refusal = {"state": "refused", "why": why, "diff": render(diff), "planned": rows}
        return Stop(EXIT_REFUSED, refusal)
    return Planned(artifact, frozenset(planned), rows)


def _apply(
    contract: Contract, seams: Seams, planned: Planned, secrets: Sequence[Secret]
) -> Stop | None:
    """Apply the compared artifact, unless the plan is empty.

    Returns:
        a Stop when the apply failed, else None.

    """
    if not planned.changes:
        return None
    code, out = seams.apply(planned.artifact, contract)
    if code == 0:
        return None
    failure: Verdict = {"state": "apply-failed", "rc": code, "tail": [scrub(out, *secrets)]}
    return Stop(EXIT_FAILED, {**failure, "planned": planned.rows})


def execute(
    contract: Contract,
    seams: Seams,
    *,
    dry: bool = False,
    secrets: Sequence[Secret] = (),
) -> tuple[int, Verdict]:
    """Run the contract through the seams and say what happened.

    Returns:
        (exit code, verdict); the verdict always has a `state`.

    """
    started = seams.clock()
    stopped = _gate(contract, seams, started, secrets)
    if stopped is not None:
        return stopped.code, stopped.verdict
    prior = capture_before(contract.after, seams.run)
    planned = _plan(contract, seams, secrets)
    if isinstance(planned, Stop):
        return planned.code, planned.verdict
    if dry:
        return EXIT_OK, {"state": "matches", "planned": planned.rows}
    failed_apply = _apply(contract, seams, planned, secrets)
    if failed_apply is not None:
        return failed_apply.code, failed_apply.verdict
    results = run_all(
        contract.after, seams.run, before=prior, started=started, unevaluated=seams.unevaluated
    )
    failed = [r.name for r in results if r.rc != 0 and not r.unevaluated]
    blind = [r.name for r in results if r.unevaluated]
    # ⚑ A REAL FAILURE OUTRANKS AN UNEVALUATED WITNESS: when both occur the state says failed, and
    # `unevaluated` still lists what could not be measured. With none failed and some unevaluated
    # the change may have landed but is not verified, so the exit is not OK either.
    suffix = "-witness-failed" if failed else ("-witness-unevaluated" if blind else "")
    state = ("applied" if planned.changes else "converged") + suffix
    verdict: Verdict = {
        "state": state,
        "planned": planned.rows,
        "witnesses": _results(results, secrets),
        "failed": failed,
        "unevaluated": blind,
    }
    code = EXIT_REFUSED if failed else (EXIT_CANNOT if blind else EXIT_OK)
    return code, verdict
