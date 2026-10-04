# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Sample a cgroup's memory and zswap counters in ONE pass.

Ported from paperkit's `tools/zswap_probe.py` (paperkit:W142). Behaviour unchanged; the cgroup
file and the cgroup root are parameters so a test can plant a fake host, and the pinned
predicate that `sample` and the selftest each carried a copy of is one function, `pinned`.

Why one pass: cross-surface equality between counters holds at rest and FAILS live under reclaim,
because separate samples skew. An exact comparison between counters is a claim about an idle box,
so read the pair together and treat the ratio as an observation, not an identity.

Emits one JSON object for the caller's OWN cgroup (the leaf of a Bazel action):

    current      memory.current              bytes charged NOW
    peak         memory.peak                 high-water (per-fd semantics)
    zswap        memory.stat `zswap`         bytes CONSUMED BY THE BACKEND (compressed)
    zswapped     memory.stat `zswapped`      bytes of APPLICATION memory swapped out
    zswap_max    memory.zswap.max            the pool ceiling, or "max"

`zswap` and `zswapped` are DIFFERENT UNITS and their pair gives the compression ratio directly.
A page moved to zswap is re-charged at its COMPRESSED size, so memory.current FALLS as pages
compress, and two workloads with identical RSS report different peaks. Scope: measured against
linux-source 7.0.0-30.30; these are claims about THAT pin.

    INSTRUMENT, NOT A GATE. Nothing in paperkit runs this; re-verify its output at each use.

    python -m mikemol.memres.zswap_probe [--selftest]
