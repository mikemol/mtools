# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Aggregate per-(claim, site) cell records into the claim's SENSITIVITY set.

Ported from paperkit's `tools/sens.py` (paperkit:W142), behaviour unchanged. The sensitivity set
is the sites whose mutation flips the check. The fanout is the build graph (one `eval` cell per
site, parallel and cached) and this just READS the results.

VALIDITY WITNESS (`--baseline`): the empty-set mutation cell runs the UNMUTATED check in the very
same sandbox. It records `flipped: false` or the failure is in the HARNESS (the environment, the
delivery), not in any mutation, and every site would read as sensitive. The output carries
`baseline`, the unmutated check's verdict, so a reader grades a flipped baseline `broken` rather
than trusting its `sens`. The baseline is excluded from `sens` (the empty set is not a site).

Two guards fail LOUD rather than emit a plausible-but-wrong set:

* a NON-monotone cell (`::flip:` condition inversion, `::dflip:` data-value perturb) must NEVER
  enter the sensitivity set: it flips only if the witness asserts, so it is not a falsifiability
  signal. The generator partitions them to the decision-coverage grid; this FAILS if one reached
  here anyway (a partition regression);
* `attempted` records every site that was swept, not only the killed ones, because `sens` alone
  cannot tell a site that SURVIVED from one never swept. This is the dual guard against a
  silently SHORT sweep.

Usage:  python -m mikemol.mutantcell.sens --baseline <empty-set record> [record ...]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Sequence

_LEAK_EXIT = 1
_NON_MONOTONE = ("::flip:", "::dflip:")
# The ledger name of the partition rule. Its first letter is a Greek capital Mu, spelled by name
# because ruff refuses the literal glyph as ambiguous with the Latin M.
_LEAK_TAG = "\N{GREEK CAPITAL LETTER MU}\N{MIDDLE DOT}sweep\N{MIDDLE DOT}atom"


class _Parsed(argparse.Namespace):
    """The typed shape `argparse` fills in."""

    baseline: str
    evals: list[str]


def _load(path: str) -> dict[str, object]:
    """Read one cell record.

    Returns:
        The JSON object the file holds.

    """
    return cast("dict[str, object]", json.loads(Path(path).read_text(encoding="utf-8")))


def _non_monotone(records: list[dict[str, object]]) -> list[str]:
    """Name the sites of the records that are non-monotone cells.

    Returns:
        Each such record's site, in order.

    """
    sites = [str(r.get("site", "")) for r in records]
    return [s for s in sites if any(tag in s for tag in _NON_MONOTONE)]


def main(argv: Sequence[str] | None = None) -> int:
    """Fold the records into one `{claim, baseline, sens, attempted}` line on stdout.

    Returns:
        0 on success; 1, with the leaked sites named on stderr, when a non-monotone cell reached
        the sensitivity set.

    """
    ap = argparse.ArgumentParser(description="aggregate cell records into a sensitivity set")
    ap.add_argument(
        "--baseline",
        required=True,
        help="the empty-set mutation cell's record: its `flipped` MUST be false",
    )
    ap.add_argument("evals", nargs="*", help="the per-site cell records")
    a = ap.parse_args(sys.argv[1:] if argv is None else argv, namespace=_Parsed())

    base = _load(a.baseline)
    # The unmutated check passes iff the empty-set cell did not flip. A flipped baseline means
    # the check fails on the UNMUTATED engine (broken harness or broken claim); every site then
    # reads sensitive, but baseline=false signals that the sens is not to be trusted.
    baseline = not base.get("flipped")
    records = [_load(f) for f in a.evals]
    leaked = _non_monotone(records)
    if leaked:
        sys.stderr.write(
            f"{_LEAK_TAG}: NON-monotone cell(s) reached pk_sens \N{EM DASH} "
            f"the partition leaked: {leaked}\n"
        )
        return _LEAK_EXIT
    sens = [str(r["site"]) for r in records if r["flipped"]]
    attempted = [str(r["site"]) for r in records]
    line = {
        "claim": base["claim"],
        "baseline": baseline,
        "sens": sorted(sens),
        "attempted": sorted(attempted),
    }
    sys.stdout.write(json.dumps(line) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
