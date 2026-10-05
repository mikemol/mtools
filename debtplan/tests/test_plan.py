# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The plan: waits follow the import closure, a cycle is one unit, and the unsettled is reported."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.debtplan.plan import plan, waits_of

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping
    from pathlib import Path

    from mikemol.debtplan.rows import Row

RING = 3
"""The files in the import ring the ring test builds."""


def _tree(root: Path, files: dict[str, str]) -> None:
    """Write `files` (path relative to `root` to source) under `root`."""
    for name, source in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding="utf-8")


def _rows(ledger: dict[str, int], root: Path, universe: tuple[str, ...] = ()) -> dict[str, Row]:
    """Plan `ledger` under `root`.

    Returns:
        The plan's rows, keyed by file.

    """
    return {row.file: row for row in plan(ledger, root, universe).rows}


def test_waits_come_from_the_closure_without_the_file_itself() -> None:
    """A file waits on every debt file in its closure, and not on itself."""
    reach = {"a": frozenset({"b", "c"}), "b": frozenset({"c"}), "c": frozenset[str]()}
    assert waits_of(reach, {"a", "b", "c"}) == {"a": ("b", "c"), "b": ("c",), "c": ()}


def test_mutual_importers_do_not_wait_on_each_other() -> None:
    """Each reaches the other, so the wait between them is dropped on both sides."""
    reach = {"a": frozenset({"b"}), "b": frozenset({"a"})}
    assert waits_of(reach, {"a", "b"}) == {"a": (), "b": ()}


def test_a_closure_member_that_is_not_debt_is_not_a_wait() -> None:
    """Only debt files are waited on: a clean file in the closure is not."""
    reach = {"a": frozenset({"clean", "b"}), "b": frozenset[str]()}
    assert waits_of(reach, {"a", "b"}) == {"a": ("b",), "b": ()}


def test_a_chain_waits_transitively_and_lists_its_dependents(tmp_path: Path) -> None:
    """Top waits on mid and leaf; the leaf is waited on by both and comes first."""
    _tree(
        tmp_path,
        {"leaf.py": "x = 1\n", "mid.py": "from leaf import x\n", "top.py": "from mid import x\n"},
    )
    result = plan({"leaf.py": 2, "mid.py": 1, "top.py": 3}, tmp_path)
    by = {row.file: row for row in result.rows}
    assert result.rows[0].file == "leaf.py"
    assert by["top.py"].waits_on == ("leaf.py", "mid.py")
    assert by["leaf.py"].waited_by == ("mid.py", "top.py")
    assert by["mid.py"].count == 1


def test_a_file_importing_only_clean_modules_is_ready(tmp_path: Path) -> None:
    """With no universe, imports of files outside the ledger are not waits."""
    _tree(tmp_path, {"a.py": "from clean import x\n", "clean.py": "x = 1\n"})
    assert _rows({"a.py": 1}, tmp_path)["a.py"].ready


def test_the_closure_runs_through_a_clean_module_given_the_universe(tmp_path: Path) -> None:
    """A imports clean, which imports the debt file: A waits on it once the universe names clean."""
    _tree(
        tmp_path,
        {"a.py": "import clean\n", "clean.py": "import debt\n", "debt.py": "x = 1\n"},
    )
    ledger = {"a.py": 1, "debt.py": 1}
    assert _rows(ledger, tmp_path)["a.py"].ready
    assert _rows(ledger, tmp_path, ("clean.py",))["a.py"].waits_on == ("debt.py",)


def test_mutual_importers_are_each_ready_but_wait_on_a_leaf_outside(tmp_path: Path) -> None:
    """Two files importing each other do not block on each other; each still waits on the leaf."""
    _tree(
        tmp_path,
        {
            "leaf.py": "x = 1\n",
            "a.py": "import b\nimport leaf\n",
            "b.py": "import a\nimport leaf\n",
        },
    )
    by = _rows({"leaf.py": 1, "a.py": 1, "b.py": 1}, tmp_path)
    assert by["a.py"].waits_on == ("leaf.py",)
    assert by["b.py"].waits_on == ("leaf.py",)


def test_a_ring_of_imports_is_all_ready(tmp_path: Path) -> None:
    """Three files importing in a ring reach each other, so none waits on another."""
    _tree(tmp_path, {"a.py": "import b\n", "b.py": "import c\n", "c.py": "import a\n"})
    by = _rows({"a.py": 1, "b.py": 1, "c.py": 1}, tmp_path)
    assert len(by) == RING
    assert all(row.ready for row in by.values())


def test_a_file_importing_itself_is_ready(tmp_path: Path) -> None:
    """A self-import is not a wait."""
    _tree(tmp_path, {"a.py": "import a\n"})
    assert _rows({"a.py": 1}, tmp_path)["a.py"].ready


def test_an_unsettled_name_is_reported_with_the_file_that_wrote_it(tmp_path: Path) -> None:
    """Two files named a, none beside the importer: no wait, and the name is returned."""
    _tree(
        tmp_path,
        {"scripts/a.py": "", "tools/a.py": "", "other/c.py": "import a\n"},
    )
    result = plan({"other/c.py": 1}, tmp_path, ("scripts/a.py", "tools/a.py"))
    assert result.ambiguous == {"other/c.py": ("a",)}
    assert result.rows[0].ready


def test_a_plan_with_nothing_unsettled_reports_nothing(tmp_path: Path) -> None:
    """The ambiguity report is empty when every name settled."""
    _tree(tmp_path, {"a.py": "import b\n", "b.py": ""})
    assert plan({"a.py": 1, "b.py": 1}, tmp_path).ambiguous == {}


def test_a_cyclic_wait_graph_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The check refuses a graph that could block its cards, naming the cycle."""
    _tree(tmp_path, {"a.py": "", "b.py": ""})

    def cyclic(
        _reach: Mapping[str, frozenset[str]], _debt: Collection[str]
    ) -> dict[str, tuple[str, ...]]:
        return {"a.py": ("b.py",), "b.py": ("a.py",)}

    monkeypatch.setattr("mikemol.debtplan.plan.waits_of", cyclic)
    with pytest.raises(ValueError, match=r"wait graph has a cycle: a\.py -> b\.py -> a\.py"):
        plan({"a.py": 1, "b.py": 1}, tmp_path)
