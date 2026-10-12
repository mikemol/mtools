# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Compare a plan's changes with a declared allowed set: the refuse-with-diff core (W1055).

Lifted from luthen-observability's `checks/apply_set.py` (W880/W882), pure and with no JSON
library of its own: it reads rows that are already parsed, `[{"address": ..., "actions": [...]}]`.

⚑ A DECLARED SET IS AN ALLOWED SUPERSET. A row that is already converged is simply absent from a
fresh plan, so requiring an exact match refuses the first real run (measured 2026-10-12: a lib-tier
row had nothing to replace). Every planned change must be one of `allowed`; only `required` changes
must be present.

⚑ ACTION ORDER IS NOT A DIFFERENCE. A replace may arrive as `delete, create` or `create, delete`;
a change is its address and the SORTED actions, so two orders are one change.

⚑ A ROW THAT IS NOT A ROW IS REFUSED, NOT SKIPPED. A set file with a row missing its address would
otherwise allow less, or more, than it reads as; it raises `ChangeShapeError` naming the row.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Iterable

type Change = tuple[str, tuple[str, ...]]


class ChangeShapeError(ValueError):
    """A declared or planned row is not an `{address, actions}` object."""


@dataclass(frozen=True)
class Diff:
    """What differs between a declared change set and a planned one."""

    missing: tuple[Change, ...]
    extra: tuple[Change, ...]

    def clean(self) -> bool:
        """Say whether the plan is within the declared set.

        Returns:
            True when no required change is missing and no planned change is outside the set.

        """
        return not self.missing and not self.extra


def change_of(address: str, actions: Iterable[str]) -> Change:
    """Make one change as a hashable pair; action order inside a replace is irrelevant.

    Returns:
        the address and its sorted actions.

    """
    return (address, tuple(sorted(actions)))


def _row(row: object, where: str) -> Change:
    """Read one `{address, actions}` row.

    Returns:
        the change.

    Raises:
        ChangeShapeError: when the row is not an object with a text address and a list of text
            actions.

    """
    if not isinstance(row, dict):
        msg = f"{where}: a change row must be an object, got {type(row).__name__}"
        raise ChangeShapeError(msg)
    fields = cast("dict[str, object]", row)
    address = fields.get("address")
    actions = fields.get("actions")
    if not isinstance(address, str) or not address:
        msg = f"{where}: a change row needs a non-empty text address"
        raise ChangeShapeError(msg)
    if not isinstance(actions, list) or not actions:
        msg = f"{where}: {address} needs a non-empty list of actions"
        raise ChangeShapeError(msg)
    listed = cast("list[object]", actions)
    if not all(isinstance(action, str) for action in listed):
        msg = f"{where}: {address} has an action that is not text"
        raise ChangeShapeError(msg)
    return change_of(address, [str(action) for action in listed])


def changes_from(rows: object, where: str = "changes") -> set[Change]:
    """Read a list of change rows as a set of changes.

    Returns:
        the set; an absent list (None) is the empty set.

    Raises:
        ChangeShapeError: when `rows` is neither None nor a list, or any row is malformed.

    """
    if rows is None:
        return set()
    if not isinstance(rows, list):
        msg = f"{where}: expected a list of change rows, got {type(rows).__name__}"
        raise ChangeShapeError(msg)
    listed = cast("list[object]", rows)
    return {_row(row, f"{where}[{index}]") for index, row in enumerate(listed)}


def compare(allowed: set[Change], required: set[Change], planned: set[Change]) -> Diff:
    """Give the required changes the plan lacks (missing) and the planned ones not allowed (extra).

    Returns:
        the diff, each side sorted.

    """
    return Diff(tuple(sorted(required - planned)), tuple(sorted(planned - allowed)))


def render(diff: Diff) -> list[str]:
    """Give the diff as printable lines: `-` required but absent, `+` planned but not allowed.

    Returns:
        one line per difference, missing before extra.

    """
    lines = [f"- {address} {'+'.join(actions)}" for address, actions in diff.missing]
    return lines + [f"+ {address} {'+'.join(actions)}" for address, actions in diff.extra]


def shown(planned: set[Change]) -> list[str]:
    """Give the planned rows as `action address` lines, for the verdict.

    Returns:
        the lines in address order.

    """
    return [f"{'+'.join(actions)} {address}" for address, actions in sorted(planned)]
