# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Route one ledger invocation to the module that owns its question.

Moved from substrate (N-a row 6).

⚑⚑⚑ WIRING RATHER THAN LOGIC. Every branch names a module that already owns the answer —
`finding_resolve` looks a key up, `finding_census` counts by kind. **Nothing here decides
anything**: a branch that made a judgement would be a second authority over a question one module
already answers, which is how substrate's original `main` grew to its size.

⚑⚑ A REFUSAL IS A RESULT, NOT AN EXCEPTION: `run` returns `(lines, code)` so a case asserts on a
refusal directly, and it never prints or exits.

⚑ THE ROSTER, THE CLASSIFIER AND THE KIND ORDER ARE ARGUMENTS. The roster is where the caller's
findings live; the classifier guesses a witness's kind (the fragile step that once binned every
witness as unknown, so it stays the caller's); the order is the caller's declared kinds, as
`finding_census` takes it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.ledger import finding_census, finding_resolve

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

# The modes this router dispatches. ⚑ DECLARED, so a case asserts the roster against the branches.
MODES: tuple[str, ...] = ("--selftest", "--register", "--pairing", "--kinds", "--list")

# ⚑⚑ THE ROUTER'S OWN REFUSAL CODE, NAMED BECAUSE IT IS NOT A KIND'S VERDICT. A witness reporting
#   UNRUNNABLE and a router that could not route both exit 2 at the shell, and they are different
#   facts: an honest gap in the ledger, and a malformed invocation.
REFUSED = 2

USAGE = (
    "ledger — the per-finding WITNESS for a findings ledger.\n\n"
    "usage: ledger <KEY> | --list | --kinds | --pairing | --selftest | --register …"
)


def _kinds_lines(
    roster: Mapping[str, Callable[[], tuple[int, str]]],
    classify: Callable[[str], str],
    order: Sequence[str],
) -> list[str]:
    """Render the by-kind census, zero rows included.

    Returns:
        the census lines, then the behavioural total.

    """
    grouped: dict[str, list[str]] = {}
    for key in roster:
        grouped.setdefault(classify(key), []).append(key)
    out = [f"── {kind:<12} {count}" for kind, count in finding_census.rows(grouped, order)]
    behavioural = finding_census.behavioural_total(grouped, order)
    vacuous = finding_census.vacuous_total(grouped)
    out.append(
        f"\n{behavioural} of {len(roster)} witnesses are BEHAVIOURAL; "
        f"{vacuous} are `standing`, which no change to the code can flip."
    )
    return out


def run(
    argv: list[str],
    roster: Mapping[str, Callable[[], tuple[int, str]]],
    classify: Callable[[str], str],
    order: Sequence[str] = finding_census.KIND_ORDER,
) -> tuple[list[str], int]:
    """Return `(lines, exit_code)` for one invocation — never raises, never exits.

    ⚑⚑ A BARE OPERAND IS A KEY, AND THAT IS THE ONLY IMPLICIT ROUTE: everything else is a declared
    flag, so an unrecognised flag is refused BY NAME rather than handed to the key resolver, which
    would report it as a missing key — true, useless, and indistinguishable from a real one.

    Returns:
        the lines to print and the exit code — a witness's own verdict, never normalised.

    """
    if not argv:
        return [USAGE], REFUSED
    if "--kinds" in argv:
        return _kinds_lines(roster, classify, order), 0
    operands = [a for a in argv if not a.startswith("--")]
    if not operands:
        unknown = [a for a in argv if a not in MODES]
        if unknown:
            return [f"ledger: unknown mode {unknown[0]!r}", USAGE], REFUSED
        return [USAGE], REFUSED
    key, witness = finding_resolve.resolve(operands[0], roster)
    if witness is None:
        return [key], REFUSED
    code, note = witness()
    return [f"{key}: {note}"], code
