# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The commit claim is keyed on the repository being committed, not on the launcher (W910).

⚑ W886 wrapped `hooks/bin/mikemol-commit` in a fence claim keyed on the LAUNCHER's checkout, so a
commit to paperkit (a gate of minutes) held every mtools commit behind it. The lock now lives where
the repository is resolved, and these arms use a TARGET repository that is not where anything runs
from, a stub fence that records the claim it was asked for, and the real `main`.
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import TYPE_CHECKING

from mikemol.hooks import commit_kata

if TYPE_CHECKING:
    from pathlib import Path

_EXECUTABLE = 0o755
_TIMEOUT_S = 60
_IDENTITY = ("-c", "user.name=t", "-c", "user.email=t@example.invalid")
_QUEUE = ".claude/paths-forward.json"
_FENCE = '#!/bin/sh\necho "CLAIM=$3 $4" >> "$FENCE_LOG"\nshift 4\nexec "$@"\n'


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", *_IDENTITY, *args], cwd=cwd, check=True, capture_output=True, timeout=_TIMEOUT_S
    )


def _repo(parent: Path, name: str) -> Path:
    """Make a repository with one tracked queue file and an uncommitted edit to it.

    Returns:
        the repository.

    """
    repo = parent / name
    (repo / ".claude").mkdir(parents=True)
    _git(parent, "init", "-q", str(repo))
    (repo / _QUEUE).write_text("{}\n", encoding="utf-8")
    _git(repo, "add", _QUEUE)
    _git(repo, "commit", "-q", "-m", "first")
    (repo / _QUEUE).write_text('{"a": 1}\n', encoding="utf-8")
    return repo


def _fence(tmp_path: Path) -> Path:
    path = tmp_path / "fence"
    path.write_text(_FENCE, encoding="utf-8")
    path.chmod(_EXECUTABLE)
    return path


def test_the_claim_names_the_target_repositorys_git_directory(tmp_path: Path) -> None:
    """The hold is on `<target>/.git/mtools/commit`, whatever checkout the launcher lives in."""
    target = _repo(tmp_path, "paperkit")
    fence = _fence(tmp_path)
    got = commit_kata.claim_of(target, {commit_kata.FENCE_ENV: str(fence)}, ["python", "x"])
    assert isinstance(got, commit_kata.Claim)
    gitdir = (target / ".git").resolve()
    assert got.argv[:5] == [str(fence), "hold", "0", f"claim:path:{gitdir}/mtools/commit", "--"]
    assert got.env["MEMBUDGET_FILE"] == f"{gitdir}/mtools/commit.ledger"


def test_two_repositories_get_two_different_claims(tmp_path: Path) -> None:
    """A paperkit gate no longer holds an mtools commit: the claim labels differ."""
    env = {commit_kata.FENCE_ENV: str(_fence(tmp_path))}
    one = commit_kata.claim_of(_repo(tmp_path, "one"), env, ["x"])
    two = commit_kata.claim_of(_repo(tmp_path, "two"), env, ["x"])
    assert isinstance(one, commit_kata.Claim)
    assert isinstance(two, commit_kata.Claim)
    assert one.argv[3] != two.argv[3]


def test_the_load_gate_is_off_and_the_wait_has_no_deadline_whatever_the_caller_sets(
    tmp_path: Path,
) -> None:
    """A busy host must not stall a commit, and the lease wait has no timer, none asked for (W1734).

    ⚑ THE KNOB IS RETIRED: `MIKEMOL_COMMIT_LOCK_TIMEOUT` was a wall-clock bound a caller could set,
    and no caller did. A caller's own `MEMBUDGET_TIMEOUT` does not reach the wait either.
    """
    target = _repo(tmp_path, "r")
    env = {commit_kata.FENCE_ENV: str(_fence(tmp_path))}
    got = commit_kata.claim_of(target, env, ["x"])
    assert isinstance(got, commit_kata.Claim)
    assert got.env["MEMBUDGET_MAXLOAD"] == "0"
    assert "MEMBUDGET_TIMEOUT" not in got.env
    env["MIKEMOL_COMMIT_LOCK_TIMEOUT"] = "90"
    env["MEMBUDGET_TIMEOUT"] = "90"
    again = commit_kata.claim_of(target, env, ["x"])
    assert isinstance(again, commit_kata.Claim)
    assert "MEMBUDGET_TIMEOUT" not in again.env


