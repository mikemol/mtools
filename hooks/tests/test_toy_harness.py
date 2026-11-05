# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A lone one-file stack lands in a toy repository through the real stack command (W2276).

⚑ THE FIRST WITNESS OF THE TOY HARNESS (W2254, W2207): a disposable repository, the REAL
`commit_kata.main` run on `--stack`, and the result read back from git. Everything the dependent
stack witnesses (W2208, W2209) will need rests on this one thing working, so it comes first.

⚑ WHAT A REPOSITORY MUST BE FOR A STACK TO LAND, MEASURED BY PROBE (2026-11-05) AND NOT GUESSED:
a stack needs the ISOLATED commit path, that path is chosen only when the TRACKED
`.githooks/pre-commit` names `MIKEMOL_REAL_ROOT` (`commit_kata.supports_isolation`), and the pace
file must name nothing (a missing file reads as no pace). The control below holds the second: the
same stack against a hook that does not name it is refused, and nothing is committed.

⚑ THE FENCE IS A STAND-IN WITH THE SAME CONTRACT, as in test_commit_lease_wait: the real one is a
console script of another distribution and is not in this one's sandbox.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import textwrap
from typing import TYPE_CHECKING

import pytest

from mikemol.hooks import runproc

if TYPE_CHECKING:
    from pathlib import Path

_STAND_IN = textwrap.dedent(
    """\
    import fcntl
    import os
    import sys

    command = sys.argv[5:]
    fd = os.open(os.environ["STAND_IN_LOCK"], os.O_CREAT | os.O_RDWR)
    fcntl.flock(fd, fcntl.LOCK_EX)
    os.set_inheritable(fd, True)
    os.execvp(command[0], command)
    """
)
# ⚑ THE CHILD IMPORTS A MODULE THIS TEST DOES NOT, so under bazel it needs the whole distribution
# staged: hooks/BUILD.bazel lists this test in `_WHOLE_DIST_TESTS`, as it does
# test_commit_lease_wait (MEASURED: the gate's first run died on `cannot import name
# 'commit_kata'`). Importing the module here would stage it too, but would also put this test in
# the mutation sites of every module in its closure.
_RUNNER = "from mikemol.hooks import commit_kata\nraise SystemExit(commit_kata.main())\n"
_NAMING_HOOK = '#!/bin/sh\n# names MIKEMOL_REAL_ROOT\n: "${MIKEMOL_REAL_ROOT:-}"\nexit 0\n'
_PLAIN_HOOK = "#!/bin/sh\nexit 0\n"
_EXECUTABLE = 0o755
_SUBJECT = "W1 toy: a lone one-file stack"
_IDENTITY = {
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.invalid",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.invalid",
    "GIT_CONFIG_NOSYSTEM": "1",
}
_TIMEOUT_S = 120


def _git(repo: Path, env: dict[str, str], *args: str) -> str:
    git = shutil.which("git")
    if git is None:
        pytest.skip("git is not installed")
    done = runproc.run([git, "-C", str(repo), *args], env=env)
    assert done.returncode == 0, done.stderr
    return done.stdout


def _environment(tmp_path: Path) -> dict[str, str]:
    """Build the process environment the stack command runs in.

    Returns:
        an environment with no inherited GIT_ or MIKEMOL_ variable, a stand-in fence, a snapshot
        root and a pace file that does not exist.

    """
    prefixes = ("GIT_", "MIKEMOL_", "MEMBUDGET")
    base = {k: v for k, v in os.environ.items() if not k.startswith(prefixes)}
    stand_in = tmp_path / "stand-in-fence.py"
    stand_in.write_text(_STAND_IN, encoding="utf-8")
    launcher = tmp_path / "fence"
    launcher.write_text(f'#!/bin/sh\nexec {sys.executable} {stand_in} "$@"\n', encoding="utf-8")
    launcher.chmod(_EXECUTABLE)
    return {
        **base,
        **_IDENTITY,
        "HOME": str(tmp_path),
        "GIT_CEILING_DIRECTORIES": str(tmp_path),
        "PYTHONPATH": os.pathsep.join(sys.path),
        "MIKEMOL_FENCE_BIN": str(launcher),
        "MIKEMOL_SNAPSHOT_ROOT": str(tmp_path / "snap"),
        "MIKEMOL_PACE_FILE": str(tmp_path / "no-pace.json"),
        "STAND_IN_LOCK": str(tmp_path / "claim.lock"),
    }


