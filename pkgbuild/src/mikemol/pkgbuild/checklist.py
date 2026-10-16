# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Print what an adopter adds to use one built wheel from a hermetic Bazel pip hub (W1136).

    mikemol-wheel checklist WHEEL [--hub HUB] [--in FILE] [--out FILE] [--python X.Y]

A repository that vendors a wheel (luthen-observability's `vendor/wheels`) uses it three ways, and
each is a line someone typed by hand before this: the requirement in the runtime `.in` file as a
`file://` reference to the wheel, the regenerated lock with the wheel's hash, and the library's
dependency on the pip-wrapped target (`@HUB//name_with_underscores`). This reads the wheel and
prints the three with the values filled in, so none is typed.

⚑ NOTHING IS WRITTEN OR RUN: the lock command is printed for the adopter to run; the `--hash`
value is the real sha256 of the file named, read here.

CONSUMED BY: `mikemol-wheel checklist`, the adopter's step after `mikemol-wheel` builds a dist.
"""

import hashlib
import re
import sys
from collections.abc import Sequence
from pathlib import Path

USAGE = 2
WHEEL_PARTS = 5
DEFAULTS = {
    "--hub": "pip",
    "--in": "requirements.in",
    "--out": "requirements.lock",
    "--python": "3.13",
}
SYNOPSIS = (
    "usage: mikemol-wheel checklist WHEEL [--hub HUB] [--in FILE] [--out FILE] [--python X.Y]\n"
)
SEPARATOR = re.compile(r"[-_.]+")


def dist_of(wheel: Path) -> str | None:
    """Read the distribution name from a wheel's file name.

    Returns:
        the name normalized with hyphens, or None when the name is not a wheel's.

    """
    if wheel.suffix != ".whl" or len(wheel.name.split("-")) < WHEEL_PARTS:
        return None
    return SEPARATOR.sub("-", wheel.name.split("-", 1)[0]).lower()


def digest(wheel: Path) -> str:
    """Hash the wheel file.

    Returns:
        its sha256 as lowercase hex.

    """
    return hashlib.sha256(wheel.read_bytes()).hexdigest()


def checklist(wheel: Path, options: dict[str, str]) -> list[str]:
    """Build the three steps for one wheel.

    Returns:
        the printed lines: the requirement, the hash the lock will carry, the compile command and
        the dependency label.

    """
    name = dist_of(wheel) or ""
    compile_flags = f"--offline --generate-hashes --python-version {options['--python']}"
    command = f"uv pip compile {compile_flags} {options['--in']} -o {options['--out']}"
    return [
        f"1. add to {options['--in']}:",
        f"   {name} @ file://{wheel.absolute()}",
        f"2. regenerate {options['--out']} (it will carry --hash=sha256:{digest(wheel)}):",
        f"   {command}",
        "3. depend on the pip-wrapped target in the library's BUILD file:",
        f'   "@{options["--hub"]}//{name.replace("-", "_")}"',
    ]


def _options(words: list[str]) -> dict[str, str] | None:
    """Take the flags out of `words`.

    Returns:
        the flags with their defaults, or None when a flag has no value.

    """
    found = dict(DEFAULTS)
    for flag in DEFAULTS:
        if flag in words:
            place = words.index(flag)
            if place + 1 >= len(words):
                return None
            found[flag] = words[place + 1]
            del words[place : place + 2]
    return found


def run(args: Sequence[str]) -> int:
    """Run `WHEEL [flags]`: print the three steps.

    Returns:
        0, or 2 for a usage error, a name that is not a wheel's, or a wheel that is not there.

    """
    words = list(args)
    options = _options(words)
    if options is None or len(words) != 1:
        sys.stderr.write(SYNOPSIS)
        return USAGE
    wheel = Path(words[0])
    if dist_of(wheel) is None or not wheel.is_file():
        sys.stderr.write(f"checklist: {wheel} is not a built wheel\n")
        return USAGE
    sys.stdout.writelines(line + "\n" for line in checklist(wheel, options))
    return 0
