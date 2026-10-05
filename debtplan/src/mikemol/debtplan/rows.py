# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""One debt file as the plan states it: its count, who it waits on, who waits on it.

A per-file edit gate refuses an edit to a file whose import closure still carries findings, so the
order of a pay-down is a fact about the import graph and not a choice. A file is `ready` when no
debt file stands in its closure but itself.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Row:
    """One debt file: its count, the debt files it waits on, and the debt files that wait on it."""

    file: str
    count: int
    waits_on: tuple[str, ...]
    waited_by: tuple[str, ...]

    @property
    def ready(self) -> bool:
        """Report whether the file can be edited now: it waits on no other debt file."""
        return not self.waits_on


def order_key(row: Row) -> tuple[int, int, str]:
    """Key a row so ready files sort first, then the ones most files wait on, then by name.

    Returns:
        A triple: how many files `row` waits on, the negated count of files waiting on it, and its
        name.

    """
    return (len(row.waits_on), -len(row.waited_by), row.file)
