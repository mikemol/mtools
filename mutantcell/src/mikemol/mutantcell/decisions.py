# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The DECISION-COVERAGE aggregator, the grid twin of paperkit's `grader.decisions_unasserted`.

Ported from paperkit's `tools/decisions.py` (paperkit:W142), behaviour unchanged. A claim's
reached-but-UNASSERTED decisions are conditions (and data values) the check runs both sides of yet
whose verdict is indifferent to which outcome selected: coverage the coarse behavioural grade
cannot see. An ORTHOGONAL axis, never a rung: it names a coverage gap, it does not lower a grade.

It consumes two pre-built cell sets, each a cell record `{site, flipped}`:

  --flips  the `flip:<qn>#<n>` cells (a NON-monotone condition inversion). flipped=True means
           inverting the condition flips the check red, i.e. the check ASSERTS on that decision.
  --reach  the raise-kind cells: `branch:<qn>#<n>` (arm reach) and `data-:<QN>#<n>` (key read).
           flipped=True means that arm or key is genuinely REACHED.

THE GRID GIVES SIBLING-INDEPENDENCE FOR FREE. Each cell is single-site, so a cell's `flipped` bit
IS a per-arm/per-key reach probe, with no group-testing correlation and so no re-probe.

Decision rules (mirroring `grader.decisions_unasserted`):

  flip:<qn>#<n>   UNASSERTED iff BOTH sibling `branch:<qn>` arms are reached AND the inversion does
                  NOT flip: both outcomes provably exercised, yet the verdict is indifferent.
                  Requiring BOTH arms rules out the "coincidentally invariant because the fixture
                  only takes one path" false positive.
  dflip:<QN>#<n>  its ONE sibling is the `data-:` DROP of the same (QN, n): UNASSERTED iff that
                  drop is reached AND the perturb does not flip (the key is read, its value is not
                  asserted).

Usage:  python -m mikemol.mutantcell.decisions --flips <rec>... --reach <rec>...
        python -m mikemol.mutantcell.decisions --summary <decisions-record>...
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Sequence

Record = dict[str, object]

_MIN_ARMS = 2  # a branch has two arms; both must be reached for the inversion to be informative


class _Parsed(argparse.Namespace):
    """The typed shape `argparse` fills in."""

    flips: list[str]
    reach: list[str]
    summary: list[str] | None


def _load(paths: Sequence[str]) -> list[Record]:
    """Read each path as one JSON record.

    Returns:
        The records, in order; a malformed one raises (the loud failure mode).

    """
    return [cast("Record", json.loads(Path(p).read_text(encoding="utf-8"))) for p in paths]


def _qn_n(site: str) -> tuple[str, str, str, int | None]:
    """Split `file::kind:qn#n` into its four parts.

    Returns:
        `(file, kind, qn, n)`; `n` is None when the `#` suffix is not a number.

    """
    file, _, spec = site.partition("::")
    kind, _, rest = spec.partition(":")
    qn, _, n = rest.rpartition("#")
    return file, kind, qn, (int(n) if n.isdigit() else None)


def decisions_unasserted(flips: Sequence[Record], reach: Sequence[Record]) -> list[str]:
    """Name the reached-but-unasserted decision labels.

    Returns:
        The sorted sites of `flips` that are unasserted by the rules in the module docstring.

    """
    # reach index: (file, kind, qn) -> {n: flipped}, so a flip can find its reached siblings.
    reached: dict[tuple[str, str, str], dict[int | None, bool]] = {}
    for r in reach:
        file, kind, qn, n = _qn_n(str(r["site"]))
        reached.setdefault((file, kind, qn), {})[n] = bool(r.get("flipped"))

    out: list[str] = []
    for fr in flips:
        site = str(fr["site"])
        file, kind, qn, n = _qn_n(site)
        if bool(fr.get("flipped")):
            continue  # the check ASSERTS on this decision: not a gap
        if kind == "flip":
            # a code condition: BOTH sibling branch arms must be genuinely reached.
            arms = reached.get((file, "branch", qn), {})
            if len(arms) >= _MIN_ARMS and all(arms.values()):
                out.append(site)
        elif kind == "dflip":
            # a data value: its ONE sibling is the data- DROP of the same (QN, n): the key is read.
            drop = reached.get((file, "data-", qn), {})
            if drop.get(n):
                out.append(site)
    return sorted(out)


def summarize(records: Sequence[Record]) -> Record:
    """Fold per-claim decision records into one project coverage summary.

    Each record is `{"decisions_unasserted": [labels]}`. `verdict: pass` means the AGGREGATION
    succeeded (every record well-formed), NOT that the count is zero: decision coverage is an
    orthogonal axis, so a nonzero count is REPORTED, never failed.

    Returns:
        The union of unasserted labels, sorted, and its size.

    """
    allu: list[str] = []
    for r in records:
        allu.extend(cast("list[str]", r.get("decisions_unasserted", [])))
    return {"verdict": "pass", "decisions_unasserted": sorted(set(allu)), "count": len(set(allu))}


def main(argv: Sequence[str] | None = None) -> int:
    """Print the unasserted decisions of a claim, or with `--summary` a project's summary.

    A MALFORMED record raises here (loud): the only failure mode. A high unasserted count is
    reported, never a build failure. The summary's JSON has no spaces after separators because
    `assert_pass.sh` greps `"verdict":"pass"`; a space would silently never match.

    Returns:
        0.

    """
    ap = argparse.ArgumentParser(description="decision-coverage aggregator")
    ap.add_argument("--flips", nargs="*", default=list[str]())
    ap.add_argument("--reach", nargs="*", default=list[str]())
    ap.add_argument(
        "--summary",
        nargs="*",
        default=None,
        help="fold per-claim decisions records into one project coverage summary",
    )
    a = ap.parse_args(sys.argv[1:] if argv is None else argv, namespace=_Parsed())
    if a.summary is not None:
        sys.stdout.write(json.dumps(summarize(_load(a.summary)), separators=(",", ":")) + "\n")
        return 0
    result: Record = {"decisions_unasserted": decisions_unasserted(_load(a.flips), _load(a.reach))}
    sys.stdout.write(json.dumps(result) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
