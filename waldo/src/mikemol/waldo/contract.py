# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A waldo's declared contract: parse it, refuse a malformed one, and lint its witnesses (W1056).

The contract is a JSON file the repo tracks (luthen's `checks/apply_sets/<name>.json` is the first
instance). It declares what the waldo may do and how it knows it did it:

    {"_": ["free-text notes, ignored"],
     "root": "host",
     "plan_env": {"NAME": "value"},
     "allowed": [{"address": "...", "actions": ["create"]}],
     "required": [],
     "before": [{"name": "...", "argv": ["..."], "must_contain": ["..."]}],
     "after": [{"name": "...", "argv": ["..."], "json_empty": ["drift"]}]}

⚑ A KEY THAT IS NOT IN THE SCHEMA IS REFUSED, NOT IGNORED. A contract with `alowed` would otherwise
read as one that allows nothing, or as a typo nobody notices; only `_` (notes) is skipped.

⚑ A WITNESS MUST BE ABLE TO FAIL. `lint` runs each witness's judge over readings that carry no
information about the act: an empty output, an empty object and an empty list. A witness that passes
any of them proves nothing (a `must_match` of `.*`, a `must_contain` of the empty text). A witness
that declares no condition at all must say `"exit_only": true`, so "the command ran" is a choice and
not an accident. The two cassian lessons this encodes: a finished oneshot unloads so `show` reads
defaults (the witness must read the journal), and a witness that settles seconds after the act is a
flake.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import cast

from mikemol.waldo.compare import Change, changes_from
from mikemol.waldo.witness import Witness, judge

TOP_KEYS = frozenset({"_", "root", "plan_env", "allowed", "required", "before", "after"})
WITNESS_KEYS = frozenset(
    {
        "name",
        "argv",
        "json_empty",
        "must_contain",
        "must_match",
        "advances",
        "increases",
        "fresh_since",
        "exit_only",
    }
)
PROBES = ("", "{}", "[]")


class ContractError(ValueError):
    """A contract file is not a valid contract."""


@dataclass(frozen=True)
class Contract:
    """A parsed contract: what may change, what must, and the witnesses around the act."""

    root: str = ""
    plan_env: Mapping[str, str] = field(default_factory=dict)
    allowed: frozenset[Change] = frozenset()
    required: frozenset[Change] = frozenset()
    before: tuple[Witness, ...] = ()
    after: tuple[Witness, ...] = ()


def _object(value: object, where: str) -> dict[str, object]:
    """Read `value` as a JSON object.

    Returns:
        the object.

    Raises:
        ContractError: when it is not an object.

    """
    if not isinstance(value, dict):
        msg = f"{where}: expected an object, got {type(value).__name__}"
        raise ContractError(msg)
    return cast("dict[str, object]", value)


def _texts(value: object, where: str) -> tuple[str, ...]:
    """Read `value` as a list of text.

    Returns:
        the texts; an absent list (None) is empty.

    Raises:
        ContractError: when it is not a list of text.

    """
    if value is None:
        return ()
    if not isinstance(value, list):
        msg = f"{where}: expected a list of text, got {type(value).__name__}"
        raise ContractError(msg)
    items = cast("list[object]", value)
    if not all(isinstance(item, str) for item in items):
        msg = f"{where}: every item must be text"
        raise ContractError(msg)
    return tuple(str(item) for item in items)


def _refuse_unknown(fields: dict[str, object], known: frozenset[str], where: str) -> None:
    """Refuse any key outside the schema.

    Raises:
        ContractError: naming the unknown keys.

    """
    unknown = sorted(set(fields) - known)
    if unknown:
        msg = f"{where}: unknown key(s) {', '.join(unknown)}"
        raise ContractError(msg)


