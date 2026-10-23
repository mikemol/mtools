# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Interlocks: the unmet preconditions come back sorted, and could-not-ask is None (W1847).

⚑ AN INTERLOCK THAT CANNOT BE EVALUATED HAS NOT BEEN MET: no opa, a wrong pin, a kind that is not
an identifier and an opa that fails or answers in another shape are each None, never an empty list.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from mikemol.waldo import planinterlock, planjson
from mikemol.waldo.planconfig import PlanConfig

_OPA = Path("/usr/bin/opa")
_PIN = "1.20.2"


@dataclass
class _Done:
    returncode: int
    stdout: str
    stderr: str = ""


class _Tools:
    def __init__(self, *, opa: bool = True, version: str = _PIN) -> None:
        self._opa = _OPA if opa else None
        self._version = version
        self.reply = _Done(0, "")
        self.calls: list[tuple[Path, tuple[str, ...], Path | None, str | None]] = []

    def find(self, name: str) -> Path | None:
        return self._opa if name == "opa" else None

    def run(
        self, tool: Path, *args: str, cwd: Path | None = None, stdin_text: str | None = None
    ) -> _Done:
        if args == ("version",):
            return _Done(0, f"Version: {self._version}\n")
        self.calls.append((tool, args, cwd, stdin_text))
        return self.reply

    def run_bounded(
        self, tool: Path, *args: str, cwd: Path | None = None, cpu_seconds: int
    ) -> _Done:
        self.calls.append((tool, (*args, str(cpu_seconds)), cwd, None))
        return self.reply


def _config(tmp: Path) -> PlanConfig:
    return PlanConfig(
        root=tmp,
        terraform=tmp / "terraform",
        policy=tmp / "policy",
        rego_package="estate",
        opa_pin=_PIN,
        user_state=tmp / "state",
        root_state=tmp / "root_state",
        root_planned=frozenset(),
    )


def _says(value: object) -> _Done:
    expr: dict[str, object] = {"value": value}
    result: dict[str, object] = {"expressions": [expr]}
    doc: dict[str, object] = {"result": [result]}
    return _Done(0, json.dumps(doc))


def test_the_unmet_preconditions_come_back_sorted(tmp_path: Path) -> None:
    """The messages are sorted, and an empty set is an empty list: every precondition holds."""
    tools = _Tools()
    tools.reply = _says(["zone not synced", "backup stale"])
    config = _config(tmp_path)
    assert planinterlock.defer(tools, config, "dns", {}) == ["backup stale", "zone not synced"]
    tools.reply = _says([])
    assert planinterlock.defer(tools, config, "dns", {}) == []


def test_opa_is_asked_the_consumers_rule_over_the_facts_on_stdin(tmp_path: Path) -> None:
    """The query is the config's, the directory is its interlocks, the facts go in as JSON."""
    tools = _Tools()
    tools.reply = _says([])
    config = _config(tmp_path)
    planinterlock.defer(tools, config, "dns", {"level": 10})
    _tool, args, _cwd, stdin = tools.calls[0]
    assert args == (
        "eval",
        "-f",
        "json",
        "-d",
        str(config.interlocks()),
        "-I",
        "data.estate.interlocks.dns.defer",
    )
    assert planjson.parse(stdin or "") == {"level": 10}


def test_a_question_that_cannot_be_asked_is_none(tmp_path: Path) -> None:
    """No opa, another version and a kind that is not an identifier never read as met."""
    config = _config(tmp_path)
    assert planinterlock.defer(_Tools(opa=False), config, "dns", {}) is None
    assert planinterlock.defer(_Tools(version="1.0.0"), config, "dns", {}) is None
    tools = _Tools()
    tools.reply = _says([])
    assert planinterlock.defer(tools, config, "dns.x", {}) is None
    assert tools.calls == []


def test_an_evaluation_that_fails_or_has_another_shape_is_none(tmp_path: Path) -> None:
    """An opa error, empty output and a value that is not a set are each None."""
    config = _config(tmp_path)
    tools = _Tools()
    tools.reply = _Done(1, "", "boom")
    assert planinterlock.defer(tools, config, "dns", {}) is None
    tools.reply = _says("not a list")
    assert planinterlock.defer(tools, config, "dns", {}) is None
