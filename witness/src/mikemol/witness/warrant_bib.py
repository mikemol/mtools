# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Engine-free warrant reads: a project's declared consumer fields, and one warrant's claim and tag.

Moved from substrate's `substrate/warrant_bib.py`, with `claim_of` and `tag` from
`substrate/warrant_records.py` (the N-d warrant split, witness half); the suites are ported to
`tests/test_warrant_bib.py`.

⚑⚑⚑ THE SEAM IS THE ENGINE. substrate split `warrant_bib` from `warrant_records` because a module
importing paperkit at module scope made a whole CLI unreachable without paperkit installed
(gate-G209). This module never imports the engine: it reads TOML with the standard library, and
`claim_of`/`tag` work on records a caller ALREADY PARSED with its engine.

⚑⚑ WHAT DID NOT TRAVEL:
- `PROJECT`, `BIB` and `CONFIG` were derived from `corpus.ROOT`; under the no-ROOT ruling there is
  no default project. `consumer_fields` takes the config path as a REQUIRED argument.
- `claim_of`/`tag` called the engine's `records()` themselves; here they take the parsed
  `records` mapping, which is what made them pure (and what lets a caller parse once, not once
  per lookup).
- substrate's `speak()` usage text and `__main__` delegation, a CLI for a module with no modes.
"""

from __future__ import annotations

import re
import tomllib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


class WarrantError(KeyError):
    """A warrant, or a field of one, is absent.

    ⚑ An exception, not `SystemExit`: a library function cannot know whether its caller wanted
    to continue. It lives in the engine-free module, so catching it never requires the engine.
    """


def consumer_fields(config: Path) -> tuple[str, ...]:
    """Read the non-engine fields a project declares its bib carries (`[paper] consumer_fields`).

    ⚑⚑ The config is READ, not restated: a tuple typed here would be a second spelling of the
    project's own declaration. ⚑ An unreadable or malformed config yields nothing rather than
    raising: the parse still works and the engine names the fields it dropped.

    Returns:
        the declared field names; empty when the config cannot be read or declares none.

    """
    try:
        with config.open("rb") as handle:
            loaded: object = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return ()
    if not isinstance(loaded, dict):
        return ()
    paper: object = loaded.get("paper")
    if not isinstance(paper, dict):
        return ()
    declared: object = paper.get("consumer_fields")
    if not isinstance(declared, list):
        return ()
    return tuple(got for got in declared if isinstance(got, str))


def claim_of(key: str, records: Mapping[str, Mapping[str, str]]) -> str:
    """Read one warrant's `claim` prose from parsed records, whitespace-collapsed.

    ⚑ The witness reads the claim, not a copy of it: a witness carrying its own copy of a figure
    is two derived views of one fact with nothing reconciling them.

    Returns:
        the claim.

    Raises:
        WarrantError: when the warrant is absent, or carries no claim.

    """
    rec = records.get(key)
    if rec is None:
        msg = f"no warrant @{key} in the records given"
        raise WarrantError(msg)
    if "claim" not in rec:
        msg = f"warrant @{key} has no claim field"
        raise WarrantError(msg)
    return " ".join(rec["claim"].split())


def tag(key: str, name: str, records: Mapping[str, Mapping[str, str]]) -> int:
    """Read the integer in a claim's own `[name=N]` marker.

    ⚑ REFUSES WHEN ABSENT: an unanchored figure is a number nobody can audit, and defaulting it to
    zero would let a witness compare against a bound the claim never made.

    Returns:
        the tagged integer.

    Raises:
        WarrantError: when the warrant, its claim, or the `[name=N]` marker is absent.

    """
    prose = claim_of(key, records)
    found = re.search(rf"\[{re.escape(name)}=(-?\d+)\]", prose)
    number = found.group(1) if found is not None else None
    if not isinstance(number, str):
        msg = f"claim {key} is UNANCHORED: no [{name}=N] tag in its prose"
        raise WarrantError(msg)
    return int(number)
