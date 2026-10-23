# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Cross-apply ordering: a plan that acts on certain addresses needs earlier steps proven (W1853).

Ported from luthen's `checks/opa_plan.py` (lines 796-897, W263), behind `PlanConfig` and `Tools`.

The policy judges ONE plan, so "snapshot before migrate" is not expressible in it. It is declared in
`<policy>/preconditions/data.json` instead: a rule `{name, root, when: [address or prefix*],
requires: [...]}` fires when the plan acts on a `when` address, and each requirement must be PROVEN.

⚑ TWO KINDS OF PROOF, AND NOTHING ELSE: `{"kind": "applied", root, address}` is a ledger entry of a
successful, witnessed apply of that address in that root (a ledger whose chain is broken proves
nothing; `aliases` are other spellings of the same resource; `"witness": false` waives the witness);
`{"kind": "witness", tool, args}` is a command that must exit 0 now. The ledger proof is "happened
at some time", not "still true", so a state that must hold now is a `witness` requirement.

⚑ AN UNKNOWN KIND, AN UNREADABLE DECLARATION AND A MISSING TOOL ARE UNMET, NEVER A PASS: each
returns a message, and `unmet_preconditions` returns one line per requirement not proven.

⚑ A MISSING DECLARATION IS UNMET UNLESS THE CONSUMER SAYS IT HAS NONE: `preconditions_required`
defaults to True, so deleting the file does not switch the ordering rules off; a consumer with no
cross-apply ordering sets it False and an absent file then means no rules (W1855, estate).
"""

from pathlib import Path

from mikemol.waldo.planconfig import PlanConfig
from mikemol.waldo.planjson import Json, as_list, as_object, list_at, parse_object
from mikemol.waldo.planledger import ledger_intact, ledger_path
from mikemol.waldo.plantools import Tools

OK_WITNESS = ("pass", "none-declared")


def rules_from(path: Path) -> list[Json] | str:
    """Read the declared precondition rules.

    Returns:
        the rules, or why the declaration cannot be read.

    """
    try:
        doc = parse_object(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return f"precondition declaration unreadable: {exc}"
    if doc is None or not isinstance(doc.get("rules"), list):
        return "precondition declaration unreadable: no rules list"
    return [as_object(rule) for rule in as_list(doc["rules"])]


def address_matches(address: str, patterns: list[str]) -> bool:
    """Say whether an address equals a pattern or starts with one that ends in `*`.

    Returns:
        True on a match.

    """
    return any(address == p or (p.endswith("*") and address.startswith(p[:-1])) for p in patterns)


def fired_rules(config: PlanConfig, root_name: str, changes: list[str]) -> list[Json] | str:
    """Pick the rules for this root whose `when` matches an address the plan acts on.

    Returns:
        the fired rules, or why the declaration could not be read.

    """
    declaration = config.preconditions_data()
    if not config.preconditions_required and not declaration.exists():
        return []
    rules = rules_from(declaration)
    if isinstance(rules, str):
        return rules
    addresses = [c.rsplit(":", 1)[0] for c in changes]
    return [
        r
        for r in rules
        if r.get("root") == root_name
        and any(address_matches(a, [str(w) for w in as_list(r.get("when"))]) for a in addresses)
    ]


def applied_before(config: PlanConfig, req: Json) -> str | None:
    """Check that the ledger proves the named apply happened.

    The proof is a ledger entry for the root: a successful apply (exit 0) whose resource set
    includes the address (or an alias) and, unless `"witness": false`, whose witness passed or said
    none. A ledger whose chain is broken proves nothing.

    Returns:
        None when it is proven, else why it is not.

    """
    root_name, address = str(req.get("root", "")), str(req.get("address", ""))
    wanted = {address, *(str(a) for a in as_list(req.get("aliases")))}
    path = ledger_path(config, root_name)
    if not path.is_file():
        return f"no apply of root {root_name!r} is recorded"
    if not ledger_intact(path):
        return f"the ledger of root {root_name!r} is not intact"
    need_witness = req.get("witness", True) is not False
    for line in path.read_text(encoding="utf-8").splitlines():
        entry = as_object(parse_object(line))
        witness = as_object(entry.get("witness"))
        seen = {str(c).rsplit(":", 1)[0] for c in as_list(entry.get("changes"))}
        good = witness.get("status") in OK_WITNESS or not need_witness
        if entry.get("apply_exit") == 0 and wanted & seen and good:
            return None
    return f"no successful, witnessed apply of {address!r} in root {root_name!r} is recorded"


def witness_now(tools: Tools, config: PlanConfig, req: Json) -> str | None:
    """Check that the declared command exits 0 right now.

    Returns:
        None when it does, else why not.

    """
    name = str(req.get("tool", ""))
    tool = tools.find(name)
    if tool is None:
        return f"precondition tool {name!r} not found"
    args = [str(a) for a in as_list(req.get("args", []))]
    proc = tools.run(tool, *args, cwd=config.root)
    return None if proc.returncode == 0 else f"{name} {' '.join(args)} exited {proc.returncode}"


def _why(tools: Tools, config: PlanConfig, req: Json) -> str | None:
    # Why one requirement is not proven, or None when it is.
    kind = req.get("kind")
    if kind == "applied":
        return applied_before(config, req)
    if kind == "witness":
        return witness_now(tools, config, req)
    return f"unknown requirement kind {kind!r}"


def unmet_preconditions(
    tools: Tools, config: PlanConfig, root_name: str, changes: list[str]
) -> list[str]:
    """List the preconditions a plan's changes require and that are not proven.

    Returns:
        one message per unmet requirement, or the one reason an unreadable declaration gives.

    """
    fired = fired_rules(config, root_name, changes)
    if isinstance(fired, str):
        return [fired]
    out: list[str] = []
    for rule in fired:
        for req in as_list(rule.get("requires", [])):
            why = _why(tools, config, as_object(req))
            if why is not None:
                out.append(f"PRECONDITION {rule.get('name')}: {why}")
    return out


def fired_names(config: PlanConfig, root_name: str, doc: Json) -> list[str]:
    """Name the precondition rules an apply fell under, for the ledger.

    Returns:
        the rule names, or an empty list when the declaration could not be read.

    """
    fired = fired_rules(config, root_name, [str(c) for c in list_at(doc, "changes")])
    return [] if isinstance(fired, str) else [str(r.get("name")) for r in fired]