"""

from __future__ import annotations

import json
import sys
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence

type Reading = str | dict[str, str]

CGROUP_FILE = Path("/proc/self/cgroup")
CGROUP_ROOT = Path("/sys/fs/cgroup")
_PAGE = 4096
_TOL_ABS = _PAGE * 64
_TOL_REL = 100
_RATIO_DIGITS = 3
_NO_BOUND = "unbounded-to-root"
_BILLION = 10**9

# A sample mixes TWO KINDS of reading and a later reader must not take the row as one kind.
# current/zswap/zswapped are INSTANTANEOUS; peak is CUMULATIVE since cgroup creation on a
# never-written fd, so on a long-lived cgroup it spans unrelated history. Labelled per FIELD.
_VALIDITY = {
    "current": "instantaneous",
    "zswap": "instantaneous",
    "zswapped": "instantaneous",
    "zswap_max": "config",
    "peak": "cumulative-since-cgroup-creation",
}


def cg_dir(cgroup_file: Path = CGROUP_FILE, root: Path = CGROUP_ROOT) -> Path:
    """Locate the caller's own cgroup directory from its `/proc/self/cgroup`.

    Returns:
        `root` joined with the path after the last `::` of `cgroup_file`.

    """
    rel = cgroup_file.read_text(encoding="utf-8").strip().split("::")[-1]
    return root / rel.lstrip("/")


def read(d: Path, name: str) -> Reading:
    """Read one cgroup file: its value, or an UNAVAILABLE reason, never a 0 for a failed read.

    Returns:
        The stripped text; `{"unavailable": "absent"}` when the file does not exist;
        `{"unavailable": "unreadable:<errno>"}` when reading it fails.

    """
    path = d / name
    if not path.exists():
        return {"unavailable": "absent"}
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError as err:
        return {"unavailable": f"unreadable:{err.errno}"}


def stat_keys(d: Path, keys: Iterable[str]) -> dict[str, int | dict[str, str]]:
    """Pick integer keys out of `memory.stat`.

    Returns:
        Each key's value; `{"unavailable": "key-absent"}` for a missing key; the file's own
        unavailable reason for every key when `memory.stat` cannot be read.

    """
    raw = read(d, "memory.stat")
    if isinstance(raw, dict):
        return dict.fromkeys(keys, raw)
    got = dict(line.split(" ", 1) for line in raw.splitlines() if " " in line)
    return {key: (int(got[key]) if key in got else {"unavailable": "key-absent"}) for key in keys}


def zswap_bound(leaf: Path, root: Path = CGROUP_ROOT) -> dict[str, object]:
    """Walk the EFFECTIVE zswap ceiling from `leaf` up to `root`.

    A zswap store is refused if ANY ancestor is at its zswap_max, so a parent's bound binds a
    child whose own file still reads "max". Reading only the leaf can report an unbounded pool
    while the pool is in fact bound one level up. The walk also stops at a directory that is its
    own parent, so a leaf outside `root` cannot loop forever.

    Returns:
        `effective_bound_at` (the nearest bounded cgroup, or `unbounded-to-root`) and `levels`
        (each cgroup's `zswap_max` and `zswap_current`, leaf first).

    """
    levels: list[dict[str, object]] = []
    binding: str | None = None
    d = leaf
    while True:
        value = read(d, "memory.zswap.max")
        levels.append(
            {
                "cgroup": str(d),
                "zswap_max": value,
                "zswap_current": read(d, "memory.zswap.current"),
            },
        )
        if isinstance(value, str) and value != "max" and binding is None:
            binding = str(d)
        if d in {root, d.parent}:
            break
        d = d.parent
    return {"effective_bound_at": binding or _NO_BOUND, "levels": levels}


def pinned(
    cur: str,
    mx: str,
    *,
    tol_rel: int = _TOL_REL,
    tol_abs: int = _TOL_ABS,
    flip: bool = False,
) -> bool:
    """Say whether a charge sits at its ceiling, within a small tolerance.

    The charge sits a few pages under max while reclaim keeps it there, so exact equality would
    miss the pinned case this exists to catch. `flip` swaps the sign of the gap; it exists for
    the selftest's mutants.

    Returns:
        True when `max > 0` and the gap `max - current` is at most the larger of `max / tol_rel`
        and `tol_abs`.

    """
    charge, ceiling = int(cur), int(mx)
    gap = (charge - ceiling) if flip else (ceiling - charge)
    return ceiling > 0 and gap <= max(ceiling // tol_rel, tol_abs)


def _pinned_reading(cur: object, mx: Reading) -> bool | None:
    """Decide the pinned bit of a sample: THE bit that makes a peak attributable.

    memory.current PINS AT memory.max under pressure while real demand keeps growing, so a
    reading taken while pinned says what the cell was GIVEN, not what it NEEDED.

    Returns:
        `pinned(cur, mx)` when both are digit strings; None otherwise.

    """
    if isinstance(cur, str) and cur.isdigit() and isinstance(mx, str) and mx.isdigit():
        return pinned(cur, mx)
    return None


def _conditions(d: Path) -> dict[str, object]:
    """Record WHICH SETTINGS WERE IN EFFECT beside the number.

    A reading carries the conditions that decide whether it is a measurement or an artifact:
    `swap_max` 0 means zswap can never be exercised here.

    Returns:
        `swap_max`, `own_cgroup` and `cgroup_is_leaf` (None when `d` is not a directory).

    """
    return {
        "swap_max": read(d, "memory.swap.max"),
        "own_cgroup": not str(d).endswith(".scope") or "sandbox" in str(d) or "run-p" in str(d),
        "cgroup_is_leaf": (
            not any(x.is_dir() and (x / "cgroup.procs").exists() for x in d.iterdir())
            if d.is_dir()
            else None
        ),
    }


def sample(
    cgroup_file: Path = CGROUP_FILE,
    root: Path = CGROUP_ROOT,
) -> dict[str, object]:
    """Sample the caller's cgroup in one pass: stat first, then the single-value files.

    A wider window is a bigger skew under reclaim. `ratio_means` travels with the ratio because
    its meaning depends on whether the pool binds: unbounded it is compressibility, bounded it
    is eviction churn.

    Returns:
        The reading: `cgroup`, `is_root`, `current`, `peak`, `zswap_max`, `zswap`, `zswapped`,
        `compression_ratio` and `ratio_means` (only when `zswap` is positive), `memory_max`,
        `pinned_at_ceiling`, `_conditions`, `hierarchy` and `_validity`.

    """
    d = cg_dir(cgroup_file, root)
    stat = stat_keys(d, ("zswap", "zswapped"))
    out: dict[str, object] = {
        "cgroup": str(d),
        "is_root": d == root,
        "current": read(d, "memory.current"),
        "peak": read(d, "memory.peak"),
        "zswap_max": read(d, "memory.zswap.max"),
        **stat,
    }
    zswap, zswapped = stat["zswap"], stat["zswapped"]
    if isinstance(zswap, int) and isinstance(zswapped, int) and zswap > 0:
        out["compression_ratio"] = round(zswapped / zswap, _RATIO_DIGITS)
    memory_max = read(d, "memory.max")
    out["memory_max"] = memory_max
    out["pinned_at_ceiling"] = _pinned_reading(out["current"], memory_max)
    hierarchy = zswap_bound(d, root)
    if "compression_ratio" in out:
        out["ratio_means"] = (
            "compressibility"
            if hierarchy["effective_bound_at"] == _NO_BOUND
            else "eviction-churn-under-bound"
        )
    out["_conditions"] = _conditions(d)
    out["hierarchy"] = hierarchy
    out["_validity"] = {
        **_VALIDITY,
        "memory_max": "config",
        "pinned_at_ceiling": "derived",
        "ratio_means": "derived",
    }
    return out


def _separates(predicate: Callable[[str, str], bool]) -> bool:
    """Ask whether a pinned predicate separates a saturated pair from an unsaturated one.

    Returns:
        True when the saturated pair reads pinned AND the unsaturated pair does not.

    """
    saturated = ("402632704", "402653184")
    unsaturated = ("100000000", "402653184")
    return predicate(*saturated) and not predicate(*unsaturated)


def _selftest() -> int:
    """Run the P and F arms over the PINNED predicate, with VALID mutants only.

    The trap: mutating the ceiling so the cgroup becomes genuinely pinned is an INVALID mutant,
    the field flipping is the predicate being RIGHT. A valid mutant leaves the world untouched and
    corrupts the COMPARISON, then asks whether the witness notices.

    P: intact, a saturated pair reads pinned and an unsaturated pair does not.
    F: sign-swapped gap / tolerance widened to 1GB / tolerance driven to 0 each destroy the
       separation, and the requirement (saturated AND NOT unsaturated) catches all three.

    Returns:
        0 when the P arm holds and every mutant is caught; 1 otherwise.

    """
    fails: list[str] = []
    if not _separates(pinned):
        fails.append("P: intact predicate does not separate saturated from unsaturated")
    mutants: tuple[tuple[str, Callable[[str, str], bool]], ...] = (
        ("sign-swapped gap", partial(pinned, flip=True)),
        ("tolerance widened to 1GB", partial(pinned, tol_abs=_BILLION)),
        ("tolerance driven to 0", partial(pinned, tol_abs=0, tol_rel=_BILLION)),
    )
    fails.extend(
        f"F: mutant '{name}' SURVIVED - the predicate is not reading the gap"
        for name, predicate in mutants
        if _separates(predicate)
    )
    for fail in fails:
        sys.stderr.write(f"  XX {fail}\n")
    verdict = "PASS (1 P-arm, 3 valid mutants caught)" if not fails else f"FAIL ({len(fails)})"
    sys.stdout.write(f"ZSWAP_PROBE SELFTEST: {verdict}\n")
    return 1 if fails else 0


def main(
    argv: Sequence[str] | None = None,
    cgroup_file: Path = CGROUP_FILE,
    root: Path = CGROUP_ROOT,
) -> int:
    """Print one sample of the caller's cgroup as JSON, or with `--selftest` run the selftest.

    Returns:
        0 for a sample, or for a passing selftest; 1 for a failing selftest.

    """
    args = sys.argv[1:] if argv is None else argv
    if "--selftest" in args:
        return _selftest()
    sys.stdout.write(json.dumps(sample(cgroup_file, root), indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
