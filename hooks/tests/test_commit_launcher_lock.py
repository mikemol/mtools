# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`hooks/bin/mikemol-commit` commits under a per-repo fence claim and restores the env (W886).

⚑ Each arm runs the real launcher in a throwaway git checkout whose fence `mikemol-membudget` is a
stub that records how it was called and then runs the command it was given, as `hold` does. The
hooks venv's `python3` is a stub that prints the budget variables it receives, so what the commit
itself would inherit is observed rather than inferred.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

_LAUNCHER = Path(__file__).parent.parent / "bin" / "mikemol-commit"
_EXECUTABLE = 0o755
_TIMEOUT_S = 30
_FENCE = (
    "#!/bin/sh\n"
    'echo "FENCE_ARGS=$1 $2 $3 $4"\n'
    'echo "FENCE_FILE=$MEMBUDGET_FILE"\n'
    'echo "FENCE_MAXLOAD=$MEMBUDGET_MAXLOAD"\n'
    'echo "FENCE_TIMEOUT=$MEMBUDGET_TIMEOUT"\n'
    "shift 4\n"
    'exec "$@"\n'
)
_PYTHON = (
    "#!/bin/sh\n"
    'echo "INNER_FILE=${MEMBUDGET_FILE-unset}"\n'
    'echo "INNER_MAXLOAD=${MEMBUDGET_MAXLOAD-unset}"\n'
    'echo "INNER_TIMEOUT=${MEMBUDGET_TIMEOUT-unset}"\n'
    'echo "INNER_PARENT=${MEMBUDGET_PARENT-unset}"\n'
    'echo "INNER_HELD=${MIKEMOL_COMMIT_LOCK_HELD-unset}"\n'
    'for a in "$@"; do echo "ARG=$a"; done\n'
)


def _stub(path: Path, text: str) -> None:
    """Write an executable stub at `path`."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    path.chmod(_EXECUTABLE)


def _checkout(tmp_path: Path, *, fence: bool, git: bool = True) -> Path:
    """Write a fake checkout with the hooks venv, optionally a fence stub, optionally a git repo.

    Returns:
        the checkout.

    """
    root = tmp_path / "project"
    root.mkdir()
    if git:
        subprocess.run(["git", "init", "-q", str(root)], check=True, timeout=_TIMEOUT_S)
    bindir = root / "bazel-bin" / "hooks" / ".venv" / "bin"
    _stub(bindir / "python3", _PYTHON)
    (bindir / "mikemol-commit").write_text("# entry\n", encoding="utf-8")
    if fence:
        _stub(root / "bazel-bin" / "fence" / ".venv" / "bin" / "mikemol-membudget", _FENCE)
    return root


def _run(root: Path, extra: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """Run the real launcher with PATH, MIKEMOL_ROOT and `extra` in its environment.

    Returns:
        the finished process.

    """
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "MIKEMOL_ROOT": str(root),
        **(extra or {}),
    }
    return subprocess.run(
        [str(_LAUNCHER), "fx", "--subject", "a subject"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=_TIMEOUT_S,
    )


def _lines(proc: subprocess.CompletedProcess[str]) -> dict[str, str]:
    """Read the stubs' KEY=VALUE lines.

    Returns:
        the last value printed for each key.

    """
    found: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        key, _, value = line.partition("=")
        found[key] = value
    return found


def test_the_commit_runs_under_a_hold_on_a_claim_in_the_git_directory(tmp_path: Path) -> None:
    """The fence is called `hold 0 claim:path:<gitdir>/mtools/commit --`, on a per-repo ledger."""
    root = _checkout(tmp_path, fence=True)
    proc = _run(root)
    seen = _lines(proc)
    gitdir = (root / ".git").resolve()
    assert seen["FENCE_ARGS"] == f"hold 0 claim:path:{gitdir}/mtools/commit --", proc.stderr
    assert seen["FENCE_FILE"] == f"{gitdir}/mtools/commit.ledger"


def test_the_load_gate_is_off_and_the_wait_is_bounded(tmp_path: Path) -> None:
    """A busy host must not stall a commit, and a wedged holder must end as a refusal."""
    proc = _run(_checkout(tmp_path, fence=True))
    assert _lines(proc)["FENCE_MAXLOAD"] == "0"
    assert _lines(proc)["FENCE_TIMEOUT"] == "3600"


def test_the_timeout_is_overridable(tmp_path: Path) -> None:
    """MIKEMOL_COMMIT_LOCK_TIMEOUT sets the bound."""
    proc = _run(_checkout(tmp_path, fence=True), {"MIKEMOL_COMMIT_LOCK_TIMEOUT": "90"})
    assert _lines(proc)["FENCE_TIMEOUT"] == "90"


def test_the_command_does_not_inherit_the_commit_ledger(tmp_path: Path) -> None:
    """With none of the budget variables set, the command sees none, so its gate uses the host's."""
    seen = _lines(_run(_checkout(tmp_path, fence=True)))
    assert seen["INNER_FILE"] == "unset"
    assert seen["INNER_MAXLOAD"] == "unset"
    assert seen["INNER_TIMEOUT"] == "unset"
    assert seen["INNER_PARENT"] == "unset"


