# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that one hook run judges a whole stack's tip, in a worktree equal to the index.

W1161. ⚑ THE HOOK IS THE MEASUREMENT: it counts its own runs into the real checkout, fails unless
the worktree equals the index (`git diff --quiet`), and fails unless every stacked edit is present
and a peer's unstaged edit is absent. A tip that was gated in the wrong tree, or twice, shows in
the file it writes or in its exit status; nothing is read from the module's own return.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import threading
from typing import TYPE_CHECKING

from mikemol.hooks import commit_kata as ck
from mikemol.hooks import stackgate, stackland

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

    import pytest

    from mikemol.hooks.isolated import Done

_EXECUTABLE = 0o755
_HOOK = (
    "#!/bin/sh\n"
    'echo run >> "$MIKEMOL_REAL_ROOT/runs"\n'
    "git diff --quiet || exit 1\n"
    '[ "$(cat a.txt)" = "edited a" ] || exit 1\n'
    '[ "$(cat b.txt)" = "edited b" ] || exit 1\n'
    '[ "$(cat c.txt)" = "original" ] || exit 1\n'
)
_REFUSING = "#!/bin/sh\necho refused >&2\nexit 1\n"
# The FIRST hook run blocks until released and then writes what its index differs from HEAD by;
# any later run (the second gate) passes at once. Order is by FIFOs and an event, never a clock.
_BLOCKING = (
    "#!/bin/sh\n"
    '[ -e "$WITNESS/first" ] && exit 0\n'
    'touch "$WITNESS/first"\n'
    'echo go > "$WITNESS/started"\n'
    'read -r go < "$WITNESS/release"\n'
    'git diff --cached --name-only > "$WITNESS/seen"\n'
)


def _git(root: Path, *args: str) -> str:
    """Run the real git and fail loudly.

    Returns:
        git's stdout.

    """
    git = shutil.which("git")
    assert git is not None
    done = subprocess.run([git, "-C", str(root), *args], check=True, capture_output=True, text=True)
    return done.stdout


def _repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hook: str) -> Path:
    """Build a repository with a, b, c, the given pre-commit, and edits to all three.

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
    path = root / ".git" / "hooks" / "pre-commit"
    path.write_text(hook, encoding="utf-8")
    path.chmod(_EXECUTABLE)
    (root / "a.txt").write_text("edited a\n", encoding="utf-8")
    (root / "b.txt").write_text("edited b\n", encoding="utf-8")
    (root / "c.txt").write_text("a peer's unstaged edit\n", encoding="utf-8")
    return root


def _tip(root: Path) -> str:
    """Build a two-entry stack and return its tip tree.

    Returns:
        the tree of the last commit.

    """
    head = _git(root, "rev-parse", "HEAD").strip()
    entries = [stackland.Entry("one\n", ("a.txt",)), stackland.Entry("two\n", ("b.txt",))]
    stack = stackland.build(root, entries, ck.run_git_in, head)
    assert stack.failed is None
    return stack.trees[-1]


def test_one_hook_run_sees_the_whole_tip_in_a_worktree_equal_to_the_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Both stacked edits present, the peer's absent, the index equal, exactly one run."""
    root = _repo(tmp_path, monkeypatch, _HOOK)
    done = stackgate.gate_tip(root, _tip(root), ck.run_git_in, tmp_path / "gate")
    assert done.returncode == 0, done.stderr
    assert (root / "runs").read_text(encoding="utf-8") == "run\n"


def test_a_refusing_hook_is_returned_as_the_gate_verdict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The control: the same call with a hook that refuses returns its status and its output."""
    root = _repo(tmp_path, monkeypatch, _REFUSING)
    done = stackgate.gate_tip(root, _tip(root), ck.run_git_in, tmp_path / "gate")
    assert done.returncode != 0
    assert "refused" in done.stderr


def test_a_second_gate_in_the_same_repository_cannot_replace_the_first_gates_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """luthen-observability:W1653, forced: gate A's hook is held; gate B reads ITS tree; A resumes.

    A judges the two-entry tip (a.txt and b.txt differ from HEAD); B judges HEAD's own tree
    (nothing differs). With one shared index file, B's read-tree replaces A's and A's hook lists
    nothing, which is the `unattributed` refusal on a tree that passes alone.
    """
    root = _repo(tmp_path, monkeypatch, _BLOCKING)
    witness = tmp_path / "witness"
    witness.mkdir()
    os.mkfifo(witness / "started")
    os.mkfifo(witness / "release")
    monkeypatch.setenv("WITNESS", str(witness))
    tip, head_tree = _tip(root), _git(root, "rev-parse", "HEAD^{tree}").strip()
    reached = threading.Event()

    def second(args: Sequence[str], env: Mapping[str, str], cwd: Path) -> Done:
        done = ck.run_git_in(args, env, cwd)
        if args[0] == "read-tree":
            reached.set()
        return done

    gate_a = threading.Thread(
        target=stackgate.gate_tip, args=(root, tip, ck.run_git_in, tmp_path / "gate")
    )
    gate_a.start()
    (witness / "started").read_text(encoding="utf-8")
    gate_b = threading.Thread(
        target=stackgate.gate_tip, args=(root, head_tree, second, tmp_path / "gate")
    )
    gate_b.start()
    reached.wait()
    (witness / "release").write_text("go\n", encoding="utf-8")
    gate_a.join()
    gate_b.join()
    assert (witness / "seen").read_text(encoding="utf-8").split() == ["a.txt", "b.txt"]
