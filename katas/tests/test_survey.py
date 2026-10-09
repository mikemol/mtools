# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `survey`: where each repo's pre-commit lives, and whether it invokes bazel."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.procrun.proc import capture

from mikemol.katas import fleet, survey

if TYPE_CHECKING:
    from pathlib import Path

_BAZEL_HOOK = "#!/bin/sh\n# bazel is mentioned only here\nexec bazel test //:precommit\n"
_PLAIN_HOOK = "#!/bin/sh\n# bazel is mentioned only here\nruff check .\n"


def _host(tmp_path: Path) -> fleet.Fleet:
    """Build a fleet rooted under `tmp_path`.

    Returns:
        the fleet.

    """
    return fleet.Fleet(tmp_path / "hosts", tmp_path / "logs")


def _repo(host: fleet.Fleet, name: str) -> Path:
    """Make a repo with a queue, so it counts as a workstream.

    Returns:
        the repo directory.

    """
    path = host.root / name
    (path / ".claude").mkdir(parents=True)
    (path / ".claude" / "paths-forward.json").write_text("{}", encoding="utf-8")
    capture(("git", "init", "-q", str(path)))
    return path


def _hook(directory: Path, text: str) -> None:
    """Write a pre-commit hook under `directory`."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "pre-commit").write_text(text, encoding="utf-8")


def test_a_repo_with_no_hook_is_reported_as_none(tmp_path: Path) -> None:
    """Neither a configured hooks path nor the default directory has a pre-commit."""
    host = _host(tmp_path)
    _repo(host, "alpha")
    row = survey.hook_row(host, "alpha")
    assert row.verdict == survey.NO_HOOK
    assert row.where == "default hooks dir"


def test_a_hook_naming_bazel_on_a_code_line_is_bazel(tmp_path: Path) -> None:
    """A non-comment line that names bazel makes the verdict BAZEL, and the line is shown."""
    host = _host(tmp_path)
    repo = _repo(host, "alpha")
    _hook(repo / ".git" / "hooks", _BAZEL_HOOK)
    row = survey.hook_row(host, "alpha")
    assert row.verdict == survey.BAZEL
    assert row.first_bazel_line == "exec bazel test //:precommit"
    assert row.where == ".git/hooks/pre-commit"


def test_bazel_only_in_a_comment_does_not_count(tmp_path: Path) -> None:
    """A hook that mentions bazel in a comment is a script."""
    host = _host(tmp_path)
    repo = _repo(host, "alpha")
    _hook(repo / ".git" / "hooks", _PLAIN_HOOK)
    assert survey.hook_row(host, "alpha").verdict == survey.SCRIPT


def test_a_configured_hooks_path_decides_where_the_hook_is(tmp_path: Path) -> None:
    """With core.hooksPath set, the hook is read from there, not from `.git/hooks`."""
    host = _host(tmp_path)
    repo = _repo(host, "alpha")
    capture(("git", "-C", str(repo), "config", "core.hooksPath", ".githooks"))
    _hook(repo / ".git" / "hooks", _PLAIN_HOOK)
    _hook(repo / ".githooks", _BAZEL_HOOK)
    row = survey.hook_row(host, "alpha")
    assert row.verdict == survey.BAZEL
    assert row.where == ".githooks/pre-commit"


def test_the_survey_has_a_row_per_workstream_in_order(tmp_path: Path) -> None:
    """Sorted by repo name."""
    host = _host(tmp_path)
    _repo(host, "zulu")
    _repo(host, "alpha")
    assert [row.repo for row in survey.survey(host)] == ["alpha", "zulu"]
