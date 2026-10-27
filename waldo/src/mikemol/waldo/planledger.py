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
from dataclasses import dataclass
from pathlib import Path

from mikemol.waldo.planconfig import PlanConfig
from mikemol.waldo.planjson import Json, parse_object
from mikemol.waldo.plantools import Tools

LEDGER_NAME = "apply-ledger.jsonl"
MARK_NAME = "apply-ledger.mark"
LEDGER_MODE = 0o644
AFTER_STATE = "after_state"
# ⚑ ONE FIXED STRING PER REFUSAL, so a caller's interlock names the cause without parsing prose
# (estate-6d, 2026-10-27). Each is what `baseline_ok` returns; None means the apply may proceed.
HASH_MISMATCH = "hash-mismatch"
NO_ENTRY_NOT_IMPORTED = "no-entry-not-imported"
CHAIN_BROKEN = "chain-broken"
TRUNCATED_BELOW_MARK = "truncated-below-mark"


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


def mark_path(path: Path) -> Path:
    """Name the high-water mark beside a ledger (estate:W52, W2056).

    Returns:
        `apply-ledger.mark` in the ledger's directory.

    """
    return path.with_name(MARK_NAME)


def _write_mark(path: Path) -> None:
    # The entry count and the last line's digest, kept BESIDE the ledger so a truncation, which
    # leaves a shorter chain that is still intact, can be told from a ledger that is whole.
    lines = path.read_text(encoding="utf-8").splitlines()
    mark: Json = {"count": len(lines), "digest": last_line_digest(path)}
    target = mark_path(path)
    target.write_text(json.dumps(mark, sort_keys=True) + "\n", encoding="utf-8")
    target.chmod(LEDGER_MODE)


def append_ledger(config: PlanConfig, root_name: str, entry: Json) -> Path:
    """Append one entry, chained to the previous line's hash, to the root's ledger.

    ⚑ THE HIGH-WATER MARK IS WRITTEN WITH EVERY APPEND (estate:W52): the count of lines and the
    digest of the last one, in a side file, so `baseline_ok` can refuse a ledger that has lost its
    tail. It is as writable as the ledger by whoever owns the directory, so it catches an
    out-of-band truncation or restore and not a deliberate forgery.

    Returns:
        the ledger's path.

    """
    path = ledger_path(config, root_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    record: Json = {**entry, "prev": last_line_digest(path)}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    path.chmod(LEDGER_MODE)
    _write_mark(path)
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


@dataclass(frozen=True, slots=True)
class Transition:
    """One apply's state transition: the domain, the three hashes and the time (estate:W52)."""

    root: str
    before_sha256: str
    after_sha256: str
    plan_sha256: str
    at: str


def record_after_state(config: PlanConfig, step: Transition) -> Path:
    """Record one apply's state transition in the root's chained ledger (estate:W52, W2056).

    ⚑ THE ENTRY IS A LATTICE EDGE, NOT ONLY A NODE: it carries the hash the baseline had before the
    act, the hash it has after, and the hash of the plan that landed, so the chain shows each
    transition's `before` equal to the previous `after`. `root` is the domain's name: one chain
    per zone, never one for all. No planfile is needed; the caller supplies the three hashes and
    the time.

    Returns:
        the ledger's path.

    """
    entry: Json = {
        "kind": AFTER_STATE,
        "root": step.root,
        "before_sha256": step.before_sha256,
        "after_sha256": step.after_sha256,
        "plan_sha256": step.plan_sha256,
        "applier": current_applier(),
        "at": step.at,
    }
    return append_ledger(config, step.root, entry)


def _lines(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []


def _truncated(path: Path) -> bool:
    # True when the high-water mark says the ledger once held more than it does now, or holds a
    # different line where the mark's last line was; a mark that cannot be read is a refusal too.
    try:
        mark = parse_object(mark_path(path).read_text(encoding="utf-8"))
    except OSError:
        return False
    count = mark.get("count") if mark is not None else None
    digest = mark.get("digest") if mark is not None else None
    if not isinstance(count, int) or not isinstance(digest, str):
        return True
    lines = _lines(path)
    if count == 0:
        return False
    return len(lines) < count or hashlib.sha256(lines[count - 1].encode()).hexdigest() != digest


def _last_after_state(path: Path, root_name: str) -> str | None:
    last: str | None = None
    for line in _lines(path):
        record = parse_object(line)
        if record is None or record.get("kind") != AFTER_STATE or record.get("root") != root_name:
            continue
        after = record.get("after_sha256")
        if isinstance(after, str):
            last = after
    return last


def baseline_ok(
    config: PlanConfig, root_name: str, baseline_sha256: str, *, imported: bool
) -> str | None:
    """Judge a baseline against the ledger before an apply (estate:W52, W2056).

    ⚑ ONE FIXED STRING PER REFUSAL, in the order they are tried: a chain with a bad link is
    `chain-broken`; a ledger that holds fewer lines than the high-water mark says it once did (or
    whose line at the mark's position differs) is `truncated-below-mark`; a baseline whose hash is
    not the last `after_sha256` recorded for the root is `hash-mismatch`. NO ENTRY YET is the first
    apply after the read-only import, allowed only when `imported` (the baseline was written by
    that import); otherwise it is `no-entry-not-imported`, which is what a ledger deleted after
    tampering looks like, and a deleted ledger with a mark left beside it is `truncated-below-mark`.

    Returns:
        None when the apply may proceed, else one of HASH_MISMATCH, NO_ENTRY_NOT_IMPORTED,
        CHAIN_BROKEN, TRUNCATED_BELOW_MARK.

    """
    path = ledger_path(config, root_name)
    if path.is_file() and not ledger_intact(path):
        return CHAIN_BROKEN
    if _truncated(path):
        return TRUNCATED_BELOW_MARK
    last = _last_after_state(path, root_name)
    if last is None:
        return None if imported else NO_ENTRY_NOT_IMPORTED
    return None if last == baseline_sha256 else HASH_MISMATCH
