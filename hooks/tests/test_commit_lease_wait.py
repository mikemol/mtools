# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A second commit waits while the first holds the repository's claim, then lands (W1733).

⚑ THE COMMIT-LEVEL WITNESS OF BLOCK-UNTIL-HELD (luthen-observability:W1409, asked 2026-10-19). The
fence's own proof is that a `hold 0 claim:` waits for the holder (fence/tests/test_admit_holder.py);
this is the other half: that the commit path asks for that blocking claim and WAITS on it, instead
of refusing with "no commit lock" or committing unlocked. Two REAL processes, no clock: the second
is known to be waiting because it SAYS so (a line the stand-in writes only after its non-blocking
try failed), and it is known to proceed because it exits 0 after the holder is released.

⚑ THE FENCE IS A STAND-IN WITH THE SAME CONTRACT, NOT THE REAL ONE: the real `mikemol-membudget`
is a console script of another distribution and is not in this one's sandbox. The stand-in takes the
argv shape `hold 0 <claim> -- <command>`, holds an exclusive file lock for the life of the command,
and writes `WAITING` first when the lock was taken. What it proves is the commit's side of the
contract: the argv it builds is one a blocking holder can serve, and the commit blocks on it.

⚑ THE PIPES ARE OS PIPES THE TEST OWNS, so every stream it reads is a plain text file object.
"""

import os
import shutil
import subprocess
import sys
import textwrap
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

_STAND_IN = textwrap.dedent(
    """\
    import fcntl
    import os
    import sys

    claim, command = sys.argv[3], sys.argv[5:]
    fd = os.open(os.environ["STAND_IN_LOCK"], os.O_CREAT | os.O_RDWR)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        sys.stderr.write("WAITING on " + claim + "\\n")
        sys.stderr.flush()
        fcntl.flock(fd, fcntl.LOCK_EX)
    os.set_inheritable(fd, True)
    os.execvp(command[0], command)
    """
)
_RUNNER = "from mikemol.hooks import commit_kata\nraise SystemExit(commit_kata.main())\n"
_HOLDER = "import sys\nprint('HELD', flush=True)\nsys.stdin.read()\n"
_GIT_IDENTITY = {
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.invalid",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.invalid",
    "GIT_CONFIG_NOSYSTEM": "1",
}
_EXECUTABLE = 0o755
_TWO = "2"
_WHO = ["--waypoint", "W1", "--subject", "s", "a.txt"]


def _git(repo: Path, env: dict[str, str], *args: str) -> str:
    git = shutil.which("git")
    assert git is not None
    done = subprocess.run(
        [git, "-C", str(repo), *args], check=True, capture_output=True, text=True, env=env
    )
    return done.stdout


def _environment(tmp_path: Path) -> dict[str, str]:
    prefixes = ("GIT_", "MIKEMOL_", "MEMBUDGET")
    base = {k: v for k, v in os.environ.items() if not k.startswith(prefixes)}
    stand_in = tmp_path / "stand-in-fence.py"
    stand_in.write_text(_STAND_IN, encoding="utf-8")
    launcher = tmp_path / "fence"
    launcher.write_text(f'#!/bin/sh\nexec {sys.executable} {stand_in} "$@"\n', encoding="utf-8")
    launcher.chmod(_EXECUTABLE)
    return {
        **base,
        **_GIT_IDENTITY,
        "HOME": str(tmp_path),
        "GIT_CEILING_DIRECTORIES": str(tmp_path),
        "PYTHONPATH": os.pathsep.join(sys.path),
        "MIKEMOL_FENCE_BIN": str(launcher),
        "MIKEMOL_COMMIT_ISOLATED": "0",
        "STAND_IN_LOCK": str(tmp_path / "claim.lock"),
    }


def _repo(tmp_path: Path, env: dict[str, str]) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, env, "init", "--quiet")
    (repo / "a.txt").write_text("one\n", encoding="utf-8")
    _git(repo, env, "add", "a.txt")
    _git(repo, env, "commit", "--quiet", "-m", "first")
    (repo / "a.txt").write_text("two\n", encoding="utf-8")
    return repo


def _pipe() -> tuple[TextIO, int]:
    # A reader the test keeps and the write end a child is given.
    read_end, write_end = os.pipe()
    return os.fdopen(read_end, "r", encoding="utf-8"), write_end


def _spawn(
    argv: Sequence[str], env: dict[str, str], cwd: Path, fds: tuple[int, int, int]
) -> subprocess.Popen[bytes]:
    child = subprocess.Popen(
        list(argv), stdin=fds[0], stdout=fds[1], stderr=fds[2], env=env, cwd=cwd
    )
    for each in fds:
        if each > 0:
            os.close(each)
    return child


def test_a_second_commit_waits_on_the_held_claim_and_lands_once_it_is_released(
    tmp_path: Path,
) -> None:
    """Held: the second says WAITING and is alive. Released: it exits 0, HEAD moved, no refusal."""
    env = _environment(tmp_path)
    repo = _repo(tmp_path, env)
    runner = tmp_path / "run_commit.py"
    runner.write_text(_RUNNER, encoding="utf-8")
    fence = [sys.executable, str(tmp_path / "stand-in-fence.py")]
    hold = [*fence, "hold", "0", "claim:test", "--", sys.executable, "-c", _HOLDER]
    held_in, release = os.pipe()
    held_out, held_out_fd = _pipe()
    holder = _spawn(hold, env, repo, (held_in, held_out_fd, subprocess.DEVNULL))
    assert held_out.readline().strip() == "HELD"
    out, out_fd = _pipe()
    err, err_fd = _pipe()
    second = _spawn(
        [sys.executable, str(runner), str(repo), *_WHO],
        env,
        repo,
        (subprocess.DEVNULL, out_fd, err_fd),
    )
    assert err.readline().startswith("WAITING")
    assert second.poll() is None
    assert _git(repo, env, "rev-list", "--count", "HEAD").strip() == "1"
    os.close(release)
    holder.wait()
    assert second.wait() == 0
    assert "COMMITTED" in out.read()
    assert "no commit lock" not in err.read()
    assert _git(repo, env, "rev-list", "--count", "HEAD").strip() == _TWO
