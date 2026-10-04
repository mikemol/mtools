# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Project a per-project memory manifest from observed cgroup peaks (the LEARN step).

Ported from paperkit's `tools/mem_learn.py` (paperkit:W142), behaviour unchanged.

A reservation is resolved (in the bib generator) down a (project, resolution, claim) specificity
ladder; this module emits the per-project layer of that ladder. Each argument is a
`<claim>__{calc,dcalc}.peak` file holding one action's tree-peak RSS in bytes. The output (stdout)
is the project's manifest, DELTA-ENCODED against the next-coarser level:

    {"file": 256, "def": 1024, "claims": {"<claim>": <bucket>, ...}}

  - a resolution key (file/def) = pow2(max peak over that resolution's claims), the per-resolution
    default, recorded because it deviates from the cold-start floor;
  - "claims" holds an override ONLY for a claim whose own pow2 bucket differs from its resolution
    default.

Buckets are clamped to the pow2 levels the resource_set map provides. A peak of 0 (observe ran
without per-action cgroup isolation) is dropped: it carries no measurement. A peak file may say
WHY it has no number (`unavailable:absent`); those are counted separately on stderr, never folded
into a zero.

Usage:  python -m mikemol.memres.mem_learn <peak file> ...   (a library for mem_db and mem_harvest)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

type Manifest = dict[str, int | dict[str, int]]

# The pow2 reservation range. It starts TINY: an over-reservation is silent (idle cores), an
# under-reservation is LOUD (the cap kills, the failure names the cell, the next pass raises it).
LO = 4
HI = 4096
BYTES_PER_MB = 1024 * 1024
_UNAVAILABLE = "unavailable:"
_SHOWN = 4


def pow2(mb: float) -> int:
    """Round `mb` up to the next power of two, clamped to the range [LO, HI].

    Returns:
        The smallest power-of-two bucket from `LO` that holds `mb`, never above `HI`.

    """
    bucket = LO
    while mb > bucket and bucket < HI:
        bucket *= 2
    return bucket


def resolution(stem: str) -> tuple[str | None, str]:
    """Split a peak file's stem into (resolution, claim), or (None, stem) if it is not ours.

    A DEF-sweep cell is a pk_eval named `<claim>__<site>`, which matches neither calc suffix. Its
    peak is charged to the DEF resolution and to its claim, so the per-claim maximum over a
    claim's grid is that claim's def cost.

    Returns:
        `("def", claim)` for `__dcalc` and `<claim>__<site>` stems, `("file", claim)` for `__calc`,
        `(None, stem)` otherwise.

    """
    if stem.endswith("__dcalc"):
        return "def", stem[: -len("__dcalc")]
    if stem.endswith("__calc"):
        return "file", stem[: -len("__calc")]
    if "__" in stem:
        return "def", stem.split("__", 1)[0]
    return None, stem


def read_peaks(
    paths: Iterable[Path],
) -> tuple[dict[str, dict[str, float]], dict[str, list[str]]]:
    """Read peak files into per-resolution claim peaks (MB) and the unavailable reasons.

    A value of 0 or above `HI` MB is dropped: it is an un-isolated read (cgroups absent, or the
    SHARED cgroup of a non-observe build), and a dropped claim falls through the ladder to its
    resolution default, never to a wrong learned floor.

    Returns:
        `(peaks, unavailable)`: `peaks[resolution][claim]` in MB, and `unavailable[reason]` the
        claims whose file said `unavailable:<reason>`.

    """
    peaks: dict[str, dict[str, float]] = {}
    unavailable: dict[str, list[str]] = {}
    for path in paths:
        res, claim = resolution(path.stem)
        if res is None:
            continue
        raw = path.read_text(encoding="utf-8").strip()
        if raw.startswith(_UNAVAILABLE):
            unavailable.setdefault(raw.split(":", 1)[1], []).append(claim)
            continue
        mb = (int(raw) if raw.isdigit() else 0) / BYTES_PER_MB
        if mb <= 0 or mb > HI:
            continue
        peaks.setdefault(res, {})[claim] = mb
    return peaks, unavailable


def build_manifest(peaks: dict[str, dict[str, float]]) -> Manifest:
    """Delta-encode per-resolution claim peaks into the manifest.

    Returns:
        The manifest: one pow2 default per resolution and `claims` holding only the overrides.

    """
    defaults: dict[str, int] = {}
    claims: dict[str, int] = {}
    for res, by_claim in sorted(peaks.items()):
        default = pow2(max(by_claim.values()))
        defaults[res] = default
        for claim, mb in sorted(by_claim.items()):
            bucket = pow2(mb)
            if bucket != default:
                claims[claim] = bucket
    return {**defaults, "claims": claims}


def main(argv: Sequence[str] | None = None) -> int:
    """Print the manifest for the peak files named in `argv`; report unavailable ones on stderr.

    Returns:
        0 always.

    """
    args = sys.argv[1:] if argv is None else argv
    peaks, unavailable = read_peaks(Path(arg) for arg in args)
    for why, claims in sorted(unavailable.items()):
        shown = sorted(claims)[:_SHOWN]
        more = "..." if len(claims) > _SHOWN else ""
        sys.stderr.write(
            f"mem_learn: {len(claims)} claim(s) UNAVAILABLE ({why}) - not measured this run, "
            f"not a zero: {shown}{more}\n",
        )
    sys.stdout.write(json.dumps(build_manifest(peaks), indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
