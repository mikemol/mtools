# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The plan-admission command line: one verified apply line, no overwriting (W1856).

⚑ THE ONLY APPLY LINE IS THE VERIFIED ONE: the line printed after an admission names
`--apply-plan`, a root-planned root's starts with sudo, and a planfile that already holds a plan is
never overwritten. The commands themselves are driven end to end through `main` with a fake host.
"""

import json
import os
import signal
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import cast

from mikemol.waldo import plancli, planflow
from mikemol.waldo.planconfig import PlanConfig

_NOW = "2026-10-23T12:00:00Z"
_TOOLS = {"tofu", "opa", "git", "probe"}
_COMMAND = "python -m the.tool"


def _plan_text() -> str:
    change: dict[str, object] = {"actions": ["create"]}
    resource: dict[str, object] = {"address": "a.x", "change": change}
    doc: dict[str, object] = {"resource_changes": [resource]}
    return json.dumps(doc)


def _opa_text() -> str:
    value: dict[str, object] = {"deny": [], "withheld": []}
    expr: dict[str, object] = {"value": value}
    result: dict[str, object] = {"expressions": [expr]}
    doc: dict[str, object] = {"result": [result]}
    return json.dumps(doc)


@dataclass
class _Done:
    returncode: int
    stdout: str = ""
    stderr: str = ""


@dataclass
class _Host:
    # A Tools that plays tofu, opa and git for a clean plan, counting the applies.
    applied: int = 0
    planned_flags: list[tuple[str, ...]] = field(default_factory=list)
    looked_up: list[str] = field(default_factory=list)

    def find(self, name: str) -> Path | None:
        self.looked_up.append(name)
        return Path("/bin") / name if name in _TOOLS else None

    def _tofu(self, args: tuple[str, ...]) -> _Done:
        sub = args[1]
        if sub == "plan":
            self.planned_flags.append(
                tuple(a for a in args if a.startswith(("-replace", "-target")))
            )
            out = next(a for a in args if a.startswith("-out="))[len("-out=") :]
            Path(out).write_bytes(b"PLANBYTES")
            return _Done(0)
        if sub == "apply":
            self.applied += 1
            return _Done(0, "applied\n")
        return _Done(0, _plan_text() if "-json" in args else "Plan: 1 to add\n")

    def run(
        self, tool: Path, *args: str, cwd: Path | None = None, stdin_text: str | None = None
    ) -> _Done:
        if tool.name == "opa":
            return _Done(0, "Version: 1.20.2\n" if args == ("version",) else _opa_text())
        if tool.name == "tofu":
            return self._tofu(args)
        return _Done(0, f"abc123 {cwd} {stdin_text}\n")

    def run_bounded(
        self, tool: Path, *args: str, cwd: Path | None = None, cpu_seconds: int
    ) -> _Done:
        return self.run(tool, *args, cwd=cwd, stdin_text=str(cpu_seconds))


@dataclass
class _World:
    tmp: Path
    host: _Host = field(default_factory=_Host)
    out: list[str] = field(default_factory=list)
    config: PlanConfig = field(init=False)

    def __post_init__(self) -> None:
        (self.tmp / "policy").mkdir()
        (self.tmp / "policy" / "plan.rego").write_text("package luthen.plan\n", encoding="utf-8")
        for name in ("stage2", "host"):
            (self.tmp / "terraform" / name / ".terraform").mkdir(parents=True)
        self.config = PlanConfig(
            root=self.tmp,
            terraform=self.tmp / "terraform",
            policy=self.tmp / "policy",
            rego_package="luthen",
            opa_pin="1.20.2",
            user_state=self.tmp / "state",
            root_state=self.tmp / "root_state",
            root_planned=frozenset({"host"}),
            trusted_uid=os.getuid(),
            preconditions_required=False,
            temp_prefix="luthen.",
        )

    def seams(self) -> planflow.Seams:
        return planflow.Seams(
            tools=self.host,
            config=self.config,
            now=lambda: _NOW,
            euid=os.getuid(),
            out=self.out.append,
        )

    def main(self, *argv: str) -> int:
        return plancli.main(list(argv), self.seams(), _COMMAND)

    def text(self) -> str:
        return "".join(self.out)


def test_the_parser_reads_every_flag_the_operator_types() -> None:
    """Repeatable --replace and --target, the booleans, and the paths as paths."""
    args = plancli.build_parser().parse_args(
        ["--apply", "--yes", "--replace", "a", "--replace", "b", "--target", "c", "--root", "s2"]
    )
    assert cast("bool", args.apply)
    assert cast("bool", args.yes)
    assert cast("list[str]", args.replace) == ["a", "b"]
    assert cast("list[str]", args.target) == ["c"]
    assert cast("str", args.root) == "s2"
    bare = plancli.build_parser().parse_args([])
    assert not cast("bool", bare.apply)
    assert cast("object", bare.apply_plan) is None
    assert cast("object", bare.verify) is None
    assert cast("object", bare.replace) is None
    assert not cast("str", bare.root)


def test_the_apply_line_is_the_verified_form_with_sudo_only_for_a_root_planned_root(
    tmp_path: Path,
) -> None:
    """User root, a sub-root, the host root under custody and the host root without it."""
    config = _World(tmp_path).config
    plan = Path("/x/p.tfplan")
    main_root = config.terraform
    assert plancli.apply_line(config, main_root, plan, _COMMAND) == (
        f"{_COMMAND} --apply-plan /x/p.tfplan"
    )
    assert plancli.apply_line(config, config.terraform / "stage2", plan, _COMMAND) == (
        f"{_COMMAND} --root stage2 --apply-plan /x/p.tfplan"
    )
    host = plancli.apply_line(config, config.terraform / "host", plan, _COMMAND)
    assert host == f"sudo {_COMMAND} --root host --apply-plan /x/p.tfplan"
    open_config = replace(config, root_custody=False)
    assert not plancli.apply_line(
        open_config, open_config.terraform / "host", plan, "x"
    ).startswith("sudo")


def test_an_existing_plan_is_never_overwritten_and_a_fresh_name_is_fine(tmp_path: Path) -> None:
    """No name gives a temp file with the config's prefix; a named plan with content is refused."""
    config = _World(tmp_path).config
    fresh = plancli.pick_planfile(config, None)
    assert isinstance(fresh, Path)
    assert fresh.name.startswith("luthen.")
    assert fresh.name.endswith(".tfplan")
    full = tmp_path / "full.tfplan"
    full.write_bytes(b"A PLAN")
    refused = plancli.pick_planfile(config, full)
    assert isinstance(refused, str)
    assert "refusing to overwrite" in refused
    empty = tmp_path / "empty.tfplan"
    empty.write_bytes(b"")
    assert plancli.pick_planfile(config, empty) == empty
    assert plancli.pick_planfile(config, tmp_path / "new.tfplan") == tmp_path / "new.tfplan"