def test_the_commands_own_budget_variables_are_put_back_or_removed(tmp_path: Path) -> None:
    """Between the hold and the commit, `env` restores what the caller had and removes the rest."""
    target = _repo(tmp_path, "r")
    env = {
        commit_kata.FENCE_ENV: str(_fence(tmp_path)),
        "MEMBUDGET_FILE": "/host/b",
        "MEMBUDGET_MAXLOAD": "7",
    }
    got = commit_kata.claim_of(target, env, ["python", "x"])
    assert isinstance(got, commit_kata.Claim)
    inner = got.argv[got.argv.index("env") :]
    assert "MEMBUDGET_FILE=/host/b" in inner
    assert "MEMBUDGET_MAXLOAD=7" in inner
    assert "-u" in inner
    assert f"{commit_kata.HELD_ENV}=1" in inner
    assert inner[-2:] == ["python", "x"]


def test_a_nested_call_does_not_take_a_second_claim(tmp_path: Path) -> None:
    """With the marker set the claim is already held above: no plan, no note."""
    target = _repo(tmp_path, "r")
    assert not commit_kata.claim_of(target, {commit_kata.HELD_ENV: "1"}, ["x"])


def test_no_fence_or_no_git_checkout_gives_a_reason_not_a_claim(tmp_path: Path) -> None:
    """Both gaps are said, and neither is an exception."""
    target = _repo(tmp_path, "r")
    nowhere = str(tmp_path / "empty" / "python")
    assert "fence venv" in str(commit_kata.claim_of(target, {}, ["x"], python=nowhere))
    plain = tmp_path / "plain"
    plain.mkdir()
    got = commit_kata.claim_of(plain, {commit_kata.FENCE_ENV: str(_fence(tmp_path))}, ["x"])
    assert "not a git checkout" in str(got)


def test_the_guard_launcher_sits_between_the_claim_and_the_commit(tmp_path: Path) -> None:
    """W921: with an interpreter beside the fence, the commit runs under guard_cli."""
    target = _repo(tmp_path, "paperkit")
    fence = _fence(tmp_path)
    interpreter = tmp_path / "python3"
    interpreter.write_text("#!/bin/sh\n", encoding="utf-8")
    interpreter.chmod(_EXECUTABLE)
    got = commit_kata.claim_of(target, {commit_kata.FENCE_ENV: str(fence)}, ["python", "x"])
    assert isinstance(got, commit_kata.Claim)
    layer = [str(interpreter), "-m", "mikemol.fence.guard_cli", "--", "python", "x"]
    assert got.argv[-len(layer) :] == layer


def test_a_host_without_the_fence_interpreter_has_no_guard_layer(tmp_path: Path) -> None:
    """The control: no interpreter beside the fence, so the command runs bare under the claim."""
    target = _repo(tmp_path, "paperkit")
    got = commit_kata.claim_of(
        target, {commit_kata.FENCE_ENV: str(_fence(tmp_path))}, ["python", "x"]
    )
    assert isinstance(got, commit_kata.Claim)
    assert got.argv[-2:] == ["python", "x"]
    assert "mikemol.fence.guard_cli" not in got.argv


def test_the_real_main_commits_under_the_target_repositorys_claim(tmp_path: Path) -> None:
    """End to end: the commit lands, and the fence saw the TARGET's claim, not the launcher's."""
    target = _repo(tmp_path, "paperkit")
    entry = tmp_path / "entry.py"
    entry.write_text(
        "from mikemol.hooks.commit_kata import main\nraise SystemExit(main())\n", encoding="utf-8"
    )
    log = tmp_path / "log"
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "PYTHONPATH": os.pathsep.join(sys.path),
        commit_kata.FENCE_ENV: str(_fence(tmp_path)),
        "FENCE_LOG": str(log),
        "HOME": str(tmp_path),
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.invalid",
    }
    done = subprocess.run(
        [sys.executable, str(entry), str(target), "--waypoint", "W9", "--subject", "s", _QUEUE],
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=_TIMEOUT_S,
    )
    assert "COMMITTED paperkit" in done.stdout, done.stderr
    routing = "mikemol-commit: path: plain (the repository's pre-commit does not name"
    assert f"{routing} MIKEMOL_REAL_ROOT); lock: held" in done.stdout
    gitdir = (target / ".git").resolve()
    assert f"CLAIM=claim:path:{gitdir}/mtools/commit --" in log.read_text(encoding="utf-8")


