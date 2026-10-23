# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Making the plan and recording its verdict: a saved plan and a sealed record (W1854).

⚑ NO PLANFILE IS A REASON, NOT A VERDICT, AND THE VERDICT IS WRITTEN WHATEVER IT WAS: a plan that
produced nothing and a `show` that failed each say why, and the record of a denial is as sealed and
as findable as the record of an admission.
"""

import os
import stat
from dataclasses import dataclass, field
from pathlib import Path

from mikemol.waldo import planjson, planplan, planverdict
from mikemol.waldo.planconfig import PlanConfig

_TOFU = Path("/usr/bin/tofu")


@dataclass
class _Done:
    returncode: int
    stdout: str = ""
    stderr: str = ""


@dataclass
class _Tofu:
    # A Tools whose `tofu plan` writes the planfile it is told to (or not) and whose `show` answers.
    writes: bool = True
    empty: bool = False
    plan_exit: int = 0
    plan_err: str = ""
    show: _Done = field(default_factory=lambda: _Done(0, '{"format_version": "1"}'))
    calls: list[tuple[str, ...]] = field(default_factory=list)

    def find(self, name: str) -> Path | None:
        self.calls.append(("find", name))
        return _TOFU if name == "tofu" else None

    def run(
        self, tool: Path, *args: str, cwd: Path | None = None, stdin_text: str | None = None
    ) -> _Done:
        self.calls.append((str(tool), str(cwd), str(stdin_text), *args))
        if "plan" in args:
            out = next(a for a in args if a.startswith("-out="))[len("-out=") :]
            if self.writes:
                Path(out).write_bytes(b"" if self.empty else b"PLANBYTES")
            return _Done(self.plan_exit, "", self.plan_err)
        return self.show

    def run_bounded(
        self, tool: Path, *args: str, cwd: Path | None = None, cpu_seconds: int
    ) -> _Done:
        return self.run(tool, *args, cwd=cwd, stdin_text=str(cpu_seconds))


def _config(tmp: Path) -> PlanConfig:
    (tmp / "policy").mkdir(exist_ok=True)
    (tmp / "policy" / "plan.rego").write_text("package luthen.plan\n", encoding="utf-8")
    return PlanConfig(
        root=tmp,
        terraform=tmp / "terraform",
        policy=tmp / "policy",
        rego_package="luthen",
        opa_pin="1.20.2",
        user_state=tmp / "state",
        root_state=tmp / "root_state",
        root_planned=frozenset({"host"}),
        trusted_uid=os.getuid(),
    )


def test_the_flags_spell_replace_then_target_in_order() -> None:
    """Each address becomes its flag, replaces first."""
    assert planplan.plan_flags(("a", "b"), ("c",)) == ("-replace=a", "-replace=b", "-target=c")
    assert planplan.plan_flags((), ()) == ()


def test_the_state_lock_is_skipped_only_for_state_this_user_cannot_write(tmp_path: Path) -> None:
    """No state, writable state and read-only state."""
    assert planplan.lock_args(tmp_path) == []
    state = tmp_path / "terraform.tfstate"
    state.write_text("{}", encoding="utf-8")
    assert planplan.lock_args(tmp_path) == []
    state.chmod(0o444)
    assert planplan.lock_args(tmp_path) == ["-lock=false"]


def test_a_saved_plan_and_its_json_come_back_with_the_callers_flags(tmp_path: Path) -> None:
    """The control: plan -out, then show -json, written beside the planfile as .json."""
    tofu = _Tofu()
    plan = tmp_path / "p.tfplan"
    got = planplan.plan_and_show(tofu, _TOFU, plan, tmp_path / "root", ("-target=a",))
    assert got == tmp_path / "p.json"
    assert planjson.parse_object(got.read_text(encoding="utf-8")) == {"format_version": "1"}
    first, second = tofu.calls
    assert first[3:] == (
        f"-chdir={tmp_path / 'root'}",
        "plan",
        "-input=false",
        "-no-color",
        "-target=a",
        f"-out={plan}",
    )
    assert second[3:] == (f"-chdir={tmp_path / 'root'}", "show", "-json", str(plan))


def test_no_planfile_or_an_empty_one_is_a_reason_with_the_last_line(tmp_path: Path) -> None:
    """A plan that wrote nothing, and one that wrote an empty file, both say why."""
    plan = tmp_path / "p.tfplan"
    nothing = _Tofu(writes=False, plan_exit=1, plan_err="x\nError: boom\n")
    got = planplan.plan_and_show(nothing, _TOFU, plan, tmp_path)
    assert got == "tofu plan produced no planfile (exit 1): Error: boom"
    empty = _Tofu(empty=True)
    assert "produced no planfile" in str(planplan.plan_and_show(empty, _TOFU, plan, tmp_path))
    silent = _Tofu(writes=False)
    assert "(no output)" in str(
        planplan.plan_and_show(silent, _TOFU, tmp_path / "q.tfplan", tmp_path)
    )


def test_a_failed_show_is_a_reason_with_its_tail(tmp_path: Path) -> None:
    """The last 200 characters of tofu's complaint."""
    tofu = _Tofu(show=_Done(1, "", "e" * 300))
    got = planplan.plan_and_show(tofu, _TOFU, tmp_path / "p.tfplan", tmp_path)
    assert got == "tofu show -json failed: " + "e" * 200


