# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The config-surface census has fixed JSON keys and reads only what the repository holds (W2201).

⚑ THE CONTRACT: `schema`, `repo` and `surfaces` at the top; `surface`, `declared`, `changed_by`,
`loaded_by` and `reviewed_by` in every surface, in the order of SURFACES. THE CONTROLS: a surface
the repository does not hold keeps its place with nothing declared and nothing reviewing it, and
the rendered JSON is the same text every time.
"""

import json
from pathlib import Path

import pytest

from mikemol.hooks import surfaces
from mikemol.hooks.payload import as_record

_USAGE_EXIT = 2
_KEYS = {"surface", "declared", "changed_by", "loaded_by", "reviewed_by"}
_NAMES = [
    "claude_md",
    "skills",
    "settings",
    "hooks",
    "loop_prompt",
    "standing",
    "memory",
    "policy",
]


def _put(root: Path, name: str) -> None:
    (root / name).parent.mkdir(parents=True, exist_ok=True)
    (root / name).write_text("x\n", encoding="utf-8")


def _rows(doc: dict[str, object]) -> dict[str, dict[str, object]]:
    listed = doc["surfaces"]
    assert isinstance(listed, list)
    return {str(as_record(row)["surface"]): as_record(row) for row in listed}


def test_the_document_has_the_fixed_keys_in_the_fixed_order(tmp_path: Path) -> None:
    """Top-level keys, every surface's keys, and the order of the surface names."""
    repo = tmp_path / "alpha"
    repo.mkdir()
    doc = surfaces.survey(repo)
    assert set(doc) == {"schema", "repo", "surfaces"}
    assert doc["schema"] == surfaces.SCHEMA
    assert doc["repo"] == "alpha"
    listed = doc["surfaces"]
    assert isinstance(listed, list)
    assert [as_record(row)["surface"] for row in listed] == _NAMES
    assert all(set(as_record(row)) == _KEYS for row in listed)


def test_declared_surfaces_are_what_exists_and_review_follows_the_git_hook(tmp_path: Path) -> None:
    """A held surface lists its paths and the pre-commit gate; an absent one lists nothing."""
    repo = tmp_path / "beta"
    for name in (
        "CLAUDE.md",
        ".claude/skills/one/SKILL.md",
        "hooks/bin/mikemol-hook-x",
        ".githooks/pre-commit",
    ):
        _put(repo, name)
    rows = _rows(surfaces.survey(repo))
    assert rows["claude_md"]["declared"] == ["CLAUDE.md"]
    assert rows["skills"]["declared"] == [".claude/skills/one/SKILL.md"]
    assert rows["hooks"]["declared"] == ["hooks/bin/mikemol-hook-x"]
    assert rows["claude_md"]["reviewed_by"] == ["git pre-commit gate"]
    assert rows["memory"]["declared"] == []
    assert rows["memory"]["reviewed_by"] == []


def test_a_repository_without_a_review_file_has_no_reviewer(tmp_path: Path) -> None:
    """The reviewer is derived from a file that exists, never assumed."""
    repo = tmp_path / "gamma"
    _put(repo, "CLAUDE.md")
    assert _rows(surfaces.survey(repo))["claude_md"]["reviewed_by"] == []


def test_the_json_is_stable_and_parses_back_to_the_survey(tmp_path: Path) -> None:
    """Two renderings are the same text and equal the survey's own record."""
    repo = tmp_path / "delta"
    _put(repo, "CLAUDE.md")
    first = surfaces.to_json(repo)
    assert first == surfaces.to_json(repo)
    assert first.endswith("\n")
    parsed: object = json.loads(first)
    assert parsed == surfaces.survey(repo)


def test_main_prints_the_survey_of_the_named_repository(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """One argument names the repository; stdout is exactly the JSON and the exit code is 0."""
    repo = tmp_path / "epsilon"
    _put(repo, "CLAUDE.md")
    assert surfaces.main([str(repo)]) == 0
    assert capsys.readouterr().out == surfaces.to_json(repo)


def test_main_refuses_a_missing_directory_and_extra_arguments(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A path that is not a directory, and a second argument, exit 2 with a usage line only."""
    assert surfaces.main([str(tmp_path / "absent")]) == _USAGE_EXIT
    assert surfaces.main([str(tmp_path), "extra"]) == _USAGE_EXIT
    seen = capsys.readouterr()
    assert not seen.out
    assert "usage: mikemol-surfaces" in seen.err
