# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Print the finding-key collision census, or check one ordinal before filing.

Moved from substrate (N-a row 6). The CLI over `finding_keys`.

⚑ THE CHECK MODE IS THE POINT: a filer about to register `family-F55` asks whether that ordinal
is free — the compare a read-modify-write over the roster does not do. The census mode is the
paydown view. ⚑ No next number is offered: a suggestion goes stale between the read and the write.

⚑⚑ THE LEDGER IS NAMED ON THE COMMAND LINE, NEVER DERIVED. Substrate's copy leaned on
`finding_keys`' default path, which was derived from `__file__`; the no-root ruling puts
resolution in a CLI, so this one takes `--ledger PATH` and refuses without it — as it refuses a
path that is not a file, rather than tracing back.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from mikemol.ledger import finding_keys

USAGE = """\
usage: finding_keys_show --ledger PATH [<family>-<letter><number>]

With no ordinal, print every ordinal naming more than one finding.
With an ordinal, report whether it is free (exit 0) or what already holds it (exit 1).

⚑ NO NEXT NUMBER IS OFFERED. A suggested ordinal goes stale between the read and the write,
  which is the read-modify-write defect this exists to catch.
"""

EXIT_TAKEN = 1
EXIT_USAGE = 2

_LEDGER_FLAG = "--ledger"
_ORDINAL = re.compile(r"^([a-z]+)-([A-Z])(\d+)$")


def _group(found: re.Match[str], index: int) -> str:
    """Narrow one captured group to `str` at the seam (`group()` is typed `str | Any`).

    Returns:
        the group's text; empty when the group did not participate.

    """
    got = found.group(index)
    return got if isinstance(got, str) else ""


def _refuse(why: str) -> int:
    """Say why the invocation is refused, then the usage.

    Returns:
        the usage exit code.

    """
    sys.stderr.write(f"finding_keys_show: {why}\n{USAGE}")
    return EXIT_USAGE


def _split(argv: list[str]) -> tuple[Path | None, list[str]]:
    """Separate `--ledger PATH` from the remaining arguments.

    Returns:
        the ledger path (None if not given) and the rest.

    """
    if _LEDGER_FLAG not in argv:
        return None, argv
    at = argv.index(_LEDGER_FLAG)
    if at + 1 >= len(argv):
        return None, argv
    return Path(argv[at + 1]), argv[:at] + argv[at + 2 :]


def _answer(ledger: Path, ordinal: str) -> int:
    """Report whether one ordinal is free, and what holds it when it is not.

    Returns:
        0 when free; 1 when taken; 2 when the ordinal is malformed.

    """
    found = _ORDINAL.match(ordinal)
    if found is None:
        return _refuse(f"{ordinal!r} is not <family>-<letter><n>")
    family, letter, number = _group(found, 1), _group(found, 2), int(_group(found, 3))
    held = [
        o
        for o in finding_keys.ordinals(ledger)
        if (o.family, o.letter, o.number) == (family, letter, number)
    ]
    if not held:
        sys.stdout.write(f"{ordinal}: FREE\n")
        return 0
    sys.stdout.write(f"{ordinal}: TAKEN by {len(held[0].slugs)} finding(s)\n")
    for slug in held[0].slugs:
        sys.stdout.write(f"  {slug or '(no slug)'}\n")
    return EXIT_TAKEN


def main(argv: list[str] | None = None) -> int:
    """Print the census, or answer about one ordinal.

    Returns:
        0 on a census or a free ordinal, 1 on a taken one, 2 on a usage error.

    """
    args = sys.argv[1:] if argv is None else argv
    if "--help" in args or "-h" in args:
        sys.stdout.write(USAGE)
        return 0
    ledger, rest = _split(args)
    if ledger is None:
        return _refuse(f"{_LEDGER_FLAG} PATH is required — the ledger is named, never derived")
    if not ledger.is_file():
        return _refuse(f"{ledger} is not a file, so there is no ledger to read")
    if not rest:
        sys.stdout.write(finding_keys.render(ledger) + "\n")
        return 0
    if len(rest) > 1:
        return _refuse(f"one ordinal at a time, not {len(rest)}")
    return _answer(ledger, rest[0])


if __name__ == "__main__":
    sys.exit(main())
