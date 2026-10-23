# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Verdict binding and custody: a plan is admitted only by a record that is its own (W1850).

Ported from luthen's `checks/opa_plan.py` (lines 261-350, W261), behind `PlanConfig`.

⚑ KEYED BY THE PLANFILE'S HASH, NOT ITS NAME, in a state directory and not beside the planfile: a
verdict is `<state>/verdicts/<sha256 of the planfile>.verdict.json`, so a planfile whose bytes moved
has no verdict, and the planner cannot drop a sidecar next to its own planfile. The binding is not a
switch (every consumer has it).

⚑ ROOT-PLANNED ROOTS' RECORDS MUST BE THE TRUSTED USER'S, in a directory nobody else can write
(owner is `trusted_uid`, mode with no group or other write bit). That is the rule that stops an
unprivileged planner forging an admission. A record for such a root found only in the user's
directory is refused. With `root_custody` off in the config there is no root-owned directory, every
record is a user record, and the root-planned rule does not apply: that is the consumer's explicit
choice after its operator's ruling, never this module's default.

⚑ A USER RECORD CARRIES A SEAL, A HASH OF ITS OWN BODY: tamper-EVIDENT against edits and staleness,
not tamper-proof, since whoever can write the file can recompute the seal.

⚑ THE POLICY DIGEST VOIDS A VERDICT WHEN THE RULES MOVE: it hashes every policy file by path and
bytes except the Rego tests, plus the consumer's declared data files, so a verdict judged under
other rules is not admitted. `declarations` maps a policy-relative directory name to a
repo-relative data file (luthen's `opa_data.DECLARATIONS`) and defaults to none.
"""

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path

from mikemol.waldo.planconfig import PlanConfig
from mikemol.waldo.planjson import Json, parse_object

GROUP_OTHER_WRITE = 0o022


def sha256_of(path: Path) -> str:
    """Hash a file's bytes.

    Returns:
        the hex sha256.

    """
    return hashlib.sha256(path.read_bytes()).hexdigest()


def policy_digest(config: PlanConfig, declarations: Mapping[str, str] | None = None) -> str:
    """Hash every policy file, rules and data but not the Rego tests, by path and bytes.

    Returns:
        the hex sha256 over the sorted files and the consumer's declared data files.

    """
    digest = hashlib.sha256()
    files = {p.relative_to(config.policy): p for p in config.policy.rglob("*") if p.is_file()}
    for name, source in (declarations or {}).items():
        files[Path(name) / "data.json"] = config.root / source
    for rel in sorted(files):
        if rel.name.endswith("_test.rego"):
            continue
        digest.update(str(rel).encode() + b"\0" + files[rel].read_bytes() + b"\0")
    return digest.hexdigest()


def seal_of(doc: Mapping[str, object]) -> str:
    """Hash a record's canonical JSON without its own seal.

    Returns:
        the hex sha256.

    """
    body = {k: v for k, v in doc.items() if k != "seal"}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


def trusted_dir(path: Path, uid: int) -> bool:
    """Say whether a directory is owned by the trusted uid and writable by no one else.

    Returns:
        True when the owner is `uid` and neither the group nor others can write to it.

    """
    try:
        info = path.stat()
    except OSError:
        return False
    return info.st_uid == uid and not info.st_mode & GROUP_OTHER_WRITE


def verdict_path(state: Path, digest: str) -> Path:
    """Name where the verdict for a planfile with this hash lives under a state directory.

    Returns:
        `<state>/verdicts/<digest>.verdict.json`.

    """
    return state / "verdicts" / f"{digest}.verdict.json"


def _document(record: Path) -> Json | None:
    # The record's JSON object, or None when it cannot be read or is not an object.
    try:
        return parse_object(record.read_text(encoding="utf-8"))
    except OSError:
        return None


def check_record(config: PlanConfig, record: Path, *, trusted: bool) -> Json | str:
    """Judge a verdict record's custody and seal.

    Returns:
        the record's document when both hold, else the reason it is refused.

    """
    uid = config.trusted_uid
    if trusted and not (trusted_dir(record.parent, uid) and record.stat().st_uid == uid):
        return f"{record} is not root-owned in a root-only directory"
    doc = _document(record)
    if doc is None:
        return f"{record} is unreadable"
    if doc.get("seal") != seal_of(doc):
        return f"{record} fails its seal (edited since it was written)"
    if config.root_custody and doc.get("root") in config.root_planned and not trusted:
        return f"the verdict for root {doc.get('root')!r} is not in the root-owned directory"
    return doc


def read_record(config: PlanConfig, planfile: Path) -> Json | str:
    """Find and judge the verdict record for a planfile's bytes.

    Returns:
        the record's document, or why none can be trusted.

    """
    try:
        digest = sha256_of(planfile)
    except OSError:
        return f"{planfile} is not readable"
    places: list[tuple[Path, bool]] = [(config.user_state, False)]
    if config.root_custody and config.root_state is not None:
        places.insert(0, (config.root_state, True))
    for state, trusted in places:
        record = verdict_path(state, digest)
        if record.is_file():
            return check_record(config, record, trusted=trusted)
    return f"no verdict for {planfile} (sha256 {digest[:12]}): it was never judged here"


def load_verdict(
    config: PlanConfig, planfile: Path, declarations: Mapping[str, str] | None = None
) -> Json | str:
    """Admit a planfile: its verdict must be a pass under the current policy.

    Returns:
        the admitted verdict, or the reason it is not admitted.

    """
    doc = read_record(config, planfile)
    if isinstance(doc, str):
        return doc
    if doc.get("exit") != 0:
        return f"{planfile} was not admitted (exit {doc.get('exit')})"
    if doc.get("policy_sha256") != policy_digest(config, declarations):
        return f"the policy changed since {planfile} was admitted; plan again"
    return doc
