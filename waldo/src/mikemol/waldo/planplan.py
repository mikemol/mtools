# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Make the plan, read what it would do, and record the verdict bound to it (W1854).

Ported from luthen's `checks/opa_plan.py` (lines 363-448), behind `PlanConfig` and `Tools`.

⚑ A SAVED PLAN, SO THE THING JUDGED IS THE THING APPLIED: `tofu plan -out <planfile>`, then
`tofu show -json <planfile>`, and the verdict is keyed by the planfile's hash (planverdict). A plan
that produced no planfile is a reason, not a verdict, and a failed `show` is too.

⚑ `-lock=false` ONLY WHEN THE STATE IS READ-ONLY TO THIS USER: a root-applied root's state file is
root-owned, the local backend locks by opening it for WRITE, and an unprivileged plan then fails.
Skipping the lock cannot admit a stale change: the apply takes the lock and refuses a saved plan
whose state moved (luthen, W53, measured 2026-09-24).

⚑ THE VERDICT IS WRITTEN WHATEVER IT WAS: a denial is recorded as well as an admission, sealed, with
the policy digest, so a policy edit after the plan voids it. A root-owned state directory gets mode
0755 so the planner can read what it cannot write.

⚑ THE DESTROY LIST'S DIGEST IS RECORDED WHEN THE FILE EXISTS (`destroys_sha256`) and is empty
when the consumer has none, where luthen's code required the file.
"""

import json
import os
from collections.abc import Mapping
from pathlib import Path

from mikemol.waldo.planconfig import PlanConfig
from mikemol.waldo.planjson import Json, as_list, as_object, list_at
from mikemol.waldo.plantools import Tools
from mikemol.waldo.planverdict import policy_digest, seal_of, sha256_of, verdict_path

STATE_DIR_MODE = 0o755
RECORD_MODE = 0o644
QUIET_ACTIONS = (["no-op"], ["read"])
SHOW_ERROR_CHARS = 200


def lock_args(root: Path) -> list[str]:
    """Say whether this user must plan without the state lock.

    Returns:
        `["-lock=false"]` when the root's state file exists and is not writable by this user, else
        an empty list.

    """
    state = root / "terraform.tfstate"
    return ["-lock=false"] if state.exists() and not os.access(state, os.W_OK) else []


def plan_flags(replace: tuple[str, ...], targets: tuple[str, ...]) -> tuple[str, ...]:
    """Spell the addresses to replace and to target as tofu's flags.

    Returns:
        every `-replace=` flag, then every `-target=` flag, in the order given.

    """
    return (*(f"-replace={a}" for a in replace), *(f"-target={a}" for a in targets))


def plan_and_show(
    tools: Tools,
    tofu: Path,
    planfile: Path,
    root: Path,
    flags: tuple[str, ...] = (),
) -> Path | str:
    """Save a plan and its JSON.

    `flags` are the `-replace=` and `-target=` arguments the caller built, passed through as given.

    Returns:
        the plan JSON's path, or why there is none.

    """
    plan = tools.run(
        tofu,
        f"-chdir={root}",
        "plan",
        "-input=false",
        "-no-color",
        *lock_args(root),
        *flags,
        f"-out={planfile}",
    )
    if not planfile.is_file() or planfile.stat().st_size == 0:
        why = (plan.stderr.strip().splitlines() or ["(no output)"])[-1]
        return f"tofu plan produced no planfile (exit {plan.returncode}): {why}"
    show = tools.run(tofu, f"-chdir={root}", "show", "-json", str(planfile))
    if show.returncode != 0:
        return f"tofu show -json failed: {show.stderr.strip()[-SHOW_ERROR_CHARS:]}"
    plan_json = planfile.with_suffix(".json")
    plan_json.write_text(show.stdout, encoding="utf-8")
    return plan_json


def plan_changes(plan: Json) -> list[str]:
    """List every resource a plan would act on.

    Returns:
        the sorted `address:action+action` strings, leaving out no-op and read-only changes.

    """
    out: list[str] = []
    for rc in (as_object(r) for r in list_at(plan, "resource_changes")):
        change = as_object(rc.get("change"))
        actions = [str(a) for a in as_list(change.get("actions"))]
        if actions and actions not in QUIET_ACTIONS:
            out.append(f"{rc.get('address')}:{'+'.join(actions)}")
    return sorted(out)


def _destroys_digest(config: PlanConfig) -> str:
    # The digest of the allowed-destroys list, or '' when the consumer has none.
    path = config.allowed_destroys()
    return sha256_of(path) if path.is_file() else ""


def record_verdict(
    config: PlanConfig,
    planfile: Path,
    outcome: tuple[int, list[str], list[str]],
    extra: Json | None = None,
    declarations: Mapping[str, str] | None = None,
) -> Path:
    """Write the verdict bound to the planfile's hash, whatever the verdict was.

    `outcome` is (exit code, deny messages, withheld messages); `extra` carries what was judged
    besides: the root, the resource set, the targets. `declarations` is what the loader is
    given, so the recorded digest is the one `load_verdict` recomputes (W1859).

    Returns:
        the record's path, under the state directory of the root named in `extra`.

    """
    code, deny, withheld = outcome
    extra = extra or {}
    doc: Json = {
        "planfile": str(planfile),
        "sha256": sha256_of(planfile),
        "exit": code,
        "deny": deny,
        "withheld": withheld,
        "policy_sha256": policy_digest(config, declarations),
        "destroys_sha256": _destroys_digest(config),
        **extra,
    }
    doc["seal"] = seal_of(doc)
    state = config.state_dir(str(extra.get("root", "")))
    record = verdict_path(state, str(doc["sha256"]))
    record.parent.mkdir(parents=True, exist_ok=True)
    if config.root_state is not None and state == config.root_state:
        for made in (record.parent.parent, record.parent):
            made.chmod(STATE_DIR_MODE)
    record.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    record.chmod(RECORD_MODE)
    return record
