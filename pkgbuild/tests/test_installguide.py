# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that the install guide is compared with the tree: dists, names, scripts, count.

W1146. ⚑ THE CONTROLS: a guide that matches the tree is silent and exits 0; each kind of drift is
its own finding (a dist not listed, a listed dist that is absent, a wrong name, a script list that
differs, a count that is wrong); a bullet continued on a second line still yields its scripts; a
library has none; and an unreadable guide or a missing root is a usage error.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from mikemol.pkgbuild import installguide

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_USAGE = 2


def _dist(root: Path, folder: str, name: str, scripts: tuple[str, ...] = ()) -> None:
    (root / folder).mkdir(parents=True)
    table = "".join(f'{s} = "x:main"\n' for s in scripts)
    text = f'[project]\nname = "{name}"\n' + (f"[project.scripts]\n{table}" if scripts else "")
    (root / folder / "pyproject.toml").write_text(text, encoding="utf-8")


def _tree(tmp_path: Path) -> Path:
    root = tmp_path / "root"
    _dist(root, "alpha", "mikemol-alpha", ("mikemol-a", "mikemol-b"))
    _dist(root, "beta", "mikemol-beta")
    return root


_GUIDE = (
    "There are 2 of them, listed below.\n\n"
    "- `alpha` (`mikemol-alpha`): the first. Scripts: `mikemol-b`,\n"
    "  `mikemol-a`.\n"
    "- `beta` (`mikemol-beta`): the second. A library, no scripts.\n\n"
    "Prose after the list.\n"
)


def test_a_guide_that_matches_the_tree_has_no_finding(tmp_path: Path) -> None:
    """Scripts continued on a second line and in another order still match; a library has none."""
    root = _tree(tmp_path)
    assert installguide.findings(_GUIDE, root) == []
    (root / "INSTALL.md").write_text(_GUIDE, encoding="utf-8")
    assert installguide.run([str(root)]) == 0


def test_each_kind_of_drift_is_its_own_finding(tmp_path: Path) -> None:
    """Not listed, listed but absent, a wrong name, a wrong script list and a wrong count."""
    root = _tree(tmp_path)
    _dist(root, "gamma", "mikemol-gamma")
    drifted = (
        "There are 9 of them.\n"
        "- `alpha` (`mikemol-alpha`): x. Script: `mikemol-a`.\n"
        "- `beta` (`mikemol-betta`): y. A library, no scripts.\n"
        "- `delta` (`mikemol-delta`): z. A library, no scripts.\n"
    )
    kinds = {(f["kind"], f.get("dist")) for f in installguide.findings(drifted, root)}
    assert kinds == {
        ("not-listed", "gamma"),
        ("listed-but-absent", "delta"),
        ("name", "beta"),
        ("scripts", "alpha"),
        ("count", None),
    }


def test_a_missing_count_sentence_is_a_finding(tmp_path: Path) -> None:
    """The guide must say how many there are."""
    root = _tree(tmp_path)
    found = installguide.findings(_GUIDE.replace("There are 2 of them", "Several"), root)
    assert [f["kind"] for f in found] == ["count"]


def test_the_command_prints_one_json_line_per_finding_and_exits_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Exit 1 and a line per finding on standard output."""
    root = _tree(tmp_path)
    guide = tmp_path / "guide.md"
    guide.write_text(_GUIDE.replace("`mikemol-beta`", "`mikemol-betta`"), encoding="utf-8")
    assert installguide.run([str(root), str(guide)]) == 1
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 1
    assert cast("dict[str, str]", json.loads(lines[0]))["kind"] == "name"


def test_a_missing_root_or_guide_is_a_usage_error(tmp_path: Path) -> None:
    """The controls: no arguments, a root that is no directory, and a guide that cannot be read."""
    assert installguide.run([]) == _USAGE
    assert installguide.run([str(tmp_path / "nowhere")]) == _USAGE
    assert installguide.run([str(_tree(tmp_path))]) == _USAGE
    assert installguide.run(["a", "b", "c"]) == _USAGE
