# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that `publishers` prints the exact form values and writes a resumable worksheet.

W1217. ⚑ THE VALUES COME FROM THE DISTS: the project name is each pyproject's own name, normalized,
and the environment is the index's. ⚑ THE CONTROLS ARE THE REFUSALS: a root with no workflow file
(a renamed workflow would otherwise fail at the first upload), an unknown index, no dist at all and
a dangling flag each exit 2 and write nothing.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from mikemol.pkgbuild import publishers

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

Row = dict[str, str]
_USAGE = 2
_TWO = 2


def _root(tmp_path: Path, *, workflow: bool = True) -> Path:
    root = tmp_path / "root"
    for folder, name in (("alpha", "Mikemol_Alpha"), ("beta", "mikemol-beta")):
        (root / folder).mkdir(parents=True)
        (root / folder / "pyproject.toml").write_text(
            f'[project]\nname = "{name}"\n', encoding="utf-8"
        )
    if workflow:
        flow = root / ".github" / "workflows"
        flow.mkdir(parents=True)
        (flow / "publish.yml").write_text("name: publish\n", encoding="utf-8")
    return root


def _rows(capsys: pytest.CaptureFixture[str]) -> list[Row]:
    out = capsys.readouterr().out.splitlines()
    return [cast("Row", json.loads(line)) for line in out]


def test_each_dist_gets_the_five_form_values_with_a_normalized_name(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Name normalized, owner and repository fixed, the workflow file, the index's environment."""
    assert publishers.run([str(_root(tmp_path))]) == 0
    rows = _rows(capsys)
    assert [r["PyPI Project Name"] for r in rows] == ["mikemol-alpha", "mikemol-beta"]
    assert rows[0] == {
        "PyPI Project Name": "mikemol-alpha",
        "Owner": "mikemol",
        "Repository name": "mtools",
        "Workflow name": "publish.yml",
        "Environment name": "pypi",
    }


def test_the_testpypi_index_changes_only_the_environment(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The control: the same dists on `--index testpypi` differ in the environment alone."""
    assert publishers.run([str(_root(tmp_path)), "--index", "testpypi"]) == 0
    assert {r["Environment name"] for r in _rows(capsys)} == {"testpypi"}


def test_the_worksheet_has_a_copy_button_per_value_and_a_remembered_box_per_row(
    tmp_path: Path,
) -> None:
    """Five copy buttons and one checkbox per dist, the index's form link, and a done count."""
    page = tmp_path / "sheet.html"
    assert publishers.run([str(_root(tmp_path)), "--html", str(page)]) == 0
    text = page.read_text(encoding="utf-8")
    assert text.count("data-copy=") == len(publishers.FIELDS) * _TWO
    assert text.count('data-key="pypi:mikemol-') == _TWO
    assert "https://pypi.org/manage/account/publishing/" in text
    assert 'id="count"' in text
    assert "localStorage" in text


def test_a_value_is_escaped_in_the_page(tmp_path: Path) -> None:
    """A name with markup in it cannot break out of the attribute or the cell."""
    root = _root(tmp_path)
    (root / "alpha" / "pyproject.toml").write_text('[project]\nname = "a<i>c"\n', encoding="utf-8")
    page = tmp_path / "sheet.html"
    assert publishers.run([str(root), "--html", str(page)]) == 0
    text = page.read_text(encoding="utf-8")
    assert "<i>" not in text
    assert "&lt;i&gt;" in text


def test_a_missing_workflow_an_unknown_index_no_dist_and_a_dangling_flag_exit_two(
    tmp_path: Path,
) -> None:
    """Each refusal exits 2 and writes no worksheet."""
    page = tmp_path / "sheet.html"
    bare = _root(tmp_path / "a", workflow=False)
    assert publishers.run([str(bare), "--html", str(page)]) == _USAGE
    assert publishers.run([str(_root(tmp_path / "b")), "--index", "elsewhere"]) == _USAGE
    empty = tmp_path / "empty"
    (empty / ".github" / "workflows").mkdir(parents=True)
    (empty / ".github" / "workflows" / "publish.yml").write_text("x: 1\n", encoding="utf-8")
    assert publishers.run([str(empty)]) == _USAGE
    assert publishers.run([str(_root(tmp_path / "c")), "--html"]) == _USAGE
    assert not page.exists()
