# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `cellstage`: the engine's bytecode is placed and ONE counterfactual delivered."""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

from mikemol.mutantcell import cellstage

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_TAG = "cpython-test"


def _write(path: Path, text: str) -> Path:
    """Write `text` at `path`, creating its directory.

    Returns:
        `path`, for chaining.

    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_cache_tag_is_this_runtimes_bytecode_tag() -> None:
    """The tag is the running implementation's own `cache_tag`, e.g. `cpython-313`."""
    assert cellstage.cache_tag() == sys.implementation.cache_tag
    assert cellstage.cache_tag().startswith("cpython-")


def test_a_runtime_with_no_cache_tag_names_the_empty_tag(monkeypatch: pytest.MonkeyPatch) -> None:
    """Where the implementation has no tag the answer is the empty string, not a made-up one."""
    monkeypatch.setattr(sys.implementation, "cache_tag", None)
    assert not cellstage.cache_tag()


def test_slot_names_the_pycache_file_and_makes_its_directory(tmp_path: Path) -> None:
    """`x/m.py` maps to `x/__pycache__/m.<tag>.pyc`; the directory exists, the file does not."""
    got = cellstage.slot(tmp_path / "x" / "m.py", _TAG)
    assert got == tmp_path / "x" / "__pycache__" / f"m.{_TAG}.pyc"
    assert got.parent.is_dir()
    assert not got.exists()


def test_place_engine_moves_each_staged_pyc_to_its_import_slot(tmp_path: Path) -> None:
    """A staged `pkg/a.pyc` and `pkg/sub/b.pyc` move into their `__pycache__` slots."""
    _write(tmp_path / "pkg" / "a.pyc", "A")
    _write(tmp_path / "pkg" / "sub" / "b.pyc", "B")
    cellstage.place_engine(str(tmp_path), _TAG)
    slot_a = tmp_path / "pkg" / "__pycache__" / f"a.{_TAG}.pyc"
    slot_b = tmp_path / "pkg" / "sub" / "__pycache__" / f"b.{_TAG}.pyc"
    assert slot_a.read_text(encoding="utf-8") == "A"
    assert slot_b.read_text(encoding="utf-8") == "B"
    assert not (tmp_path / "pkg" / "a.pyc").exists()
    assert not (tmp_path / "pkg" / "sub" / "b.pyc").exists()


def test_place_engine_leaves_bytecode_already_in_a_pycache_alone(tmp_path: Path) -> None:
    """A `.pyc` already under `__pycache__` is not moved again."""
    placed = _write(tmp_path / "pkg" / "__pycache__" / f"c.{_TAG}.pyc", "C")
    cellstage.place_engine(str(tmp_path), _TAG)
    assert placed.read_text(encoding="utf-8") == "C"
    assert sorted(p.name for p in placed.parent.iterdir()) == [placed.name]


def test_file_plus_injects_an_absent_file_with_its_directories(tmp_path: Path) -> None:
    """`file+:` creates the file, empty, even under directories that do not yet exist."""
    target = tmp_path / "new" / "dir" / "x.txt"
    cellstage.deliver(cellstage.Site(f"file+:{target}"), _TAG)
    assert target.is_file()
    assert target.stat().st_size == 0


def test_file_minus_drops_a_present_file_and_tolerates_an_absent_one(tmp_path: Path) -> None:
    """`file-:` removes the file; running it again on the now-absent file is not an error."""
    target = _write(tmp_path / "x.txt", "here")
    site = cellstage.Site(f"file-:{target}")
    cellstage.deliver(site, _TAG)
    assert not target.exists()
    cellstage.deliver(site, _TAG)
    assert not target.exists()


def test_content_minus_removes_the_substring_from_the_staged_file(tmp_path: Path) -> None:
    """`content-` drops every occurrence of the text file's contents from the target."""
    target = _write(tmp_path / "bib.txt", "keep result:paper keep")
    text = _write(tmp_path / "drop.txt", "result:paper")
    site = cellstage.Site("content-", content_path=str(target), content_textfile=str(text))
    cellstage.deliver(site, _TAG)
    assert target.read_text(encoding="utf-8") == "keep  keep"


