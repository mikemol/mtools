# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A point-of-no-return confirmation: reproduce a value read off the thing destroyed (W1065).

From cassian's P8 revoke, which demands `P8_CONFIRM_REVOKE=<the genesis root's accessor>`: "a typed
value only a human who looked can produce". A `yes` or a typed phrase proves only that someone
typed; the accessor proves they read the target.

⚑ THE EXPECTED VALUE IS READ FROM THE WORLD AT ISSUE TIME, NEVER DECLARED. `issue` takes a reading
of the target and a pattern, and the first group is the answer; a reading without it issues no
challenge, because a confirmation nobody can check is not a confirmation. An answer under
`MIN_LENGTH` is refused as guessable.

⚑ THE ANSWER IS NEVER PRINTED. The expected value is hidden from `repr`, and no refusal, instruction
or fingerprint carries it: a refusal says what to supply and where to read it, not what it is. An
accepted answer is reported only as its fingerprint, for the ledger.

⚑ THE COMPARISON IS CONSTANT-TIME (`hmac.compare_digest`) and exact: no trimming of the supplied
value beyond one trailing newline, no case folding.
"""

import hmac
import re
from collections.abc import Mapping
from dataclasses import dataclass, field

from mikemol.waldo.cli import matches_shape
from mikemol.waldo.custody import fingerprint

MIN_LENGTH = 8


class ConfirmError(ValueError):
    """The confirmation cannot be issued, or the answer given does not confirm."""


@dataclass(frozen=True)
class Challenge:
    """What must be reproduced: the variable it is supplied in and where the operator reads it."""

    name: str
    source: str
    expected: str = field(repr=False)


def issue(name: str, source: str, reading: str, pattern: str) -> Challenge:
    """Issue a challenge whose answer is the first group of `pattern` in `reading`.

    Returns:
        the Challenge.

    Raises:
        ConfirmError: when the reading has no such value, or the value is too short to be a check.

    """
    found = re.search(pattern, reading)
    if found is None or not found.groups() or not found.group(1):
        msg = f"cannot issue a challenge: {source} did not show the value to confirm with"
        raise ConfirmError(msg)
    if len(found.group(1)) < MIN_LENGTH:
        msg = f"cannot issue a challenge: the value read from {source} is too short to check"
        raise ConfirmError(msg)
    return Challenge(name, source, found.group(1))


def instructions(challenge: Challenge, command: str) -> str:
    """Tell the operator how to confirm, without the answer.

    Returns:
        text naming the variable, where to read its value, and the command to re-run.

    Raises:
        ConfirmError: when the command is not of the standard invocation shape.

    """
    if not matches_shape(command):
        msg = f"not of the standard invocation shape: {command!r}"
        raise ConfirmError(msg)
    return (
        f"This step cannot be undone. Read the value from {challenge.source}, then supply it as "
        f"{challenge.name} in the environment of: {command}"
    )


def check(challenge: Challenge, env: Mapping[str, str]) -> str:
    """Accept only the exact value the challenge expects.

    Returns:
        the fingerprint of the accepted value, safe to record.

    Raises:
        ConfirmError: when the variable is absent or empty, or its value is not the expected one.

    """
    given = env.get(challenge.name, "").removesuffix("\n")
    if not given:
        msg = f"confirmation required: supply {challenge.name} (read it from {challenge.source})"
        raise ConfirmError(msg)
    if not hmac.compare_digest(given.encode("utf-8"), challenge.expected.encode("utf-8")):
        msg = f"{challenge.name} does not match the value read from {challenge.source}"
        raise ConfirmError(msg)
    return fingerprint(given)