def test_a_commit_that_cannot_take_the_lease_refuses_naming_the_pin(tmp_path: Path) -> None:
    """W1696: no fence is exit 2 with the pin line, and nothing is committed."""
    target = _repo(tmp_path, "paperkit")
    entry = tmp_path / "entry.py"
    entry.write_text(
        "from mikemol.hooks.commit_kata import main\nraise SystemExit(main())\n", encoding="utf-8"
    )
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "PYTHONPATH": os.pathsep.join(sys.path),
        commit_kata.FENCE_ENV: str(tmp_path / "no-such-fence"),
        "HOME": str(tmp_path),
    }
    done = subprocess.run(
        [sys.executable, str(entry), str(target), "--waypoint", "W9", "--subject", "s", _QUEUE],
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=_TIMEOUT_S,
    )
    assert done.returncode == commit_kata.EXIT_USAGE, done.stderr
    assert "REFUSED, no commit lock" in done.stderr
    assert commit_kata.FENCE_PIN in done.stderr
    assert "COMMITTED" not in done.stdout


def test_a_named_fence_wins_over_the_one_beside_the_interpreter() -> None:
    """The launcher's choice is kept: the sibling is only a fallback."""
    named = {commit_kata.FENCE_ENV: "/named/fence"}
    assert commit_kata.fence_of(named, "/venv/bin/python") == "/named/fence"


def test_with_no_fence_named_the_one_beside_the_interpreter_is_used() -> None:
    """A repo with the hooks and fence wheels in one venv has no launcher; its own script serves."""
    expected = "/venv/bin/mikemol-membudget"
    assert commit_kata.fence_of({}, "/venv/bin/python") == expected
    assert commit_kata.fence_of({commit_kata.FENCE_ENV: ""}, "/venv/bin/python") == expected


def test_a_fence_installed_beside_the_interpreter_takes_the_claim(tmp_path: Path) -> None:
    """The linux-sources shape: no MIKEMOL_FENCE_BIN, a fence in the interpreter's bin/."""
    target = _repo(tmp_path, "linux-sources")
    bindir = tmp_path / "venv" / "bin"
    bindir.mkdir(parents=True)
    fence = bindir / "mikemol-membudget"
    fence.write_text(_FENCE, encoding="utf-8")
    fence.chmod(_EXECUTABLE)
    got = commit_kata.claim_of(target, {}, ["python", "x"], python=str(bindir / "python"))
    assert isinstance(got, commit_kata.Claim)
    assert got.argv[0] == str(fence)


def _bazel_bin(tmp_path: Path) -> tuple[str, Path]:
    """Lay out the bazel build: a hooks venv with no fence, and a fence venv beside it.

    Returns:
        the hooks venv's interpreter path, and the fence venv's script (made executable).

    """
    top = tmp_path / "bazel-bin"
    fence = top / "fence" / ".venv" / "bin" / "mikemol-membudget"
    fence.parent.mkdir(parents=True)
    fence.write_text(_FENCE, encoding="utf-8")
    fence.chmod(_EXECUTABLE)
    return str(top / "hooks" / ".venv" / "bin" / "python3"), fence


def test_the_fence_venv_beside_the_hooks_venv_in_a_bazel_build_is_found(tmp_path: Path) -> None:
    """The build keeps the fence in `bazel-bin/fence/.venv`, not in the hooks venv's bin/."""
    python, fence = _bazel_bin(tmp_path)
    assert commit_kata.fence_of({}, python) == str(fence)


def test_the_script_beside_the_interpreter_wins_over_the_bazel_sibling(tmp_path: Path) -> None:
    """When both exist the nearer one is used."""
    python, _ = _bazel_bin(tmp_path)
    near = tmp_path / "bazel-bin" / "hooks" / ".venv" / "bin" / "mikemol-membudget"
    near.parent.mkdir(parents=True)
    near.write_text(_FENCE, encoding="utf-8")
    near.chmod(_EXECUTABLE)
    assert commit_kata.fence_of({}, python) == str(near)


def test_a_checkout_venv_finds_the_fence_in_the_checkouts_bazel_bin(tmp_path: Path) -> None:
    """`<checkout>/hooks/.venv` with no fence of its own uses `<checkout>/bazel-bin/fence/.venv`."""
    _, fence = _bazel_bin(tmp_path)
    python = tmp_path / "hooks" / ".venv" / "bin" / "python3"
    assert commit_kata.fence_of({}, str(python)) == str(fence)


def test_a_shallow_interpreter_path_has_no_bazel_sibling_and_does_not_raise() -> None:
    """A path too short to have a `bazel-bin` above it falls back to the script beside it."""
    assert commit_kata.fence_of({}, "/bin/python") == "/bin/mikemol-membudget"
