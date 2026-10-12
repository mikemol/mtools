# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the contract: it parses what luthen's set files hold and refuses what is wrong.

W1056. ⚑ LUTHEN'S REAL SHAPE IS THE POSITIVE CONTROL: a contract in the form of
`checks/apply_sets/main.json` parses and lints clean, so a refusal of a typo'd key, a repeated name,
a witness that cannot fail, or a required row nobody allowed is a refusal of the thing and not of
the format.
"""

from __future__ import annotations

import pytest

from mikemol.waldo.compare import change_of
from mikemol.waldo.contract import ContractError, has_condition, lint, parse, witness_from
from mikemol.waldo.witness import Witness

_NS = 'module.w45.kubernetes_namespace_v1.throwaway["amr-skills"]'
_ROLLED = {
    "name": "grafana-rolled",
    "argv": ["kubectl", "-n", "buildbuddy", "rollout", "status", "deployment/grafana"],
    "must_contain": ["successfully rolled out"],
}
_GOOD = {
    "_": ["notes are free text"],
    "root": "",
    "plan_env": {"TF_VAR_cdi_device_plugin": "true"},
    "allowed": [{"address": _NS, "actions": ["create"]}],
    "required": [],
    "before": [{"name": "tree-clean", "argv": ["git", "status"], "must_match": ["clean"]}],
    "after": [_ROLLED],
}
_WORLD_KINDS = (("advances", r"v=(\d+)"), ("fresh_since", r"ts=(\d+)"), ("json_empty", "x"))


def test_a_contract_of_luthens_shape_parses_and_lints_clean() -> None:
    """The positive control: every field is read and nothing is found wrong."""
    contract = parse(_GOOD)
    assert not contract.root
    assert dict(contract.plan_env) == {"TF_VAR_cdi_device_plugin": "true"}
    assert contract.allowed == {change_of(_NS, ["create"])}
    assert [w.name for w in contract.before] == ["tree-clean"]
    assert contract.after[0].must_contain == ("successfully rolled out",)
    assert not lint(contract)


def test_an_empty_object_is_the_empty_contract() -> None:
    """Every part is optional; an empty contract allows nothing and witnesses nothing."""
    contract = parse({})
    assert not contract.allowed
    assert not contract.after


@pytest.mark.parametrize("doc", ["text", ["list"], 3, None])
def test_a_contract_that_is_not_an_object_is_refused(doc: object) -> None:
    """The top level must be an object."""
    with pytest.raises(ContractError, match="expected an object"):
        parse(doc)


def test_an_unknown_top_level_key_is_refused_not_ignored() -> None:
    """A typo'd `alowed` must not read as a contract that allows nothing."""
    with pytest.raises(ContractError, match=r"unknown key.*alowed"):
        parse({"alowed": []})


def test_an_unknown_witness_key_is_refused() -> None:
    """A witness key outside the six kinds, the name, the argv and exit_only is a typo."""
    row = {"name": "w", "argv": ["x"], "must_contians": ["a"]}
    with pytest.raises(ContractError, match=r"before\[0\]: unknown key"):
        parse({"before": [row]})


@pytest.mark.parametrize(
    ("row", "message"),
    [
        ({"argv": ["x"]}, "non-empty text name"),
        ({"name": "", "argv": ["x"]}, "non-empty text name"),
        ({"name": "w"}, "non-empty argv"),
        ({"name": "w", "argv": []}, "non-empty argv"),
        ({"name": "w", "argv": "x"}, "expected a list of text"),
        ({"name": "w", "argv": ["x", 3]}, "every item must be text"),
        ({"name": "w", "argv": ["x"], "exit_only": "yes"}, "exit_only must be true or false"),
        ({"name": "w", "argv": ["x"], "must_match": "a"}, "expected a list of text"),
    ],
)
def test_a_malformed_witness_is_refused_with_its_reason(row: object, message: str) -> None:
    """Each way a witness row can be wrong has its own message."""
    with pytest.raises(ContractError, match=message):
        witness_from(row, "after[0]")


def test_a_repeated_witness_name_is_refused() -> None:
    """Two witnesses with one name would make a verdict ambiguous."""
    with pytest.raises(ContractError, match="used twice: grafana-rolled"):
        parse({"after": [_ROLLED, _ROLLED]})


def test_plan_env_and_root_must_be_text() -> None:
    """A number where an environment value or the root belongs is refused."""
    with pytest.raises(ContractError, match="every value must be text"):
        parse({"plan_env": {"A": 1}})
    with pytest.raises(ContractError, match="root: expected text"):
        parse({"root": 3})


def test_a_malformed_change_row_is_a_shape_error_not_a_pass() -> None:
    """The compare module's refusal reaches the caller through parse."""
    with pytest.raises(ValueError, match=r"allowed\[0\]"):
        parse({"allowed": [{"actions": ["create"]}]})


def test_a_required_row_that_is_not_allowed_is_a_finding() -> None:
    """A row the plan must contain but that nobody allowed could never be applied."""
    contract = parse({"required": [{"address": _NS, "actions": ["create"]}]})
    assert lint(contract) == [f"required {_NS} create is not in allowed"]


def test_a_witness_with_no_condition_must_say_exit_only() -> None:
    """The exit code alone is a choice that has to be written down."""
    bare = parse({"after": [{"name": "ran", "argv": ["true"]}]})
    assert lint(bare) == ["ran: declares no condition; say exit_only if the exit code is enough"]
    chosen = parse({"after": [{"name": "ran", "argv": ["true"], "exit_only": True}]})
    assert not lint(chosen)


@pytest.mark.parametrize(
    ("kind", "value"),
    [("must_match", ".*"), ("must_contain", ""), ("must_match", "^$")],
)
def test_a_witness_that_passes_on_an_empty_reading_is_a_finding(kind: str, value: str) -> None:
    """A condition satisfied by no information proves nothing."""
    contract = parse({"after": [{"name": "vacuous", "argv": ["x"], kind: [value]}]})
    findings = lint(contract)
    assert findings
    assert findings[0] == "vacuous: passes on the reading ''"


def test_advances_and_fresh_since_and_json_empty_cannot_pass_a_blank_reading() -> None:
    """The three kinds that compare against the world fail every probe, so they lint clean."""
    for kind, value in _WORLD_KINDS:
        contract = parse({"after": [{"name": "w", "argv": ["x"], kind: [value]}]})
        assert not lint(contract), kind


@pytest.mark.parametrize(
    "kind", ["json_empty", "must_contain", "must_match", "advances", "fresh_since"]
)
def test_has_condition_sees_each_of_the_five_lists(kind: str) -> None:
    """Any single non-empty list counts as a declared condition, and none counts as none."""
    assert not has_condition(Witness("w", ("x",)))
    witness = witness_from({"name": "w", "argv": ["x"], kind: ["a"]}, "after[0]")
    assert has_condition(witness)
