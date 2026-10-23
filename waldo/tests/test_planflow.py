# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The plan-admit-apply flow: every gate stops the apply, and only a whole verdict passes (W1855).

⚑ THE APPLY IS REACHED ONLY THROUGH ITS GATES, AND EACH GATE IS TESTED ALONE: no verdict, a verdict
for another root, a moved resource set, an unproven precondition and a missing terminal each leave
the apply uncalled, while the control applies exactly once. Afterwards a failed apply is recorded
and denied, a witness that cannot run after a success is loud, and an unwritable ledger says the
apply happened.
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from mikemol.waldo import planflow, planjson, planledger, planverdict
from mikemol.waldo.planconfig import PlanConfig

_NOW = "2026-10-23T12:00:00Z"
_TOOLS = {"tofu", "opa", "git", "probe"}
_GONE = "tty gone"


def _plan_text(address: str, action: str) -> str:
    change: dict[str, object] = {"actions": [action]}
    resource: dict[str, object] = {"address": address, "change": change}
    doc: dict[str, object] = {"resource_changes": [resource]}
    return json.dumps(doc)


def _opa_text(deny: list[str], withheld: list[str]) -> str:
    value: dict[str, object] = {"deny": deny, "withheld": withheld}
    expr: dict[str, object] = {"value": value}
    result: dict[str, object] = {"expressions": [expr]}
    doc: dict[str, object] = {"result": [result]}
    return json.dumps(doc)


def _declare_rule(tmp: Path, rule: dict[str, object]) -> None:
    folder = tmp / "policy" / "preconditions"
    folder.mkdir()
    declared: dict[str, object] = {"rules": [rule]}
    (folder / "data.json").write_text(json.dumps(declared), encoding="utf-8")


@dataclass
class _Done:
    returncode: int
    stdout: str = ""
    stderr: str = ""


@dataclass
class _Host:
    # A Tools that plays tofu, opa, git and a witness probe, and records what was run.
    deny: list[str] = field(default_factory=list)
    withheld: list[str] = field(default_factory=list)
    plan_json: str = field(default_factory=lambda: _plan_text("a.x", "create"))
    show_text: str = "Plan: 1 to add\n"
    apply_exit: int = 0
    witness_exit: int = 0
    writes_plan: bool = True
    applied: int = 0
    calls: list[tuple[str, tuple[str, ...]]] = field(default_factory=list)

    def find(self, name: str) -> Path | None:
        self.calls.append(("find", (name,)))
        return Path("/bin") / name if name in _TOOLS else None

    def _opa(self, args: tuple[str, ...]) -> _Done:
        if args == ("version",):
            return _Done(0, "Version: 1.20.2\n")
        return _Done(0, _opa_text(self.deny, self.withheld))

    def _tofu(self, args: tuple[str, ...]) -> _Done:
        sub = args[1]
        if sub == "plan":
            out = next(a for a in args if a.startswith("-out="))[len("-out=") :]
            if self.writes_plan:
                Path(out).write_bytes(b"PLANBYTES")
            return _Done(0 if self.writes_plan else 1, "", "" if self.writes_plan else "no plan")
        if sub == "apply":
            self.applied += 1
            return _Done(self.apply_exit, "applied\n")
        return _Done(0, self.plan_json if "-json" in args else self.show_text)

    def run(
        self, tool: Path, *args: str, cwd: Path | None = None, stdin_text: str | None = None
    ) -> _Done:
        self.calls.append((tool.name, (*args, str(cwd), str(stdin_text))[: len(args)]))
        if tool.name == "opa":
            return self._opa(args)
        if tool.name == "git":
            return _Done(0, "abc123\n")
        if tool.name == "tofu":
            return self._tofu(args)
        return _Done(self.witness_exit)

    def run_bounded(
        self, tool: Path, *args: str, cwd: Path | None = None, cpu_seconds: int
    ) -> _Done:
        return self.run(tool, *args, cwd=cwd, stdin_text=str(cpu_seconds))


@dataclass
class _World:
    tmp: Path
    host: _Host
    out: list[str] = field(default_factory=list)
    interactive: bool = False
    reply: str = "y"
    pre_plan_exit: int | None = None
    tofu: Path = Path("/bin/tofu")
    opa: Path = Path("/bin/opa")
    config: PlanConfig = field(init=False)
    root: Path = field(init=False)
    plan: Path = field(init=False)

    def __post_init__(self) -> None:
        (self.tmp / "policy").mkdir()
        (self.tmp / "policy" / "plan.rego").write_text("package luthen.plan\n", encoding="utf-8")
        self.root = self.tmp / "terraform" / "stage2"
        (self.root / ".terraform").mkdir(parents=True)
        self.plan = self.tmp / "p.tfplan"
        self.config = PlanConfig(
            root=self.tmp,
            terraform=self.tmp / "terraform",
            policy=self.tmp / "policy",
            rego_package="luthen",
            opa_pin="1.20.2",
            user_state=self.tmp / "state",
            trusted_uid=os.getuid(),
            preconditions_required=False,
        )

    def seams(self) -> planflow.Seams:
        return planflow.Seams(
            tools=self.host,
            config=self.config,
            now=lambda: _NOW,
            euid=os.getuid(),
            out=self.out.append,
            pre_plan=lambda _root: self.pre_plan_exit,
            interactive=self.interactive,
            answer=lambda: self.reply,
        )

    def binaries(self) -> tuple[Path, Path]:
        return self.tofu, self.opa

    def judge(self) -> int:
        return planflow.judge(self.seams(), self.binaries(), self.root, self.plan, ((), ()))

    def apply(self, *, yes: bool = True) -> int:
        return planflow.confirm_and_apply(
            self.seams(), self.tofu, self.root, self.plan, assume_yes=yes
        )

    def declare_witness(self) -> None:
        folder = self.tmp / "policy" / "witnesses"
        folder.mkdir()
        declared: dict[str, object] = {"roots": {"stage2": {"tool": "probe"}}}
        (folder / "data.json").write_text(json.dumps(declared), encoding="utf-8")

    def text(self) -> str:
        return "".join(self.out)


