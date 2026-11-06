# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that a stack of commits is built without a hook, each holding only its own paths.

W1160. ⚑ THE HOOK IS THE CONTROL: the repository carries a pre-commit that fails and leaves a
marker, so a build that ran `git commit` would show the marker and one built with plumbing does not.
Every claim is read from real git (`show --name-only`, `rev-parse`), not from the module's return.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest

from mikemol.hooks import commit_kata as ck
from mikemol.hooks import runproc, scratch, stackland

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path


_HOOK = "#!/bin/sh\ntouch hook-ran\nexit 1\n"
_TWO = 2
_EXECUTABLE = 0o755


def _git(root: Path, *args: str) -> str:
    """Run the real git and fail loudly.

    Returns:
        git's stdout.

    """
    code, out = scratch.git_out(
        ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args]
    )
    assert code == 0, out
    return out


def _repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Build a repository with a, b, c committed, a failing pre-commit and edits to a, b and c.

    Returns:
        the repository's root.

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
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "--quiet")
    for name in ("a.txt", "b.txt", "c.txt"):
        (root / name).write_text("original\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "--quiet", "-m", "first")
    hook = root / ".git" / "hooks" / "pre-commit"
    hook.write_text(_HOOK, encoding="utf-8")
    hook.chmod(_EXECUTABLE)
    (root / "a.txt").write_text("edited a\n", encoding="utf-8")
    (root / "b.txt").write_text("edited b\n", encoding="utf-8")
    (root / "c.txt").write_text("a peer's unstaged edit\n", encoding="utf-8")
    return root


def test_each_commit_holds_only_its_own_paths_in_order_and_no_hook_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two entries make two commits: a.txt then b.txt; c.txt is never in either; HEAD is unmoved."""
    root = _repo(tmp_path, monkeypatch)
    head = _git(root, "rev-parse", "HEAD").strip()
    entries = [
        stackland.Entry("first card\n\nWaypoint: W1\n", ("a.txt",)),
        stackland.Entry("second card\n\nWaypoint: W2\n", ("b.txt",)),
    ]
    stack = stackland.build(root, entries, ck.run_git_in, head)
    assert stack.failed is None
    assert len(stack.commits) == _TWO
    first, second = stack.commits
    assert _git(root, "show", "--name-only", "--format=", first).split() == ["a.txt"]
    assert _git(root, "show", "--name-only", "--format=", second).split() == ["b.txt"]
    assert _git(root, "rev-parse", f"{second}^").strip() == first
    assert _git(root, "rev-parse", f"{first}^").strip() == head
    assert "Waypoint: W2" in _git(root, "log", "-1", "--format=%B", second)
    assert _git(root, "rev-parse", "HEAD").strip() == head
    assert not (root / "hook-ran").exists()


def test_a_path_git_cannot_add_stops_the_chain_and_returns_what_was_built(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The second entry names a file that is not there: the first commit is built, then it fails."""
    root = _repo(tmp_path, monkeypatch)
    head = _git(root, "rev-parse", "HEAD").strip()
    entries = [stackland.Entry("one\n", ("a.txt",)), stackland.Entry("two\n", ("missing.txt",))]
    stack = stackland.build(root, entries, ck.run_git_in, head)
    assert len(stack.commits) == 1
    assert stack.failed is not None
    assert stack.failed.returncode != 0
    assert _git(root, "rev-parse", "HEAD").strip() == head


def test_the_tip_names_its_own_tree_and_every_earlier_commit_names_the_tip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stack gates only its tip: Gated-Tree on the last commit, Gated-by: its waypoint before."""
    root = _repo(tmp_path, monkeypatch)
    head = _git(root, "rev-parse", "HEAD").strip()
    entries = [
        stackland.Entry("W1: first card\n\nWaypoint: W1\n", ("a.txt",)),
        stackland.Entry("W2: second card\n\nWaypoint: W2\n", ("b.txt",)),
    ]
    stack = stackland.build(root, entries, ck.run_git_in, head)
    first, second = stack.commits
    assert "Gated-by: W2" in _git(root, "log", "-1", "--format=%B", first)
    assert "Gated-Tree" not in _git(root, "log", "-1", "--format=%B", first)
    tip_message = _git(root, "log", "-1", "--format=%B", second)
    assert f"Gated-Tree: {stack.trees[-1]}" in tip_message
    assert "Gated-by" not in tip_message


def test_a_one_entry_stack_is_its_own_tip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """With nothing before it, the only commit carries the tree trailer and no Gated-by."""
    root = _repo(tmp_path, monkeypatch)
    head = _git(root, "rev-parse", "HEAD").strip()
    stack = stackland.build(root, [stackland.Entry("W7: only\n", ("a.txt",))], ck.run_git_in, head)
    only = _git(root, "log", "-1", "--format=%B", stack.commits[0])
    assert f"Gated-Tree: {stack.trees[0]}" in only
    assert "Gated-by" not in only


def test_the_tip_name_is_the_leading_waypoint_or_a_dash() -> None:
    """A message that does not open with a waypoint has no name to give, and says so."""
    assert stackland.tip_name("W1757: withdraw") == "W1757"
    assert stackland.tip_name("card two\n\nWaypoint: W2\n") == "W2"
    assert stackland.tip_name("no waypoint here") == stackland.NO_TIP


_ROW = "nemik/W1660/series"


def _landed(root: Path, message: str) -> str:
    """Land an empty commit with `message` on HEAD, past the failing hook.

    Returns:
        the new HEAD.

    """
    _git(root, "commit", "--quiet", "--no-verify", "--allow-empty", "-m", message)
    return _git(root, "rev-parse", "HEAD").strip()


def test_an_admission_already_in_history_refuses_the_whole_chain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SPENT is history's: a commit reachable from head with the exact line spends the row."""
    root = _repo(tmp_path, monkeypatch)
    head = _landed(root, f"first use\n\nAdmission: {_ROW}")
    entries = [stackland.Entry(f"repeat\n\nAdmission: {_ROW}\n", ("a.txt",))]
    stack = stackland.build(root, entries, ck.run_git_in, head)
    assert stack.commits == []
    assert stack.failed is not None
    assert "already spent" in stack.failed.stderr
    assert _git(root, "rev-parse", "HEAD").strip() == head


def test_an_unspent_admission_lands(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The control: a row nothing carries lands with its trailer."""
    root = _repo(tmp_path, monkeypatch)
    head = _git(root, "rev-parse", "HEAD").strip()
    entries = [stackland.Entry(f"use\n\nAdmission: {_ROW}\n", ("a.txt",))]
    stack = stackland.build(root, entries, ck.run_git_in, head)
    assert stack.failed is None
    landed = _git(root, "log", "-1", "--format=%B", stack.commits[0])
    assert f"Admission: {_ROW}" in landed


def test_the_same_row_twice_in_one_chain_is_refused_at_the_second(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two stacks in one train cannot both be admitted: the cumulative index names the second."""
    root = _repo(tmp_path, monkeypatch)
    head = _git(root, "rev-parse", "HEAD").strip()
    entries = [
        stackland.Entry(f"one\n\nAdmission: {_ROW}\n", ("a.txt",)),
        stackland.Entry(f"two\n\nAdmission: {_ROW}\n", ("b.txt",)),
    ]
    stack = stackland.build(root, entries, ck.run_git_in, head)
    assert len(stack.commits) == 1
    assert stack.failed is not None
    assert "already spent" in stack.failed.stderr


def test_a_line_that_only_mentions_an_admission_in_prose_spends_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The trailer is an EXACT line: the words inside a sentence do not forge it."""
    root = _repo(tmp_path, monkeypatch)
    head = _landed(root, f"see Admission: {_ROW} for the rule")
    entries = [stackland.Entry(f"use\n\nAdmission: {_ROW}\n", ("a.txt",))]
    stack = stackland.build(root, entries, ck.run_git_in, head)
    assert stack.failed is None


_ROW_TWO = "nemik/W1660/other"


def _head(root: Path) -> str:
    """Read HEAD.

    Returns:
        the commit id.

    """
    return _git(root, "rev-parse", "HEAD").strip()


def _failing_log(argv: Sequence[str], env: Mapping[str, str], cwd: Path) -> runproc.Result:
    """Run real git except `log`, which fails as a broken repository's would.

    Returns:
        git's answer, or a failed one for `log`.

    """
    if argv and argv[0] == "log":
        return runproc.Result(128, "", "fatal: broken")
    return ck.run_git_in(argv, env, cwd)


def test_an_admitted_entry_with_a_file_and_no_change_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A replay: an admitted non-queue entry whose change is already in the parent fails."""
    root = _repo(tmp_path, monkeypatch)
    first = stackland.build(
        root, [stackland.Entry("one\n", ("a.txt",))], ck.run_git_in, _head(root)
    )
    repeat = [stackland.Entry(f"two\n\nAdmission: {_ROW}\n", ("a.txt",))]
    again = stackland.build(root, repeat, ck.run_git_in, first.commits[0])
    assert again.commits == []
    assert again.failed is not None
    assert "changes nothing" in again.failed.stderr


def test_a_follower_with_no_admission_that_changes_nothing_still_lands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """github-14's B1: an honest same-blob follower is not a replay and must land."""
    root = _repo(tmp_path, monkeypatch)
    first = stackland.build(
        root, [stackland.Entry("one\n", ("a.txt",))], ck.run_git_in, _head(root)
    )
    follower = [stackland.Entry("two\n", ("a.txt",))]
    again = stackland.build(root, follower, ck.run_git_in, first.commits[0])
    assert again.failed is None
    assert len(again.commits) == 1


def test_a_stack_that_renames_an_earlier_entrys_path_still_lands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two entries naming one path, with no admission, are both built."""
    root = _repo(tmp_path, monkeypatch)
    entries = [stackland.Entry("one\n", ("a.txt",)), stackland.Entry("two\n", ("a.txt",))]
    stack = stackland.build(root, entries, ck.run_git_in, _head(root))
    assert stack.failed is None
    assert len(stack.commits) == _TWO


def test_an_admitted_entry_after_another_that_made_the_change_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The parent tree advances with the chain: the second entry is empty against the first."""
    root = _repo(tmp_path, monkeypatch)
    entries = [
        stackland.Entry(f"one\n\nAdmission: {_ROW}\n", ("a.txt",)),
        stackland.Entry(f"two\n\nAdmission: {_ROW_TWO}\n", ("a.txt",)),
    ]
    stack = stackland.build(root, entries, ck.run_git_in, _head(root))
    assert len(stack.commits) == 1
    assert stack.failed is not None
    assert "changes nothing" in stack.failed.stderr


def test_an_admitted_entry_naming_a_queue_file_and_an_unchanged_file_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One non-queue path with no change is enough: a queue file beside it does not excuse it."""
    root = _repo(tmp_path, monkeypatch)
    queue = root / ".claude" / "paths-forward.json"
    queue.parent.mkdir()
    queue.write_text("{}\n", encoding="utf-8")
    _git(root, "add", ".claude", "a.txt")
    head = _landed(root, "queue and a")
    paths = (".claude/paths-forward.json", "a.txt")
    entries = [stackland.Entry(f"use\n\nAdmission: {_ROW}\n", paths)]
    stack = stackland.build(root, entries, ck.run_git_in, head)
    assert stack.commits == []
    assert stack.failed is not None
    assert "changes nothing" in stack.failed.stderr


@pytest.mark.parametrize(
    "history",
    [
        f"Admission: {_ROW}-longer",
        f"Admission: {_ROW} trailing words",
        f"leading words Admission: {_ROW}",
        f"admission: {_ROW}",
    ],
)
def test_a_row_is_spent_only_by_its_exact_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, history: str
) -> None:
    """A longer row, trailing or leading text and another case do not spend this row."""
    root = _repo(tmp_path, monkeypatch)
    head = _landed(root, f"history\n\n{history}")
    entries = [stackland.Entry(f"use\n\nAdmission: {_ROW}\n", ("a.txt",))]
    assert stackland.build(root, entries, ck.run_git_in, head).failed is None


def test_a_row_with_a_metacharacter_is_matched_literally(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The dot in `r/1.2` is a dot: a history row `r/1x2` does not spend it."""
    root = _repo(tmp_path, monkeypatch)
    head = _landed(root, "history\n\nAdmission: r/1x2")
    entries = [stackland.Entry("use\n\nAdmission: r/1.2\n", ("a.txt",))]
    assert stackland.build(root, entries, ck.run_git_in, head).failed is None


def test_a_row_spent_only_on_an_unreachable_branch_is_not_spent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """History is what is reachable from head: a commit on another branch spends nothing."""
    root = _repo(tmp_path, monkeypatch)
    base = _head(root)
    _git(root, "checkout", "--quiet", "-b", "other")
    _landed(root, f"elsewhere\n\nAdmission: {_ROW}")
    _git(root, "checkout", "--quiet", "--detach", base)
    entries = [stackland.Entry(f"use\n\nAdmission: {_ROW}\n", ("a.txt",))]
    assert stackland.build(root, entries, ck.run_git_in, base).failed is None


def test_any_spent_row_of_several_in_one_message_refuses_the_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every row is checked, not only the first."""
    root = _repo(tmp_path, monkeypatch)
    head = _landed(root, f"history\n\nAdmission: {_ROW_TWO}")
    message = f"use\n\nAdmission: {_ROW}\nAdmission: {_ROW_TWO}\n"
    stack = stackland.build(root, [stackland.Entry(message, ("a.txt",))], ck.run_git_in, head)
    assert stack.commits == []
    assert stack.failed is not None
    assert _ROW_TWO in stack.failed.stderr


def test_the_admissions_of_a_message_are_its_exact_lines_only() -> None:
    """A trailing word, a leading word or a bare label names no row."""
    text = "a\nAdmission: r/1\nAdmission: r/1 x\n x Admission: r/2\nAdmission: r/3\nAdmission:\n"
    assert stackland.admissions(text) == ["r/1", "r/3"]


def test_a_shallow_history_is_refused_for_an_admission(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A clone cut off at depth 1 cannot show whether the row was spent, so it is refused."""
    root = _repo(tmp_path, monkeypatch)
    _landed(root, "second commit")
    clone = tmp_path / "clone"
    code, out = scratch.git_out(
        ["git", "clone", "--quiet", "--depth", "1", f"file://{root}", str(clone)]
    )
    assert code == 0, out
    entries = [stackland.Entry(f"use\n\nAdmission: {_ROW}\n", ("a.txt",))]
    stack = stackland.build(clone, entries, ck.run_git_in, _head(clone))
    assert stack.commits == []
    assert stack.failed is not None
    assert "shallow or unreadable" in stack.failed.stderr


def _failing_shallow_probe(
    argv: Sequence[str], env: Mapping[str, str], cwd: Path
) -> runproc.Result:
    """Run real git except the shallow-repository probe, which fails.

    Returns:
        git's answer, or a failed one for the probe.

    """
    if "--is-shallow-repository" in argv:
        # ⚑ THE FAILED PROBE STILL PRINTS "false": only its exit status says it failed, so the
        # status check is what this test witnesses.
        return runproc.Result(128, "false\n", "fatal: broken")
    return ck.run_git_in(argv, env, cwd)


def test_a_failed_shallow_probe_is_refused_for_an_admission(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Whether the history is complete is unknown when the probe fails: the row is refused."""
    root = _repo(tmp_path, monkeypatch)
    entries = [stackland.Entry(f"use\n\nAdmission: {_ROW}\n", ("a.txt",))]
    stack = stackland.build(root, entries, _failing_shallow_probe, _head(root))
    assert stack.commits == []
    assert stack.failed is not None
    assert "shallow or unreadable" in stack.failed.stderr


def test_a_plain_stack_in_a_shallow_clone_still_lands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only an admission needs the whole history: an ordinary entry builds in a shallow clone."""
    root = _repo(tmp_path, monkeypatch)
    _landed(root, "second commit")
    clone = tmp_path / "clone"
    code, out = scratch.git_out(
        ["git", "clone", "--quiet", "--depth", "1", f"file://{root}", str(clone)]
    )
    assert code == 0, out
    (clone / "a.txt").write_text("changed in the clone\n", encoding="utf-8")
    entries = [stackland.Entry("plain\n", ("a.txt",))]
    stack = stackland.build(clone, entries, ck.run_git_in, _head(clone))
    assert stack.failed is None
    assert len(stack.commits) == 1


def test_an_admitted_replay_with_a_changed_queue_file_is_still_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """github-14's block 2: a changed queue file does not make an unchanged a.txt look new."""
    root = _repo(tmp_path, monkeypatch)
    queue = root / ".claude" / "paths-forward.json"
    queue.parent.mkdir()
    queue.write_text("{}\n", encoding="utf-8")
    _git(root, "add", ".claude")
    base = _landed(root, "queue state")
    first = stackland.build(root, [stackland.Entry("one\n", ("a.txt",))], ck.run_git_in, base)
    queue.write_text('{"changed": true}\n', encoding="utf-8")
    paths = (".claude/paths-forward.json", "a.txt")
    replay = [stackland.Entry(f"two\n\nAdmission: {_ROW}\n", paths)]
    again = stackland.build(root, replay, ck.run_git_in, first.commits[0])
    assert again.commits == []
    assert again.failed is not None
    assert "changes nothing" in again.failed.stderr


def test_an_admitted_entry_that_cannot_be_compared_with_its_parent_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed comparison is not an empty one: the entry is not admitted."""

    def failing_diff(argv: Sequence[str], env: Mapping[str, str], cwd: Path) -> runproc.Result:
        if argv and argv[0] == "diff-tree":
            return runproc.Result(128, "", "fatal: broken")
        return ck.run_git_in(argv, env, cwd)

    root = _repo(tmp_path, monkeypatch)
    entries = [stackland.Entry(f"use\n\nAdmission: {_ROW}\n", ("a.txt",))]
    stack = stackland.build(root, entries, failing_diff, _head(root))
    assert stack.commits == []
    assert stack.failed is not None
    assert "could not be compared" in stack.failed.stderr


def test_a_history_that_cannot_be_read_is_refused_for_an_admission(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed `git log` is not an empty answer: the row is refused, never admitted."""
    root = _repo(tmp_path, monkeypatch)
    entries = [stackland.Entry(f"use\n\nAdmission: {_ROW}\n", ("a.txt",))]
    stack = stackland.build(root, entries, _failing_log, _head(root))
    assert stack.commits == []
    assert stack.failed is not None
    assert "could not be read" in stack.failed.stderr


def test_a_queue_only_entry_with_no_change_still_lands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A queue-only entry freezes no paths and may always be empty: it is never refused for it."""
    root = _repo(tmp_path, monkeypatch)
    queue = root / ".claude" / "paths-forward.json"
    queue.parent.mkdir()
    queue.write_text("{}\n", encoding="utf-8")
    _git(root, "add", ".claude")
    head = _landed(root, "queue state")
    message = f"queue only\n\nAdmission: {_ROW}\n"
    entries = [stackland.Entry(message, (".claude/paths-forward.json",))]
    stack = stackland.build(root, entries, ck.run_git_in, head)
    assert stack.failed is None
    assert len(stack.commits) == 1