def test_content_plus_appends_the_substring_to_the_staged_file(tmp_path: Path) -> None:
    """`content+` appends the text file's contents to the target."""
    target = _write(tmp_path / "bib.txt", "head ")
    text = _write(tmp_path / "add.txt", "tail")
    site = cellstage.Site("content+", content_path=str(target), content_textfile=str(text))
    cellstage.deliver(site, _TAG)
    assert target.read_text(encoding="utf-8") == "head tail"


def test_content_toggle_replaces_the_hardlink_and_never_writes_the_source_inode(
    tmp_path: Path,
) -> None:
    """Unlink-then-write: a hardlinked source keeps its content when the staged copy changes."""
    source = _write(tmp_path / "source.txt", "abc")
    staged = tmp_path / "staged.txt"
    os.link(source, staged)
    text = _write(tmp_path / "t.txt", "b")
    site = cellstage.Site("content-", content_path=str(staged), content_textfile=str(text))
    cellstage.deliver(site, _TAG)
    assert staged.read_text(encoding="utf-8") == "ac"
    assert source.read_text(encoding="utf-8") == "abc"


def test_a_module_swap_delivers_source_and_bytecode_over_the_staged_module(
    tmp_path: Path,
) -> None:
    """A module cell replaces the `.py` AND writes the mutant `.pyc` into the import slot."""
    module = _write(tmp_path / "pkg" / "m.py", "original")
    mutant_py = _write(tmp_path / "mutant.py", "mutant source")
    mutant_pyc = _write(tmp_path / "mutant.pyc", "mutant bytecode")
    site = cellstage.Site(
        "pkg/m.py::f",
        module=str(module),
        mutant_py=str(mutant_py),
        mutant_pyc=str(mutant_pyc),
    )
    cellstage.deliver(site, _TAG)
    assert module.read_text(encoding="utf-8") == "mutant source"
    placed = tmp_path / "pkg" / "__pycache__" / f"m.{_TAG}.pyc"
    assert placed.read_text(encoding="utf-8") == "mutant bytecode"


def test_a_module_swap_replaces_the_hardlink_and_never_writes_the_source_inode(
    tmp_path: Path,
) -> None:
    """Unlink first: a hardlinked source keeps its content when the staged module is swapped."""
    source = _write(tmp_path / "source.py", "original")
    module = tmp_path / "pkg" / "m.py"
    module.parent.mkdir()
    os.link(source, module)
    mutant_py = _write(tmp_path / "mutant.py", "mutant source")
    mutant_pyc = _write(tmp_path / "mutant.pyc", "mutant bytecode")
    site = cellstage.Site(
        "pkg/m.py::f",
        module=str(module),
        mutant_py=str(mutant_py),
        mutant_pyc=str(mutant_pyc),
    )
    cellstage.deliver(site, _TAG)
    assert module.read_text(encoding="utf-8") == "mutant source"
    assert source.read_text(encoding="utf-8") == "original"


def test_a_module_swap_creates_a_module_outside_the_staged_closure(tmp_path: Path) -> None:
    """A mutated module that was never staged is created, not required to exist."""
    (tmp_path / "pkg").mkdir()
    module = tmp_path / "pkg" / "unstaged.py"
    mutant_py = _write(tmp_path / "mutant.py", "src")
    mutant_pyc = _write(tmp_path / "mutant.pyc", "pyc")
    site = cellstage.Site(
        "pkg/unstaged.py::f",
        module=str(module),
        mutant_py=str(mutant_py),
        mutant_pyc=str(mutant_pyc),
    )
    cellstage.deliver(site, _TAG)
    assert module.read_text(encoding="utf-8") == "src"


def test_a_site_with_no_module_and_no_file_kind_is_a_no_op(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An empty module must not reach `Path('.').unlink()`: nothing is touched at all."""
    marker = _write(tmp_path / "marker.txt", "x")
    monkeypatch.chdir(tmp_path)
    cellstage.deliver(cellstage.Site("0"), _TAG)
    assert sorted(p.name for p in tmp_path.iterdir()) == [marker.name]
