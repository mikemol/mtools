# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol-commit` in isolated mode, on a decoy repository (W902, W903).

⚑ THE FIRST ARM IS THE POSITIVE CONTROL: a plain edit commits through the private index and
snapshot, HEAD moves, and the verdict line says so. The rest ask what isolation is for: a peer's
unstaged file is neither committed nor in the way, the real index reads the committed paths as
committed (no staged reversal), a staged deletion lands as a deletion, and a new file is taken.

Every GIT_* variable is removed first, the identity is fixed, and the snapshot namespace is
tmp_path, so nothing here touches a real repository or /var/tmp/mikemol.
"""

from __future__ import annotations

import io
import os
import shutil
import subprocess
from typing import TYPE_CHECKING

from mikemol.hooks import commit_kata as ck
from mikemol.hooks.snapshot import NAMESPACE_ENV

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_ORIGINAL = "original\n"
_EDITED = "edited by this session\n"
_PEER = "edited by a peer, not staged\n"
_EXECUTABLE = 0o755
_REQUEST = ck.Request(waypoint="W1", subject="isolated subject", paths=("a.txt",))


def _git(root: Path, *args: str) -> str:
    """Run the real git (resolved, not by partial path) and fail loudly.

    Returns:
        git's stdout.

    """
    git = shutil.which("git")
    assert git is not None
    done = subprocess.run([git, "-C", str(root), *args], check=True, capture_output=True, text=True)
    return done.stdout


def _status(root: Path) -> list[str]:
    """Read `git status --porcelain` as lines.

    Returns:
        one line per changed path; empty when the repository is clean.

    """
    return _git(root, "status", "--porcelain").splitlines()


def _decoy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Build a repository with a.txt, b.txt and c.txt committed, in a clean git environment.

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
        NAMESPACE_ENV: str(tmp_path / "gate"),
    }.items():
        monkeypatch.setenv(key, value)
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "--quiet")
    for name in ("a.txt", "b.txt", "c.txt"):
        (root / name).write_text(_ORIGINAL, encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "--quiet", "-m", "first")
    return root


def _isolated(root: Path, request: ck.Request = _REQUEST) -> tuple[int, str]:
    """Commit the request in isolated mode with the real git runner.

    Returns:
        the exit code and the text written to `out`.

    """
    out = io.StringIO()
    code = ck.commit(root, request, out, isolated=True)
    return code, out.getvalue()


def test_an_edit_commits_through_the_private_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The positive control: HEAD moves, holds the edit, and the verdict says COMMITTED."""
    root = _decoy(tmp_path, monkeypatch)
    (root / "a.txt").write_text(_EDITED, encoding="utf-8")
    code, shown = _isolated(root)
    assert code == 0, shown
    assert "COMMITTED repo" in shown.splitlines()[-1]
    assert _git(root, "show", "HEAD:a.txt") == _EDITED


