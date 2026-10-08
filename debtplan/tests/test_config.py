# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The repository's own debtplan file: known keys only, an absent file declares nothing (W791)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.debtplan.cli import EXIT_CANNOT, EXIT_OK, main
from mikemol.debtplan.config import Config, ConfigError, parse_config, path_for, read_config

if TYPE_CHECKING:
    from pathlib import Path

_BUILD_SKIPPED = '{"exclude": ["build"]}'
_STOP = "stop after the resolutions are seen"


def _no_worktrees(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the walk's git question answer none, so no repository is needed."""

    def fake(_root: Path) -> list[Path]:
        return []

    monkeypatch.setattr("mikemol.pathwalk.walk.other_worktrees", fake)


def _declare(root: Path, doc: str) -> Path:
    """Write a repository's debtplan file.

    Returns:
        Its path.

    """
    path = path_for(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(doc, encoding="utf-8")
    return path


def test_both_keys_are_read() -> None:
    """The exclusions keep their order and the resolutions their mapping."""
    got = parse_config('{"exclude": ["build", "x"], "resolutions": {"a": "p/a.py"}}', "d.json")
    assert got == Config(("build", "x"), {"a": "p/a.py"})


def test_an_empty_object_declares_nothing() -> None:
    """Both keys are optional."""
    assert parse_config("{}", "d.json") == Config()


@pytest.mark.parametrize(
    ("doc", "match"),
    [
        ("{", "not valid JSON"),
        ("[]", "expected a JSON object, got list"),
        ('{"excludes": []}', r"unknown key\(s\) \['excludes'\]"),
        ('{"exclude": "build"}', "exclude must be a list"),
        ('{"exclude": ["a/b"]}', "no '/'"),
        ('{"exclude": [""]}', "non-empty"),
        ('{"exclude": [3]}', "non-empty"),
        ('{"resolutions": []}', "expected a JSON object of name to file"),
        ('{"resolutions": {"a": 3}}', "must map to a file path string"),
    ],
)
def test_a_malformed_file_is_refused_naming_what_is_wrong(doc: str, match: str) -> None:
    """A misspelt key must not silently drop every exclusion, so each shape error is named."""
    with pytest.raises(ConfigError, match=match):
        parse_config(doc, "d.json")


def test_an_absent_file_declares_nothing(tmp_path: Path) -> None:
    """No file is no declarations; the repository simply has not declared any."""
    assert read_config(tmp_path) == Config()


def test_a_file_is_read_from_the_repository_s_claude_directory(tmp_path: Path) -> None:
    """The file lives at .claude/debtplan.json under the root."""
    _declare(tmp_path, _BUILD_SKIPPED)
    assert path_for(tmp_path) == tmp_path / ".claude" / "debtplan.json"
    assert read_config(tmp_path) == Config(("build",), {})


def test_a_symlinked_file_is_refused_as_data(tmp_path: Path) -> None:
    """A link is never followed, whatever it points at."""
    real = tmp_path / "real.json"
    real.write_text("{}", encoding="utf-8")
    link = path_for(tmp_path)
    link.parent.mkdir(parents=True)
    link.symlink_to(real)
    with pytest.raises(ConfigError, match="is a link; refused as data"):
        read_config(tmp_path)


def _repo(root: Path) -> Path:
    """Plant a clean leaf, a file in a build directory, and a ledger over the leaf.

    Returns:
        The ledger's path.

    """
    (root / "build").mkdir()
    (root / "build" / "gen.py").write_text("y = 1\n", encoding="utf-8")
    (root / "leaf.py").write_text("x = 1\n", encoding="utf-8")
    ledger = root / "ledger.json"
    ledger.write_text('{"leaf.py": 2}', encoding="utf-8")
    return ledger


def _universe(root: Path, ledger: Path, *extra: str, capsys: pytest.CaptureFixture[str]) -> int:
    """Run `plan` and read the walk's file count from its stderr line.

    Returns:
        The number of files in the universe.

    """
    assert main(["plan", "--root", str(root), "--ledger", str(ledger), *extra]) == EXIT_OK
    said = capsys.readouterr().err
    return int(said.split("universe ")[1].split(" file")[0])


def test_the_repository_s_exclusions_apply_without_a_flag(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A directory the file names is skipped on every run, so two runs agree."""
    _no_worktrees(monkeypatch)
    ledger = _repo(tmp_path)
    assert _universe(tmp_path, ledger, capsys=capsys) == len(("leaf.py", "build/gen.py"))
    _declare(tmp_path, _BUILD_SKIPPED)
    assert _universe(tmp_path, ledger, capsys=capsys) == len(("leaf.py",))


def test_a_flag_adds_to_the_file_and_never_un_skips_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exclusions are the union: --exclude can only skip more than the repository declared."""
    _no_worktrees(monkeypatch)
    ledger = _repo(tmp_path)
    (tmp_path / "other").mkdir()
    (tmp_path / "other" / "o.py").write_text("z = 1\n", encoding="utf-8")
    _declare(tmp_path, _BUILD_SKIPPED)
    assert _universe(tmp_path, ledger, "--exclude", "other", capsys=capsys) == len(("leaf.py",))


def test_a_malformed_repository_file_refuses_the_whole_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The run is exit 2 naming the key, never a plan made without the repository's exclusions."""
    _no_worktrees(monkeypatch)
    ledger = _repo(tmp_path)
    _declare(tmp_path, '{"excludes": ["build"]}')
    assert main(["plan", "--root", str(tmp_path), "--ledger", str(ledger)]) == EXIT_CANNOT
    assert "unknown key(s)" in capsys.readouterr().err


def test_a_flag_resolution_wins_over_the_file_s_for_the_same_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The file is the base and a --resolutions file overrides it per name."""
    _no_worktrees(monkeypatch)
    ledger = _repo(tmp_path)
    _declare(tmp_path, '{"resolutions": {"a": "from_file.py", "b": "b.py"}}')
    flagged = tmp_path / "flag.json"
    flagged.write_text('{"a": "from_flag.py"}', encoding="utf-8")
    seen: dict[str, str] = {}

    def spy(_ledger: object, _root: Path, _files: object, declared: dict[str, str] | None) -> None:
        seen.update(declared or {})
        raise ConfigError(_STOP)

    monkeypatch.setattr("mikemol.debtplan.cli.plan", spy)
    argv = ["plan", "--root", str(tmp_path), "--ledger", str(ledger), "--resolutions", str(flagged)]
    assert main(argv) == EXIT_CANNOT
    assert seen == {"a": "from_flag.py", "b": "b.py"}
