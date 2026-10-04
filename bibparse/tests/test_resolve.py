# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `resolve`: a planted project directory resolves to the bibs its toml names."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.bibparse.resolve import DEFAULT_WARRANTS, ProjectError, bib_paths, token_path

if TYPE_CHECKING:
    from pathlib import Path


def _plant(project: Path, toml: str, bibs: tuple[str, ...]) -> None:
    """Write `paper.toml` and an empty file for each relative path in `bibs`."""
    project.mkdir(parents=True, exist_ok=True)
    (project / "paper.toml").write_text(toml, encoding="utf-8")
    for rel in bibs:
        target = project / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("", encoding="utf-8")


def test_default_warrants_is_the_one_conventional_name() -> None:
    """The default when `warrants` is absent is the single conventional name."""
    assert DEFAULT_WARRANTS == ("warrants.bib",)


def test_absent_warrants_defaults_to_warrants_bib(tmp_path: Path) -> None:
    """A paper.toml with a [paper] table but no `warrants` resolves to warrants.bib."""
    _plant(tmp_path, '[paper]\ntitle = "t"\n', ("warrants.bib",))
    assert bib_paths(tmp_path) == [tmp_path / "warrants.bib"]


def test_a_toml_without_a_paper_table_defaults_too(tmp_path: Path) -> None:
    """No [paper] table at all is the same as no `warrants`."""
    _plant(tmp_path, "[checks]\n", ("warrants.bib",))
    assert bib_paths(tmp_path) == [tmp_path / "warrants.bib"]


def test_declared_warrants_keep_their_order(tmp_path: Path) -> None:
    """The bibs come back in the order paper.toml lists them, not sorted."""
    _plant(tmp_path, '[paper]\nwarrants = ["b.bib", "a.bib"]\n', ("a.bib", "b.bib"))
    assert bib_paths(tmp_path) == [tmp_path / "b.bib", tmp_path / "a.bib"]


def test_label_tokens_resolve_against_the_project_directory(tmp_path: Path) -> None:
    """`//pkg:file`, `//:path/file` and `@repo//pkg:file` are project-relative `pkg/file`."""
    toml = '[paper]\nwarrants = ["//lib:concepts.bib", "//:deep/x.bib", "@repo//pkg:f.bib"]\n'
    _plant(tmp_path, toml, ("lib/concepts.bib", "deep/x.bib", "pkg/f.bib"))
    assert bib_paths(tmp_path) == [
        tmp_path / "lib" / "concepts.bib",
        tmp_path / "deep" / "x.bib",
        tmp_path / "pkg" / "f.bib",
    ]


def test_token_path_resolves_a_bare_name_and_a_label(tmp_path: Path) -> None:
    """A bare token is project-relative; a label with a package names `pkg/file`."""
    assert token_path(tmp_path, "w.bib") == tmp_path / "w.bib"
    assert token_path(tmp_path, "//a:b.bib") == tmp_path / "a" / "b.bib"
    assert token_path(tmp_path, "//:b.bib") == tmp_path / "b.bib"


@pytest.mark.parametrize("token", [":b.bib", "x:y.bib"])
def test_a_label_without_slashes_is_refused(tmp_path: Path, token: str) -> None:
    """A colon token with no `//` names no package, so it is refused rather than guessed."""
    with pytest.raises(ProjectError, match="label with no"):
        token_path(tmp_path, token)


def test_a_project_without_paper_toml_is_refused(tmp_path: Path) -> None:
    """No silent fall back to warrants.bib: the project is not a project."""
    (tmp_path / "warrants.bib").write_text("", encoding="utf-8")
    with pytest.raises(ProjectError, match=r"no paper\.toml"):
        bib_paths(tmp_path)


def test_a_named_bib_that_is_absent_is_refused(tmp_path: Path) -> None:
    """A bib the toml names but the disk lacks would drop its edges silently, so it refuses."""
    _plant(tmp_path, '[paper]\nwarrants = ["gone.bib"]\n', ())
    with pytest.raises(ProjectError, match=r"gone\.bib, which is not a file"):
        bib_paths(tmp_path)


@pytest.mark.parametrize(
    "toml",
    ['[paper]\nwarrants = "a.bib"\n', "[paper]\nwarrants = [1]\n", "[paper]\nwarrants = ["],
)
def test_malformed_warrants_are_refused(tmp_path: Path, toml: str) -> None:
    """A non-list, a non-string element, and unparsable toml each refuse naming paper.toml."""
    _plant(tmp_path, toml, ())
    with pytest.raises(ProjectError, match=r"paper\.toml"):
        bib_paths(tmp_path)