def test_a_peers_unstaged_file_is_neither_committed_nor_in_the_way(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The peer's edit survives in the worktree, out of the commit, still unstaged afterwards."""
    root = _decoy(tmp_path, monkeypatch)
    (root / "a.txt").write_text(_EDITED, encoding="utf-8")
    (root / "b.txt").write_text(_PEER, encoding="utf-8")
    code, shown = _isolated(root)
    assert code == 0, shown
    assert _git(root, "show", "HEAD:b.txt") == _ORIGINAL
    assert (root / "b.txt").read_text(encoding="utf-8") == _PEER
    assert _status(root) == [" M b.txt"]


def test_the_real_index_reads_the_committed_path_as_committed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No staged reversal is left behind: git status is clean for the committed path."""
    root = _decoy(tmp_path, monkeypatch)
    (root / "a.txt").write_text(_EDITED, encoding="utf-8")
    assert _isolated(root)[0] == 0
    assert _status(root) == []
    assert not (root / ".git" / "index.lock").exists()


def test_a_staged_deletion_lands_as_a_deletion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`git rm` then commit the path: HEAD no longer has it, and neither does the worktree."""
    root = _decoy(tmp_path, monkeypatch)
    _git(root, "rm", "--quiet", "c.txt")
    request = ck.Request(waypoint="W1", subject="remove c", paths=("c.txt",))
    code, shown = _isolated(root, request)
    assert code == 0, shown
    assert "c.txt" not in _git(root, "ls-tree", "-r", "--name-only", "HEAD")
    assert _status(root) == []


def test_a_new_file_is_taken_though_git_does_not_track_it_yet(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Nothing is staged in the real index, so existence on disk is what makes a path count."""
    root = _decoy(tmp_path, monkeypatch)
    (root / "new.txt").write_text(_EDITED, encoding="utf-8")
    request = ck.Request(waypoint="W1", subject="add new", paths=("new.txt",))
    code, shown = _isolated(root, request)
    assert code == 0, shown
    assert _git(root, "show", "HEAD:new.txt") == _EDITED


def test_a_peers_staged_file_at_another_path_stays_staged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The peer's `git add b.txt` survives our commit of a.txt: staged, uncommitted, intact."""
    root = _decoy(tmp_path, monkeypatch)
    (root / "a.txt").write_text(_EDITED, encoding="utf-8")
    (root / "b.txt").write_text(_PEER, encoding="utf-8")
    _git(root, "add", "b.txt")
    code, shown = _isolated(root)
    assert code == 0, shown
    assert _git(root, "show", "HEAD:b.txt") == _ORIGINAL
    assert _status(root) == ["M  b.txt"]


def test_a_refused_commit_leaves_head_and_the_real_index_as_they_were(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failing pre-commit hook refuses: HEAD stays, the peer's staged file stays, no lock."""
    root = _decoy(tmp_path, monkeypatch)
    hook = root / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\necho refused by the gate >&2\nexit 1\n", encoding="utf-8")
    hook.chmod(_EXECUTABLE)
    (root / "a.txt").write_text(_EDITED, encoding="utf-8")
    (root / "b.txt").write_text(_PEER, encoding="utf-8")
    _git(root, "add", "b.txt")
    before = _git(root, "rev-parse", "HEAD")
    code, shown = _isolated(root)
    assert code != 0
    assert shown.splitlines()[-1].startswith("REFUSED repo")
    assert _git(root, "rev-parse", "HEAD") == before
    assert _status(root) == [" M a.txt", "M  b.txt"]
    assert not (root / ".git" / "index.lock").exists()


_NEEDS_REAL_TOOL = (
    "#!/bin/sh\n"
    '[ -x "${MIKEMOL_REAL_ROOT:?not set}/.venv/bin/tool" ] || exit 1\n'
    "[ ! -e .venv ] || exit 1\n"
)


def _tool_only_the_real_root_has(root: Path) -> None:
    """Give the repository an untracked host tool and a pre-commit hook that needs it."""
    tool = root / ".venv" / "bin" / "tool"
    tool.parent.mkdir(parents=True)
    tool.write_text("#!/bin/sh\n", encoding="utf-8")
    tool.chmod(_EXECUTABLE)
    hook = root / ".git" / "hooks" / "pre-commit"
    hook.write_text(_NEEDS_REAL_TOOL, encoding="utf-8")
    hook.chmod(_EXECUTABLE)


def test_an_isolated_commit_finds_a_tool_only_the_real_root_has(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """W941: the hook runs in a snapshot with no .venv and reads its tool from MIKEMOL_REAL_ROOT."""
    root = _decoy(tmp_path, monkeypatch)
    _tool_only_the_real_root_has(root)
    (root / "a.txt").write_text(_EDITED, encoding="utf-8")
    code, shown = _isolated(root)
    assert code == 0, shown
    assert _git(root, "show", "HEAD:a.txt") == _EDITED


def test_the_same_hook_refuses_a_normal_commit_which_is_the_control(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without isolation MIKEMOL_REAL_ROOT is unset, so the hook refuses: it does discriminate."""
    root = _decoy(tmp_path, monkeypatch)
    _tool_only_the_real_root_has(root)
    (root / "a.txt").write_text(_EDITED, encoding="utf-8")
    before = _git(root, "rev-parse", "HEAD")
    out = io.StringIO()
    code = ck.commit(root, _REQUEST, out)
    assert code != 0
    assert out.getvalue().splitlines()[-1].startswith("REFUSED repo")
    assert _git(root, "rev-parse", "HEAD") == before


def _hook_text(root: Path, text: str) -> None:
    """Write the repository's pre-commit with the given text."""
    hook = root / ".githooks" / "pre-commit"
    hook.parent.mkdir(exist_ok=True)
    hook.write_text(text, encoding="utf-8")


def test_isolation_is_on_where_the_repos_hook_reads_the_real_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """W904: unset, the pre-commit's own text decides; naming MIKEMOL_REAL_ROOT opts in."""
    root = _decoy(tmp_path, monkeypatch)
    _hook_text(root, 'tools="${MIKEMOL_REAL_ROOT:-$root}"\n')
    assert ck.isolation_wanted(root, {})


def test_isolation_is_off_where_the_hook_does_not_know_the_real_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A peer repository's gate that finds its tools beside the checkout keeps today's mode."""
    root = _decoy(tmp_path, monkeypatch)
    assert not ck.isolation_wanted(root, {})
    _hook_text(root, "#!/bin/sh\nexit 0\n")
    assert not ck.isolation_wanted(root, {})


def test_the_environment_opts_out_and_forces(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """=0 turns isolation off even where supported; =1 turns it on even where it is not."""
    root = _decoy(tmp_path, monkeypatch)
    _hook_text(root, "MIKEMOL_REAL_ROOT\n")
    assert not ck.isolation_wanted(root, {ck.ISOLATED_ENV: "0"})
    _hook_text(root, "#!/bin/sh\n")
    assert ck.isolation_wanted(root, {ck.ISOLATED_ENV: "1"})
    assert not ck.isolation_wanted(root, {ck.ISOLATED_ENV: "yes"})


def test_a_path_that_is_neither_on_disk_nor_tracked_is_not_a_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Nothing to take reads NOT COMMITTED and HEAD does not move."""
    root = _decoy(tmp_path, monkeypatch)
    before = _git(root, "rev-parse", "HEAD")
    request = ck.Request(waypoint="W1", subject="nothing", paths=("ghost.txt",))
    code, shown = _isolated(root, request)
    assert code == ck.EXIT_NOT_COMMITTED
    assert shown.startswith("NOT COMMITTED repo")
    assert _git(root, "rev-parse", "HEAD") == before