def _world(tmp: Path, host: _Host | None = None) -> _World:
    return _World(tmp, host or _Host())


def test_a_clean_plan_is_judged_ok_and_its_verdict_loads(tmp_path: Path) -> None:
    """The control: no denial, no hold, exit 0, a sealed verdict the apply can read back."""
    world = _world(tmp_path)
    assert world.judge() == planflow.EXIT_OK
    assert "0 deny, 0 withheld" in world.text()
    doc = planverdict.load_verdict(world.config, world.plan)
    assert isinstance(doc, dict)
    assert (doc["root"], doc["changes"]) == ("stage2", ["a.x:create"])


def test_a_denial_is_exit_one_with_its_message_and_is_recorded(tmp_path: Path) -> None:
    """DENY prints the message, records exit 1, and the plan is then refused at apply time."""
    world = _world(tmp_path, _Host(deny=["D1"]))
    assert world.judge() == planflow.EXIT_DENY
    assert "  DENY  D1" in world.text()
    assert "was not admitted (exit 1)" in str(planverdict.load_verdict(world.config, world.plan))


def test_a_withheld_check_and_an_unproven_precondition_are_exit_three(tmp_path: Path) -> None:
    """HELD lines for opa's withheld and for a precondition that is not proven."""
    world = _world(tmp_path, _Host(withheld=["W1"]))
    before: dict[str, object] = {"kind": "applied", "root": "stage2", "address": "a.before"}
    rule: dict[str, object] = {
        "name": "order",
        "root": "stage2",
        "when": ["a.*"],
        "requires": [before],
    }
    _declare_rule(tmp_path, rule)
    assert world.judge() == planflow.EXIT_WITHHELD
    assert "  HELD  W1" in world.text()
    assert "  HELD  PRECONDITION order:" in world.text()


def test_a_plan_that_cannot_be_made_is_exit_two_not_a_verdict(tmp_path: Path) -> None:
    """No planfile: the reason is said and nothing is recorded."""
    world = _world(tmp_path, _Host(writes_plan=False))
    assert world.judge() == planflow.EXIT_STOPPED
    assert "opa_plan A: tofu plan produced no planfile" in world.text()
    assert not (tmp_path / "state").exists()


def test_an_admitted_plan_applies_once_and_a_passing_witness_is_exit_zero(tmp_path: Path) -> None:
    """The control: judge, apply with assume_yes, witness passes, the ledger holds the apply."""
    world = _world(tmp_path)
    world.declare_witness()
    assert world.judge() == planflow.EXIT_OK
    assert world.apply() == planflow.EXIT_OK
    assert world.host.applied == 1
    ledger = planledger.ledger_path(world.config, "stage2")
    entry = planjson.parse_object(ledger.read_text(encoding="utf-8")) or {}
    assert (entry["apply_exit"], entry["root"], entry["commit"]) == (0, "stage2", "abc123")
    assert entry["witness"] == {"status": "pass", "exit": 0, "why": None}
    assert planledger.ledger_intact(ledger)


def test_a_witness_that_cannot_run_after_a_success_is_exit_four_and_loud(tmp_path: Path) -> None:
    """No witness declared for the root: the apply happened, and that is said."""
    world = _world(tmp_path)
    world.judge()
    assert world.apply() == planflow.EXIT_WITNESS
    assert "THE APPLY HAPPENED but its witness did not pass" in world.text()


def test_a_failed_apply_is_exit_one_recorded_with_no_witness_run(tmp_path: Path) -> None:
    """The attempt is in the ledger, the witness is not-run, the exit is DENY."""
    world = _world(tmp_path, _Host(apply_exit=1))
    world.declare_witness()
    world.judge()
    assert world.apply() == planflow.EXIT_DENY
    ledger = planledger.ledger_path(world.config, "stage2")
    entry = planjson.parse_object(ledger.read_text(encoding="utf-8")) or {}
    assert entry["apply_exit"] == 1
    assert planjson.as_object(entry["witness"])["status"] == "not-run"


