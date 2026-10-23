# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Judging a plan: each refusal is a reason, the evaluation reads deny and withheld (W1851).

⚑ EVERY REFUSAL STOPS AND SAYS WHY, AND THE CONTROL PASSES: the tools, the init, the policy
directory and the root-planned-as-root rule each refuse alone, and the all-present case returns
the two binaries.
"""

import json
from dataclasses import dataclass, replace
from pathlib import Path

from mikemol.waldo import planeval, planjson
from mikemol.waldo.planconfig import PlanConfig

_OPA = Path("/usr/bin/opa")
_TOFU = Path("/usr/bin/tofu")
_PIN = "1.20.2"
_HINT = "sudo python -m the.tool --root host"


@dataclass
class _Done:
    returncode: int
    stdout: str
    stderr: str = ""


class _Tools:
    # A Tools: the binaries it knows, opa's version, and a canned reply to `opa eval`.
    def __init__(self, *, tofu: bool = True, opa: bool = True, version: str = _PIN) -> None:
        self._found = {"tofu": _TOFU if tofu else None, "opa": _OPA if opa else None}
        self._version = version
        self.reply = _Done(0, "")
        self.calls: list[tuple[Path, tuple[str, ...], Path | None, str | None]] = []

    def find(self, name: str) -> Path | None:
        return self._found.get(name)

    def run(
        self, tool: Path, *args: str, cwd: Path | None = None, stdin_text: str | None = None
    ) -> _Done:
        self.calls.append((tool, args, cwd, stdin_text))
        if args == ("version",):
            return _Done(0, f"Version: {self._version}\n")
        return self.reply

    def run_bounded(
        self, tool: Path, *args: str, cwd: Path | None = None, cpu_seconds: int
    ) -> _Done:
        self.calls.append((tool, (*args, str(cpu_seconds)), cwd, None))
        return self.reply


def _config(tmp: Path) -> PlanConfig:
    (tmp / "policy").mkdir()
    return PlanConfig(
        root=tmp,
        terraform=tmp / "terraform",
        policy=tmp / "policy",
        rego_package="luthen",
        opa_pin=_PIN,
        user_state=tmp / "state",
        root_state=tmp / "root_state",
        root_planned=frozenset({"host"}),
    )


def _root(tmp: Path, name: str = "stage2") -> Path:
    root = tmp / "terraform" / name
    (root / ".terraform").mkdir(parents=True)
    return root


def _refuse(tools: _Tools, config: PlanConfig, root: Path, euid: int = 1000) -> object:
    return planeval.refuse_unless(tools, config, root, euid=euid, rerun_hint=_HINT)


def _opa_says(value: object) -> str:
    expr: dict[str, object] = {"value": value}
    result: dict[str, object] = {"expressions": [expr]}
    doc: dict[str, object] = {"result": [result]}
    return json.dumps(doc)


def _read(path: Path) -> object:
    return planjson.parse(path.read_text(encoding="utf-8"))


def test_with_everything_present_the_two_binaries_come_back(tmp_path: Path) -> None:
    """The control: tofu and the pinned opa, an initialised root and a policy directory pass."""
    assert _refuse(_Tools(), _config(tmp_path), _root(tmp_path)) == (_TOFU, _OPA)


def test_each_missing_piece_refuses_with_its_reason(tmp_path: Path) -> None:
    """No tofu, no opa, the wrong opa, an uninitialised root and no policy directory each stop."""
    config = _config(tmp_path)
    root = _root(tmp_path)
    assert _refuse(_Tools(tofu=False), config, root) == "tofu is not installed"
    assert _refuse(_Tools(opa=False), config, root) == f"opa {_PIN} is not installed"
    assert _refuse(_Tools(version="1.0.0"), config, root) == f"opa {_PIN} is not installed"
    bare = tmp_path / "terraform" / "bare"
    bare.mkdir()
    assert "is not initialised" in str(_refuse(_Tools(), config, bare))
    other = replace(config, policy=tmp_path / "nowhere")
    assert "does not exist" in str(_refuse(_Tools(), other, root))


def test_a_root_planned_root_needs_root_unless_custody_is_off(tmp_path: Path) -> None:
    """The host root run by a non-root user is refused with the rerun hint, the user root is not."""
    config = _config(tmp_path)
    host = _root(tmp_path, "host")
    got = str(_refuse(_Tools(), config, host))
    assert "reads root-only targets" in got
    assert _HINT in got
    assert _refuse(_Tools(), config, host, euid=0) == (_TOFU, _OPA)
    assert _refuse(_Tools(), replace(config, root_custody=False), host) == (_TOFU, _OPA)


def test_a_service_principal_replaces_root_as_the_trusted_uid(tmp_path: Path) -> None:
    """With trusted_uid set, that uid plans a root-planned root and root is refused, by name."""
    base = _config(tmp_path)
    config = replace(base, trusted_uid=4242)
    host = _root(tmp_path, "host")
    assert _refuse(_Tools(), config, host, euid=4242) == (_TOFU, _OPA)
    got = str(_refuse(_Tools(), config, host, euid=0))
    assert "Plan it as uid 4242" in got
    assert "Plan it as root" in str(_refuse(_Tools(), base, host))


def test_the_scope_file_lists_the_targets_beside_the_plan(tmp_path: Path) -> None:
    """An empty target list is written as empty (untargeted), a set is written as given."""
    plan = tmp_path / "p.json"
    empty = planeval.scope_file(plan, ())
    assert empty == tmp_path / "p.scope.json"
    assert _read(empty) == {"plan_scope": {"targets": []}}
    planeval.scope_file(plan, ("a.b", "c.d"))
    assert _read(empty) == {"plan_scope": {"targets": ["a.b", "c.d"]}}


def test_the_evaluation_returns_deny_and_withheld_and_runs_the_consumers_query(
    tmp_path: Path,
) -> None:
    """Opa gets the plan, the policy, the scope and the extra data, in order, then the query."""
    config = _config(tmp_path)
    tools = _Tools()
    tools.reply = _Done(0, _opa_says({"deny": ["D1"], "withheld": ["H1", "H2"]}))
    plan = tmp_path / "p.json"
    data = tmp_path / "data"
    got = planeval.evaluate(tools, config, _OPA, planeval.Evidence(plan, ("t",), (data,)))
    assert got == (["D1"], ["H1", "H2"])
    (_, args, _, _) = tools.calls[-1]
    assert args[:4] == ("eval", "-f", "json", "-i")
    assert args[4:] == (
        str(plan),
        "-d",
        str(config.policy),
        "-d",
        str(tmp_path / "p.scope.json"),
        "-d",
        str(data),
        "data.luthen.plan",
    )


def test_the_output_is_kept_beside_the_plan_and_reported_reads_it_back(tmp_path: Path) -> None:
    """The eval file holds opa's stdout, and `reported` comes from it."""
    tools = _Tools()
    tools.reply = _Done(0, _opa_says({"deny": [], "withheld": [], "reported": ["R"]}))
    plan = tmp_path / "p.json"
    planeval.evaluate(tools, _config(tmp_path), _OPA, planeval.Evidence(plan))
    assert (tmp_path / "p.eval.json").read_text(encoding="utf-8") == tools.reply.stdout
    assert planeval.reported_of(plan) == ["R"]


