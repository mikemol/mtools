# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The hash-chained apply ledger: one line per apply attempt, tamper-evident (W1852).

Ported from luthen's `checks/opa_plan.py` (lines 717-793, W260), behind `PlanConfig` and `Tools`.

⚑ EVERY APPLY ATTEMPT APPENDS ONE JSON LINE to `apply-ledger.jsonl` in the root's state directory
(`PlanConfig.state_dir`, so the root-owned directory for a root-planned root under custody), and
each line carries `prev`, the sha256 of the line before it. An edit or a deletion breaks every later
`prev`, and `ledger_intact` says so. The file cannot be made append-only against root without
`chattr +a`, so a root-written ledger is tamper-evident to everyone but root, and a user ledger only
tamper-evident.

⚑ NAMES, NEVER SECRETS: `applier` records the login and sudo's invoking user as account names.

⚑ THE ENTRY IS ASSEMBLED BY THE CALLER (W1854): which witness result, which preconditions fired
and which run record it carries belong to the apply flow; this module is the chain, the path and
the two facts any entry needs (who and which commit).
"""

import hashlib
import json
import os
import pwd
from pathlib import Path

from mikemol.waldo.planconfig import PlanConfig
from mikemol.waldo.planjson import Json, parse_object
from mikemol.waldo.plantools import Tools

LEDGER_NAME = "apply-ledger.jsonl"
LEDGER_MODE = 0o644


def ledger_path(config: PlanConfig, root_name: str) -> Path:
    """Name the apply ledger a root's applies are appended to, beside its verdicts.

    Returns:
        `<state dir for the root>/apply-ledger.jsonl`.

    """
    return config.state_dir(root_name) / LEDGER_NAME


def applier(uid: int, sudo_user: str) -> dict[str, str]:
    """Say who is applying: account NAMES only (the login, and sudo's invoking user).

    Returns:
        `user` and `sudo_user`; the login is `uid<N>` when the uid has no passwd entry.

    """
    try:
        user = pwd.getpwuid(uid).pw_name
    except KeyError:
        user = f"uid{uid}"
    return {"user": user, "sudo_user": sudo_user}


def current_applier() -> dict[str, str]:
    """Say who is applying, from this process.

    Returns:
        `applier` over the real uid and `SUDO_USER`.

    """
    return applier(os.getuid(), os.environ.get("SUDO_USER", ""))


def _inputs(config: PlanConfig) -> list[str]:
    # The apply inputs as git pathspecs: the terraform and policy directories, relative to the root.
    names: list[str] = []
    for path in (config.terraform, config.policy):
        try:
            names.append(str(path.relative_to(config.root)))
        except ValueError:
            names.append(str(path))
    return names


def repo_commit(tools: Tools, config: PlanConfig) -> dict[str, object]:
    """Read the repo's HEAD and whether the apply inputs (terraform, policy) are uncommitted.

    Returns:
        `commit` ('' when unknown) and `dirty` (None when git could not say).

    """
    git = tools.find("git")
    if git is None:
        return {"commit": "", "dirty": None}
    root = str(config.root)
    head = tools.run(git, "-C", root, "rev-parse", "HEAD")
    status = tools.run(git, "-C", root, "status", "--porcelain", "--", *_inputs(config))
    ok = head.returncode == 0 and status.returncode == 0
    return {
        "commit": head.stdout.strip() if head.returncode == 0 else "",
        "dirty": bool(status.stdout.strip()) if ok else None,
    }


def last_line_digest(path: Path) -> str:
    """Hash the ledger's last line.

    Returns:
        the hex sha256, or '' for an empty or absent ledger.

    """
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    return hashlib.sha256(lines[-1].encode()).hexdigest() if lines else ""


def append_ledger(config: PlanConfig, root_name: str, entry: Json) -> Path:
    """Append one entry, chained to the previous line's hash, to the root's ledger.

    Returns:
        the ledger's path.

    """
    path = ledger_path(config, root_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    record: Json = {**entry, "prev": last_line_digest(path)}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    path.chmod(LEDGER_MODE)
    return path


def ledger_intact(path: Path) -> bool:
    """Check that every entry's `prev` is the sha256 of the line before it.

    Returns:
        True for a whole chain; False for an unreadable file, a line that is not an object, or any
        broken link.

    """
    prev = ""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return False
    for line in lines:
        record = parse_object(line)
        if record is None or record.get("prev") != prev:
            return False
        prev = hashlib.sha256(line.encode()).hexdigest()
    return True
