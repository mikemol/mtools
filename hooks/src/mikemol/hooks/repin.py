# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The pure core of `mikemol-repin`: find an adopter's mtools pins, and rewrite their sha.

mtools:W957. An adopting repo names an mtools distribution at a commit in one of three shapes, all
measured in the fleet's pyprojects: a PEP 508 line (`mikemol-x @ git+https://github.com/mikemol/
mtools.git@SHA#subdirectory=x`), a uv source table (`{ git = "...", subdirectory = "x", rev =
"SHA" }`), and a vendored wheel (`vendor/wheels/mikemol_x-0.1.0+gSHA-py3-none-any.whl`).

⚑ A VENDORED WHEEL IS REPORTED AND NEVER REWRITTEN. Its sha is part of a file name beside a binary
that was built from that commit; changing the name without rebuilding the wheel would make the pin
a false statement about the bytes, which is worse than a stale pin. The survey names it so the
person re-vendors it.

⚑ ONE SHA, MANY DISTS (mtools INSTALL.md): two specs of one repo at different commits may resolve to
two copies of the shared namespace, so a rewrite moves every selected pin together.

CONSUMED BY: the `mikemol-repin` shell (W958).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_GIT = r"https://github\.com/mikemol/mtools(?:\.git)?"
_SHA = r"[0-9a-f]{7,40}"
_PEP508 = re.compile(rf"(?P<head>{_GIT})@(?P<sha>{_SHA})#subdirectory=(?P<dist>[A-Za-z0-9_]+)")
_SOURCE = re.compile(
    rf'(?P<head>git\s*=\s*"{_GIT}"\s*,\s*subdirectory\s*=\s*"(?P<dist>[A-Za-z0-9_]+)"\s*,\s*'
    rf'rev\s*=\s*")(?P<sha>{_SHA})(?P<tail>")'
)
_WHEEL = re.compile(rf"vendor/wheels/mikemol_(?P<dist>[a-z0-9]+)-[0-9.]+\+g(?P<sha>{_SHA})-")
_FULL = re.compile(r"[0-9a-f]{40}")

PEP508 = "pep508"
SOURCE = "uv-source"
WHEEL = "wheel"


@dataclass(frozen=True)
class Pin:
    """One pin: the distribution, the commit it names and the shape it was written in."""

    dist: str
    sha: str
    form: str


def check_sha(sha: str) -> None:
    """Refuse a target that is not a full lowercase 40-hex commit.

    Raises:
        ValueError: when `sha` is anything else; a short or branch-like target would rewrite every
            pin to a name that does not pin.

    """
    if _FULL.fullmatch(sha) is None:
        msg = f"target {sha!r} must be a full 40-character lowercase hex commit"
        raise ValueError(msg)


def same(pinned: str, target: str) -> bool:
    """Say whether a pinned sha (possibly abbreviated) names the target commit.

    Returns:
        True when one is a prefix of the other.

    """
    return target.startswith(pinned) or pinned.startswith(target)


def find(text: str) -> tuple[Pin, ...]:
    """List every mtools pin in a pyproject's text, in file order.

    Returns:
        one Pin per match of the three shapes.

    """
    found = [
        (m.start(), str(m.group("dist")), str(m.group("sha")), form)
        for pattern, form in ((_PEP508, PEP508), (_SOURCE, SOURCE), (_WHEEL, WHEEL))
        for m in pattern.finditer(text)
    ]
    return tuple(Pin(dist, sha, form) for _start, dist, sha, form in sorted(found))


def rewrite(
    text: str, sha: str, dists: frozenset[str] | None = None
) -> tuple[str, tuple[str, ...]]:
    """Move the git pins (not the vendored wheels) to `sha`, for the chosen dists or all.

    Returns:
        the new text and the dists whose pin actually changed (PEP 508 pins first, then sources).

    """
    check_sha(sha)
    changed: list[str] = []

    def chosen(dist: str, pinned: str) -> bool:
        wanted = dists is None or dist in dists
        if wanted and pinned != sha:
            changed.append(dist)
        return wanted

    def pep508(m: re.Match[str]) -> str:
        if not chosen(str(m.group("dist")), str(m.group("sha"))):
            return m.group(0)
        return f"{m.group('head')}@{sha}#subdirectory={m.group('dist')}"

    def source(m: re.Match[str]) -> str:
        if not chosen(str(m.group("dist")), str(m.group("sha"))):
            return m.group(0)
        return f"{m.group('head')}{sha}{m.group('tail')}"

    return _SOURCE.sub(source, _PEP508.sub(pep508, text)), tuple(changed)
