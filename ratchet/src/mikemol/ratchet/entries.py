# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The entries a ratchet file holds, one record each, so a codemod can work them (W2306).

The census (`kinds.value_of`) says HOW MANY entries a file records; this says WHICH. The count is
the contract: for every file the census reads, the number of entries listed here equals its value,
because a list that disagreed with the census would pay down debt the census still counts.

⚑ AN ENTRY'S KEY IS ITS IDENTITY IN THE FILE. A JSON file is read by its leaves exactly as the
census reads them (a scalar is one entry, an empty string and false are none), and the key is the
path of object keys and list positions down to the leaf, joined with `/`. In a `file -> rule ->
count` baseline the first two keys are also given as `file` and `rule`. A text file's key is the
line itself; a `.tsv` file's header line is not an entry. A file that cannot be read has no list,
never an empty one: None, the same UNREAD the census answers.
"""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import NamedTuple, cast

_SEP = "/"
_FILE_AND_RULE = 2
_SCALARS: frozenset[type] = frozenset({str, int, float, bool})


class Entry(NamedTuple):
    """One recorded entry: its key in the file, and the file and rule where the shape has them."""

    key: str
    file: str | None
    rule: str | None


def _leaves(node: object, trail: tuple[str, ...]) -> Iterator[tuple[str, ...]]:
    # The trail to every counted leaf, by the census's own rule (kinds._weight).
    if node is False or (isinstance(node, str) and not node):
        return
    if type(node) in _SCALARS:
        yield trail
    elif isinstance(node, list):
        for where, item in enumerate(cast("list[object]", node)):
            yield from _leaves(item, (*trail, str(where)))
    elif isinstance(node, dict):
        for name, item in cast("dict[str, object]", node).items():
            yield from _leaves(item, (*trail, name))


def _from_trail(trail: tuple[str, ...]) -> Entry:
    # The file and rule are the first two keys when the trail is deep enough to hold them.
    shaped = len(trail) >= _FILE_AND_RULE
    return Entry(_SEP.join(trail), trail[0] if shaped else None, trail[1] if shaped else None)


def entries_of(path: Path) -> list[Entry] | None:
    """List the entries of a ratchet file.

    Returns:
        one entry per recorded debt, in file order; None when the file is a link, cannot be read,
        or is a JSON file that does not parse.

    """
    if path.is_symlink():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    if path.suffix == ".json":
        try:
            parsed: object = json.loads(text)
        except ValueError:
            return None
        return [_from_trail(trail) for trail in _leaves(parsed, ())]
    lines = [line.strip() for line in text.splitlines()]
    kept = [line for line in lines if line and not line.startswith("#")]
    rows = kept[1:] if path.suffix == ".tsv" and kept else kept
    return [Entry(line, None, None) for line in rows]


def as_json(ratchet: str, kind: str, entry: Entry) -> str:
    """Spell one entry as the JSON line `census --entries` prints.

    Returns:
        a JSON object with the ratchet path, its kind, the key, and file and rule (null when the
        shape has none).

    """
    record: dict[str, str | None] = {
        "ratchet": ratchet,
        "kind": kind,
        "key": entry.key,
        "file": entry.file,
        "rule": entry.rule,
    }
    return json.dumps(record, sort_keys=True)
