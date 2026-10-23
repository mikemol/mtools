# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Judge a plan: the refusals before it, the policy evaluation and the target scope (W1851).

Ported from luthen's `checks/opa_plan.py` (lines 178-258), behind `PlanConfig` and `Tools`.

⚑ THE SEAMS ARE THE CONSUMER'S: opa and tofu are found and run through `Tools`, a consumer's
extra policy data (luthen's `opa_data.materialised()`) comes in as directories to pass to
`opa eval` after the policy and the scope file, and the text that tells an operator how to rerun a
refused plan as root is the consumer's `rerun_hint`. Nothing here names luthen.

⚑ A REFUSAL IS A REASON, AND EVERY ONE OF THEM IS A STOP: no tofu, no pinned opa, a root that was
never initialised, no policy directory, and a root-planned root run by someone who is not the
trusted principal each return the sentence that says why, so an unmeasured plan is never read as a
clean one. The last rule applies only with `root_custody` on, since a consumer with no root-planned
roots has none.

⚑ THE TRUSTED PRINCIPAL IS A UID, NOT ALWAYS ROOT (estate, W1842; the operator's enclave ruling,
estate session d9d766b9 line 3763): `PlanConfig.trusted_uid` is who may plan a root-planned root
and who owns its records. Luthen's is 0, so its behaviour and its wording ("Plan it as root") are
unchanged; a consumer that runs the waldo as a dedicated service identity sets that uid, and root
is then refused for those roots like any other user.

⚑ THE -target SET IS WRITTEN WHERE THE POLICY READS IT (W421): tofu's plan JSON records no targets,
so the gate that passed `-target` is the only witness, and an empty list means UNTARGETED, which the
policy treats as withholding every unmeasured check.

⚑ opa's OUTPUT IS KEPT BESIDE THE PLAN (`<plan>.eval.json`) whether or not it parsed, so a verdict
can be re-read, and `reported_of` reads it back, empty when anything about it is off.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from mikemol.waldo.planconfig import PlanConfig
from mikemol.waldo.planjson import as_list, as_object, list_at, parse_object
from mikemol.waldo.planopa import pinned_opa
from mikemol.waldo.plantools import Tools

TOFU = "tofu"


@dataclass(frozen=True, slots=True)
class Evidence:
    """What a policy evaluation reads: the plan's JSON, its -target set and any extra data."""

    plan_json: Path
    targets: tuple[str, ...] = ()
    extra_data: tuple[Path, ...] = ()


def refuse_unless(
    tools: Tools, config: PlanConfig, root: Path, *, euid: int, rerun_hint: str
) -> tuple[Path, Path] | str:
    """Decide whether the act may run.

    Returns:
        (tofu, opa) when it may, else the reason it may not.

    """
    tofu, opa = tools.find(TOFU), pinned_opa(tools, config.opa_pin)
    if tofu is None:
        return "tofu is not installed"
    if opa is None:
        return f"opa {config.opa_pin} is not installed"
    if not (root / ".terraform").is_dir():
        return f"{root} is not initialised (tofu init)"
    if not config.policy.is_dir():
        return f"{config.policy} does not exist"
    if config.root_custody and root.name in config.root_planned and euid != config.trusted_uid:
        who = "root" if config.trusted_uid == 0 else f"uid {config.trusted_uid}"
        return (
            f"{root} reads root-only targets at refresh (an unprivileged plan ERRORS, which the "
            f"policy refuses). Plan it as {who}: {rerun_hint}"
        )
    return tofu, opa


def scope_file(plan_json: Path, targets: tuple[str, ...]) -> Path:
    """Write the plan's -target set where the policy reads it (`data.plan_scope.targets`).

    Returns:
        the scope file's path, beside the plan JSON.

    """
    path = plan_json.with_suffix(".scope.json")
    scope: dict[str, object] = {"targets": list(targets)}
    document: dict[str, object] = {"plan_scope": scope}
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def _value_of(text: str) -> dict[str, object] | None:
    # The policy's value in `opa eval -f json` output, or None when the shape is not that.
    results = list_at(parse_object(text), "result")
    exprs = list_at(as_object(results[0]), "expressions") if results else []
    value = as_object(exprs[0]).get("value") if exprs else None
    return as_object(value) if isinstance(value, dict) else None


def reported_of(plan_json: Path) -> list[str]:
    """Read the `reported` set of the last evaluation (checks outside the -target closure).

    Returns:
        the messages, or an empty list when the evaluation file is missing or in another shape.

    """
    try:
        text = plan_json.with_suffix(".eval.json").read_text(encoding="utf-8")
    except OSError:
        return []
    value = _value_of(text)
    return [] if value is None else [str(m) for m in as_list(value.get("reported", []))]


def evaluate(
    tools: Tools, config: PlanConfig, opa: Path, evidence: Evidence
) -> tuple[list[str], list[str]] | str:
    """Evaluate the policy over a plan.

    Returns:
        (deny, withheld) from the policy, or the reason it could not be evaluated.

    """
    plan_json = evidence.plan_json
    scope = scope_file(plan_json, evidence.targets)
    args = ["eval", "-f", "json", "-i", str(plan_json), "-d", str(config.policy), "-d", str(scope)]
    for directory in evidence.extra_data:
        args += ["-d", str(directory)]
    proc = tools.run(opa, *args, config.plan_query())
    plan_json.with_suffix(".eval.json").write_text(proc.stdout or proc.stderr, encoding="utf-8")
    if proc.returncode != 0:
        return "opa eval failed: " + (proc.stderr.strip().splitlines() or ["(no output)"])[-1]
    value = _value_of(proc.stdout)
    if value is None:
        return "opa output not in the expected shape"
    deny = [str(m) for m in as_list(value.get("deny", []))]
    withheld = [str(m) for m in as_list(value.get("withheld", []))]
    return deny, withheld