def _repo(tmp_path: Path, env: dict[str, str], hook: str) -> Path:
    """Build a repository holding `a.txt`, a tracked gate hook, and an uncommitted edit.

    Returns:
        the repository's root.

    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, env, "init", "--quiet", "-b", "main")
    _git(repo, env, "config", "core.hooksPath", ".githooks")
    (repo / "a.txt").write_text("one\n", encoding="utf-8")
    gate = repo / ".githooks" / "pre-commit"
    gate.parent.mkdir()
    gate.write_text(hook, encoding="utf-8")
    gate.chmod(_EXECUTABLE)
    _git(repo, env, "add", "a.txt", ".githooks/pre-commit")
    _git(repo, env, "commit", "--quiet", "-m", "first")
    (repo / "a.txt").write_text("two\n", encoding="utf-8")
    return repo


def _stack(tmp_path: Path) -> Path:
    """Write a stack file holding one entry that takes `a.txt`.

    Returns:
        the stack file.

    """
    entries: list[dict[str, object]] = [{"waypoint": "W1", "subject": _SUBJECT, "paths": ["a.txt"]}]
    stack = tmp_path / "stack.json"
    stack.write_text(json.dumps(entries), encoding="utf-8")
    return stack


def _submit(tmp_path: Path, hook: str) -> tuple[Path, dict[str, str], runproc.Result]:
    """Run the stack command against a toy repository gated by `hook`.

    Returns:
        the repository, the environment it ran in, and what the command exited with and printed.

    """
    env = _environment(tmp_path)
    repo = _repo(tmp_path, env, hook)
    runner = tmp_path / "run_commit.py"
    runner.write_text(_RUNNER, encoding="utf-8")
    argv = [sys.executable, str(runner), str(repo), "--stack", str(_stack(tmp_path))]
    return repo, env, runproc.run(argv, cwd=repo, env=env, timeout=_TIMEOUT_S)


def test_a_lone_one_file_stack_lands_through_the_isolated_path(tmp_path: Path) -> None:
    """The real stack command commits the one file with the entry's subject and says it did."""
    repo, env, done = _submit(tmp_path, _NAMING_HOOK)
    said = done.stdout + done.stderr
    assert done.returncode == 0, said
    assert "path: isolated" in said
    head = _git(repo, env, "rev-parse", "--short", "HEAD").strip()
    assert f"COMMITTED repo {head}" in done.stdout
    assert _git(repo, env, "log", "-1", "--format=%s").strip() == _SUBJECT
    assert _git(repo, env, "show", "HEAD:a.txt") == "two\n"


def test_a_hook_that_does_not_name_the_real_root_refuses_the_stack_and_commits_nothing(
    tmp_path: Path,
) -> None:
    """The control: without MIKEMOL_REAL_ROOT in the tracked hook there is no isolated path."""
    repo, env, done = _submit(tmp_path, _PLAIN_HOOK)
    assert done.returncode != 0
    assert "a stack needs the isolated commit path" in done.stdout + done.stderr
    assert _git(repo, env, "log", "-1", "--format=%s").strip() == "first"


def _held_hook(tmp_path: Path) -> tuple[str, Path, Path]:
    """Build a gate hook that reports it is running, then waits to be released.

    ⚑ NAMED PIPES, NOT A POLL AND NOT A TIMER: the hook writes `held` once its gate is running and
    then blocks reading `release`, so the test blocks on the child's own progress in both
    directions. A child that never reaches the hook leaves the read open until the test runner's
    own limit ends it.

    Returns:
        the hook text, the pipe it announces on and the pipe it waits on.

    """
    held, release = tmp_path / "held", tmp_path / "release"
    os.mkfifo(held)
    os.mkfifo(release)
    hook = (
        '#!/bin/sh\n: "${MIKEMOL_REAL_ROOT:-}"\n'
        f"echo held > '{held}'\nread _go < '{release}'\nexit 0\n"
    )
    return hook, held, release


def test_a_stack_sharing_a_file_with_a_held_stack_is_refused_unless_built_on_its_bytes(
    tmp_path: Path,
) -> None:
    """W2209 witness b: a stack built on HEAD's copy of a file a stack ahead froze is refused."""
    hook, held, release = _held_hook(tmp_path)
    env = _environment(tmp_path)
    repo = _repo(tmp_path, env, _NAMING_HOOK)
    gate = repo / ".githooks" / "pre-commit"
    gate.write_text(hook, encoding="utf-8")
    _git(repo, env, "add", ".githooks/pre-commit")
    _git(repo, env, "commit", "--quiet", "--no-verify", "-m", "hold the gate")
    runner = tmp_path / "run_commit.py"
    runner.write_text(_RUNNER, encoding="utf-8")
    first = runproc.start(
        [sys.executable, str(runner), str(repo), "--stack", str(_stack(tmp_path))],
        cwd=repo,
        env=env,
    )
    assert held.read_text(encoding="utf-8") == "held\n"
    (repo / "a.txt").write_text("three\n", encoding="utf-8")
    entries: list[dict[str, object]] = [
        {"waypoint": "W2", "subject": "W2 toy: built on HEAD", "paths": ["a.txt"]}
    ]
    other = tmp_path / "stack2.json"
    other.write_text(json.dumps(entries), encoding="utf-8")
    second = runproc.run(
        [sys.executable, str(runner), str(repo), "--stack", str(other)],
        cwd=repo,
        env=env,
        timeout=_TIMEOUT_S,
    )
    release.write_text("go\n", encoding="utf-8")
    done = first.wait(timeout=_TIMEOUT_S)
    said = second.stdout + second.stderr
    assert second.returncode != 0, said
    assert "shares 1 file(s) with a stack ahead" in said
    assert "a.txt" in said
    assert done.returncode == 0, done.stdout + done.stderr
    assert _git(repo, env, "show", "HEAD:a.txt") == "two\n"
    assert _git(repo, env, "log", "-1", "--format=%s").strip() == _SUBJECT


def test_a_stack_submitted_from_a_linked_worktree_is_refused_and_commits_nothing(
    tmp_path: Path,
) -> None:
    """W2209 witness c: an undeclared worktree submit would take a queue and lease beside main's."""
    env = _environment(tmp_path)
    repo = _repo(tmp_path, env, _NAMING_HOOK)
    linked = tmp_path / "linked"
    _git(repo, env, "worktree", "add", "--quiet", "-b", "linked", str(linked))
    runner = tmp_path / "run_commit.py"
    runner.write_text(_RUNNER, encoding="utf-8")
    argv = [sys.executable, str(runner), str(linked), "--stack", str(_stack(tmp_path))]
    done = runproc.run(argv, cwd=linked, env=env, timeout=_TIMEOUT_S)
    said = done.stdout + done.stderr
    assert done.returncode != 0, said
    assert "an undeclared worktree submit" in said
    assert "mtools:W2103" in said
    assert _git(repo, env, "log", "-1", "--format=%s").strip() == "first"
