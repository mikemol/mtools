# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Judge the files a built sdist or wheel actually SHIPS, through the Rego sets (W1148, W1144).

    OPA_BIN=<opa> mikemol-privacy-shipped ARTIFACT...

The tree audit (`mikemol-privacy-audit`) reads everything git tracks, and most of what it flags
never leaves the repository: tests, fixtures and notes. What PyPI publishes is what the sdist and
the wheel CARRY, so this reads each artifact's member files and judges them with the same
`publish_privacy.findings` rule, one evaluation per artifact. A finding is `{"kind", "rule",
"path", "line"}` with `path` as `ARTIFACT/MEMBER`, never the matched text; a summary line follows
each artifact. The exit is 1 if any artifact has a deny OR a withheld finding the policy has not
accepted (W1198): a placeholder a person has read is listed in `publish_privacy.rego` with its
reason and marked `"accepted": true`, and the rest must be fixed.

⚑ THE ARTIFACTS ARE THE ONES `mikemol-wheel release-check` BUILDS from a pinned sha, so this judges
the bytes that would be uploaded and not a working tree that may differ from them.

⚑ A MEMBER THAT IS NOT A REGULAR FILE (a link in a tar) IS SKIPPED, NOT FOLLOWED, and a member with
a NUL in its first 8 KiB is counted as skipped, not decoded.

CONSUMED BY: the publish preflight (W1150).
"""

from __future__ import annotations

import json
import os
import sys
import tarfile
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.hooks import privacy_audit

if TYPE_CHECKING:
    from collections.abc import Sequence

Finding = privacy_audit.Finding


def entry_of(name: str, raw: bytes) -> tuple[Finding, bool]:
    """Turn one member's bytes into an entry of the bulk rule.

    Returns:
        the entry, and whether it was skipped as binary (its lines are then empty).

    """
    if b"\0" in raw[: privacy_audit.SNIFF]:
        return {"path": name, "lines": []}, True
    return {"path": name, "lines": raw.decode("utf-8", "replace").splitlines()}, False


def members_of(artifact: Path) -> tuple[list[Finding], int]:
    """Read every regular member of an sdist (`.tar.gz`) or a wheel (`.whl`, a zip).

    Returns:
        the entries, with paths as `ARTIFACT/MEMBER`, and the number skipped.

    """
    entries: list[Finding] = []
    skipped = 0
    if artifact.name.endswith(".tar.gz"):
        with tarfile.open(artifact) as archive:
            for member in archive.getmembers():
                handle = archive.extractfile(member) if member.isfile() else None
                if handle is None:
                    skipped += 1
                    continue
                entry, binary = entry_of(f"{artifact.name}/{member.name}", handle.read())
                entries.append(entry)
                skipped += int(binary)
        return entries, skipped
    with zipfile.ZipFile(artifact) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            entry, binary = entry_of(f"{artifact.name}/{info.filename}", archive.read(info))
            entries.append(entry)
            skipped += int(binary)
    return entries, skipped


def run(args: Sequence[str]) -> int:
    """Run `ARTIFACT...`: findings and a summary per artifact; exit 1 if any has a deny.

    Returns:
        0 when no artifact has a deny, 1 when one does, 2 for a usage error or a missing judge.

    """
    opa = os.environ.get("OPA_BIN", "")
    if not args or not opa:
        sys.stderr.write("usage: OPA_BIN=<opa> mikemol-privacy-shipped ARTIFACT...\n")
        return 2
    total = 0
    for name in args:
        files, skipped = members_of(Path(name))
        findings = privacy_audit.judge(opa, privacy_audit.POLICY, files)
        sys.stdout.writelines(json.dumps(f, sort_keys=True) + "\n" for f in findings)
        denies = sum(1 for f in findings if f["kind"] == "deny")
        unaccepted = sum(1 for f in findings if f["kind"] == "withheld" and "accepted" not in f)
        summary: Finding = {
            "artifact": Path(name).name,
            "files": len(files),
            "skipped": skipped,
            "deny": denies,
            "withheld": len(findings) - denies,
            "unaccepted": unaccepted,
        }
        sys.stdout.write(json.dumps(summary, sort_keys=True) + "\n")
        total += denies + unaccepted
    return 1 if total else 0


def main() -> None:
    """Console entry: exit with `run`'s status."""
    sys.exit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()
