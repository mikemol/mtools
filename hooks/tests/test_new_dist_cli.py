# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the `mikemol-new-dist` shell, over a throwaway repository built from inline text.

W945. ⚑ THE SUCCESS CASE IS THE POSITIVE CONTROL for the refusals: each refusal also asserts the
tree is byte-identical afterwards, which a shell that wrote before checking would fail.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.hooks import new_dist, new_dist_cli

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_MODULE = (
    'pip.parse(\n    hub_name = "pathwalk_deps",\n    python_version = "3.13",\n'
    '    requirements_lock = "//pathwalk:requirements.txt",\n)\n'
    'pip.parse(\n    hub_name = "pathwalk_dev",\n    python_version = "3.13",\n'
    '    uv_lock = "//pathwalk:uv.lock",\n)\n'
    'use_repo(\n    pip,\n    "pathwalk_deps",\n    "pathwalk_dev",\n)\n'
)
_INSTALL = "There are 1 of them\n\n- `pathwalk` (`mikemol-pathwalk`): walk. A library.\n"
_BUILD = 'load("@pathwalk_dev//:requirements.bzl", dev_requirement = "requirement")\n'
_PYPROJECT = '[project]\nname = "mikemol-pathwalk"\ndescription = "x"\nkeywords = ["a"]\n'


def _repo(root: Path) -> None:
    (root / "MODULE.bazel").write_text(_MODULE, encoding="utf-8")
    (root / "INSTALL.md").write_text(_INSTALL, encoding="utf-8")
    source = root / new_dist.TEMPLATE
    source.mkdir()
    for name in new_dist.FILES:
        text = {"BUILD.bazel": _BUILD, "pyproject.toml": _PYPROJECT}.get(name, "")
        (source / name).write_text(text, encoding="utf-8")


def _snapshot(root: Path) -> dict[str, str]:
    files = [p for p in root.rglob("*") if p.is_file()]
    return {str(p.relative_to(root)): p.read_text(encoding="utf-8") for p in files}


def _run(root: Path, *operands: str) -> int:
    return new_dist_cli.main(["--root", str(root), "--no-lock", *operands])


def test_a_scaffold_writes_the_directory_and_both_edits(tmp_path: Path) -> None:
    """The positive control: files, hubs and the INSTALL entry all appear."""
    _repo(tmp_path)
    steps = new_dist_cli.scaffold(tmp_path, "htmlstruct", "Read HTML.", lock=False)
    assert (tmp_path / "htmlstruct" / "src/mikemol/htmlstruct/__init__.py").is_file()
    assert "htmlstruct_dev" in (tmp_path / "MODULE.bazel").read_text(encoding="utf-8")
    assert "There are 2 of them" in (tmp_path / "INSTALL.md").read_text(encoding="utf-8")
    assert any("mikemol-gen-warrants" in s for s in steps)


def test_a_refusal_leaves_the_tree_untouched(tmp_path: Path) -> None:
    """Bad name, existing directory and a missing template are each refused before any write."""
    _repo(tmp_path)
    before = _snapshot(tmp_path)
    assert _run(tmp_path, "Bad", "d") == new_dist_cli.EXIT_REFUSED
    assert _run(tmp_path, "pathwalk", "d") == new_dist_cli.EXIT_REFUSED
    assert _run(tmp_path, "only") == new_dist_cli.EXIT_REFUSED
    assert _snapshot(tmp_path) == before
    (tmp_path / "pathwalk" / "paper.toml").unlink()
    gone = _snapshot(tmp_path)
    assert _run(tmp_path, "fresh", "d") == new_dist_cli.EXIT_REFUSED
    assert _snapshot(tmp_path) == gone


def test_main_prints_the_remaining_steps(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Success exits 0 and names the human steps."""
    _repo(tmp_path)
    assert _run(tmp_path, "htmlstruct", "Read HTML.") == 0
    assert "bazel build //htmlstruct:.venv" in capsys.readouterr().out