def test_an_unwritable_ledger_is_loud_after_a_success(tmp_path: Path) -> None:
    """The ledger directory cannot be made: NOT WRITTEN, THE APPLY HAPPENED, exit witness."""
    world = _world(tmp_path)
    world.declare_witness()
    world.judge()
    (tmp_path / "state" / "apply-ledger.jsonl").mkdir()
    assert world.apply() == planflow.EXIT_WITNESS
    assert "NOT WRITTEN" in world.text()


def test_no_verdict_or_another_roots_verdict_never_reaches_the_apply(tmp_path: Path) -> None:
    """A planfile never judged, and one judged for another root, are refused with exit two."""
    world = _world(tmp_path)
    world.plan.write_bytes(b"PLANBYTES")
    assert world.apply() == planflow.EXIT_STOPPED
    assert world.host.applied == 0
    world.judge()
    other = world.tmp / "terraform" / "other"
    (other / ".terraform").mkdir(parents=True)
    got = planflow.confirm_and_apply(world.seams(), world.tofu, other, world.plan, assume_yes=True)
    assert got == planflow.EXIT_STOPPED
    assert "judged for root 'stage2', not 'other'" in world.text()
    assert world.host.applied == 0


def test_a_moved_resource_set_is_refused_before_the_apply(tmp_path: Path) -> None:
    """If the planfile now acts on other resources than the judged set, nothing is applied."""
    world = _world(tmp_path)
    world.judge()
    world.host.plan_json = _plan_text("b.y", "delete")
    assert world.apply() == planflow.EXIT_STOPPED
    assert "is not the judged set" in world.text()
    assert world.host.applied == 0


def test_an_unproven_precondition_at_apply_time_is_exit_three_and_not_applied(
    tmp_path: Path,
) -> None:
    """The precondition may have moved since the plan: it is checked again before applying."""
    world = _world(tmp_path)
    probe: dict[str, object] = {"kind": "witness", "tool": "probe"}
    rule: dict[str, object] = {
        "name": "order",
        "root": "stage2",
        "when": ["a.*"],
        "requires": [probe],
    }
    _declare_rule(tmp_path, rule)
    assert world.judge() == planflow.EXIT_OK
    world.host.witness_exit = 1
    assert world.apply() == planflow.EXIT_WITHHELD
    assert "a declared precondition is not proven" in world.text()
    assert world.host.applied == 0


def test_without_assume_yes_it_needs_a_terminal_and_a_yes(tmp_path: Path) -> None:
    """No terminal is exit two, a no is exit two, a yes applies; assume_yes replaces the human."""
    world = _world(tmp_path)
    world.judge()
    assert world.apply(yes=False) == planflow.EXIT_STOPPED
    assert "no terminal to confirm on" in world.text()
    world.interactive, world.reply = True, "n"
    assert world.apply(yes=False) == planflow.EXIT_STOPPED
    assert "not applied" in world.text()
    assert world.host.applied == 0
    world.reply = "y"
    world.apply(yes=False)
    assert world.host.applied == 1


def test_an_empty_plan_is_nothing_to_apply_and_asks_nothing(tmp_path: Path) -> None:
    """`No changes.` is exit zero with no apply and no question."""
    world = _world(tmp_path, _Host(show_text="No changes.\n"))
    world.judge()
    assert world.apply(yes=False) == planflow.EXIT_OK
    assert "nothing to apply" in world.text()
    assert world.host.applied == 0


def test_preflight_returns_the_binaries_or_the_code_that_stops_the_run(tmp_path: Path) -> None:
    """Tools and a pre-plan check: refused is two, a held pre-plan is its code, none passes."""
    world = _world(tmp_path)
    assert world.binaries() == planflow.preflight(world.seams(), world.root)
    world.pre_plan_exit = planflow.EXIT_WITHHELD
    assert planflow.preflight(world.seams(), world.root) == planflow.EXIT_WITHHELD
    bare = tmp_path / "terraform" / "bare"
    bare.mkdir()
    assert planflow.preflight(world.seams(), bare) == planflow.EXIT_STOPPED
    assert "opa_plan S: REFUSED" in world.text()


class _Dead:
    # A stdout that has gone away, as after an ssh drop.
    @staticmethod
    def write(_text: str) -> int:
        raise OSError(_GONE)

    @staticmethod
    def flush() -> None:
        raise OSError(_GONE)


def test_the_default_seams_run_no_pre_plan_check_and_answer_nothing(tmp_path: Path) -> None:
    """A consumer that supplies neither gets the binaries from preflight and a no at the prompt."""
    world = _world(tmp_path)
    plain = planflow.Seams(
        tools=world.host, config=world.config, now=lambda: _NOW, euid=os.getuid(), interactive=True
    )
    assert planflow.preflight(plain, world.root) == world.binaries()
    assert plain.pre_plan(world.root) is None
    assert isinstance(plain.answer(), str)
    assert not plain.answer()
    assert not plain.rerun_hint


def test_say_writes_and_flushes_and_survives_a_gone_terminal(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The apply and its ledger line must not die when stdout is a dead tty or closed pipe."""
    planflow.say("hello\n")
    assert capsys.readouterr().out == "hello\n"
    monkeypatch.setattr("sys.stdout", _Dead())
    planflow.say("lost\n")
