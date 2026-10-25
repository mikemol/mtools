# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Read Commitment-shaped rows another extractor wrote, for one resolver and one ledger (W1986).

amr-skills classifies assistant sentences with an AMR model and writes JSON lines in this tool's
own row shape; a statement both extractors find must count ONCE, and a guess the classifier flags
as uncertain must never inflate the debt metric. The agreed row (github:W44, amr-skills
2026-10-25):

    {"line": int, "uuid": str, "session": str, "repo": str, "family": str, "text": str,
     "names": [str], "at": str, "uncertain": bool (optional), ...any other key is ignored}

⚑ ALL OR NOTHING, as the batch reader of mikemol-otlp is: a line that is not an object with these
typed fields refuses the whole file and says which line, so a half-read file never reads as a
whole one. A bool is not an int (`line`), and `names` holds strings only.

⚑ `text` IS CARRIED AS GIVEN, EMPTY INCLUDED. amr-skills keeps the sentences on its own machine by
design and sends an empty string; resolution reads only `names`, never `text`, so nothing here
ever tries to fill it.

⚑ ONE ROW PER (uuid, line). The first row seen is kept, every family that found the place is
recorded in the order seen, and the row is uncertain only when EVERY source that found it said
so: a firm source and an uncertain one agreeing is a firm commitment.

⚑ ROWS ARE PER REPOSITORY: only the rows whose `repo` is the one asked for are kept, because each
repository has its own queue to resolve against.

CONSUMED BY: the `--resolve` mode of `mikemol-transcriptstruct` (W1986).
"""

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import cast

from mikemol.transcriptstruct import commitledger
from mikemol.transcriptstruct.commitments import Commitment


@dataclass(frozen=True, slots=True)
class Incoming:
    """A commitment as read from a rows file, with who found it and whether they were unsure."""

    commitment: Commitment
    uncertain: bool
    families: tuple[str, ...]


def _row_of(line: str) -> tuple[Commitment, bool] | None:
    try:
        parsed: object = json.loads(line)
    except ValueError:
        return None
    if not isinstance(parsed, dict):
        return None
    row = cast("dict[str, object]", parsed)
    number, names = row.get("line"), row.get("names")
    words = [row.get(key) for key in ("uuid", "session", "repo", "family", "text", "at")]
    listed = cast("list[object]", names) if isinstance(names, list) else None
    unsure = row.get("uncertain", False)
    if type(number) is not int or listed is None or not isinstance(unsure, bool):
        return None
    if not all(isinstance(word, str) for word in words):
        return None
    if not all(isinstance(name, str) for name in listed):
        return None
    uuid, session, repo, family, text, at = (str(word) for word in words)
    found = Commitment(number, uuid, session, repo, family, text, tuple(map(str, listed)), at)
    return found, unsure


def read(lines: Iterable[str], repo: str) -> tuple[list[Incoming], str]:
    """Read the rows of one repository out of a rows file.

    Returns:
        the deduplicated rows in first-seen order and an empty string; no rows and the reason
        (naming the 1-based line) when a line is not a well-typed row.

    """
    kept: dict[tuple[str, int], tuple[Commitment, list[str], list[bool]]] = {}
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        got = _row_of(line)
        if got is None:
            return [], f"line {number} is not a commitment row"
        said, unsure = got
        if said.repo != repo:
            continue
        entry = kept.setdefault((said.uuid, said.line), (said, [], []))
        if said.family not in entry[1]:
            entry[1].append(said.family)
        entry[2].append(unsure)
    rows = [
        Incoming(first, all(votes), tuple(families)) for first, families, votes in kept.values()
    ]
    return rows, ""


def resolve(
    incoming: Sequence[Incoming], cards: Sequence[Mapping[str, object]]
) -> list[commitledger.LedgerRow]:
    """Resolve rows from a file against a queue, keeping who found them and how sure they were.

    Returns:
        one ledger row per incoming row, in order, with `uncertain` and `families` set.

    """
    resolved = commitledger.resolve([row.commitment for row in incoming], cards)
    return [
        replace(row, uncertain=found.uncertain, families=found.families)
        for row, found in zip(resolved, incoming, strict=True)
    ]
