# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`clean_env`: no `GIT_*` survives, nothing else is lost, and the hazard it closes is real.

⚑⚑ THE LAST TWO ARMS ARE THE NEGATIVE CONTROL substrate measured by hand, codified: a fixture
commit run under a HOSTILE environment that aims `GIT_DIR` and `GIT_INDEX_FILE` at a DECOY
repository. Unscrubbed, the commit lands in the decoy, which proves the hazard bites here; scrubbed,
it stays out of the decoy. The decoy is always a temp repository — never this one.
"""

from __future__ import annotations

import os
import subprocess
from typing import TYPE_CHECKING

from mikemol.fence import git_env

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_KEPT = {"PATH": "/usr/bin", "MYGIT_DIR": "not-git's", "LANG": "C"}
_DROPPED = {"GIT_DIR": "/elsewhere/.git", "GIT_INDEX_FILE": "/elsewhere/index",
            "GIT_WORK_TREE": "/elsewhere", "GIT_CONFIG_NOSYSTEM": "1"}
_IDENTITY = ("-c", "user.name=t", "-c", "user.email=t@t")


def test_every_git_variable_is_dropped_and_nothing_else_is() -> None:
    """All `GIT_*` go (no allowlist); a name merely CONTAINING `GIT` is the kept control."""
    assert git_env.clean_env({**_KEPT, **_DROPPED}) == _KEPT


def test_the_base_mapping_is_not_modified() -> None:
    """A caller's mapping comes back untouched; the result is a new dict."""
    base = {**_KEPT, **_DROPPED}
    snapshot = dict(base)
    git_env.clean_env(base)
    assert base == snapshot


def test_the_default_base_is_this_processs_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """With no base, `os.environ` is read — and its `GIT_*` still dropped."""
    monkeypatch.setenv("GIT_DIR", _DROPPED["GIT_DIR"])
    monkeypatch.setenv("MYGIT_DIR", _KEPT["MYGIT_DIR"])
    got = git_env.clean_env()
    assert "GIT_DIR" not in got
    assert got["MYGIT_DIR"] == _KEPT["MYGIT_DIR"]


def _git(env: dict[str, str], *args: str) -> str:
    """Run git under `env`, failing loudly with its stderr.

    Returns:
        git's stdout.

    """
    proc = subprocess.run(["git", *args], env=env, capture_output=True, text=True, check=False)
    assert proc.returncode == 0, f"git {' '.join(args)}: {proc.stderr.strip()}"
    return proc.stdout


def _commit_under_hostile_env(tmp_path: Path, *, scrub: bool) -> str:
    """Commit in a fixture repo with `GIT_DIR`/`GIT_INDEX_FILE` aimed at a decoy.

    Returns:
        the decoy's refs afterwards — empty when nothing landed there.

    """
    clean = git_env.clean_env()
    decoy = tmp_path / "decoy"
    fixture = tmp_path / "fixture"
    _git(clean, "init", "-q", str(decoy))
    _git(clean, "init", "-q", str(fixture))
    (fixture / "f.txt").write_text("x\n", encoding="utf-8")
    hostile = {**os.environ, "GIT_DIR": str(decoy / ".git"),
               "GIT_INDEX_FILE": str(decoy / ".git" / "index")}
    env = git_env.clean_env(hostile) if scrub else hostile
    _git(env, "-C", str(fixture), "add", "f.txt")
    _git(env, "-C", str(fixture), *_IDENTITY, "commit", "-qm", "fixture")
    return _git(clean, "-C", str(decoy), "for-each-ref")


def test_an_unscrubbed_fixture_commits_into_the_decoy(tmp_path: Path) -> None:
    """THE HAZARD, measured: under the hostile environment a fixture's commit lands in the decoy.

    ⚑ Without this arm the scrubbed arm could pass because the hazard never bit at all.
    """
    assert _commit_under_hostile_env(tmp_path, scrub=False)


def test_a_scrubbed_fixture_leaves_the_decoy_empty(tmp_path: Path) -> None:
    """THE FIX: the same commit run under `clean_env` leaves the decoy with no refs."""
    assert not _commit_under_hostile_env(tmp_path, scrub=True)
