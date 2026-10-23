# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Cross-apply ordering: a plan's changes need earlier steps proven (W1853).

⚑ UNPROVEN IS UNMET: an unreadable declaration, an unknown requirement kind, a ledger with a broken
chain, a failed apply, a failed witness and a missing tool each leave a requirement unmet, and the
control is the same requirement proven by a whole ledger and a passing witness.
"""

import json
from dataclasses import dataclass, replace
from pathlib import Path

from mikemol.waldo import planledger, planprecond
from mikemol.waldo.planconfig import PlanConfig

_TOOL = Path("/usr/bin/probe")
_TWO = 2


@dataclass
class _Done:
    returncode: int
    stdout: str = ""
    stderr: str = ""


class _Tools:
    # A Tools with one tool `probe` whose exit is set, recording the argv it was run with.
    def __init__(self, *, exit_code: int = 0, has_tool: bool = True) -> None:
        self._exit = exit_code
        self._has = has_tool
        self.calls: list[tuple[Path, tuple[str, ...], Path | None]] = []

    def find(self, name: str) -> Path | None:
        return _TOOL if (self._has and name == "probe") else None

    def run(
        self, tool: Path, *args: str, cwd: Path | None = None, stdin_text: str | None = None
    ) -> _Done:
        self.calls.append((tool, (*args, str(stdin_text)), cwd))
        return _Done(self._exit)

    def run_bounded(
        self, tool: Path, *args: str, cwd: Path | None = None, cpu_seconds: int
    ) -> _Done:
        self.calls.append((tool, (*args, str(cpu_seconds)), cwd))
        return _Done(self._exit)


def _rule(name: str, root: str, when: list[str], requires: list[object]) -> dict[str, object]:
    return {"name": name, "root": root, "when": when, "requires": requires}


def _config(tmp: Path, rules: list[dict[str, object]] | None = None) -> PlanConfig:
    policy = tmp / "policy"
    if rules is not None:
        (policy / "preconditions").mkdir(parents=True)
        declared: dict[str, object] = {"rules": rules}
        (policy / "preconditions" / "data.json").write_text(json.dumps(declared), encoding="utf-8")
    return PlanConfig(
        root=tmp,
        terraform=tmp / "terraform",
        policy=policy,
        rego_package="luthen",
        opa_pin="1.20.2",
        user_state=tmp / "state",
    )


def _applied(config: PlanConfig, *, changes: list[str], exit_code: int, witness: str) -> None:
    status: dict[str, object] = {"status": witness}
    entry: dict[str, object] = {"changes": changes, "apply_exit": exit_code, "witness": status}
    planledger.append_ledger(config, "stage2", entry)


_REQ_APPLIED: dict[str, object] = {"kind": "applied", "root": "stage2", "address": "a.snapshot"}


def test_the_declaration_is_read_or_the_reason_it_cannot_be(tmp_path: Path) -> None:
    """A missing file, a file with no rules list and a good one."""
    missing = planprecond.rules_from(tmp_path / "none.json")
    assert isinstance(missing, str)
    assert "unreadable" in missing
    bare = tmp_path / "bare.json"
    bare.write_text("{}", encoding="utf-8")
    assert "no rules list" in str(planprecond.rules_from(bare))
    good = _config(tmp_path, [_rule("r", "stage2", ["x"], [])])
    assert planprecond.rules_from(good.preconditions_data()) == [_rule("r", "stage2", ["x"], [])]


def test_an_address_matches_exactly_or_by_a_star_prefix() -> None:
    """`a.b` equals itself, `a.*` covers a.b and a.c, neither covers z."""
    assert planprecond.address_matches("a.b", ["a.b"])
    assert planprecond.address_matches("a.b", ["x", "a.*"])
    assert not planprecond.address_matches("z", ["a.*", "a.b"])
    assert not planprecond.address_matches("a", ["a.*"])


def test_a_rule_fires_for_its_root_and_a_matching_address_only(tmp_path: Path) -> None:
    """The action suffix is stripped, another root's rule and a non-matching address do not fire."""
    rules = [
        _rule("mine", "stage2", ["a.*"], []),
        _rule("other-root", "host", ["a.*"], []),
        _rule("elsewhere", "stage2", ["z.*"], []),
    ]
    config = _config(tmp_path, rules)
    fired = planprecond.fired_rules(config, "stage2", ["a.migrate:update"])
    assert isinstance(fired, list)
    assert [r["name"] for r in fired] == ["mine"]
    assert planprecond.fired_names(config, "stage2", {"changes": ["a.migrate:update"]}) == ["mine"]
    unreadable = _config(tmp_path / "none")
    assert isinstance(planprecond.fired_rules(unreadable, "stage2", ["a:create"]), str)
    assert not planprecond.fired_names(unreadable, "stage2", {"changes": ["a:create"]})


