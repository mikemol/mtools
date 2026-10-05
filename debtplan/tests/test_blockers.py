# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The blockers: an unsettled name blocks only where its answer could change a wait."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.importdag.resolve import Resolution, Unsettled

from mikemol.debtplan.plan import direct_unsettled, mattering, plan
from mikemol.debtplan.rows import Row

if TYPE_CHECKING:
    from pathlib import Path

CANDIDATES = ("p/a.py", "q/a.py")
RESOLVED = {"c.py": Resolution(frozenset(), (Unsettled("a", CANDIDATES),))}


def _tree(root: Path, files: dict[str, str]) -> None:
    """Write `files` (path relative to `root` to source) under `root`."""
    for name, source in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding="utf-8")


def test_a_name_matters_when_a_candidate_is_a_debt_file() -> None:
    """Settling it to that candidate would add a wait."""
    edges: dict[str, list[str]] = {"c.py": [], "p/a.py": [], "q/a.py": []}
    assert mattering(RESOLVED, edges, {"p/a.py"}) == {"a"}


def test_a_name_matters_when_a_candidate_reaches_a_debt_file() -> None:
    """The wait would be through the candidate's own imports."""
    edges: dict[str, list[str]] = {"c.py": [], "p/a.py": [], "q/a.py": ["debt.py"], "debt.py": []}
    assert mattering(RESOLVED, edges, {"debt.py"}) == {"a"}


def test_a_name_whose_candidates_reach_no_debt_does_not_matter() -> None:
    """Every answer leaves the waits as they are, so nothing is blocked on it."""
    edges: dict[str, list[str]] = {"c.py": [], "p/a.py": [], "q/a.py": []}
    assert mattering(RESOLVED, edges, {"c.py"}) == frozenset()


def test_a_file_behind_a_holder_is_not_blocked_on_the_name_again() -> None:
    """Y waits on x, which holds m: y keeps its wait on x and names nothing of its own."""
    rows = [
        Row("x.py", 1, (), ("y.py", "z.py"), ("m",)),
        Row("y.py", 1, ("x.py",), (), ("m",)),
        Row("z.py", 1, ("x.py",), (), ("m", "n")),
    ]
    assert direct_unsettled(rows) == {"x.py": ("m",), "y.py": (), "z.py": ("n",)}


def test_a_file_that_waits_on_a_file_without_the_name_keeps_it() -> None:
    """The wait does not hold the name, so the file is blocked on it directly."""
    rows = [Row("x.py", 1, (), ("y.py",)), Row("y.py", 1, ("x.py",), (), ("m",))]
    assert direct_unsettled(rows)["y.py"] == ("m",)


def test_an_unsettled_name_over_clean_candidates_blocks_nothing(tmp_path: Path) -> None:
    """The name is still reported, but the file is ready: no answer could change its waits."""
    files = {"scripts/a.py": "", "tools/a.py": "", "other/c.py": "import a\n"}
    _tree(tmp_path, files)
    result = plan({"other/c.py": 1}, tmp_path, tuple(files))
    assert result.rows[0].ready
    assert result.rows[0].unsettled == ()
    assert set(result.ambiguous) == {"other/c.py"}


def test_a_candidate_reaching_debt_through_a_clean_module_blocks(tmp_path: Path) -> None:
    """Tools/a imports a debt helper, so settling `a` to it would add a wait: the file is held."""
    files = {
        "scripts/a.py": "",
        "tools/a.py": "import helper\n",
        "helper.py": "x = 1\n",
        "other/c.py": "import a\n",
    }
    _tree(tmp_path, files)
    result = plan({"other/c.py": 1, "helper.py": 1}, tmp_path, tuple(files))
    rows = {row.file: row for row in result.rows}
    assert rows["other/c.py"].unsettled == ("a",)
    assert rows["helper.py"].ready
