# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A tool run as root drops to the stat owner of its path, in the right order, never for root."""

import os
import pwd
from pathlib import Path

import pytest

from mikemol.hooks import rootdrop

_ENV = {"HOME": "/root", "PATH": "/usr/bin"}


def test_a_process_that_is_not_root_never_drops(tmp_path: Path) -> None:
    """Only euid 0 changes identity: an ordinary user's tool runs as itself."""
    assert rootdrop.owner_of(tmp_path, euid=1000) is None


def test_root_over_a_user_owned_path_becomes_that_user(tmp_path: Path) -> None:
    """The owner is the stat uid and gid, with the name and home of its passwd entry."""
    if os.getuid() == rootdrop.ROOT_UID:
        pytest.skip("the temp directory is root's here, so there is no user to become")
    owner = rootdrop.owner_of(tmp_path, euid=rootdrop.ROOT_UID)
    assert owner is not None
    assert (owner.uid, owner.gid) == (tmp_path.stat().st_uid, tmp_path.stat().st_gid)
    assert owner.home == pwd.getpwuid(owner.uid).pw_dir


def test_a_root_owned_path_changes_nothing() -> None:
    """Root over root's own path runs as root, unchanged (a stat saying uid 0)."""

    def root_owned(_path: Path) -> os.stat_result:
        return os.stat_result((0o40755, 1, 1, 1, 0, 0, 0, 0, 0, 0))

    assert rootdrop.owner_of(Path("/"), rootdrop.ROOT_UID, root_owned) is None


def test_a_missing_path_has_no_owner_to_drop_to(tmp_path: Path) -> None:
    """Nothing to stat is nothing to become, not a crash."""
    assert rootdrop.owner_of(tmp_path / "absent", euid=rootdrop.ROOT_UID) is None


def test_the_invoking_user_is_found_through_sudo_user_not_home() -> None:
    """HOME is /root for a root shell; SUDO_USER names the real account and its passwd home."""
    me = pwd.getpwuid(os.getuid())
    if me.pw_name == "root":
        pytest.skip("no ordinary account to look up")
    assert rootdrop.invoker_home({"SUDO_USER": me.pw_name, "HOME": "/root"}) == Path(me.pw_dir)


def test_without_a_usable_sudo_user_there_is_no_invoker_home() -> None:
    """Unset, root itself, or a name with no passwd entry: none, never a guess."""
    assert rootdrop.invoker_home({}) is None
    assert rootdrop.invoker_home({"SUDO_USER": "root"}) is None
    assert rootdrop.invoker_home({"SUDO_USER": "no-such-account-w1752"}) is None


def test_the_drop_sets_groups_then_gid_then_uid_and_gives_the_owner_environment() -> None:
    """Groups and gid need uid 0, so uid goes last; HOME, USER and LOGNAME are the owner's."""
    calls: list[tuple[str, object]] = []
    ops = rootdrop.Ops(
        lambda name, gid: calls.append(("initgroups", (name, gid))),
        lambda gid: calls.append(("setgid", gid)),
        lambda uid: calls.append(("setuid", uid)),
    )
    owner = rootdrop.Owner("mikemol", 1000, 1001, "/home/mikemol")
    env = rootdrop.drop(owner, _ENV, ops)
    assert calls == [("initgroups", ("mikemol", 1001)), ("setgid", 1001), ("setuid", 1000)]
    assert env == {
        "HOME": "/home/mikemol",
        "USER": "mikemol",
        "LOGNAME": "mikemol",
        "PATH": "/usr/bin",
    }
