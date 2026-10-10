# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The marks ledger: every admitted transition's verdict, persisted beside the queue (W852).

⚑⚑ A VERDICT IS A MARK, NOT ONLY A RETURN VALUE (the operator's stigmaturgy requirement, relayed by
the luthen host, 2026-10-08). Another session reads `<queue>.marks.jsonl` unasked: what was judged,
when, by which policy, over which input, and what residue it left. Nothing needs the writer's
session to be alive to resume from a mark.

One JSON object per line, append-only, kept apart from the prose `.ledger` so a reader parses no
text. A record is {as_of, op, symbol, policy_version, input_digest, verdict} for an add or update,
and {as_of, op, symbol, drop} for a drop (the waypoint is gone, so there is nothing to judge).
`policy_version` is the sha256 of the policy file that judged, and `input_digest` the sha256 of the
canonical input, so a mark can be re-derived and a stale one told from a current one.

⚑ THE WRITER STAMPS THE CLOCK, because Rego has none: `as_of` is the same `now` handed to the
policy as `input.now`, which keeps a verdict a pure function of its input.
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

from mikemol.pathsforward import opa_eval, ownership

if TYPE_CHECKING:
    from pathlib import Path

    from mikemol.pathsforward.model import Json

MARKS = ".marks.jsonl"


def policy_version() -> str:
    """Name the policy that judges, by the hash of its file.

    Returns:
        the sha256 hex digest of realizability.rego.

    """
    return hashlib.sha256(opa_eval.POLICY.read_bytes()).hexdigest()


def input_digest(item: Json) -> str:
    """Hash one policy input in its canonical form.

    Returns:
        the sha256 hex digest of the item with sorted keys and no spaces.

    """
    canonical = json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _symbol(item: Json) -> str:
    """Read the waypoint symbol out of a policy item.

    Returns:
        the symbol, or an empty string when the item carries none.

    """
    waypoint = item.get("waypoint")
    return str(waypoint.get("symbol", "")) if isinstance(waypoint, dict) else ""


def judged(op: str, now: str, item: Json, verdict: Json) -> Json:
    """Build the mark for a transition the policy judged.

    Returns:
        the record.

    """
    return {
        "as_of": now,
        "op": op,
        "symbol": _symbol(item),
        "policy_version": policy_version(),
        "input_digest": input_digest(item),
        "verdict": verdict,
    }


def dropped(now: str, symbol: str, gate: str, reference_arm: str, reason: str) -> Json:
    """Build the mark for a drop: the gate it died at, against which arm, and why.

    Returns:
        the record.

    """
    return {
        "as_of": now,
        "op": "drop",
        "symbol": symbol,
        "drop": {"gate": gate, "reference_arm": reference_arm, "reason": reason},
    }


def append(path: Path, record: Json) -> None:
    """Append one record as one line.

    ⚑ ONE WRITE PER RECORD, called under the queue's flock, so two writers never interleave a
    line and a crash loses at most the line being written.
    """
    line = json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n"
    with ownership.open_append(path) as marks:
        marks.write(line)
