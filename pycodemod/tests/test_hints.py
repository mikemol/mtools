# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for alias_hint: where a call census is blind, located through an aliased import."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.pycodemod import hints

if TYPE_CHECKING:
    from pathlib import Path

_FILES = {
    "store.py": "def tenant(x):\n    return x\n",
    "renamed_module.py": "import store as _s\n_s.tenant(1)\n",
    "renamed_name.py": "from store import tenant as _t\n_t(1)\n",
    "dotted.py": "import pkg.store as ps\nps.tenant(2)\n",
    "from_module.py": "from pkg import store as st\nst.tenant(3)\n",
    "bare.py": "import store\nstore.tenant(1)\n",
    "unrelated.py": "import other as o\no.tenant(1)\n",
}


def _tree(tmp_path: Path) -> tuple[str, list[str]]:
    for name, text in _FILES.items():
        (tmp_path / name).write_text(text, encoding="utf-8")
    population = [str(tmp_path / n) for n in sorted(_FILES) if n != "store.py"]
    return str(tmp_path / "store.py"), population


def _rows(tmp_path: Path) -> dict[str, tuple[int, tuple[str, ...], tuple[str, ...]]]:
    store, population = _tree(tmp_path)
    got = hints.alias_hint("tenant", [store], population).rows
    return {r.path.rsplit("/", 1)[-1]: (r.line, r.aliases, r.modules) for r in got}


def test_a_module_imported_under_an_alias_is_hinted(tmp_path: Path) -> None:
    """`import store as _s` then `_s.tenant(1)`: the site, its alias and module are named."""
    assert _rows(tmp_path)["renamed_module.py"] == (2, ("_s",), ("store",))


def test_a_renamed_name_is_hinted_at_its_calls(tmp_path: Path) -> None:
    """⚑⚑⚑ `from store import tenant as _t` then `_t(1)`: found through the alias's own calls.

    Measured on the origin with libcst present: it returned nothing for this file.
    """
    assert _rows(tmp_path)["renamed_name.py"] == (2, ("tenant as _t",), ("store",))


def test_a_dotted_module_matches_on_any_segment(tmp_path: Path) -> None:
    """⚑ `import pkg.store as ps` matches a `store` defining module; the origin tested the head."""
    assert _rows(tmp_path)["dotted.py"] == (2, ("ps",), ("pkg.store",))


def test_a_module_selected_from_a_package_under_an_alias_is_hinted(tmp_path: Path) -> None:
    """`from pkg import store as st` is a module alias, narrowed by attribute reads."""
    assert _rows(tmp_path)["from_module.py"] == (2, ("store as st",), ("pkg",))


def test_a_bare_import_or_an_unrelated_alias_is_not_hinted(tmp_path: Path) -> None:
    """`import store` is visible to the census; an alias of another module is not a blind spot."""
    got = _rows(tmp_path)
    assert ("bare.py" in got, "unrelated.py" in got) == (False, False)


def test_no_defining_module_hints_nothing(tmp_path: Path) -> None:
    """With no defining module there is nothing to be blind to."""
    _, population = _tree(tmp_path)
    assert hints.alias_hint("tenant", [], population).rows == []


def test_an_unread_file_is_reported(tmp_path: Path) -> None:
    """⚑ A file that cannot be read is skipped with its reason, never silently dropped."""
    store, _ = _tree(tmp_path)
    bad = tmp_path / "bad.py"
    bad.write_bytes(b"\xff\xfe import store as s")
    got = hints.alias_hint("tenant", [store], [str(bad)])
    whys: list[str] = [s.why for s in got.skipped]
    assert (got.rows, whys) == ([], ["undecodable"])