def test_an_applied_requirement_is_proven_only_by_a_whole_witnessed_successful_ledger(
    tmp_path: Path,
) -> None:
    """The control passes, then a missing ledger, a failed apply, a failed witness do not."""
    config = _config(tmp_path)
    assert "no apply of root" in str(planprecond.applied_before(config, _REQ_APPLIED))
    _applied(config, changes=["a.snapshot:create"], exit_code=1, witness="pass")
    assert "no successful, witnessed apply" in str(planprecond.applied_before(config, _REQ_APPLIED))
    _applied(config, changes=["a.snapshot:create"], exit_code=0, witness="fail")
    assert planprecond.applied_before(config, _REQ_APPLIED) is not None
    _applied(config, changes=["a.snapshot:create"], exit_code=0, witness="pass")
    assert planprecond.applied_before(config, _REQ_APPLIED) is None


def test_the_witness_can_be_waived_and_an_alias_proves_the_same_resource(tmp_path: Path) -> None:
    """`witness: false` accepts a failed witness, and a moved resource's old address counts."""
    config = _config(tmp_path)
    _applied(config, changes=["old.name:create"], exit_code=0, witness="fail")
    aliased: dict[str, object] = {**_REQ_APPLIED, "aliases": ["old.name"]}
    assert planprecond.applied_before(config, aliased) is not None
    waived: dict[str, object] = {**aliased, "witness": False}
    assert planprecond.applied_before(config, waived) is None
    assert planprecond.applied_before(config, {**_REQ_APPLIED, "witness": False}) is not None


def test_a_ledger_with_a_broken_chain_proves_nothing(tmp_path: Path) -> None:
    """The same good entry, but with its predecessor edited, is not a proof."""
    config = _config(tmp_path)
    _applied(config, changes=["x:create"], exit_code=0, witness="pass")
    _applied(config, changes=["a.snapshot:create"], exit_code=0, witness="pass")
    path = planledger.ledger_path(config, "stage2")
    lines = path.read_text(encoding="utf-8").splitlines()
    lines[0] = lines[0].replace('"x:create"', '"y:create"')
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert "not intact" in str(planprecond.applied_before(config, _REQ_APPLIED))


def test_a_missing_declaration_is_unmet_unless_the_consumer_says_it_has_none(
    tmp_path: Path,
) -> None:
    """Deleting the file must not switch the rules off; a consumer with no ordering may."""
    config = _config(tmp_path)
    required = planprecond.unmet_preconditions(_Tools(), config, "stage2", ["a:create"])
    assert len(required) == 1
    assert "unreadable" in required[0]
    free = replace(config, preconditions_required=False)
    assert not planprecond.unmet_preconditions(_Tools(), free, "stage2", ["a:create"])
    assert planprecond.fired_rules(free, "stage2", ["a:create"]) == []
    declared = _config(tmp_path / "x", [])
    still = replace(declared, preconditions_required=False)
    assert planprecond.fired_rules(still, "stage2", ["a:create"]) == []


def test_a_witness_requirement_must_exit_zero_now(tmp_path: Path) -> None:
    """A passing command is met, a failing one says its exit, a missing tool says so."""
    config = _config(tmp_path)
    req: dict[str, object] = {"kind": "witness", "tool": "probe", "args": ["--ok"]}
    ok = _Tools()
    assert planprecond.witness_now(ok, config, req) is None
    assert ok.calls == [(_TOOL, ("--ok", "None"), tmp_path)]
    assert planprecond.witness_now(_Tools(exit_code=4), config, req) == "probe --ok exited 4"
    gone = planprecond.witness_now(_Tools(has_tool=False), config, req)
    assert gone == "precondition tool 'probe' not found"


def test_each_unproven_requirement_is_one_message_and_nothing_unproven_passes(
    tmp_path: Path,
) -> None:
    """An unmet applied, an unknown kind and an unreadable declaration all come back as text."""
    wit: dict[str, object] = {"kind": "witness", "tool": "probe"}
    weird: dict[str, object] = {"kind": "magic"}
    rule = _rule("order", "stage2", ["a.*"], [_REQ_APPLIED, wit, weird])
    config = _config(tmp_path, [rule])
    got = planprecond.unmet_preconditions(_Tools(), config, "stage2", ["a.migrate:update"])
    assert len(got) == _TWO
    assert got[0].startswith("PRECONDITION order: no apply of root")
    assert got[1] == "PRECONDITION order: unknown requirement kind 'magic'"
    nothing = planprecond.unmet_preconditions(_Tools(), config, "stage2", ["z:create"])
    assert nothing == []
    bad = planprecond.unmet_preconditions(_Tools(), _config(tmp_path / "x"), "stage2", ["a:create"])
    assert len(bad) == 1
    assert "unreadable" in bad[0]


def test_when_everything_is_proven_nothing_is_unmet(tmp_path: Path) -> None:
    """The control: the applied proof and a passing witness leave no message."""
    wit: dict[str, object] = {"kind": "witness", "tool": "probe"}
    config = _config(tmp_path, [_rule("order", "stage2", ["a.*"], [_REQ_APPLIED, wit])])
    _applied(config, changes=["a.snapshot:create"], exit_code=0, witness="none-declared")
    assert not planprecond.unmet_preconditions(_Tools(), config, "stage2", ["a.migrate:update"])
