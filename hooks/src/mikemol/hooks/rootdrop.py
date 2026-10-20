# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A user-level tool run as root drops to the owner of the path it was given (W1752).

⚑ THE RULING (operator, 2026-10-15, host session 695f3e0a line 67571, uuid 97814ac7: "`The tool
should refuse a user-level set run as root, with a message naming the right shell.` Remember, I've
made this error befor, and the answer was to ensure commands run as root be safe even if they modify
nonroot, by ensuring permissions and ownerships et al are not modified inappropriately.") IS NOT A
REFUSAL: the tool runs, and nothing it makes belongs to root. On 2026-10-19 the operator ran a
requeue script as root, `mikemol-commit` resolved the bare name against /root/github, every
withdrawal failed, and a crash left root-owned files under a user's `.git`.

⚑ THE OWNER IS THE STAT OWNER (uid and gid) OF THE PATH GIVEN (github-8f 2026-10-20, relaying the
same rule). With euid 0 and an owner that is not root, the groups, gid and uid are set to the
owner's (groups from the owner's passwd entry) before anything is touched, and HOME, USER and
LOGNAME come from that entry. A root-owned path, or a process that is not root, changes nothing.

⚑ THE SYSTEM CALLS ARE A SEAM: `Ops` holds initgroups, setgid and setuid, so the order is tested
without a real setuid, which a test must never perform.
"""

import os
import pwd
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

ROOT_UID = 0


@dataclass(frozen=True, slots=True)
class Owner:
    """The account that owns a path: what to become and the environment that account has."""

    name: str
    uid: int
    gid: int
    home: str


@dataclass(frozen=True, slots=True)
class Ops:
    """The three calls that change identity, in the order they must run."""

    initgroups: Callable[[str, int], None]
    setgid: Callable[[int], None]
    setuid: Callable[[int], None]


REAL = Ops(os.initgroups, os.setgid, os.setuid)

type StatOf = Callable[[Path], os.stat_result]


def owner_of(path: Path, euid: int, stat_of: StatOf = Path.stat) -> Owner | None:
    """Find the account to drop to for `path`.

    Returns:
        the path's owner when this process is root and that owner is not; None when the process is
        not root, the path is root's, the path is missing, or the owner has no passwd entry.

    """
    if euid != ROOT_UID:
        return None
    try:
        seen = stat_of(path)
        entry = pwd.getpwuid(seen.st_uid)
    except (OSError, KeyError):
        return None
    if seen.st_uid == ROOT_UID:
        return None
    return Owner(entry.pw_name, seen.st_uid, seen.st_gid, entry.pw_dir)


def invoker_home(env: Mapping[str, str]) -> Path | None:
    """Find the home of the user who ran a tool through sudo, whatever HOME says.

    ⚑ A BARE REPO NAME IS RESOLVED INDEPENDENTLY OF HOME (W1752): as root, HOME is /root, where no
    fleet root exists, and every name failed to resolve. `SUDO_USER` names who is really asking.

    Returns:
        that user's home directory, or None when no `SUDO_USER` is set or it has no entry.

    """
    name = env.get("SUDO_USER")
    if not name or name == "root":
        return None
    try:
        return Path(pwd.getpwnam(name).pw_dir)
    except KeyError:
        return None


def drop(owner: Owner, env: Mapping[str, str], ops: Ops = REAL) -> dict[str, str]:
    """Become the owner: groups, then gid, then uid, because the first two need uid 0.

    Returns:
        a copy of `env` with HOME, USER and LOGNAME set to the owner's.

    """
    ops.initgroups(owner.name, owner.gid)
    ops.setgid(owner.gid)
    ops.setuid(owner.uid)
    return {**env, "HOME": owner.home, "USER": owner.name, "LOGNAME": owner.name}
