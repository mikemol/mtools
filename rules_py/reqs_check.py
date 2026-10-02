# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Check one distribution's requirements.txt pins agree with its uv.lock (W233).

Bazel's `_deps` hub reads requirements.txt while the host venv and the `_dev` hub read uv.lock, so
the two resolvers drift silently unless something compares them (operator 2026-09-28: they must be
kept in sync). W232 measured the drift by hand once (hooks' ast-serialize, 0.9.0 against 0.11.1);
this is that measurement as a check each distribution runs over its own tree.

    reqs_check.py DIST_DIR

Exit 0 when every pin agrees; 1 with one line per finding otherwise; 2 on a usage error.
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

_USAGE = "usage: reqs_check.py DIST_DIR"
_PIN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s;\\]+)")
_NAME = re.compile(r'^name = "([^"]+)"$')
_VERSION = re.compile(r'^version = "([^"]+)"$')


def norm(name: str) -> str:
    """PEP 503 normalize a distribution name.

    Returns:
        the normalized name.

    """
    return re.sub(r"[-_.]+", "-", name).lower()


def pins(text: str) -> dict[str, str]:
    """Read the `name==version` pins of a compiled requirements file.

    Returns:
        normalized name -> pinned version.

    """
    out: dict[str, str] = {}
    for line in text.splitlines():
        match = _PIN.match(line)
        if match:
            out[norm(match.group(1))] = match.group(2)
    return out


def locked(text: str) -> dict[str, str]:
    """Read every package version a uv.lock records.

    The TOML is parsed first, so a malformed lock raises rather than reading as empty. The values
    are then read per `[[package]]` table from the text, because strict mypy reads every value
    `tomllib` returns as `Any`; uv writes `name` and `version` as the first plain lines of each.

    Returns:
        normalized name -> locked version.

    """
    tomllib.loads(text)
    out: dict[str, str] = {}
    for block in text.split("[[package]]")[1:]:
        name = version = ""
        for line in block.splitlines():
            if line.startswith("["):
                break
            name_match, version_match = _NAME.match(line), _VERSION.match(line)
            if name_match and not name:
                name = name_match.group(1)
            if version_match and not version:
                version = version_match.group(1)
        if name and version:
            out[norm(name)] = version
    return out


def check(dist: Path) -> list[str]:
    """Compare every requirements.txt pin with the same package in uv.lock.

    A lock that records no package at all is a finding, never a vacuous pass: every uv.lock holds
    at least the distribution itself, so an empty read means the comparison never ran.

    Returns:
        one finding per missing file, disagreeing pin, or pin the lock does not carry.

    """
    req, lock = dist / "requirements.txt", dist / "uv.lock"
    missing = [f"{p}: missing; no pin can be compared" for p in (req, lock) if not p.is_file()]
    if missing:
        return missing
    have = locked(lock.read_text(encoding="utf-8"))
    if not have:
        return [f"{lock}: records no package; the comparison would be vacuous"]
    findings = []
    for name, version in sorted(pins(req.read_text(encoding="utf-8")).items()):
        if name not in have:
            findings.append(f"{req}: {name}=={version} is absent from uv.lock")
        elif have[name] != version:
            findings.append(f"{req}: {name}=={version} but uv.lock has {have[name]}")
    return findings


def main(argv: list[str]) -> int:
    """Check the distribution named on the command line.

    Returns:
        0 when every pin agrees, 1 on findings, 2 on a usage error.

    """
    if len(argv) != 1:
        sys.stderr.write(_USAGE + "\n")
        return 2
    findings = check(Path(argv[0]))
    for finding in findings:
        sys.stderr.write(finding + "\n")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
