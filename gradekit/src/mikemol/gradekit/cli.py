# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The command-line boundary shared by every script in this package.

Each script takes plain positional words and a few `--name value` options. Reading them by hand
keeps the argument values typed (the standard parser hands back untyped attributes), and one
`report` turns every expected failure into a one-line message and exit status 2, so no script
ends in a traceback for a bad argument or a bad input file.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence

USAGE_STATUS = 2


class UsageError(Exception):
    """The command line is not one the script accepts."""


def take_options(
    argv: Sequence[str],
    names: Collection[str],
) -> tuple[list[str], dict[str, list[str]]]:
    """Split `argv` into positional words and the values of the named `--name value` options.

    An option may repeat; its values are kept in order. A word after `--` is positional even if it
    starts with a dash.

    Returns:
        The positional words, and for each option that appeared, its values.

    Raises:
        UsageError: An option is not one of `names`, or has no value after it.

    """
    positional: list[str] = []
    options: dict[str, list[str]] = {}
    words = list(argv)
    while words:
        word = words.pop(0)
        if word == "--":
            positional.extend(words)
            break
        if not word.startswith("--"):
            positional.append(word)
            continue
        if word[2:] not in names:
            msg = f"unknown option {word!r}"
            raise UsageError(msg)
        if not words:
            msg = f"option {word!r} needs a value"
            raise UsageError(msg)
        options.setdefault(word[2:], []).append(words.pop(0))
    return positional, options


def report(prog: str, err: Exception) -> int:
    """Print an expected failure as one line on standard error.

    Returns:
        The usage status, 2, so a caller can `return report(...)`.

    """
    sys.stderr.write(f"{prog}: {err}\n")
    return USAGE_STATUS
