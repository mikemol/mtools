# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.corpus.tree_root`: substrate's `tree_root_selftest` arms, ported.

The differential arm (agreement with `corpus.ROOT`) retires with `corpus.ROOT`, which this
distribution does not have. Trees are SYNTHETIC, in tmp_path.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.corpus import tree_root as tr

if TYPE_CHECKING:
    from pathlib import Path


def test_a_bare_argv_refuses_naming_the_flag() -> None:
    """An argv without `--root` refuses, and the refusal names the flag to pass."""
    with pytest.raises(tr.RootError, match=tr.ROOT_FLAG):
        tr.from_argv(["--defs", "x"])


def test_adding_only_the_flag_flips_the_refusal(tmp_path: Path) -> None:
    """The same argv plus only `--root <dir>` succeeds: the flag is READ, not refused always."""
    got, rest = tr.from_argv(["--defs", tr.ROOT_FLAG, str(tmp_path)])
    assert got.path == tmp_path.absolute()
    assert rest == ["--defs"]


def test_a_flag_with_no_operand_refuses() -> None:
    """`--root` as the last token refuses rather than reading past the end."""
    with pytest.raises(tr.RootError, match="needs a directory"):
        tr.from_argv([tr.ROOT_FLAG])


def test_a_flag_is_never_taken_as_the_operand() -> None:
    """`--root --apply` refuses for a missing directory, not for `--apply` not existing.

    ⚑ Consuming the next token blindly would bind `--apply` as the tree: the right verdict by the
    wrong route, and the caller told the wrong argument was at fault.
    """
    with pytest.raises(tr.RootError, match="needs a directory"):
        tr.from_argv([tr.ROOT_FLAG, "--apply"])


def test_a_missing_tree_refuses(tmp_path: Path) -> None:
    """`of` refuses a path that is not a directory."""
    with pytest.raises(tr.RootError):
        tr.of(tmp_path / "no-such-tree")


def test_the_flag_and_operand_are_consumed_in_any_position(tmp_path: Path) -> None:
    """`--root <dir>` leaves argv whether it leads, sits in the middle, or trails.

    ⚑ Order-independent, because a caller's own flags are not this module's to order.
    """
    root = str(tmp_path)
    assert tr.from_argv(["--calls", "foo", tr.ROOT_FLAG, root, "--apply"])[1] == [
        "--calls",
        "foo",
        "--apply",
    ]
    assert tr.from_argv([tr.ROOT_FLAG, root, "--apply"])[1] == ["--apply"]
    assert tr.from_argv(["--apply", tr.ROOT_FLAG, root])[1] == ["--apply"]


def test_label_trims_inside_and_returns_outside_whole(tmp_path: Path) -> None:
    """Inside paths are trimmed; outside, relative, and the tree itself are returned whole.

    ⚑ The outside arm is the crash class: `Path.relative_to` raises there.
    """
    root = tr.of(tmp_path)
    assert root.label(root.path / "pkg" / "mod.py") == "pkg/mod.py"
    assert root.label("/somewhere/else/mod.py") == "/somewhere/else/mod.py"
    assert root.label("pkg/x.py") == "pkg/x.py"
    assert root.label(root.path) == str(root.path)


def test_holds_in_both_directions_and_not_a_name_prefix(tmp_path: Path) -> None:
    """An inside path is held; an outside path and a sibling sharing a name prefix are not.

    ⚑ `/repo` is a string prefix of `/repository`: a bare `startswith` would claim it.
    """
    root = tr.of(tmp_path)
    assert root.holds(root.path / "pkg")
    assert not root.holds("/somewhere/else")
    assert not root.holds(str(root.path) + "x")


def test_package_files_names_the_package_asked_for_not_a_tree(tmp_path: Path) -> None:
    """`package_files` returns the named package's directory, holding its modules, not a tree.

    ⚑⚑ substrate's took no argument and asked for its own package, so moved here unchanged it
    would have answered with THIS distribution's files: the `corpus.ROOT` defect in a new place.
    """
    pkg = tr.package_files("mikemol.corpus")
    assert pkg.name == "corpus"
    assert (pkg / "tree_root.py").exists()
    assert pkg != tmp_path


def test_census_resolves_every_root_and_refuses_a_missing_one(tmp_path: Path) -> None:
    """Every named tree resolves; one missing tree refuses the census; none yields nothing.

    ⚑ Refusing rather than skipping: a dropped root shrinks the population, not the denominator.
    """
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    assert len(tr.census([tmp_path / "a", tmp_path / "b"])) == len(["a", "b"])
    with pytest.raises(tr.RootError):
        tr.census([tmp_path / "a", tmp_path / "missing"])
    assert tr.census([]) == []


def test_a_namespace_package_is_refused_not_turned_into_a_bogus_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`package_files` refuses a namespace package rather than returning a path to nowhere.

    ⚑ Measured while porting: `files()` on a namespace package is a `MultiplexedPath` whose `str`
    is not a path, and `Path(str(...))` made it one silently. The package here is built in
    tmp_path with no `__init__.py`, so it is a namespace package by construction.
    """
    (tmp_path / "nsdemo_tree_root").mkdir()
    (tmp_path / "nsdemo_tree_root" / "mod.py").write_text("", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    with pytest.raises(tr.NotOnePackageDirError, match="nsdemo_tree_root"):
        tr.package_files("nsdemo_tree_root")
