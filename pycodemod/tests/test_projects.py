# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `paperkit_projects`: foreign bibs by OWNERSHIP, from the resolved path (W614).

⚑⚑ THE ARMS ARE SUBSTRATE'S, RE-CUT WITH THE RESOLVER AS AN OPERAND: a `../` token that escapes is
foreign, a label that resolves inside is not, the foreign row names the RESOLVED destination, and a
nested child's bib is foreign to its parent (ownership, not containment). The unreadable-manifest,
outside-any-project and prune arms are new here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.pycodemod.projects import OUTSIDE, Foreign, Project, paperkit_projects

if TYPE_CHECKING:
    from pathlib import Path


def _resolve(token: str, directory: Path) -> Path:
    """Stand in for paperkit's resolver: a label is `//pkg:file` under the project, else a path.

    Returns:
        the path the token names.

    """
    if token.startswith(("//", "@")) or ":" in token:
        pkg, _, name = token.split("//", 1)[1].partition(":")
        return directory / pkg / name if pkg else directory / name
    return directory / token


def _write(root: Path, directory: str, text: str) -> None:
    folder = root / directory if directory else root
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "paper.toml").write_text(text, encoding="utf-8")


def _corpus(tmp_path: Path) -> Path:
    """Build the substrate fixture: a root, a nested child, an importer and a solo project.

    Returns:
        the corpus root.

    """
    (tmp_path / "shared").mkdir()
    (tmp_path / "importer" / "local").mkdir(parents=True)
    _write(tmp_path, "solo", '[paper]\ntitle = "Solo"\nwarrants = ["warrants.bib"]\n')
    _write(
        tmp_path,
        "importer",
        '[paper]\nwarrants = ["warrants.bib", "../shared/common.bib", "//local:own.bib"]\n',
    )
    _write(tmp_path, "", '[paper]\nwarrants = ["warrants.bib", "//child:owned.bib"]\n')
    _write(tmp_path, "child", '[paper]\nwarrants = ["owned.bib"]\n')
    return tmp_path


def _by_directory(root: Path) -> dict[str, Project]:
    return {
        p.directory: p for p in paperkit_projects(root, _resolve, include_worktrees=True).projects
    }


def test_a_project_is_found_per_manifest_in_sorted_order(tmp_path: Path) -> None:
    """One project per `paper.toml`, the corpus root named `.`."""
    found = paperkit_projects(_corpus(tmp_path), _resolve, include_worktrees=True)
    assert [p.directory for p in found.projects] == [".", "child", "importer", "solo"]


def test_a_project_with_only_a_local_bib_has_no_foreign_import(tmp_path: Path) -> None:
    """The control: a local-only project reports nothing foreign."""
    assert _by_directory(_corpus(tmp_path))["solo"].foreign == ()


def test_a_token_that_escapes_the_project_is_foreign_and_names_the_resolved_path(
    tmp_path: Path,
) -> None:
    """`../shared/common.bib` is foreign though it is no label; the row gives where it lands."""
    imp = _by_directory(_corpus(tmp_path))["importer"]
    assert imp.foreign == (Foreign("../shared/common.bib", "shared/common.bib", "."),)


def test_a_label_that_resolves_inside_the_project_is_not_foreign(tmp_path: Path) -> None:
    """`//local:own.bib` is spelled like an import and lives in the project, so it is local."""
    imp = _by_directory(_corpus(tmp_path))["importer"]
    spelled = {f.token for f in imp.foreign}
    assert "//local:own.bib" in imp.warrants
    assert "//local:own.bib" not in spelled


def test_a_nested_childs_bib_is_foreign_to_its_parent_by_ownership(tmp_path: Path) -> None:
    """The root contains `child/`, so a containment test calls this local; ownership does not."""
    root = _by_directory(_corpus(tmp_path))["."]
    assert root.foreign == (Foreign("//child:owned.bib", "child/owned.bib", "child"),)


def test_the_child_owns_its_own_bib(tmp_path: Path) -> None:
    """The nearest enclosing project of `child/owned.bib` is the child itself."""
    assert _by_directory(_corpus(tmp_path))["child"].foreign == ()


def test_a_project_with_no_warrants_list_gets_the_default(tmp_path: Path) -> None:
    """No `warrants` key means `warrants.bib`, which the project owns."""
    _write(tmp_path, "plain", '[paper]\ntitle = "Plain"\n')
    plain = _by_directory(tmp_path)["plain"]
    assert plain.warrants == ("warrants.bib",)
    assert plain.foreign == ()


def test_a_malformed_manifest_is_a_skip_and_not_a_project(tmp_path: Path) -> None:
    """An unparseable `paper.toml` and a non-list `warrants` are reported, never silent."""
    _write(tmp_path, "broken", "[paper\n")
    _write(tmp_path, "wrong", '[paper]\nwarrants = "warrants.bib"\n')
    _write(tmp_path, "mixed", '[paper]\nwarrants = [1, "a.bib"]\n')
    _write(tmp_path, "fine", "[paper]\n")
    found = paperkit_projects(tmp_path, _resolve, include_worktrees=True)
    assert [p.directory for p in found.projects] == ["fine"]
    assert sorted((s.path.rsplit("/", 2)[-2], s.why) for s in found.skipped) == [
        ("broken", "unreadable"),
        ("mixed", "malformed"),
        ("wrong", "malformed"),
    ]


def test_a_directory_named_by_exclude_is_not_walked(tmp_path: Path) -> None:
    """Pruning is the corpus walk's: a project under an excluded directory is not listed."""
    _write(tmp_path, "keep", "[paper]\n")
    _write(tmp_path, "build/inside", "[paper]\n")
    found = paperkit_projects(tmp_path, _resolve, ["build"], include_worktrees=True)
    assert [p.directory for p in found.projects] == ["keep"]


def test_a_bib_outside_every_project_is_foreign_to_nobody_in_particular(tmp_path: Path) -> None:
    """A token that lands where no project lives has the placeholder owner."""
    _write(tmp_path, "lone", '[paper]\nwarrants = ["../elsewhere/x.bib"]\n')
    lone = _by_directory(tmp_path)["lone"]
    assert [(f.token, f.owner) for f in lone.foreign] == [("../elsewhere/x.bib", OUTSIDE)]
