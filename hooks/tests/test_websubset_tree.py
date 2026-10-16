# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the whole-tree idiom census (mtools:W1338): the counts and the files it skips.

⚑ THE CONTROLS ARE WHAT IT MUST NOT COUNT: a test module, a stub, an `__init__` and a file outside
any `src` tree are not read, a clean module is counted clean, and a rule that sits at several sites
of one module counts that module once and every site.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.hooks import websubset_cli, websubset_tree

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_FUTURE = "from __future__ import annotations\n"
_DUAL = "try:\n    pass\nexcept (A, B):\n    pass\ntry:\n    pass\nexcept (C, D):\n    pass\n"


def _tree(tmp_path: Path) -> Path:
    src = tmp_path / "d" / "src" / "pkg"
    src.mkdir(parents=True)
    (src / "a.py").write_text(_FUTURE + _DUAL, encoding="utf-8")
    (src / "b.py").write_text(_FUTURE, encoding="utf-8")
    (src / "c.py").write_text("x = 1\n", encoding="utf-8")
    (src / "__init__.py").write_text(_FUTURE, encoding="utf-8")
    for skipped in ("tests", "stubs"):
        (tmp_path / "d" / "src" / skipped).mkdir()
        (tmp_path / "d" / "src" / skipped / "z.py").write_text(_FUTURE, encoding="utf-8")
    (tmp_path / "outside.py").write_text(_FUTURE, encoding="utf-8")
    return tmp_path


def test_each_rule_counts_its_modules_once_and_every_site(tmp_path: Path) -> None:
    """Two `except (A, B)` in one module is one module and two sites; the future import is two."""
    found = websubset_tree.census([_tree(tmp_path)], "codon")
    by_rule = {c.rule: (c.modules, c.sites) for c in found.rules}
    assert by_rule["tuple-except"] == (1, 2)
    assert by_rule["future-import"] == (2, 2)


def test_tests_stubs_init_and_files_outside_src_are_not_read(tmp_path: Path) -> None:
    """Three modules are read (a, b, c) and the one without findings is counted clean."""
    found = websubset_tree.census([_tree(tmp_path)], "codon")
    assert (found.total, found.clean, found.unreadable) == (3, 1, 0)


def test_the_target_selects_the_rules_and_the_report_orders_by_modules(tmp_path: Path) -> None:
    """py2many reads no codon rule, and the codon report puts the wider rule first."""
    root = _tree(tmp_path)
    assert not websubset_tree.census([root], "py2many").rules
    lines = websubset_tree.render(websubset_tree.census([root], "codon")).splitlines()
    assert lines[1].startswith("future-import")
    assert lines[2].startswith("tuple-except")


def test_the_cli_mode_prints_the_report_and_exits_clean(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--idioms ROOT` prints the census; it is a report, not a gate, so the status is 0."""
    status = websubset_cli.main(["--idioms", str(_tree(tmp_path)), "--target", "codon"])
    assert status == 0
    assert "tuple-except: 1 module(s), 2 site(s)" in capsys.readouterr().out
