# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Ship the commitments ledger as gauges (W1933, github:W44).

    mikemol-commitments-emit LEDGER

LEDGER is the output of `mikemol-transcriptstruct LOG --commitments --queue QUEUE`: one JSON
document {as_of, rows: [...]} and then comment lines, which are skipped. The contract fixed on
2026-10-24 (sent to nemik-84, luthen-observability-ab and github-8f):

 - `mikemol.commitments.open{repo,layer}`: the rows still counted, by layer. A row is counted while
   its follow-through is none, memory or instructions (a recurring class resolved only in prose is
   a coverability residue, luthen-observability:W1599); a sum over `layer` is the repository's
   open count.
 - `mikemol.commitments.said{repo}`: the statements made. The statement is the sensor and is never
   penalised, so this series only counts what was said.

⚑ ALL THREE COUNTED LAYERS ARE SENT FOR EVERY REPOSITORY, ZEROS INCLUDED. A series that disappears
when its last row resolves reads as no data, not as debt paid down; a zero is the paydown.

⚑ THE COUNTED LAYERS ARE NAMED HERE AS THE CONTRACT NAMES THEM, not imported: this distribution
does not depend on the transcript one (`commitledger.COUNTED` is the same three).

⚑ BEST EFFORT, as every send here: no binary or store, a failed spawn or an unreadable ledger
changes nothing and the exit is still 0.
"""

import json
import os
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from mikemol.hooks.ratchet_emit import Row, Spawn, emit
from mikemol.hooks.vlogdetach import spawn_with_stdin

OPEN = "mikemol.commitments.open"
SAID = "mikemol.commitments.said"
NAMESPACE = "commitments"
COUNTED = ("none", "memory", "instructions")
EXIT_USAGE = 2
ARGUMENTS = 1


def _rows_in(document: object) -> list[dict[str, object]]:
    if not isinstance(document, dict):
        return []
    listed = cast("dict[str, object]", document).get("rows")
    items = cast("list[object]", listed) if isinstance(listed, list) else []
    return [cast("dict[str, object]", item) for item in items if isinstance(item, dict)]


def ledger_rows(text: str) -> list[dict[str, object]]:
    """Read the ledger document out of the mode's output.

    Returns:
        the document's rows; empty when there is no readable document.

    """
    for line in text.splitlines():
        if not line.startswith("{"):
            continue
        try:
            document: object = json.loads(line)
        except ValueError:
            return []
        return _rows_in(document)
    return []


def rows_of(ledger: Sequence[dict[str, object]], now_ns: int) -> list[Row]:
    """Turn ledger rows into the contract's gauges.

    Returns:
        for each repository, one `said` row and one `open` row per counted layer (zeros included).

    """
    said: dict[str, int] = {}
    held: dict[str, dict[str, int]] = {}
    for row in ledger:
        repo = str(row.get("repo", ""))
        said[repo] = said.get(repo, 0) + 1
        blank: dict[str, int] = dict.fromkeys(COUNTED, 0)
        layers = held.setdefault(repo, blank)
        layer = str(row.get("layer", ""))
        if layer in layers:
            layers[layer] += 1
    rows: list[Row] = []
    for repo, count in said.items():
        rows.append({"name": SAID, "value": count, "time_ns": now_ns, "fields": {"repo": repo}})
        for layer in COUNTED:
            fields = {"repo": repo, "layer": layer}
            value = held[repo][layer]
            rows.append({"name": OPEN, "value": value, "time_ns": now_ns, "fields": fields})
    return rows


def main(argv: Sequence[str] | None = None, spawn: Spawn = spawn_with_stdin) -> int:
    """Read one ledger output file and ship its gauges.

    Returns:
        0 once the arguments are right (a send that cannot start changes nothing); 2 with usage.

    """
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != ARGUMENTS:
        sys.stderr.write("usage: mikemol-commitments-emit LEDGER\n")
        return EXIT_USAGE
    try:
        text = Path(args[0]).read_text(encoding="utf-8")
    except OSError:
        sys.stdout.write("commitments emit: the ledger is unreadable; nothing sent\n")
        return 0
    rows = rows_of(ledger_rows(text), time.time_ns())
    sent = emit(rows, os.environ, spawn, NAMESPACE)
    sys.stdout.write(f"commitments emit: {len(rows)} row(s), sent={sent}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
