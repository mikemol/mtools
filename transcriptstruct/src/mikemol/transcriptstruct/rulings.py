# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Stage 9: the rulings ledger, append-only, incremental by record, across every transcript.

mtools:W1401 (append) and W1402 (walk). ⚑⚑ A RULING MUST SURVIVE THE SESSION THAT HEARD IT
(operator, 2026-10-16: "this is why we mechanize"). The harvest stage turns each operator utterance
into one PROV-O entity; this stage keeps them: one JSON line per entity in a ledger file that is
only ever appended to, so a line written once is never rewritten and a reader can trust history.

⚑ INCREMENTAL BY THE ENTITY'S OWN IRI (`file#uuid`): a line already in the ledger is not written
again, so harvesting the same transcript twice adds nothing, and a transcript that grew adds only
its new lines. The ledger is the single source of "already harvested"; no second index can drift
from it.

⚑ A FILE UNCHANGED SINCE ITS LAST HARVEST IS NOT READ AGAIN. The tree is hundreds of megabytes of
transcripts, so a (size, mtime) record per file, kept beside the ledger, spares the walk. That
record is only a speed-up: deleting it costs a slow run and loses nothing, because the ledger's
IRIs still refuse a duplicate. Links are never followed and never read.
"""

import json
import os
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from mikemol.transcriptstruct.harvest import harvest
from mikemol.transcriptstruct.records import read_path

SEEN_SUFFIX = ".seen"


@dataclass(frozen=True, slots=True)
class Summary:
    """What one walk did: files read, files spared, lines appended, human lines uncitable."""

    read: int
    spared: int
    added: int
    uncitable: int


def known(ledger: Path) -> set[str]:
    """Read the IRIs already in the ledger.

    Returns:
        every `@id` of a line; empty when the ledger does not exist yet.

    """
    if not ledger.is_file():
        return set()
    ids: set[str] = set()
    for line in ledger.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entity = cast("dict[str, object]", json.loads(line))
            ids.add(str(entity["@id"]))
    return ids


def append(
    ledger: Path, entities: Iterable[dict[str, object]], held: set[str] | None = None
) -> int:
    """Append the entities the ledger does not hold, one JSON line each, never rewriting a line.

    `held` is the set of IRIs already known, kept up to date by this call, so a walk over many
    transcripts reads the ledger once instead of once per file.

    Returns:
        how many lines were written.

    """
    ids = known(ledger) if held is None else held
    fresh = [e for e in entities if str(e["@id"]) not in ids]
    ids.update(str(e["@id"]) for e in fresh)
    if fresh:
        ledger.parent.mkdir(parents=True, exist_ok=True)
        with ledger.open("a", encoding="utf-8") as sink:
            sink.writelines(json.dumps(e, ensure_ascii=False) + "\n" for e in fresh)
    return len(fresh)


def transcripts(root: Path) -> list[Path]:
    """List every transcript under `root`, links neither followed nor listed.

    Returns:
        the `.jsonl` files in path order.

    """
    found: list[Path] = []
    for here, _dirs, names in os.walk(root, followlinks=False):
        for name in names:
            path = Path(here) / name
            if name.endswith(".jsonl") and not path.is_symlink():
                found.append(path)
    return sorted(found)


def _stamp(path: Path) -> list[int]:
    info = path.stat()
    return [info.st_size, info.st_mtime_ns]


def _load_seen(ledger: Path) -> dict[str, list[int]]:
    seen = ledger.with_name(ledger.name + SEEN_SUFFIX)
    if not seen.is_file():
        return {}
    try:
        return cast("dict[str, list[int]]", json.loads(seen.read_text(encoding="utf-8")))
    except ValueError:
        return {}


def harvest_tree(root: Path, ledger: Path, scheduled: Sequence[str] = ()) -> Summary:
    """Harvest every changed transcript under `root` into the ledger.

    Returns:
        the counts; a file whose (size, mtime) matches its last harvest is spared.

    """
    seen = _load_seen(ledger)
    held = known(ledger)
    read = spared = added = uncitable = 0
    for path in transcripts(root):
        stamp = _stamp(path)
        if seen.get(str(path)) == stamp:
            spared += 1
            continue
        found = harvest(read_path(path), path, scheduled)
        added += append(ledger, found.entities, held)
        uncitable += found.uncitable
        seen[str(path)] = stamp
        read += 1
    ledger.with_name(ledger.name + SEEN_SUFFIX).write_text(json.dumps(seen), encoding="utf-8")
    return Summary(read, spared, added, uncitable)