def test_the_changes_are_the_sorted_actions_without_no_ops_or_reads() -> None:
    """address:action+action, sorted, leaving out no-op, read and actionless changes."""
    plan: planjson.Json = {
        "resource_changes": [
            {"address": "b.x", "change": {"actions": ["delete", "create"]}},
            {"address": "a.x", "change": {"actions": ["update"]}},
            {"address": "c.x", "change": {"actions": ["no-op"]}},
            {"address": "d.x", "change": {"actions": ["read"]}},
            {"address": "e.x", "change": {"actions": []}},
        ]
    }
    assert planplan.plan_changes(plan) == ["a.x:update", "b.x:delete+create"]
    assert planplan.plan_changes({}) == []


def test_the_verdict_is_sealed_keyed_by_the_hash_and_readable_back(tmp_path: Path) -> None:
    """A recorded admission loads through planverdict, a denial is recorded and refused there."""
    config = _config(tmp_path)
    plan = tmp_path / "p.tfplan"
    plan.write_bytes(b"PLANBYTES")
    record = planplan.record_verdict(config, plan, (0, [], []), {"root": "stage2", "changes": []})
    assert record == planverdict.verdict_path(config.user_state, planverdict.sha256_of(plan))
    doc = planverdict.load_verdict(config, plan)
    assert isinstance(doc, dict)
    assert (doc["exit"], doc["root"], doc["planfile"]) == (0, "stage2", str(plan))
    assert doc["policy_sha256"] == planverdict.policy_digest(config)
    assert stat.S_IMODE(record.stat().st_mode) == planplan.RECORD_MODE
    planplan.record_verdict(config, plan, (1, ["D1"], []), {"root": "stage2"})
    denied = planverdict.load_verdict(config, plan)
    assert isinstance(denied, str)
    assert "was not admitted (exit 1)" in denied


def test_a_root_planned_root_gets_its_record_in_the_root_directory_with_open_modes(
    tmp_path: Path,
) -> None:
    """Under custody the host record lands in the root state and its directories are 0755."""
    config = _config(tmp_path)
    plan = tmp_path / "p.tfplan"
    plan.write_bytes(b"PLANBYTES")
    assert config.root_state is not None
    closed = config.root_state / "verdicts"
    closed.mkdir(parents=True)
    closed.chmod(0o700)
    config.root_state.chmod(0o700)
    record = planplan.record_verdict(config, plan, (0, [], []), {"root": "host"})
    assert record.is_relative_to(config.root_state)
    for directory in (record.parent, record.parent.parent):
        assert stat.S_IMODE(directory.stat().st_mode) == planplan.STATE_DIR_MODE


def test_the_destroy_list_digest_is_recorded_when_there_is_one(tmp_path: Path) -> None:
    """The file's sha256 when it exists, empty when the consumer has none."""
    config = _config(tmp_path)
    plan = tmp_path / "p.tfplan"
    plan.write_bytes(b"PLANBYTES")
    none = planplan.record_verdict(config, plan, (0, [], []), {"root": "stage2"})
    assert not (planjson.parse_object(none.read_text(encoding="utf-8")) or {})["destroys_sha256"]
    (config.policy / "allowed_destroys").mkdir()
    listed = config.allowed_destroys()
    listed.write_text("{}", encoding="utf-8")
    record = planplan.record_verdict(config, plan, (0, [], []), {"root": "stage2"})
    written = planjson.parse_object(record.read_text(encoding="utf-8")) or {}
    assert written["destroys_sha256"] == planverdict.sha256_of(listed)
