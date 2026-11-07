# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses of a whole stack run: one gate, every commit pushed, a verdict each, or nothing lands.

W1162. ⚑ THE HOOK COUNTS ITS OWN RUNS into the real checkout, so "one gate for N commits" is read
from a file the gate wrote, not from the module. ⚑ THE REMOTE IS READ BACK from a bare repository.
The refusing hook is the control: a stack that landed anyway shows as a moved HEAD or remote.
"""

from __future__ import annotations

import io
import json
import os
from typing import TYPE_CHECKING

from mikemol.hooks import commit_kata as ck
from mikemol.hooks import scratch, stackrun

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    import pytest


_EXECUTABLE = 0o755
_PASSING = '#!/bin/sh\necho run >> "$MIKEMOL_REAL_ROOT/runs"\n'
_REFUSING = '#!/bin/sh\necho run >> "$MIKEMOL_REAL_ROOT/runs"\necho "gate says no" >&2\nexit 1\n'
_PUSH = "#!/bin/sh\ngit push origin HEAD:main\n"


def _git(root: Path, *args: str) -> str:
    """Run the real git and fail loudly.

    Returns:
        git's stdout.

    """
    code, out = scratch.git_out(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@example.invalid",
            *args,
        ]
    )
    assert code == 0, out
    return out


def _repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, pre_commit: str) -> tuple[Path, Path]:
    """Build a pushed repository with the given pre-commit, a pushing post-commit, edits to a, b.

    Returns:
        the working repository's root and the bare remote's path.

    """
    for name in [name for name in os.environ if name.startswith("GIT_")]:
        monkeypatch.delenv(name)
    for key, value in {
        "GIT_CEILING_DIRECTORIES": str(tmp_path),
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.invalid",
        "GIT_CONFIG_NOSYSTEM": "1",
        "HOME": str(tmp_path),
    }.items():
        monkeypatch.setenv(key, value)
    remote = tmp_path / "origin.git"
    remote.mkdir()
    _git(remote, "init", "--quiet", "--bare", "-b", "main")
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "--quiet", "-b", "main")
    for name in ("a.txt", "b.txt"):
        (root / name).write_text("original\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "--quiet", "-m", "first")
    _git(root, "remote", "add", "origin", str(remote))
    _git(root, "push", "--quiet", "origin", "HEAD:main")
    for hook_name, text in (("pre-commit", pre_commit), ("post-commit", _PUSH)):
        hook = root / ".git" / "hooks" / hook_name
        hook.write_text(text, encoding="utf-8")
        hook.chmod(_EXECUTABLE)
    (root / "a.txt").write_text("edited a\n", encoding="utf-8")
    (root / "b.txt").write_text("edited b\n", encoding="utf-8")
    return root, remote


def _items() -> list[stackrun.Item]:
    """Name the two commits asked for.

    Returns:
        the items: a.txt under W1, then b.txt under W2.

    """
    return [
        stackrun.Item("W1", "first card", "", ("a.txt",)),
        stackrun.Item("W2", "second card", "", ("b.txt",)),
    ]


def _run(root: Path, tmp_path: Path, flaked: list[Path] | None = None) -> tuple[int, list[str]]:
    """Run the stack with the real git; `flaked`, when given, collects each flake's git directory.

    Returns:
        the exit code and the lines written.

    """
    out = io.StringIO()

    def on_flake(git_dir: Path) -> bool:
        if flaked is None:
            return False
        flaked.append(git_dir)
        return True

    seams = stackrun.Seams(
        run=ck.run_git_in,
        namespace=tmp_path / "gate",
        message_of=lambda item: f"{item.subject}\n\nWaypoint: {item.waypoint}\n",
        published=lambda _sha: "PUSHED",
        flaked=on_flake,
    )
    code = stackrun.run_stack(root, _items(), out, seams)
    return code, out.getvalue().splitlines()


def test_a_stack_lands_with_one_gate_run_one_verdict_per_commit_and_the_remote_at_the_tip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two COMMITTED lines in order, the hook ran once, HEAD and origin both read the second sha."""
    root, remote = _repo(tmp_path, monkeypatch, _PASSING)
    code, lines = _run(root, tmp_path)
    assert code == 0
    tip = _git(root, "rev-parse", "HEAD").strip()
    first = _git(root, "rev-parse", "HEAD^").strip()
    verdicts = [line for line in lines if line.startswith("COMMITTED")]
    assert verdicts == [
        f"COMMITTED repo {first[:7]} first card [PUSHED]",
        f"COMMITTED repo {tip[:7]} second card [PUSHED]",
    ]
    assert (root / "runs").read_text(encoding="utf-8") == "run\n"
    assert _git(remote, "rev-parse", "main").strip() == tip


