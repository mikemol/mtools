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
import re
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
PLAN_ERROR_CHARS = 600
EXCLUDE_SINCE = (1, 9)
"""The first OpenTofu release that plans with `-exclude` (W2872)."""
_TOFU_VERSION = re.compile(r"v(\d+)\.(\d+)")


def plan_failure(stderr: str) -> str:
    """Say why a plan failed, from the whole error block rather than its last line.

    ⚑ THE LAST LINE OF A TOFU ERROR IS RARELY THE CAUSE (luthen-observability:W1968): a state-lock
    failure prints `Error: Error acquiring the state lock`, then the lock's ID, path, operation and
    holder, and ends on a line about how to release it, so reporting only the last line hid what
    the lock was and who held it. Lines before the first `Error` are warnings and are dropped; the
    rest are joined with ` / ` so the verdict stays one line, and the head is kept when it is cut,
    because the summary line comes first.

    Returns:
        the failure text, `(no output)` when stderr held nothing.

    """
    lines = [" ".join(line.split()) for line in stderr.splitlines() if line.strip()]
    start = next((i for i, line in enumerate(lines) if line.startswith("Error")), 0)
    text = " / ".join(lines[start:]) or "(no output)"
    return text if len(text) <= PLAN_ERROR_CHARS else f"{text[:PLAN_ERROR_CHARS]}..."


def lock_args(root: Path) -> list[str]:
    """Say whether this user must plan without the state lock.

    Returns:
        `["-lock=false"]` when the root's state file exists and is not writable by this user, else
        an empty list.

    """
    state = root / "terraform.tfstate"
    return ["-lock=false"] if state.exists() and not os.access(state, os.W_OK) else []


def plan_flags(
    replace: tuple[str, ...], targets: tuple[str, ...], excludes: tuple[str, ...] = ()
) -> tuple[str, ...]:
    """Spell the addresses to replace, target and exclude as tofu's flags.

    Returns:
        every `-replace=` flag, then every `-target=` flag, then every `-exclude=` flag (W2872),
        in the order given.

    """
    return (
        *(f"-replace={a}" for a in replace),
        *(f"-target={a}" for a in targets),
        *(f"-exclude={a}" for a in excludes),
    )


def exclude_refusal(tools: Tools, tofu: Path) -> str | None:
    """Say why `-exclude` cannot be used with this tofu, failing loudly rather than planning wide.

    ⚑ A TOFU THAT DOES NOT KNOW `-exclude` MUST NEVER FALL BACK TO A WHOLE PLAN (github-82): the
    excluded row is the one that fails, so a plan over everything would defer nothing and judge
    the very row the caller meant to hold back.

    Returns:
        the reason, or None when the tofu is at least `EXCLUDE_SINCE`.

    """
    done = tools.run(tofu, "version")
    found = _TOFU_VERSION.search(done.stdout)
    if done.returncode != 0 or found is None:
        return "tofu version could not be read, so -exclude is refused rather than assumed"
    if (int(found[1]), int(found[2])) < EXCLUDE_SINCE:
        return f"tofu {found[0]} cannot -exclude (needs v1.9 or later): refusing, not planning wide"
    return None


def _segments(address: str) -> list[str]:
    # An address split on the dots that are outside brackets and quotes: a key may hold a dot.
    parts: list[str] = []
    depth, quoted, start = 0, False, 0
    for at, char in enumerate(address):
        if char == '"':
            quoted = not quoted
        elif quoted:
            continue
        elif char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
        elif char == "." and depth == 0:
            parts.append(address[start:at])
            start = at + 1
    return [*parts, address[start:]]


def _module_node(config: Json, names: list[str]) -> Json | None:
    # The configuration of the module `module.<a>.module.<b>` names, or None when a call is absent.
    node = config
    for name in names:
        call = as_object(node.get("module_calls")).get(name)
        if not isinstance(call, dict):
            return None
        node = as_object(as_object(call).get("module"))
    return node


def _collect(module: Json, found: set[str]) -> None:
    # Every instance address under a values module, through its child modules.
    found.update(str(as_object(item).get("address")) for item in as_list(module.get("resources")))
    for child in as_list(module.get("child_modules")):
        _collect(as_object(child), found)


def _instances(plan: Json) -> set[str]:
    # The instances the plan knows: those already in the state and those it plans.
    found: set[str] = set()
    prior = as_object(as_object(plan.get("prior_state")).get("values"))
    _collect(as_object(prior.get("root_module")), found)
    _collect(as_object(as_object(plan.get("planned_values")).get("root_module")), found)
    return found


def _unheld(plan: Json, address: str) -> str | None:
    # Why an excluded address names nothing the plan holds, or None when it does.
    segments = _segments(address)
    names: list[str] = []
    while len(segments) > 1 and segments[0] == "module":
        names.append(segments[1].partition("[")[0])
        segments = segments[2:]
    node = _module_node(as_object(as_object(plan.get("configuration")).get("root_module")), names)
    if node is None:
        return "names no module of the configuration"
    resource = ".".join(segment.partition("[")[0] for segment in segments)
    if segments and resource not in {
        str(as_object(item).get("address")) for item in as_list(node.get("resources"))
    }:
        return "names no resource of the configuration"
    if "[" in address and not any(
        held == address or held.startswith(f"{address}.") for held in _instances(plan)
    ):
        return "names an instance that is in neither prior_state nor planned_values"
    return None


def unheld_excludes(plan: Json, excludes: tuple[str, ...]) -> list[str]:
    """Say which excluded addresses name nothing this plan holds (W2872, github-82).

    ⚑ AN EXCLUDE THAT MATCHES NOTHING DEFERS NOTHING AND LOOKS LIKE A DEFERRAL: tofu's plan JSON
    lists only what is planned, so an excluded address is absent from it by construction. Each is
    resolved against the plan's `configuration` (root module and `module_calls`, recursively), and
    an indexed one must also be an instance in `prior_state` or `planned_values`.

    Returns:
        one `address: reason` line per address that is not held, empty when all are.

    """
    return [f"{a}: {why}" for a in excludes if (why := _unheld(plan, a)) is not None]


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
        return (
            f"tofu plan produced no planfile (exit {plan.returncode}): {plan_failure(plan.stderr)}"
        )
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


class UndecidablePlanError(ValueError):
    """A plan whose JSON has no `resource_changes` list to decide from."""


def plan_has_work(plan: Json) -> bool:
    """Decide from the plan's structure whether applying it would change anything.

    The decision is never read from rendered text: `tofu show` renders the content of every planned
    file, so any string a planned file holds can appear in it (W2765).

    Returns:
        True when a resource or an output has an action other than a no-op or a read, else False.

    Raises:
        UndecidablePlanError: when the plan has no `resource_changes` list to decide from.

    """
    if not isinstance(plan.get("resource_changes"), list):
        msg = "the plan's JSON has no resource_changes list"
        raise UndecidablePlanError(msg)
    if plan_changes(plan):
        return True
    outputs = as_object(plan.get("output_changes"))
    return any(
        [str(a) for a in as_list(as_object(o).get("actions"))] not in ([], ["no-op"])
        for o in outputs.values()
    )


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