def test_sighup_is_ignored_inside_the_guard_and_restored_after() -> None:
    """A dropped ssh must not cut an apply: the disposition is held, then put back."""
    before = signal.getsignal(signal.SIGHUP)
    with plancli.hangup_ignored():
        assert signal.getsignal(signal.SIGHUP) == signal.SIG_IGN
    assert signal.getsignal(signal.SIGHUP) == before


def test_a_plan_is_admitted_and_the_verified_apply_line_is_printed(tmp_path: Path) -> None:
    """Exit 0, ADMITTED, the apply line with the planfile, the survive hint, and no apply."""
    world = _World(tmp_path)
    plan = tmp_path / "p.tfplan"
    assert world.main("--root", "stage2", "--planfile", str(plan)) == planflow.EXIT_OK
    text = world.text()
    assert "opa_plan: ADMITTED -- apply exactly this plan:" in text
    assert f"{_COMMAND} --root stage2 --apply-plan {plan}" in text
    assert plancli.SURVIVE_HINT in text
    assert world.host.applied == 0


def test_the_flags_reach_tofu_and_a_planfile_that_holds_a_plan_is_refused(tmp_path: Path) -> None:
    """--replace and --target become tofu flags, and an existing plan is not replaced."""
    world = _World(tmp_path)
    plan = tmp_path / "p.tfplan"
    code = world.main(
        "--root", "stage2", "--planfile", str(plan), "--replace", "a", "--target", "b"
    )
    assert code == planflow.EXIT_OK
    assert world.host.planned_flags == [("-replace=a", "-target=b")]
    assert world.main("--root", "stage2", "--planfile", str(plan)) == planflow.EXIT_STOPPED
    assert "already holds a plan" in world.text()


def test_apply_plan_applies_an_admitted_plan_and_verify_confirms_it(tmp_path: Path) -> None:
    """--verify admits the planfile, --apply-plan --yes applies exactly it, once."""
    world = _World(tmp_path)
    plan = tmp_path / "p.tfplan"
    world.main("--root", "stage2", "--planfile", str(plan))
    assert world.main("--verify", str(plan)) == planflow.EXIT_OK
    assert "admitted and unchanged" in world.text()
    world.main("--root", "stage2", "--apply-plan", str(plan), "--yes")
    assert world.host.applied == 1


def test_verify_refuses_a_planfile_whose_bytes_moved(tmp_path: Path) -> None:
    """The moved planfile has no verdict, so it is not admitted."""
    world = _World(tmp_path)
    plan = tmp_path / "p.tfplan"
    world.main("--root", "stage2", "--planfile", str(plan))
    plan.write_bytes(b"MOVED")
    assert world.main("--verify", str(plan)) == planflow.EXIT_STOPPED
    assert "never judged here" in world.text()


def test_apply_plans_then_applies_in_one_command(tmp_path: Path) -> None:
    """--apply --yes is plan, verify, apply: one command, the same gates."""
    world = _World(tmp_path)
    plan = tmp_path / "p.tfplan"
    world.main("--root", "stage2", "--planfile", str(plan), "--apply", "--yes")
    assert world.host.applied == 1
