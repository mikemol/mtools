# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The post-apply witness runs the declared check, and one that cannot run is a failure (W1853).

⚑ NOTHING THAT CANNOT BE MEASURED IS A PASS: an undeclared root, an unreadable declaration, a
missing tool and a runner that cannot bound CPU are each `cannot-run`, the control is a declared
check that exits 0, and a root that says in words it has no witness yet says so.
"""

import json
import stat
from dataclasses import dataclass, field
from pathlib import Path

from mikemol.waldo import planjson, planwitness
from mikemol.waldo.planconfig import PlanConfig

_TOOL = Path("/usr/bin/check")
_NOW = "2026-10-23T12:00:00Z"
_DIGEST = "d" * 64
_LONG = 30
_NO_RUNNER = "no prlimit"


@dataclass
class _Done:
    returncode: int
    stdout: str = ""
    stderr: str = ""


@dataclass
class _Tools:
    # A Tools with one tool, a canned bounded reply and a record of every call it was given.
    has_tool: bool = True
    reply: _Done = field(default_factory=lambda: _Done(0))
    raises: bool = False
    calls: list[tuple[Path, tuple[str, ...], Path | None, int | None]] = field(default_factory=list)

    def find(self, name: str) -> Path | None:
        return _TOOL if (self.has_tool and name == "check") else None

    def run(
        self, tool: Path, *args: str, cwd: Path | None = None, stdin_text: str | None = None
    ) -> _Done:
        self.calls.append((tool, (*args, str(stdin_text)), cwd, None))
        return self.reply

    def run_bounded(
        self, tool: Path, *args: str, cwd: Path | None = None, cpu_seconds: int
    ) -> _Done:
        if self.raises:
            raise OSError(_NO_RUNNER)
        self.calls.append((tool, args, cwd, cpu_seconds))
        return self.reply


def _config(tmp: Path, roots: dict[str, object] | None = None) -> PlanConfig:
    policy = tmp / "policy"
    if roots is not None:
        (policy / "witnesses").mkdir(parents=True)
        declared: dict[str, object] = {"roots": roots}
        (policy / "witnesses" / "data.json").write_text(json.dumps(declared), encoding="utf-8")
    return PlanConfig(
        root=tmp,
        terraform=tmp / "terraform",
        policy=policy,
        rego_package="luthen",
        opa_pin="1.20.2",
        user_state=tmp / "state",
        root_state=tmp / "root_state",
        root_planned=frozenset({"host"}),
    )


def _run(tools: _Tools, config: PlanConfig, root: str = "stage2") -> planjson.Json:
    return planwitness.run_witness(tools, config, root, _NOW)


def test_a_declared_check_that_exits_zero_passes_with_its_evidence(tmp_path: Path) -> None:
    """The control: status pass, the argv, the exit and the tails, with the caller's time."""
    entry: dict[str, object] = {"tool": "check", "args": ["--live", "x"]}
    tools = _Tools(reply=_Done(0, "a\nb\n", "w\n"))
    got = _run(tools, _config(tmp_path, {"stage2": entry}))
    assert got["status"] == "pass"
    assert (got["root"], got["as_of"]) == ("stage2", _NOW)
    assert got["argv"] == ["check", "--live", "x"]
    assert (got["exit"], got["stdout_tail"], got["stderr_tail"]) == (0, ["a", "b"], ["w"])
    assert tools.calls == [(_TOOL, ("--live", "x"), tmp_path, planwitness.WITNESS_CPU_SECONDS)]


def test_a_declared_check_that_exits_nonzero_fails(tmp_path: Path) -> None:
    """A non-zero exit is `fail`, with the exit code kept."""
    entry: dict[str, object] = {"tool": "check"}
    got = _run(_Tools(reply=_Done(3)), _config(tmp_path, {"stage2": entry}))
    assert (got["status"], got["exit"]) == ("fail", 3)


def test_each_way_of_not_running_is_cannot_run_never_a_pass(tmp_path: Path) -> None:
    """No declaration file, an undeclared root, a missing tool and no bounded runner."""
    entry: dict[str, object] = {"tool": "check"}
    declared = _config(tmp_path, {"stage2": entry})
    assert _run(_Tools(), _config(tmp_path / "x"), "stage2")["status"] == "cannot-run"
    undeclared = _run(_Tools(), declared, "other")
    assert undeclared["status"] == "cannot-run"
    assert "absence is not health" in str(undeclared["why"])
    no_tool = _run(_Tools(has_tool=False), declared)
    assert no_tool["status"] == "cannot-run"
    assert "not found" in str(no_tool["why"])
    no_runner = _run(_Tools(raises=True), declared)
    assert no_runner["status"] == "cannot-run"
    assert "no CPU-bounded runner" in str(no_runner["why"])


def test_a_root_that_says_in_words_it_has_no_witness_is_none_declared(tmp_path: Path) -> None:
    """The words are kept, and nothing is run."""
    tools = _Tools()
    entry: dict[str, object] = {"none": "not written yet"}
    got = _run(tools, _config(tmp_path, {"stage2": entry}))
    assert (got["status"], got["why"]) == ("none-declared", "not written yet")
    assert not tools.calls


def test_the_cpu_bound_is_the_entrys_own_or_the_default(tmp_path: Path) -> None:
    """A declared cpu_seconds is used, a bool or absent one falls back to the default."""
    for given, expected in (
        (_LONG, _LONG),
        (True, planwitness.WITNESS_CPU_SECONDS),
        (None, planwitness.WITNESS_CPU_SECONDS),
    ):
        entry: dict[str, object] = {"tool": "check"}
        if given is not None:
            entry["cpu_seconds"] = given
        tools = _Tools()
        _run(tools, _config(tmp_path / str(expected) / str(given), {"stage2": entry}))
        assert [call[3] for call in tools.calls] == [expected]


def test_the_result_is_kept_beside_the_verdict_it_belongs_to(tmp_path: Path) -> None:
    """`<digest>.witness.json` in the root's state directory, readable by others."""
    config = _config(tmp_path)
    result: planjson.Json = {"status": "pass"}
    path = planwitness.store_witness(config, "host", _DIGEST, result)
    assert path == tmp_path / "root_state" / "verdicts" / f"{_DIGEST}.witness.json"
    assert planjson.parse_object(path.read_text(encoding="utf-8")) == result
    assert stat.S_IMODE(path.stat().st_mode) == planwitness.RECORD_MODE
    other = planwitness.store_witness(config, "stage2", _DIGEST, result)
    assert other.parent.parent == tmp_path / "state"


def test_the_tail_is_the_last_lines_only() -> None:
    """Long output is cut to the last lines, short output whole."""
    text = "\n".join(str(n) for n in range(50))
    assert planwitness.tail_lines(text) == [str(n) for n in range(30, 50)]
    assert planwitness.tail_lines("a\nb\n", 5) == ["a", "b"]
