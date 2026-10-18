# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""--tick-open says when the canonical loop prompt changed since the last tick (W1524)."""

import json
from pathlib import Path

import pytest

from mikemol.pathsforward import cli, promptwatch


def _files(tmp_path: Path) -> tuple[Path, Path]:
    return tmp_path / "loop-prompt.md", tmp_path / "git" / "mtools" / "loop-prompt.seen"


def test_an_absent_prompt_says_nothing_and_records_nothing(tmp_path: Path) -> None:
    """A repo with no canonical prompt has nothing to watch."""
    prompt, seen = _files(tmp_path)
    assert promptwatch.notice(prompt, seen) == []
    assert not seen.exists()


def test_the_first_reading_is_recorded_and_said_once(tmp_path: Path) -> None:
    """With no earlier text there is nothing to diff."""
    prompt, seen = _files(tmp_path)
    prompt.write_text("rule one\n", encoding="utf-8")
    first = promptwatch.notice(prompt, seen)
    assert len(first) == 1
    assert first[0].startswith("canonical loop prompt: first reading recorded")
    assert promptwatch.notice(prompt, seen) == []


def test_a_changed_prompt_names_the_lines_added_and_removed(tmp_path: Path) -> None:
    """The notice is the difference, so the reader need not find it."""
    prompt, seen = _files(tmp_path)
    prompt.write_text("rule one\nrule two\n", encoding="utf-8")
    promptwatch.notice(prompt, seen)
    prompt.write_text("rule one\nrule three\n", encoding="utf-8")
    got = promptwatch.notice(prompt, seen)
    assert got[0].startswith("canonical loop prompt changed since your last tick (2 lines)")
    assert got[1:] == ["  -rule two", "  +rule three"]


def test_a_change_repeats_until_it_is_acknowledged(tmp_path: Path) -> None:
    """Printing the lines is not a reading: every tick says them until --prompt-ack (W1563)."""
    prompt, seen = _files(tmp_path)
    prompt.write_text("a\n", encoding="utf-8")
    promptwatch.notice(prompt, seen)
    prompt.write_text("b\n", encoding="utf-8")
    first = promptwatch.notice(prompt, seen)
    assert first
    assert first[0].endswith("then run --prompt-ack")
    assert promptwatch.notice(prompt, seen) == first
    assert promptwatch.acknowledge(prompt, seen) is not None
    assert promptwatch.notice(prompt, seen) == []


def test_a_long_change_lists_a_few_lines_and_counts_the_rest(tmp_path: Path) -> None:
    """A rewrite does not flood the opening output."""
    prompt, seen = _files(tmp_path)
    prompt.write_text("old\n", encoding="utf-8")
    promptwatch.notice(prompt, seen)
    prompt.write_text("".join(f"line {n}\n" for n in range(promptwatch.SHOWN + 5)), "utf-8")
    got = promptwatch.notice(prompt, seen)
    assert len(got) == promptwatch.SHOWN + 2
    assert got[-1].startswith("  ... and ")


def test_tick_open_prints_the_notice_from_the_prompt_above_the_repo(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The canonical file lives in the directory above the repo, as it does under ~/github."""
    canonical = tmp_path / ".claude" / promptwatch.PROMPT_NAME
    canonical.parent.mkdir()
    canonical.write_text("rule one\n", encoding="utf-8")
    state = tmp_path / "myrepo" / ".claude" / "paths-forward.json"
    state.parent.mkdir(parents=True)
    root = str(tmp_path / "myrepo")
    doc: dict[str, object] = {"counter": 0, "waypoints": [], "project_root": root}
    state.write_text(json.dumps(doc), encoding="utf-8")
    assert cli.main(["--state", str(state), "--tick-open", "tester"]) == 0
    assert "canonical loop prompt: first reading recorded" in capsys.readouterr().out
    canonical.write_text("rule two\n", encoding="utf-8")
    cli.main(["--state", str(state), "--unlock", "tester"])
    capsys.readouterr()
    assert cli.main(["--state", str(state), "--tick-open", "tester"]) == 0
    assert "canonical loop prompt changed since your last tick" in capsys.readouterr().out


def test_an_acknowledgement_records_the_prompt_as_read_and_counts_its_lines(tmp_path: Path) -> None:
    """After it, the prompt as it stands is the reading the next notice compares against."""
    prompt, seen = _files(tmp_path)
    prompt.write_text("a\nb\n", encoding="utf-8")
    assert promptwatch.acknowledge(prompt, seen) == len(("a", "b"))
    assert seen.read_text(encoding="utf-8") == "a\nb\n"
    assert promptwatch.notice(prompt, seen) == []


def test_an_acknowledgement_of_no_prompt_or_of_a_record_that_did_not_take_is_none(
    tmp_path: Path,
) -> None:
    """It claims nothing it cannot read back."""
    prompt, seen = _files(tmp_path)
    assert promptwatch.acknowledge(prompt, seen) is None
    prompt.write_text("a\n", encoding="utf-8")
    blocker = tmp_path / "blocker"
    blocker.write_text("a file where the directory should be", encoding="utf-8")
    assert promptwatch.acknowledge(prompt, blocker / "loop-prompt.seen") is None


def test_the_prompt_ack_flag_records_the_reading_beside_the_git_directory(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The session says it read the prompt, by name, and the record is where the notice looks."""
    canonical = tmp_path / ".claude" / promptwatch.PROMPT_NAME
    canonical.parent.mkdir()
    canonical.write_text("rule one\n", encoding="utf-8")
    state = tmp_path / "myrepo" / ".claude" / "paths-forward.json"
    state.parent.mkdir(parents=True)
    root = str(tmp_path / "myrepo")
    doc: dict[str, object] = {"counter": 0, "waypoints": [], "project_root": root}
    state.write_text(json.dumps(doc), encoding="utf-8")
    assert cli.main(["--state", str(state), "--prompt-ack"]) == 0
    assert "loop prompt acknowledged" in capsys.readouterr().out
    seen = tmp_path / "myrepo" / ".git" / "mtools" / promptwatch.SEEN_NAME
    assert seen.read_text(encoding="utf-8") == "rule one\n"
    canonical.unlink()
    assert cli.main(["--state", str(state), "--prompt-ack"]) != 0
