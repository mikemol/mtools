# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `pycheck_closure`: unclean imports named from debtplan's graph, else silence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.hooks import pycheck_closure

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

LEDGER_COUNTS: dict[str, int] = {"lib/b.py": 12, "lib/c.py": 3}
PLAN = '{"rows": [{"file": "app/a.py", "waits_on": ["lib/c.py", "lib/b.py"]}]}'
CLEAN_PLAN = '{"rows": [{"file": "app/a.py", "waits_on": []}]}'
B_COUNT = LEDGER_COUNTS["lib/b.py"]
C_COUNT = LEDGER_COUNTS["lib/c.py"]
PLANNER_PATH = Path("/fake/mikemol-debtplan")


def _project(root: Path, ledger: str | None = None) -> None:
    """Make a project with an optional ledger file and a fake planner in its venv."""
    (root / ".claude").mkdir()
    (root / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
    planner = root / ".venv" / "bin" / pycheck_closure.PLANNER
    planner.parent.mkdir(parents=True)
    planner.write_text("#!/bin/sh\n", encoding="utf-8")
    if ledger is not None:
        (root / pycheck_closure.LEDGER).write_text(ledger, encoding="utf-8")


def _answers(stdout: str | None, seen: list[str]) -> Callable[[Sequence[str]], str | None]:
    """Build a planner stand-in that records the probe ledger it was given.

    Returns:
        a runner that returns `stdout`, appending the ledger file's text to `seen`.

    """

    def run(argv: Sequence[str]) -> str | None:
        ledger_path = Path(argv[argv.index("--ledger") + 1])
        seen.append(ledger_path.read_text(encoding="utf-8"))
        return stdout

    return run


def test_the_planner_is_found_by_env_then_venv(tmp_path: Path) -> None:
    """The env override wins, then the project's venv; none found is None."""
    assert pycheck_closure.find_planner(tmp_path, {}) is None
    _project(tmp_path)
    venv = tmp_path / ".venv" / "bin" / pycheck_closure.PLANNER
    assert pycheck_closure.find_planner(tmp_path, {}) == venv
    other = tmp_path / "other-planner"
    other.write_text("", encoding="utf-8")
    env = {pycheck_closure.PLANNER_ENV: str(other)}
    assert pycheck_closure.find_planner(tmp_path, env) == other


def test_a_ledger_is_a_flat_map_of_counts_and_nothing_else(tmp_path: Path) -> None:
    """A missing ledger, bad JSON, a non-int count and a bool are all None, never partial."""
    _project(tmp_path)
    assert pycheck_closure.read_ledger(tmp_path) is None
    ledger = tmp_path / pycheck_closure.LEDGER
    ledger.write_text(json.dumps(LEDGER_COUNTS), encoding="utf-8")
    assert pycheck_closure.read_ledger(tmp_path) == LEDGER_COUNTS
    ledger.write_text("not json", encoding="utf-8")
    assert pycheck_closure.read_ledger(tmp_path) is None
    ledger.write_text('{"a.py": "3"}', encoding="utf-8")
    assert pycheck_closure.read_ledger(tmp_path) is None
    ledger.write_text('{"a.py": true}', encoding="utf-8")
    assert pycheck_closure.read_ledger(tmp_path) is None


def test_the_frontier_asks_as_if_the_clean_file_had_one_finding(tmp_path: Path) -> None:
    """The throwaway ledger adds the edited file with a count of 1; its waits_on come back."""
    seen: list[str] = []
    found = pycheck_closure.frontier(
        tmp_path, "app/a.py", LEDGER_COUNTS, PLANNER_PATH, _answers(PLAN, seen)
    )
    assert found == [("lib/b.py", B_COUNT), ("lib/c.py", C_COUNT)]
    assert '"app/a.py": 1' in seen[0]


def test_an_unreadable_plan_is_none_and_a_file_with_no_row_has_no_frontier(
    tmp_path: Path,
) -> None:
    """A planner that failed or printed junk is None; a plan without the file's row is empty."""
    seen: list[str] = []
    args = (tmp_path, "app/a.py", LEDGER_COUNTS, PLANNER_PATH)
    assert pycheck_closure.frontier(*args, _answers(None, seen)) is None
    assert pycheck_closure.frontier(*args, _answers("junk", seen)) is None
    assert pycheck_closure.frontier(*args, _answers('{"rows": []}', seen)) == []


def test_the_advice_names_each_unclean_import_with_its_findings() -> None:
    """The context text carries every file and its count, and says the gate judges one file."""
    text = pycheck_closure.advice("app/a.py", [("lib/b.py", B_COUNT), ("lib/c.py", C_COUNT)])
    assert "lib/b.py (12)" in text
    assert "lib/c.py (3)" in text
    assert "one file" in text


def test_context_is_said_only_when_there_is_debt_to_name(tmp_path: Path) -> None:
    """No ledger, no debt among the imports: silence; a ledger and a frontier: the advice."""
    _project(tmp_path)
    target = str(tmp_path / "app" / "a.py")
    assert pycheck_closure.context_for(target, tmp_path, {}, _answers(PLAN, [])) is None
    (tmp_path / pycheck_closure.LEDGER).write_text(json.dumps(LEDGER_COUNTS), encoding="utf-8")
    clean = pycheck_closure.context_for(target, tmp_path, {}, _answers(CLEAN_PLAN, []))
    assert clean is None
    said = pycheck_closure.context_for(target, tmp_path, {}, _answers(PLAN, []))
    assert said is not None
    assert "lib/b.py (12)" in said


def test_a_file_outside_the_project_is_never_advised(tmp_path: Path) -> None:
    """A path that is not under the root says nothing."""
    _project(tmp_path, json.dumps(LEDGER_COUNTS))
    assert pycheck_closure.context_for("/elsewhere/x.py", tmp_path, {}, _answers(PLAN, [])) is None
