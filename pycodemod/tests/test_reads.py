# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for what a function reads: authored fresh, substrate has no arm for `touches`."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.pycodemod import reads as rd

if TYPE_CHECKING:
    from pathlib import Path


def _reads(
    tmp_path: Path,
    body: str,
    module_dirs: tuple[str, ...] = (),
    root_names: tuple[str, ...] = ("ROOT",),
) -> rd.Reads:
    src = tmp_path / "items.py"
    src.write_text("import os\n\n\ndef w():\n" + body + "\n\n\ndef other():\n    return 'x.py'\n")
    return rd.function_reads(str(src), "w", root_names, module_dirs, str(tmp_path))


def test_join_over_literals_is_a_file_with_root_skipped(tmp_path: Path) -> None:
    """`join(ROOT, "scripts", "a.py")` reads `scripts/a.py`; `ROOT` is named by the caller."""
    got = _reads(tmp_path, '    return os.path.join(ROOT, "scripts", "a.py")')
    assert got.files == ["scripts/a.py"]
    assert got.unresolved == []


def test_root_names_are_the_callers_not_a_suffix(tmp_path: Path) -> None:
    """A part not named in `root_names` is unresolved, even if it ends in ROOT."""
    got = _reads(tmp_path, '    return os.path.join(F.ROOT, "a.py")')
    assert got.files == []
    assert got.unresolved == ["a.py"]


def test_assignment_binding_is_followed(tmp_path: Path) -> None:
    """`x = "a.py"` then `join(d, x)` follows the binding."""
    body = '    x = "a.py"\n    return os.path.join(ROOT, "d", x)'
    assert _reads(tmp_path, body).files == ["d/a.py"]


def test_for_over_literal_tuple_yields_every_element(tmp_path: Path) -> None:
    """`for n in ("a.py", "b.py")` yields both files."""
    body = '    for n in ("a.py", "b.py"):\n        os.path.join(ROOT, "t", n)'
    assert _reads(tmp_path, body).files == ["t/a.py", "t/b.py"]


def test_import_resolves_to_a_file_in_module_dirs(tmp_path: Path) -> None:
    """`import m` is a read of `<dir>/m.py`; a stdlib import contributes no edge."""
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "m.py").write_text("")
    body = "    import m\n    import json\n    return m, json"
    got = _reads(tmp_path, body, module_dirs=("scratch", "scripts"))
    assert got.files == ["scripts/m.py"]


def test_import_found_in_no_dir_is_no_edge(tmp_path: Path) -> None:
    """With no module dir holding it, an imported name is not invented as a file."""
    assert _reads(tmp_path, "    import m\n    return m", module_dirs=("scripts",)).files == []


def test_non_literal_part_is_unresolved_and_partial_is_not_a_file(tmp_path: Path) -> None:
    """An unbound part reports the partial path as unresolved, never in `files`."""
    got = _reads(tmp_path, '    return os.path.join(ROOT, "d", name, "a.py")')
    assert got.files == []
    assert got.unresolved == ["d/a.py"]


def test_alternatives_over_the_cap_are_unresolved(tmp_path: Path) -> None:
    """A product past `MAX_ALTERNATIVES` is reported unresolved, not truncated into files."""
    items = ", ".join(f'"f{i}.py"' for i in range(rd.MAX_ALTERNATIVES + 1))
    body = f"    for n in ({items}):\n        os.path.join(ROOT, n)"
    got = _reads(tmp_path, body)
    assert got.files == []
    assert got.unresolved


def test_bare_directory_is_not_a_read(tmp_path: Path) -> None:
    """`join(ROOT, "scratch")` has no suffix: import plumbing, not a file."""
    got = _reads(tmp_path, '    return os.path.join(ROOT, "scratch")')
    assert got.files == []


def test_flag_literal_is_a_symbol_and_prose_is_not(tmp_path: Path) -> None:
    """`"--set"` is a symbol; a docstring sentence and a read file name are not."""
    body = '    """Does a thing."""\n    return "--set" in "a b c" or os.path.join(ROOT, "a.py")'
    got = _reads(tmp_path, body)
    assert got.symbols == ["--set"]
    assert got.files == ["a.py"]


def test_other_functions_are_not_read(tmp_path: Path) -> None:
    """A literal in a sibling function is neither a symbol nor a file."""
    got = _reads(tmp_path, "    return 1")
    assert got.symbols == []
    assert got.files == []


def test_absent_function_raises(tmp_path: Path) -> None:
    """A name defined nowhere is an error, not an empty "reads nothing"."""
    src = tmp_path / "items.py"
    src.write_text("def w():\n    return 1\n")
    with pytest.raises(LookupError):
        rd.function_reads(str(src), "nope", ("ROOT",), (), str(tmp_path))


def test_unparseable_file_is_a_skip(tmp_path: Path) -> None:
    """An unparseable file comes back empty with its skip, not as a clean census."""
    src = tmp_path / "bad.py"
    src.write_text("def (:\n")
    got = rd.function_reads(str(src), "w", ("ROOT",), (), str(tmp_path))
    assert [s.why for s in got.skipped] == ["unparseable"]
    assert got.files == []


def test_missing_file_is_a_skip(tmp_path: Path) -> None:
    """A path that does not exist is reported as unreadable."""
    got = rd.function_reads(str(tmp_path / "none.py"), "w", ("ROOT",), (), str(tmp_path))
    assert [s.why for s in got.skipped] == ["unreadable"]
