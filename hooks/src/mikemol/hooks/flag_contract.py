# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""What a gate may be ASKED: an unknown flag refused, and an unstated choice between two refused.

Substrate's `ratchet_flags`, moved (N-a row 5b, `inbox/2026-09-24-substrate-ratchet-log-flags-
letter.md`), with its policy left behind. Every refusal and every acceptance is also an event for
`refusal_log`, sent where the caller says.

⚑⚑ NOT ARGPARSE, DELIBERATELY. These functions VALIDATE a raw argv that the caller then reads its
own way — gates invoked positionally from shell hooks, several taking bare paths. Swapping in a
parser would change every call site to fix a typo problem; a membership check is the whole fix.

⚑ CALL `check_flags` FIRST, THEN `exactly_one` FOR EACH CHOICE, AND IN SEVERITY ORDER. A typo'd
`--aply` must be reported as an unknown flag, not as an unstated intent, or the operator goes
looking for a flag they in fact typed. And a tool that both writes and reaches a store should
hear about the unstated MUTATION first.

⚑ WHAT DID NOT TRAVEL, AND WHY:
- the tenant pair (`--sandbox`/`--live`) and its `tenant(require=…)` remedy are substrate's store
  policy — substrate builds its own `Choice`;
- `SUBSTRATE_EXPLICIT_MUTATION=0`, an ambient switch that downgraded the refusal to a warning: a
  caller wanting advice rather than refusal does not call the refusal;
- `arg_after`, which EXTRACTS a value rather than validating: this package's hooks parse their own.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

from mikemol.hooks.refusal_log import Refusal, log_fallthrough

if TYPE_CHECKING:
    from collections.abc import Iterable

EXIT_REFUSED = 2


def rest(argv: object) -> list[str]:
    """Return the flag-bearing tail of `argv`, whether or not the caller already sliced it.

    ⚑ `argv[1:]` WAS AN UNCHECKED PRECONDITION: one caller passed a pre-sliced list, so the guard
    stripped its only flag and passed `--queit` with rc=0. argv[0] is dropped only when it is a
    program path — which never starts with `-`, where a flag always does.

    Returns:
        the arguments after the program, as strings; junk is empty.

    """
    items = [str(a) for a in argv] if isinstance(argv, (list, tuple)) else []
    if items and not items[0].startswith("-"):
        return items[1:]
    return items


def check_flags(
    argv: object, known: Iterable[str], label: str, *, destination: str | None
) -> int | None:
    """Refuse any flag not in `known`, naming the known set. Call this FIRST.

    ⚑ NO GATE REJECTED AN UNKNOWN FLAG: a typo'd `--queit` silently degraded five gates to
    verbose-but-passing, all exit 0. A flag nobody validates can be wrong forever.

    ⚑ AN ACCEPT IS AN EVENT TOO — which capabilities are actually used is not answerable from
    source, because a dispatch branch has a caller by construction.

    Returns:
        None when every flag is known; the refusal's exit code otherwise.

    """
    args = rest(argv)
    names = sorted(set(known))
    unknown = [a for a in args if a.startswith("-") and a not in names]
    flags = [a for a in args if a.startswith("-")]
    if not unknown:
        log_fallthrough(
            label, "accepted", " ".join(flags), Refusal(names, args, 0), destination=destination
        )
        return None
    sys.stderr.write(
        f"{label}: unknown flag(s) {' '.join(unknown)} — known: {' '.join(names)}\n"
        "  Refusing rather than running with a flag you did not mean; a silently ignored "
        "--quiet is a gate that looks like it ran.\n"
    )
    log_fallthrough(
        label,
        "unknown-flag",
        " ".join(unknown),
        Refusal(names, args, EXIT_REFUSED),
        destination=destination,
    )
    return EXIT_REFUSED


@dataclass(frozen=True, slots=True)
class Choice:
    """Two mutually exclusive flags, one of which must be stated, and what not stating costs.

    `subject` says what the tool does ("MUTATES"), `consequence` why an unstated choice is
    dangerous, `reason` the event's name, and `remedy` any in-code escape worth naming.
    """

    flags: tuple[str, str]
    subject: str
    consequence: str
    reason: str
    remedy: str = ""


MUTATION = Choice(
    flags=("--apply", "--dry-run"),
    subject="This tool MUTATES.",
    consequence=(
        "A default-dry silently does nothing when you meant to write; a default-apply silently "
        "writes when you meant to look."
    ),
    reason="unstated-mutation",
)


def exactly_one(argv: object, label: str, choice: Choice, *, destination: str | None) -> int | None:
    """Refuse unless exactly one of `choice`'s flags is stated.

    ⚑ NO BARE-RUN EXEMPTION: a tool may treat no target as THE WHOLE TREE, so a no-argument run
    is not help-seeking by default. A tool wanting help dispatches usage BEFORE calling this.

    Returns:
        None when exactly one is stated; the refusal's exit code for neither or both.

    """
    args = rest(argv)
    first, second = choice.flags
    stated = [f for f in choice.flags if f in args]
    if len(stated) == 1:
        return None
    if stated:
        sys.stderr.write(
            f"⚑ {label}: BOTH {first} and {second} given — mutually exclusive. "
            "Refusing rather than picking one.\n"
        )
        return EXIT_REFUSED
    remedy = f"\n  {choice.remedy}" if choice.remedy else ""
    sys.stderr.write(
        f"⚑ {label}: neither {first} nor {second} was given.\n"
        f"  {choice.subject} {choice.consequence} State one.{remedy}\n"
    )
    log_fallthrough(
        label,
        choice.reason,
        refusal=Refusal(list(choice.flags), args, EXIT_REFUSED),
        destination=destination,
    )
    return EXIT_REFUSED
