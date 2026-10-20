# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A bare repo name resolves independently of HOME, and a root run becomes the owner (W1752)."""

import os
import pwd
from pathlib import Path

import pytest

from mikemol.hooks import commit_kata

_ABSENT = "no-such-repo-w1752"


def test_the_named_host_root_wins(tmp_path: Path) -> None:
    """MIKEMOL_ROOT-style override: the environment's root is used as given."""
    env = {commit_kata.ROOT_ENV: str(tmp_path)}
    assert commit_kata.fleet_root("mtools", env) == tmp_path


def test_with_nothing_named_the_effective_users_fleet_root_is_used() -> None:
    """No override and no sudo user: HOME's github directory, as before."""
    assert commit_kata.fleet_root(_ABSENT, {}) == Path.home() / "github"


def test_a_sudo_user_whose_fleet_root_lacks_the_name_falls_back_to_the_effective_user() -> None:
    """The invoker's directory is chosen only when it holds the name, never on SUDO_USER alone."""
    me = pwd.getpwuid(os.getuid())
    if me.pw_name == "root":
        pytest.skip("no ordinary account to name as the sudo user")
    got = commit_kata.fleet_root(_ABSENT, {"SUDO_USER": me.pw_name})
    assert got == Path.home() / "github"


def test_a_process_that_is_not_root_keeps_its_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Becoming the owner is inert for an ordinary user: HOME and the rest are untouched."""
    monkeypatch.setenv("HOME", str(tmp_path))
    if os.geteuid() == 0:
        pytest.skip("this test process is root, which would really drop")
    commit_kata.become_owner(tmp_path)
    assert os.environ["HOME"] == str(tmp_path)


def test_a_path_is_resolved_as_a_path_and_a_name_under_the_fleet_root(tmp_path: Path) -> None:
    """A slash or a leading dot is a path; anything else is a name under the host root."""
    env = {commit_kata.ROOT_ENV: str(tmp_path)}
    assert commit_kata.resolve_root(str(tmp_path), env) == tmp_path.resolve()
    assert commit_kata.resolve_root("named", env) == tmp_path / "named"
