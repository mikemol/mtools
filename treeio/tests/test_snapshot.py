# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `snapshot`: the stash commit, the untracked copies, the journal and the notice."""

from __future__ import annotations

import contextvars
import os
from typing import TYPE_CHECKING

from mikemol.treeio.context import SNAPSHOT_STATE, SnapshotState
from mikemol.treeio.gitrun import git
from mikemol.treeio.layout import Layout
from mikemol.treeio.snapshot import announce, copy_untracked, record, snapshot

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    import pytest

_SHA_LEN = 40
_SHORT = 12
_MANY = 7


def _fresh[T](fn: Callable[[], T]) -> T:
    """Run `fn` as its own invocation, so the snapshot record never leaks between tests.

    Returns:
        Whatever `fn` returns.

    """
    return contextvars.copy_context().run(fn)


def _isolate(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    """Give git a fixed identity, no inherited repository, and a ceiling at the temp root."""
    for name in [n for n in os.environ if n.startswith("GIT_")]:
        monkeypatch.delenv(name)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(root.parent))
    for who in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{who}_NAME", "t")
        monkeypatch.setenv(f"GIT_{who}_EMAIL", "t@t")


def _repo(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Make `root` a repository whose one commit holds a.txt."""
    _isolate(monkeypatch, root)
    git(root, "init", "-q")
    (root / "a.txt").write_text("one", encoding="utf-8")
    git(root, "add", "a.txt")
    git(root, "commit", "-qm", "c")


def test_a_snapshot_is_a_real_commit_pinned_by_a_ref_that_leaves_the_worktree_alone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The sha resolves to a commit, a ref keeps it alive, and nothing is staged or reverted."""
    _repo(tmp_path, monkeypatch)
    (tmp_path / "a.txt").write_text("two", encoding="utf-8")
    before = git(tmp_path, "status", "--porcelain", "--untracked-files=no").stdout
    sha = _fresh(lambda: snapshot("tool target", ["a.txt"], tmp_path))
    assert sha is not None
    assert len(sha) == _SHA_LEN
    assert git(tmp_path, "cat-file", "-t", sha).stdout.strip() == "commit"
    assert (
        git(tmp_path, "rev-parse", "--verify", f"refs/edit-snapshots/{sha[:_SHORT]}").stdout.strip()
        == sha
    )
    assert git(tmp_path, "status", "--porcelain", "--untracked-files=no").stdout == before
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "two"


def test_a_dirty_worktree_snapshots_to_a_stash_commit_and_a_clean_one_to_head(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With changes the sha is a new commit holding them; with none it is HEAD."""
    _repo(tmp_path, monkeypatch)
    head = git(tmp_path, "rev-parse", "HEAD").stdout.strip()
    clean = _fresh(lambda: snapshot("clean", [], tmp_path))
    (tmp_path / "a.txt").write_text("two", encoding="utf-8")
    dirty = _fresh(lambda: snapshot("dirty", [], tmp_path))
    assert clean == head
    assert dirty is not None
    assert dirty != head
    assert git(tmp_path, "show", f"{dirty}:a.txt").stdout == "two"


def test_there_is_no_snapshot_outside_a_repository_or_before_the_first_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing net returns None and never raises, and records nothing in the journal."""
    _isolate(monkeypatch, tmp_path)
    assert _fresh(lambda: snapshot("nowhere", ["a.txt"], tmp_path)) is None
    git(tmp_path, "init", "-q")
    assert _fresh(lambda: snapshot("unborn", [], tmp_path)) is None
    assert not (tmp_path / "scratch" / "edit_snapshot.journal.tsv").exists()


def test_the_journal_gets_a_header_once_and_a_row_per_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each row is sha, label, path count and paths; the three-line header is written only once."""
    _repo(tmp_path, monkeypatch)
    first = _fresh(lambda: snapshot("one", ["a.txt", "b/c.txt"], tmp_path))
    second = _fresh(lambda: snapshot("two", [], tmp_path))
    lines = (
        (tmp_path / "scratch" / "edit_snapshot.journal.tsv")
        .read_text(encoding="utf-8")
        .splitlines()
    )
    assert lines[:3] == [
        "# sha\tlabel\tn_paths\tpaths",
        "# restore:  git checkout <sha> -- <path>...",
        "# list:     git show --stat <sha>",
    ]
    assert lines[3:] == [f"{first}\tone\t2\ta.txt,b/c.txt", f"{second}\ttwo\t0\t"]


def test_a_snapshot_survives_a_journal_it_cannot_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Best-effort by construction: a file where the scratch directory belongs breaks nothing."""
    _repo(tmp_path, monkeypatch)
    (tmp_path / "scratch").write_text("in the way", encoding="utf-8")
    assert _fresh(lambda: snapshot("blocked", ["a.txt"], tmp_path)) is not None


def test_record_writes_relative_paths_and_caps_the_row_at_forty(tmp_path: Path) -> None:
    """Absolute paths are journaled relative to the root, and only forty of them."""
    here = Layout(tmp_path)
    (tmp_path / "scratch").mkdir()
    paths = [tmp_path / f"f{n}.txt" for n in range(50)]
    record(here, "abc", "lab", paths)
    row = here.journal.read_text(encoding="utf-8").splitlines()[-1]
    sha, label, count, listed = row.split("\t")
    assert (sha, label, count) == ("abc", "lab", "50")
    assert listed.split(",") == [f"f{n}.txt" for n in range(40)]


def test_untracked_files_are_copied_aside_and_named_in_the_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Git cannot hold them, so the copy is the recovery point, and the report says where it is."""
    _repo(tmp_path, monkeypatch)
    (tmp_path / "tool.py").write_text("print(1)", encoding="utf-8")
    sha = _fresh(lambda: snapshot("t", ["tool.py", "a.txt", "missing.py"], tmp_path))
    assert sha is not None
    assert (tmp_path / "scratch" / ".edit-snapshots" / "tool.py").read_text(
        encoding="utf-8"
    ) == "print(1)"
    assert not (tmp_path / "scratch" / ".edit-snapshots" / "a.txt").exists()
    assert capsys.readouterr().out == (
        "  ⚑ 1 UNTRACKED file(s) copied to scratch/.edit-snapshots/ (git cannot hold them):\n"
        "      cp scratch/.edit-snapshots/tool.py tool.py\n"
    )


def test_many_untracked_files_are_summarized_after_five(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The report names the first five copies and counts the rest."""
    _repo(tmp_path, monkeypatch)
    names = [f"t{n}.py" for n in range(_MANY)]
    for name in names:
        (tmp_path / name).write_text(name, encoding="utf-8")
    _fresh(lambda: snapshot("t", names, tmp_path))
    out = capsys.readouterr().out.splitlines()
    assert out[0].startswith(f"  ⚑ {_MANY} UNTRACKED file(s) copied")
    assert [ln for ln in out if ln.startswith("      cp ")] == [
        f"      cp scratch/.edit-snapshots/{n} {n}" for n in names[:5]
    ]
    assert out[-1] == "      … and 2 more (see --list)"


def test_copy_untracked_accepts_absolute_paths_and_skips_tracked_and_missing_ones(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only a file that exists and git does not track is copied."""
    _repo(tmp_path, monkeypatch)
    (tmp_path / "d").mkdir()
    (tmp_path / "d" / "new.py").write_text("n", encoding="utf-8")
    here = Layout(tmp_path)
    saved = _fresh(
        lambda: copy_untracked(here, [tmp_path / "d" / "new.py", "a.txt", "gone.py", "d"])
    )
    assert saved == [("d/new.py", tmp_path / "scratch" / ".edit-snapshots" / "d" / "new.py")]


def test_an_already_copied_file_is_not_overwritten_by_its_damaged_successor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The pre-write copy is the recovery point, so a second call must not replace it."""
    _repo(tmp_path, monkeypatch)
    (tmp_path / "tool.py").write_text("good", encoding="utf-8")
    here = Layout(tmp_path)

    def twice() -> tuple[list[str], list[str], set[str]]:
        SNAPSHOT_STATE.set(SnapshotState(sha=None, label="t"))
        first = [rel for rel, _ in copy_untracked(here, ["tool.py"])]
        (tmp_path / "tool.py").write_text("DAMAGED", encoding="utf-8")
        second = [rel for rel, _ in copy_untracked(here, ["tool.py"])]
        state = SNAPSHOT_STATE.get()
        assert state is not None
        return first, second, state.copied

    assert _fresh(twice) == (["tool.py"], [], {"tool.py"})
    assert (tmp_path / "scratch" / ".edit-snapshots" / "tool.py").read_text(
        encoding="utf-8"
    ) == "good"


def test_the_copied_set_accumulates_across_calls_so_later_files_are_still_copied(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A latch would copy file one and skip the rest; the record skips only what it saved."""
    _repo(tmp_path, monkeypatch)
    for name in ("a.py", "b.py"):
        (tmp_path / name).write_text(name, encoding="utf-8")
    here = Layout(tmp_path)

    def both() -> set[str]:
        SNAPSHOT_STATE.set(SnapshotState(sha=None, label="t"))
        copy_untracked(here, ["a.py"])
        copy_untracked(here, ["b.py"])
        state = SNAPSHOT_STATE.get()
        assert state is not None
        return state.copied

    assert _fresh(both) == {"a.py", "b.py"}


def test_a_copy_that_fails_is_skipped_without_stopping_the_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Best-effort: when the store cannot be created nothing is reported and nothing is raised."""
    _repo(tmp_path, monkeypatch)
    (tmp_path / "tool.py").write_text("t", encoding="utf-8")
    (tmp_path / "scratch").write_text("in the way", encoding="utf-8")
    assert _fresh(lambda: copy_untracked(Layout(tmp_path), ["tool.py"])) == []


def test_snapshot_establishes_the_per_invocation_record_when_none_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A direct caller still gets a record, labelled by its first snapshot, and keeps its own."""
    _repo(tmp_path, monkeypatch)

    def direct() -> tuple[str | None, str | None, str | None]:
        before = SNAPSHOT_STATE.get()
        snapshot("first", [], tmp_path)
        snapshot("second", [], tmp_path)
        state = SNAPSHOT_STATE.get()
        assert before is None
        assert state is not None
        return state.label, state.sha, None

    assert _fresh(direct) == ("first", None, None)


def test_announce_says_how_to_recover_or_that_there_is_no_snapshot() -> None:
    """The notice names the short sha and the checkout, or warns that edits are unrecoverable."""
    heard: list[str] = []
    announce("0123456789abcdef", "tool target", heard.append)
    announce(None, "tool target", heard.append)
    assert heard == [
        "snapshot 0123456789ab [tool target] — recover any file with:",
        "    git checkout 0123456789ab -- <path>",
        "⚠ tool target: NO SNAPSHOT (not a git worktree?) — edits are unrecoverable",
    ]


def test_announce_writes_to_stdout_by_default(capsys: pytest.CaptureFixture[str]) -> None:
    """With no sink given the notice goes to stdout, one line each."""
    announce("0123456789abcdef", "t")
    assert capsys.readouterr().out == (
        "snapshot 0123456789ab [t] — recover any file with:\n"
        "    git checkout 0123456789ab -- <path>\n"
    )