def witness_from(value: object, where: str) -> Witness:
    """Read one witness row.

    Returns:
        the Witness.

    Raises:
        ContractError: when the row is not a valid witness.

    """
    fields = _object(value, where)
    _refuse_unknown(fields, WITNESS_KEYS, where)
    name = fields.get("name")
    if not isinstance(name, str) or not name:
        msg = f"{where}: a witness needs a non-empty text name"
        raise ContractError(msg)
    argv = _texts(fields.get("argv"), f"{where}.argv")
    if not argv:
        msg = f"{where}: {name} needs a non-empty argv"
        raise ContractError(msg)
    exit_only = fields.get("exit_only", False)
    if not isinstance(exit_only, bool):
        msg = f"{where}: {name} exit_only must be true or false"
        raise ContractError(msg)
    return Witness(
        name,
        argv,
        json_empty=_texts(fields.get("json_empty"), f"{where}.json_empty"),
        must_contain=_texts(fields.get("must_contain"), f"{where}.must_contain"),
        must_match=_texts(fields.get("must_match"), f"{where}.must_match"),
        advances=_texts(fields.get("advances"), f"{where}.advances"),
        increases=_texts(fields.get("increases"), f"{where}.increases"),
        fresh_since=_texts(fields.get("fresh_since"), f"{where}.fresh_since"),
        exit_only=exit_only,
    )


def _witnesses(value: object, where: str) -> tuple[Witness, ...]:
    """Read a list of witness rows, refusing a repeated name.

    Returns:
        the witnesses in order.

    Raises:
        ContractError: when the value is not a list of witnesses or two share a name.

    """
    if value is None:
        return ()
    if not isinstance(value, list):
        msg = f"{where}: expected a list of witnesses, got {type(value).__name__}"
        raise ContractError(msg)
    rows = cast("list[object]", value)
    found = tuple(witness_from(row, f"{where}[{index}]") for index, row in enumerate(rows))
    names = [w.name for w in found]
    repeated = sorted({name for name in names if names.count(name) > 1})
    if repeated:
        msg = f"{where}: witness name(s) used twice: {', '.join(repeated)}"
        raise ContractError(msg)
    return found


def parse(doc: object) -> Contract:
    """Read a contract from parsed JSON.

    Returns:
        the Contract.

    Raises:
        ContractError: when the document is not a valid contract.

    """
    fields = _object(doc, "contract")
    _refuse_unknown(fields, TOP_KEYS, "contract")
    root = fields.get("root", "")
    if not isinstance(root, str):
        msg = "contract.root: expected text"
        raise ContractError(msg)
    env = _object(fields.get("plan_env", {}), "contract.plan_env")
    if not all(isinstance(value, str) for value in env.values()):
        msg = "contract.plan_env: every value must be text"
        raise ContractError(msg)
    return Contract(
        root=root,
        plan_env={key: str(value) for key, value in env.items()},
        allowed=frozenset(changes_from(fields.get("allowed"), "allowed")),
        required=frozenset(changes_from(fields.get("required"), "required")),
        before=_witnesses(fields.get("before"), "before"),
        after=_witnesses(fields.get("after"), "after"),
    )


def has_condition(witness: Witness) -> bool:
    """Say whether a witness declares anything its output must show.

    Returns:
        True when any of the five condition lists is non-empty.

    """
    return bool(
        witness.json_empty
        or witness.must_contain
        or witness.must_match
        or witness.advances
        or witness.increases
        or witness.fresh_since
    )


def _witness_findings(witness: Witness) -> list[str]:
    """Find what is wrong with one witness.

    Returns:
        a line for a witness with no condition and no `exit_only`, and one per reading it passes.

    """
    if not has_condition(witness):
        if witness.exit_only:
            return []
        return [f"{witness.name}: declares no condition; say exit_only if the exit code is enough"]
    return [
        f"{witness.name}: passes on the reading {probe!r}"
        for probe in PROBES
        if judge(witness, 0, probe).rc == 0
    ]


def lint(contract: Contract) -> list[str]:
    """Find the witnesses that cannot fail, and a required row that is not allowed.

    Returns:
        one line per finding; empty when the contract is sound.

    """
    findings = [
        f"required {address} {'+'.join(actions)} is not in allowed"
        for address, actions in sorted(contract.required - contract.allowed)
    ]
    for witness in (*contract.before, *contract.after):
        findings.extend(_witness_findings(witness))
    return findings
