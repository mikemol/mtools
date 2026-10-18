# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Other acceptable suppliers of the asset a waiting card wants (W1511, nemik:W343).

⚑ A FALLBACK, NEVER A SECOND BLOCK: a card stays blocked on `blocked_on` alone.
`acceptable_suppliers` is a list of citations in the `blocked_on` form (empty means any owner, a
list restricts) and `want` is one line of free text naming the asset. Neither makes a card blocked
or unblocked and neither moves it in the ranking; they are stored and shown so a reader can see
who else could unblock it.
CONSUMED BY: `ops.update` (stores them) and nemik (reads them to route a wait).
"""

from mikemol.pathsforward.model import RefusedError, is_reference


def fields(suppliers: tuple[str, ...] | None, want: str | None) -> dict[str, object | None]:
    """Name the supplier fields an update sets, an empty value clearing the field.

    Returns:
        `acceptable_suppliers` and `want`, each only when given.

    """
    out: dict[str, object | None] = {}
    if suppliers is not None:
        out["acceptable_suppliers"] = list(suppliers) or None
    if want is not None:
        out["want"] = want or None
    return out


def check(sym: str, suppliers: tuple[str, ...] | None, want: str | None) -> None:
    """Refuse a supplier that is not a citation and a want that is not one line.

    Raises:
        RefusedError: naming the card and the offending value.

    """
    for item in suppliers or ():
        if not is_reference(item):
            msg = f"{sym}: acceptable supplier {item!r} is not W<n> or <repo>:W<n>"
            raise RefusedError(msg)
    if want is not None and ("\n" in want or "\r" in want):
        msg = f"{sym}: want must be one line"
        raise RefusedError(msg)