def test_a_failed_evaluation_is_a_reason_with_opas_last_line(tmp_path: Path) -> None:
    """A non-zero opa gives its last stderr line, and its stderr is what is kept."""
    tools = _Tools()
    tools.reply = _Done(2, "", "first\nrego_parse_error: boom\n")
    plan = tmp_path / "p.json"
    got = planeval.evaluate(tools, _config(tmp_path), _OPA, planeval.Evidence(plan))
    assert got == "opa eval failed: rego_parse_error: boom"
    assert "first" in (tmp_path / "p.eval.json").read_text(encoding="utf-8")


def test_output_in_another_shape_is_a_reason_and_reported_is_empty(tmp_path: Path) -> None:
    """Not JSON, no result and a non-object value are the unexpected shape, never a pass."""
    plan = tmp_path / "p.json"
    config = _config(tmp_path)
    for text in ("not json", "{}", _opa_says(3)):
        tools = _Tools()
        tools.reply = _Done(0, text)
        got = planeval.evaluate(tools, config, _OPA, planeval.Evidence(plan))
        assert got == "opa output not in the expected shape"
        assert planeval.reported_of(plan) == []


def test_reported_of_a_missing_evaluation_is_empty(tmp_path: Path) -> None:
    """No eval file reads as no reports."""
    assert planeval.reported_of(tmp_path / "never.json") == []