def test_a_refused_tip_lands_nothing_and_says_so(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The control: the gate refuses, HEAD and the remote are where they were, the line says why."""
    root, remote = _repo(tmp_path, monkeypatch, _REFUSING)
    start = _git(root, "rev-parse", "HEAD").strip()
    code, lines = _run(root, tmp_path)
    assert code == 1
    assert any(
        line.startswith("REFUSED repo (rc=1)") and "nothing landed" in line for line in lines
    )
    assert "gate says no" in lines
    assert _git(root, "rev-parse", "HEAD").strip() == start
    assert _git(remote, "rev-parse", "main").strip() == start
    assert not [line for line in lines if line.startswith("COMMITTED")]


def test_a_pass_on_a_tree_that_was_refused_is_named_a_flake_and_recorded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """W2007: the same files, a refusing hook then a passing one: the second run says FLAKE."""
    root, _remote = _repo(tmp_path, monkeypatch, _REFUSING)
    code, lines = _run(root, tmp_path)
    assert code == 1
    assert not [line for line in lines if line.startswith("FLAKE")]
    (root / ".git" / "hooks" / "pre-commit").write_text(_PASSING, encoding="utf-8")
    code, lines = _run(root, tmp_path)
    assert code == 0
    flake = [line for line in lines if line.startswith("FLAKE repo:")]
    assert len(flake) == 1
    assert "refused before" in flake[0]
    kept = (root / ".git" / "mtools" / "gate-verdicts.jsonl").read_text(encoding="utf-8")
    kinds = [line for line in kept.splitlines() if '"kind"' in line]
    assert ['"refused"' in kinds[0], '"passed"' in kinds[1], '"flake"' in kinds[2]] == [True] * 3


def test_a_flake_tells_the_metric_seam_and_a_plain_pass_does_not(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """W2009: the seam is called once, with the repository's git directory, only on a flake.

    The controls are the first run (refused) and a clean pass on a tree never refused.
    """
    root, _remote = _repo(tmp_path, monkeypatch, _REFUSING)
    seen: list[Path] = []
    code, _lines = _run(root, tmp_path, seen)
    assert (code, seen) == (1, [])
    (root / ".git" / "hooks" / "pre-commit").write_text(_PASSING, encoding="utf-8")
    code, _lines = _run(root, tmp_path, seen)
    assert code == 0
    assert seen == [root / ".git"]
    (tmp_path / "clean").mkdir()
    clean, _other = _repo(tmp_path / "clean", monkeypatch, _PASSING)
    code, _lines = _run(clean, tmp_path / "clean", seen)
    assert (code, len(seen)) == (0, 1)


def test_a_tip_whose_declared_mutants_do_not_plant_is_refused_before_the_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The lint's problems are printed, nothing lands, and the gate never runs (W1704)."""
    root, remote = _repo(tmp_path, monkeypatch, _PASSING)
    start = _git(root, "rev-parse", "HEAD").strip()
    seen: list[list[str]] = []

    def lint(snapshot: Path, dists: Sequence[str]) -> list[str]:
        seen.append([snapshot.name, *dists])
        return ["dist: M1: the pattern matches nothing in its scope"]

    out = io.StringIO()
    seams = stackrun.Seams(
        run=ck.run_git_in,
        namespace=tmp_path / "gate",
        message_of=lambda item: f"{item.subject}\n\nWaypoint: {item.waypoint}\n",
        published=lambda _sha: "PUSHED",
        lint=lint,
    )
    (root / "pkg").mkdir()
    (root / "pkg" / "a.txt").write_text("a\n", encoding="utf-8")
    items = [
        stackrun.Item("W1", "first card", "", ("pkg/a.txt",)),
        stackrun.Item("W2", "second card", "", ("b.txt",)),
    ]
    assert stackrun.run_stack(root, items, out, seams) == 1
    lines = out.getvalue().splitlines()
    assert "dist: M1: the pattern matches nothing in its scope" in lines
    assert any(line.startswith("REFUSED repo (rc=1)") and "W1704" in line for line in lines)
    assert [found[1:] for found in seen] == [["pkg"]]
    assert not (root / "runs").exists()
    assert _git(root, "rev-parse", "HEAD").strip() == start
    assert _git(remote, "rev-parse", "main").strip() == start


def test_a_stack_file_is_read_and_a_malformed_one_is_named(tmp_path: Path) -> None:
    """A good file gives its items; a non-list and an entry without paths each say what is wrong."""
    good = tmp_path / "good.json"
    entries = [{"waypoint": "W1", "subject": "s", "body": "b", "paths": ["a"]}]
    good.write_text(json.dumps(entries), encoding="utf-8")
    assert stackrun.items_of(good) == [stackrun.Item("W1", "s", "b", ("a",))]
    bad = tmp_path / "bad.json"
    bad.write_text('{"waypoint": "W1"}', encoding="utf-8")
    assert "non-empty JSON list" in str(stackrun.items_of(bad))
    bad.write_text('[{"waypoint": "W1", "subject": "s", "paths": []}]', encoding="utf-8")
    assert "entry 1 needs" in str(stackrun.items_of(bad))


def test_an_entry_whose_body_carries_a_tool_trailer_is_named_with_its_place(
    tmp_path: Path,
) -> None:
    """W1273: entry 2's body has a Waypoint: line, so the whole file is refused naming entry 2."""
    entries = [
        {"waypoint": "W1", "subject": "s", "body": "fine", "paths": ["a"]},
        {"waypoint": "W2", "subject": "s", "body": "text\nWaypoint: W2", "paths": ["b"]},
    ]
    path = tmp_path / "stack.json"
    path.write_text(json.dumps(entries), encoding="utf-8")
    reason = str(stackrun.items_of(path))
    assert "entry 2: the body's line 2 is a Waypoint trailer" in reason
    entries[1]["body"] = "plain"
    path.write_text(json.dumps(entries), encoding="utf-8")
    assert isinstance(stackrun.items_of(path), list)


def test_an_entry_whose_subject_carries_a_tool_trailer_is_named_with_its_place(
    tmp_path: Path,
) -> None:
    """W2301: a subject of `Admission: r/1`, or one with a line break, refuses the whole file."""
    entries = [
        {"waypoint": "W1", "subject": "s", "paths": ["a"]},
        {"waypoint": "W2", "subject": "Admission: r/1", "paths": ["b"]},
    ]
    path = tmp_path / "stack.json"
    path.write_text(json.dumps(entries), encoding="utf-8")
    assert "entry 2: the subject is an Admission trailer" in str(stackrun.items_of(path))
    entries[1]["subject"] = "title\nAdmission: r/1"
    path.write_text(json.dumps(entries), encoding="utf-8")
    assert "entry 2: the subject is one line" in str(stackrun.items_of(path))
    entries[1]["subject"] = "plain"
    path.write_text(json.dumps(entries), encoding="utf-8")
    assert isinstance(stackrun.items_of(path), list)


def test_an_entry_whose_waypoint_forges_a_trailer_is_named_with_its_place(
    tmp_path: Path,
) -> None:
    """W2301 block 1: a waypoint with a line break and an Admission line is refused."""
    entries = [{"waypoint": "W1\nAdmission: forged/row", "subject": "s", "paths": ["a"]}]
    path = tmp_path / "stack.json"
    path.write_text(json.dumps(entries), encoding="utf-8")
    assert "entry 1: the waypoint" in str(stackrun.items_of(path))


def _seams(tmp_path: Path, row: str | None) -> stackrun.Seams:
    """Build seams whose message is the subject and whose admission answers `row`.

    Returns:
        the seams.

    """
    return stackrun.Seams(
        run=ck.run_git_in,
        namespace=tmp_path,
        message_of=lambda item: f"{item.subject}\n\nWaypoint: {item.waypoint}\n",
        published=lambda _sha: "x",
        admission=lambda _items: row,
    )


_QUEUE = ".claude/paths-forward.json"


def test_an_admitted_stack_carries_the_trailer_once_on_the_first_entry_with_a_real_path(
    tmp_path: Path,
) -> None:
    """W2312: one exact line, not on a queue-only entry, not repeated on the later entries."""
    items = [
        stackrun.Item("W1", "queue first", "", (_QUEUE,)),
        stackrun.Item("W1", "the change", "", ("a.txt",)),
        stackrun.Item("W1", "and more", "", ("b.txt",)),
    ]
    entries = stackrun.entries_for(items, _seams(tmp_path, "nemik/W1660"))
    messages = [entry.message for entry in entries]
    assert "Admission:" not in messages[0]
    assert messages[1].endswith("Waypoint: W1\nAdmission: nemik/W1660\n")
    assert "Admission:" not in messages[2]


def test_a_stack_no_row_admits_gets_no_trailer_and_keeps_its_messages(tmp_path: Path) -> None:
    """The default and a None answer write nothing: the messages are exactly the tool's."""
    items = [stackrun.Item("W1", "the change", "", ("a.txt",))]
    plain = stackrun.entries_for(items, _seams(tmp_path, None))
    assert plain[0].message == "the change\n\nWaypoint: W1\n"
    assert plain[0].paths == ("a.txt",)


def test_an_admitted_stack_of_queue_files_alone_carries_no_trailer(tmp_path: Path) -> None:
    """With no entry that has a real path there is nothing to spend a row on."""
    items = [stackrun.Item("W1", "queue", "", (_QUEUE,))]
    entries = stackrun.entries_for(items, _seams(tmp_path, "nemik/W1660"))
    assert "Admission:" not in entries[0].message


_NAMING = '#!/bin/sh\necho "lint: b.txt line 3 is wrong" >&2\nexit 1\n'


def test_the_refused_line_names_the_entry_whose_path_the_gate_printed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The gate names b.txt, so the second entry is blamed and the first is not."""
    root, _remote = _repo(tmp_path, monkeypatch, _NAMING)
    code, lines = _run(root, tmp_path)
    assert code == 1
    refused = [line for line in lines if line.startswith("REFUSED")]
    assert len(refused) == 1
    assert refused[0].endswith("culprit: entry 2/2 (W2)")


def test_a_gate_that_names_no_path_of_the_stack_is_unattributed_not_guessed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The control: a refusal with no path in it blames nobody, and says so."""
    root, _remote = _repo(tmp_path, monkeypatch, _REFUSING)
    _code, lines = _run(root, tmp_path)
    refused = [line for line in lines if line.startswith("REFUSED")]
    assert refused[0].endswith(
        "culprit: unattributed (the failing check names no path in this stack)"
    )


def test_a_path_matches_exactly_as_a_trailing_path_or_inside_a_directory() -> None:
    """The three shapes count; a longer name that merely contains the path does not."""
    items = [
        stackrun.Item("W1", "s", "", ("src/a.py",)),
        stackrun.Item("W2", "s", "", ("docs/",)),
        stackrun.Item("W3", "s", "", ("c.txt",)),
    ]
    assert stackrun.culprits("error in src/a.py:3", items) == [0]
    assert stackrun.culprits("/gate/tree/src/a.py:9: failed", items) == [0]
    assert stackrun.culprits("docs/guide.md is empty", items) == [1]
    assert stackrun.culprits("see abc.txt and xc.txt", items) == []
    assert stackrun.culprits("c.txt and src/a.py", items) == [0, 2]


_COUNT_LINES = 40
_SECTION = 12


def _output_with_a_section(counts: int, section: int) -> str:
    """Build gate output: per-dist counts, then the said-marker and a numbered section.

    Returns:
        the output text.

    """
    head = [f"/staged/dist{i}: {i} test functions, 0 finding(s)" for i in range(counts)]
    tail = [f"      failing line {i}" for i in range(section)]
    return "\n".join([*head, f"pre-commit: {stackrun.SAID}", "  --- the check", *tail])


def test_the_refusal_ends_on_the_failing_checks_own_lines_not_the_counts_above_them() -> None:
    """Forty count lines above a twelve-line section: the tail is the section alone."""
    shown = _output_with_a_section(_COUNT_LINES, _SECTION)
    tail = stackrun.refusal_tail(shown).splitlines()
    assert tail[0] == "  --- the check"
    assert tail[-1] == f"      failing line {_SECTION - 1}"
    assert not [line for line in tail if "test functions" in line]


def test_a_section_longer_than_the_measured_bound_keeps_its_last_lines() -> None:
    """The bound is a ceiling: a longer section is cut from the top, never from the end."""
    shown = _output_with_a_section(0, stackrun.SECTION_LINES + _SECTION)
    tail = stackrun.refusal_tail(shown).splitlines()
    assert len(tail) == stackrun.SECTION_LINES
    assert tail[-1] == f"      failing line {stackrun.SECTION_LINES + _SECTION - 1}"


_SAYING = (
    "#!/bin/sh\n"
    'echo "pre-commit: the failing check(s) said:" >&2\n'
    'echo "  --- the check" >&2\n'
    'echo "      the cause" >&2\n'
    "exit 1\n"
)


def test_a_refused_stack_ends_on_the_failing_checks_lines_after_the_refused_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """W1662: the REFUSED line is followed by the check's own section, so the verdict ends on it."""
    root, _remote = _repo(tmp_path, monkeypatch, _SAYING)
    code, lines = _run(root, tmp_path)
    assert code == 1
    place = next(i for i, line in enumerate(lines) if line.startswith("REFUSED"))
    assert lines[place + 1 :] == ["  --- the check", "      the cause"]


def test_output_with_no_failing_section_adds_nothing() -> None:
    """The control: a refusal that printed no section gets no reprint."""
    assert not stackrun.refusal_tail("gate says no\n")
    assert not stackrun.refusal_tail("")


def test_a_stack_the_landing_refuses_never_becomes_a_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """W2330 B1: the pace judged again at the landing refuses; HEAD does not move; rc is 1."""
    root, _remote = _repo(tmp_path, monkeypatch, _PASSING)
    before = _git(root, "rev-parse", "HEAD").strip()
    seams = stackrun.Seams(
        run=ck.run_git_in,
        namespace=tmp_path / "gate",
        message_of=lambda item: f"{item.subject}\n\nWaypoint: {item.waypoint}\n",
        published=lambda _sha: "PUSHED",
        landing_refusal=lambda _items: "behind its ratchet paydown",
    )
    out = io.StringIO()
    assert stackrun.run_stack(root, _items(), out, seams) == 1
    assert "refused at the landing: behind its ratchet paydown" in out.getvalue()
    assert _git(root, "rev-parse", "HEAD").strip() == before


def test_entries_for_builds_what_it_is_given_and_leaves_the_pace_to_its_callers(
    tmp_path: Path,
) -> None:
    """The pace is judged by run_stack and, per group, by the train, not by the builder."""
    seams = stackrun.Seams(
        run=ck.run_git_in,
        namespace=tmp_path,
        message_of=lambda item: item.subject,
        published=lambda _sha: "x",
        admission=lambda _items: "nemik/W1660",
        landing_refusal=lambda _items: "still refused",
    )
    entries = stackrun.entries_for([stackrun.Item("W1", "s", "", ("a.txt",))], seams)
    assert entries[0].message.endswith("Admission: nemik/W1660\n")
