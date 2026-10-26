# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A second domain witness on one victim WAITS for the first and does not refuse (W1692, W1688).

⚑ THE RESIDUE GUARD CANNOT TELL A PEER'S LIVE PROBE FROM AN ABANDONED ONE, so two gates reaching the
same fixed victim list made the second exit 2 while the first behaved correctly. The witness now
takes an advisory lock keyed by the victim, before that guard, and holds it until it exits.

⚑ THE WITNESS RUNS FROM A COPY INSIDE THE SCRATCH REPOSITORY, because it `cd`s to its own
directory first: run from the source tree it would work on the real repository, not the fixture.

⚑ THE FIXTURE NEEDS NO BAZEL: the lock is taken before any arm runs, and a victim that already
carries the probe marker makes the run end at the residue guard right after it, with exit 2. So the
test holds the lock itself, starts the witness, waits until the kernel lists the witness as BLOCKED
on that lock (`/proc/locks`, a waiter shows a `->`), then releases it and expects the residue
refusal. Without the lock the run would have exited at once and never been seen waiting.
"""

import fcntl
import shutil
import subprocess
from pathlib import Path

_SCRIPT = Path(__file__).absolute().parents[2] / "domain_witness.sh"
_VICTIM = "victim.py"
_RESIDUE = "x = 1\n# transient domain probe 1\n"
_REFUSED = 2


def _git(repo: Path, *args: str, text: str | None = None) -> str:
    done = subprocess.run(
        ["git", *args], cwd=repo, input=text, capture_output=True, text=True, check=True
    )
    return done.stdout.strip()


def _blocked_on(inode: int) -> bool:
    # Whether /proc/locks lists a waiter (a line with `->`) on this inode.
    for line in Path("/proc/locks").read_text(encoding="utf-8").splitlines():
        if "->" in line and f":{inode} " in line + " ":
            return True
    return False


def test_a_second_witness_waits_on_the_first_and_then_runs(tmp_path: Path) -> None:
    """Blocked while the lock is held; after release it reaches the residue guard and exits 2."""
    _git(tmp_path, "init", "-q")
    (tmp_path / _VICTIM).write_text(_RESIDUE, encoding="utf-8")
    for name in (_SCRIPT.name, "git_env.sh"):
        shutil.copy(_SCRIPT.parent / name, tmp_path / name)
    _git(tmp_path, "add", _VICTIM)
    key = _git(tmp_path, "hash-object", "--stdin", text=_VICTIM)
    lock = tmp_path / ".git" / "mtools" / f"domain-witness-{key}.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open("w", encoding="utf-8") as held:
        fcntl.flock(held, fcntl.LOCK_EX)
        run = subprocess.Popen(
            ["bash", _SCRIPT.name, "dist", "//dist:t", _VICTIM],
            cwd=tmp_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        while run.poll() is None and not _blocked_on(lock.stat().st_ino):
            pass
        assert run.poll() is None, run.communicate()[1]
        fcntl.flock(held, fcntl.LOCK_UN)
    _out, err = run.communicate()
    code = run.wait()
    assert code == _REFUSED
    assert "already carries probe residue" in err
