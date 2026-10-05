# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Read a debt ledger: a JSON object from file path to its count of findings.

The ledger is whatever a checker counted, once per file (mypy's findings, ruff's, a ratchet's). This
module takes the one shape the plan needs and refuses everything else by name, so a malformed ledger
is a refusal that says which file and which row, and not a plan over a guess.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from pathlib import Path


class LedgerError(ValueError):
    """A ledger is not a JSON object of file path to a positive integer count."""


def parse_ledger(text: str, where: str) -> dict[str, int]:
    """Parse ledger text, narrowing it to the one shape the plan reads.

    Returns:
        Each file path and its count of findings.

    Raises:
        LedgerError: The text is not JSON, is not an object, or a row's count is not a positive
            integer. A count of zero is refused: a clean file has no row.

    """
    try:
        loaded = cast("object", json.loads(text))
    except json.JSONDecodeError as exc:
        msg = f"{where}: not valid JSON ({exc})"
        raise LedgerError(msg) from exc
    if not isinstance(loaded, dict):
        msg = f"{where}: expected a JSON object of file to count, got {type(loaded).__name__}"
        raise LedgerError(msg)
    out: dict[str, int] = {}
    # A JSON object's keys are strings by the grammar, so only the values are narrowed.
    for key, value in cast("dict[str, object]", loaded).items():
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            msg = f"{where}: the row {key!r} must be a positive integer count, got {value!r}"
            raise LedgerError(msg)
        out[key] = value
    return out


def read_ledger(path: Path) -> dict[str, int]:
    """Read and parse the ledger at `path`.

    A file that cannot be read raises `OSError` from `read_text`, and one that is not UTF-8
    `UnicodeDecodeError`; neither is turned into an empty ledger, because an empty ledger reads as
    a repository with nothing to pay down.

    Returns:
        Each file path and its count of findings.

    """
    return parse_ledger(path.read_text(encoding="utf-8"), str(path))