def test_the_commands_own_budget_variables_are_put_back(tmp_path: Path) -> None:
    """A caller's ledger and ceilings survive the hold untouched."""
    given = {
        "MEMBUDGET_FILE": "/host/budget.cotype",
        "MEMBUDGET_MAXLOAD": "7",
        "MEMBUDGET_TIMEOUT": "12",
        "MEMBUDGET_PARENT": "outer1",
    }
    seen = _lines(_run(_checkout(tmp_path, fence=True), given))
    assert seen["INNER_FILE"] == "/host/budget.cotype"
    assert seen["INNER_MAXLOAD"] == "7"
    assert seen["INNER_TIMEOUT"] == "12"
    assert seen["INNER_PARENT"] == "outer1"


def test_the_arguments_still_reach_the_console_script(tmp_path: Path) -> None:
    """Locking does not drop or re-split an argument."""
    proc = _run(_checkout(tmp_path, fence=True))
    args = [line for line in proc.stdout.splitlines() if line.startswith("ARG=")]
    assert args[1:] == ["ARG=fx", "ARG=--subject", "ARG=a subject"]


def test_the_command_is_told_it_holds_the_claim(tmp_path: Path) -> None:
    """The marker is set inside, so a nested commit does not wait on its own parent."""
    assert _lines(_run(_checkout(tmp_path, fence=True)))["INNER_HELD"] == "1"


def test_a_nested_call_does_not_take_a_second_claim(tmp_path: Path) -> None:
    """With the marker already set the fence is never called: the claim is held above."""
    proc = _run(_checkout(tmp_path, fence=True), {"MIKEMOL_COMMIT_LOCK_HELD": "1"})
    assert "FENCE_ARGS" not in _lines(proc)
    assert "INNER_FILE" in _lines(proc)


def test_an_unbuilt_fence_commits_unlocked_and_says_so(tmp_path: Path) -> None:
    """No fence venv: the commit runs, with one stderr line naming the missing lock."""
    proc = _run(_checkout(tmp_path, fence=False))
    assert proc.returncode == 0
    assert "INNER_FILE" in _lines(proc)
    assert "no commit lock" in proc.stderr


def test_a_checkout_that_is_not_a_repository_commits_unlocked_and_says_so(tmp_path: Path) -> None:
    """The git directory cannot be resolved: unlocked, said, and the command still runs."""
    proc = _run(_checkout(tmp_path, fence=True, git=False))
    assert proc.returncode == 0
    assert "FENCE_ARGS" not in _lines(proc)
    assert "no commit lock" in proc.stderr
