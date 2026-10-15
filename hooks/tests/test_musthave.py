# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the must-have fixes list and the `mikemol-repin --must-have` verb (W1137).

⚑ THE CONTROLS: a short sha, no dists, a two-line reason, a repeated sha and a sha git cannot find
are each refused; a dry run writes nothing and `--write` writes once; adding the same fix again
changes nothing; and the check names every entry git cannot resolve.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, cast

from mikemol.hooks import musthave, musthave_cli, repin_cli

if TYPE_CHECKING:
    from collections.abc import Sequence

    import pytest

_A = "a" * 40
_B = "b" * 40
_C = "c" * 40
_REFUSED = 2


def _runner(missing: frozenset[str] = frozenset()) -> musthave.Runner:
    def run(argv: Sequence[str], _repo: Path) -> tuple[int, str]:
        sha = argv[-1].removesuffix("^{commit}")
        return (1, "unknown") if sha in missing else (0, "")

    return run


def _file(root: Path) -> Path:
    return root / musthave.FILE


def _read(root: Path) -> list[dict[str, object]]:
    return cast("list[dict[str, object]]", json.loads(_file(root).read_text(encoding="utf-8")))


def _verb(root: Path, *words: str, missing: frozenset[str] = frozenset()) -> int:
    valued: dict[str, list[str]] = {}
    flags: set[str] = set()
    rest = list(words)
    while rest:
        name = rest.pop(0)
        if name in {"--write", "--check-must-have"}:
            flags.add(name)
        else:
            valued.setdefault(name, []).append(rest.pop(0))
    return musthave_cli.run(root, valued, frozenset(flags), _runner(missing))


def test_a_sound_entry_has_no_shape_problem_and_each_defect_is_named() -> None:
    """A short sha, empty dists, a two-line reason, a bad requires and a repeated sha each fail."""
    good: dict[str, object] = {
        "sha": _A,
        "dists": ["hooks"],
        "reason": "one line",
        "requires": [_B],
    }
    assert musthave.shape_problems([good]) == []
    bad: list[dict[str, object]] = [
        {"sha": "abc", "dists": ["hooks"], "reason": "r", "requires": []},
        {"sha": _B, "dists": [], "reason": "r", "requires": []},
        {"sha": _C, "dists": ["hooks"], "reason": "two\nlines", "requires": ["short"]},
        good,
        good,
    ]
    said = "\n".join(musthave.shape_problems(bad))
    assert "entry 0: sha must be a full" in said
    assert "dists must be a non-empty list" in said
    assert "reason must be one non-empty line" in said
    assert "requires must be a list of full" in said
    assert "sha appears twice" in said


def test_adding_is_idempotent_on_sha_and_merges_dists_and_requires() -> None:
    """added, then unchanged on a rerun, then updated when a dist or the reason differs."""
    first, status = musthave.add([], _A, ["hooks"], "why", [])
    assert status == "added"
    again, status = musthave.add(first, _A, ["hooks"], "why", [])
    assert (status, again) == ("unchanged", first)
    more, status = musthave.add(again, _A, ["fence"], "why", [_B])
    assert status == "updated"
    assert (more[0]["dists"], more[0]["requires"]) == (["fence", "hooks"], [_B])
    reworded, status = musthave.add(more, _A, ["fence"], "better why", [])
    assert (status, reworded[0]["reason"]) == ("updated", "better why")


def test_a_missing_file_is_empty_a_bad_one_is_a_reason_and_save_is_stable(tmp_path: Path) -> None:
    """Absent loads as no entries; a non-list is refused with its path; save orders by sha."""
    path = tmp_path / "must_have.json"
    assert musthave.load(path) == []
    path.write_text("{}", encoding="utf-8")
    assert "not a JSON list" in str(musthave.load(path))
    path.write_text("[", encoding="utf-8")
    assert "cannot read" in str(musthave.load(path))
    entries, _ = musthave.add([], _B, ["x"], "r", [])
    entries, _ = musthave.add(entries, _A, ["x"], "r", [])
    musthave.save(path, entries)
    loaded = musthave.load(path)
    assert not isinstance(loaded, str)
    assert [e["sha"] for e in loaded] == [_A, _B]
    assert not path.with_name(path.name + ".tmp").exists()


def test_the_history_check_names_every_sha_and_required_sha_git_cannot_find() -> None:
    """One entry's own sha and its requires are both looked up; only the unknown ones are named."""
    entries, _ = musthave.add([], _A, ["hooks"], "r", [_B, _C])
    found = musthave.history_problems(entries, Path("/x"), _runner(frozenset({_A, _C})))
    assert len(found) == _REFUSED
    assert any(_A in line for line in found)
    assert any(f"requires {_C[:12]}" in line for line in found)
    assert musthave.history_problems(entries, Path("/x"), _runner()) == []


def test_a_dry_run_writes_nothing_and_write_writes_once(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """WOULD ADDED without --write and no file; ADDED with it; the rerun says UNCHANGED."""
    words = ["--must-have", _A, "--dists", "hooks", "--reason", "why", "--requires", _B]
    assert _verb(tmp_path, *words) == 0
    assert "WOULD ADDED aaaaaaaaaaaa" in capsys.readouterr().out
    assert not _file(tmp_path).exists()
    assert _verb(tmp_path, *words, "--write") == 0
    assert "ADDED aaaaaaaaaaaa" in capsys.readouterr().out
    assert _read(tmp_path)[0]["requires"] == [_B]
    assert _verb(tmp_path, *words, "--write") == 0
    assert "UNCHANGED" in capsys.readouterr().out


def test_a_refused_entry_exits_two_and_leaves_the_file_alone(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A short sha, no dists, and a sha git cannot find are each refused; nothing is written."""
    short = ["--must-have", "abc", "--dists", "hooks", "--reason", "r", "--write"]
    assert _verb(tmp_path, *short) == _REFUSED
    assert _verb(tmp_path, "--must-have", _A, "--reason", "r", "--write") == _REFUSED
    words = ["--must-have", _A, "--dists", "hooks", "--reason", "r", "--write"]
    assert _verb(tmp_path, *words, missing=frozenset({_A})) == _REFUSED
    assert not _file(tmp_path).exists()
    assert "is not a commit in this history" in capsys.readouterr().err


def test_the_check_exits_one_naming_a_problem_and_zero_when_sound(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A file whose sha git cannot find fails the check; the same file with it present passes."""
    assert _verb(tmp_path, "--must-have", _A, "--dists", "hooks", "--reason", "r", "--write") == 0
    capsys.readouterr()
    assert _verb(tmp_path, "--check-must-have") == 0
    assert "1 fix(es), 0 problem(s)" in capsys.readouterr().out
    assert _verb(tmp_path, "--check-must-have", missing=frozenset({_A})) == 1
    assert "PROBLEM aaaaaaaaaaaa" in capsys.readouterr().out


def test_repin_main_routes_the_must_have_modes_to_the_verb(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The shell hands `--must-have` and `--check-must-have` over with the --mtools directory."""
    seen: list[str] = []

    def runner(argv: Sequence[str], _repo: Path) -> tuple[int, str]:
        seen.append(argv[-1])
        return 0, ""

    words = ["--must-have", _A, "--dists", "hooks", "--reason", "r", "--mtools", str(tmp_path)]
    assert repin_cli.main([*words, "--write"], runner) == 0
    assert _read(tmp_path)[0]["sha"] == _A
    assert seen == [f"{_A}^{{commit}}"]
    assert repin_cli.main(["--check-must-have", "--mtools", str(tmp_path)], runner) == 0
    assert "1 fix(es), 0 problem(s)" in capsys.readouterr().out
