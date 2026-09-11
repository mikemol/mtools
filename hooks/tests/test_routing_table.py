# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The cases for `mikemol.hooks.routing_table` — whose table a hook reads, and what it says.

⚑⚑ THE LOCATION CASES ARE THE ONES THE PORT NEEDED. In the origin tree the table was found by
walking up from `__file__`, which works for a script and CANNOT work for an installed package:
`site-packages/mikemol/hooks/` has no `.claude` above it, so a faithful port would have produced
an EMPTY claims table — and an empty claims table is a gate that refuses nothing while reporting
itself armed. That is the failure this package exists to make impossible, arriving disguised as
fidelity. The cases below pin the replacement: the table follows the EDITED repo.

⚑ AND `table_path` RETURNING None IS TESTED SEPARATELY FROM `claims` RETURNING `{}`. "This repo
declares no table" and "this repo's table claims nothing" are different facts; a reader that
renders them identically reports a MISSING READER as an EMPTY SET.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.hooks import routing_table

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

# A routing table in the shape the hooks read: an `artifact | tool | … | claims` row grid.
_TABLE = """\
# Structural tools

| artifact | tool | notes | claims |
|----------|------|-------|--------|
| python source | `pycodemod.py` | the AST reader | `.py` |
| markdown | `mdstruct.py` | headings and rows | `.md` |
| agda source | `agdastruct.py` | the core reader | `.agda` `.agdai` |
| a row with no claims column |
"""


def _write_table(root: Path, body: str = _TABLE) -> Path:
    """Create a repo at `root` carrying `body` as its routing table.

    Returns:
        The path to the table that was written, so a caller can read or mutate the same file the
        subject under test will resolve — rather than reconstructing the relative path a second
        time and testing against a location that only looks like the one in use.

    """
    path = root / routing_table.SKILL_RELPATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_the_project_dir_env_names_the_repo(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The harness's declaration of which repo this session is in wins."""
    monkeypatch.setenv(routing_table.PROJECT_DIR_ENV, str(tmp_path))
    assert routing_table.project_dir() == tmp_path.absolute()


def test_without_the_env_the_working_directory_decides(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """⚑ UNSET FALLS BACK TO THIS PROCESS'S DIRECTORY, which is what an in-repo run always got.

    The positive control for the case above: without it, both would pass against a `project_dir`
    that returned `tmp_path` by some other route.
    """
    monkeypatch.delenv(routing_table.PROJECT_DIR_ENV, raising=False)
    monkeypatch.chdir(tmp_path)
    assert routing_table.project_dir() == tmp_path.absolute()


def test_a_repo_with_no_table_reports_none_rather_than_empty(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """⚑ ABSENT IS NOT EMPTY, and collapsing them makes an unconfigured repo look permissive."""
    monkeypatch.setenv(routing_table.PROJECT_DIR_ENV, str(tmp_path))
    assert routing_table.table_path() is None


def test_a_repo_with_a_table_reports_its_path(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The found case, without which the absent case above proves nothing."""
    written = _write_table(tmp_path)
    monkeypatch.setenv(routing_table.PROJECT_DIR_ENV, str(tmp_path))
    assert routing_table.table_path() == written


def test_the_table_is_read_from_the_edited_repo_not_the_package(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """⚑⚑ THE PORT'S CENTRAL REPAIR, ASSERTED AGAINST A REPO THIS PACKAGE DOES NOT LIVE IN.

    An installed package has no `.claude` above its own files, so any `__file__`-derived lookup
    yields nothing here. This passing means the lookup went to the repo under edit.
    """
    _write_table(tmp_path)
    monkeypatch.setenv(routing_table.PROJECT_DIR_ENV, str(tmp_path))
    assert routing_table.claims()[".py"] == ("python source", "pycodemod.py")


def test_every_declared_suffix_in_a_cell_is_claimed(tmp_path: Path) -> None:
    """⚑ A CELL MAY DECLARE SEVERAL, and stopping at the first silently unclaims the rest."""
    table = _write_table(tmp_path)
    got = routing_table.claims(table)
    assert got[".agda"] == got[".agdai"] == ("agda source", "agdastruct.py")


def test_an_unclaimed_suffix_is_absent(tmp_path: Path) -> None:
    """⚑ THE POSITIVE CONTROL FOR THE CLAIMS READER.

    Every claim case above would pass against a `claims` that returned the same owner for any key
    asked of it. Only a suffix no row declares distinguishes a real table read from that.
    """
    assert ".tsv" not in routing_table.claims(_write_table(tmp_path))


def test_the_header_and_separator_rows_are_not_claims(tmp_path: Path) -> None:
    """The word `artifact` and a `---` rule are table furniture, not routes."""
    tools = {tool for _artifact, tool in routing_table.routes(_write_table(tmp_path))}
    assert "tool" not in tools
    assert not any(set(t) <= set("-: ") for t in tools)


def test_a_row_too_short_for_a_claims_column_is_skipped(tmp_path: Path) -> None:
    """⚑ A RAGGED ROW MUST NOT RAISE — a table is hand-maintained prose, not a schema.

    The fixture carries a one-cell row for exactly this. A hook that dies reading its own routing
    table refuses nothing, which is worse than a table with a typo in it.
    """
    assert len(routing_table.claims(_write_table(tmp_path))) > 0


def test_a_short_row_still_routes_when_it_has_a_tool(tmp_path: Path) -> None:
    """`routes` needs two cells where `claims` needs four, so the two readers differ by design."""
    got = routing_table.routes(_write_table(tmp_path))
    assert ("python source", "pycodemod.py") in got


def test_an_unreadable_table_yields_nothing_rather_than_raising(tmp_path: Path) -> None:
    """A path that is not a readable file is reported as no rows, not as a traceback."""
    assert routing_table.routes(tmp_path / "absent.md") == []


def test_no_table_means_no_claims(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """With nothing declared the reader says so; the HOOK is what must not read that as OK."""
    monkeypatch.setenv(routing_table.PROJECT_DIR_ENV, str(tmp_path))
    assert routing_table.claims() == {}
