# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""Which declared mutants a rewrite has left matching nothing, read before the gate does.

⚑⚑ A DECLARED MUTANT IS A REGEX AGAINST A FILE'S TEXT, AND A REWRITE CAN REMOVE THE TEXT. The
mutants grid refuses a declaration that stops matching (`unapplied`), but only after a gate run of
an hour. Two dists were refused that way by the codemods in this session (buildtel's
`except (binascii.Error, ValueError)` split, corpus's `except (OSError, SyntaxError)` guarded), each
found a gate late. The check is the same regex search the runner starts with: does the pattern occur
in its file at all?

    <file>|<name>|<pattern>|<replacement>|def=<function>      (mutants.regex: five fields)

⚑ WEAKER THAN THE RUNNER, ON PURPOSE: the runner also scopes a match to the named function and to
the formatted source; this asks only whether the pattern occurs in the file, so it can say
"applied" where the runner says "unapplied" but never the reverse. A line it calls unapplied is
certainly stale. A line whose text is not five fields is reported as malformed, not skipped.
"""

import re
from collections.abc import Callable

_FIELDS = 5


def unapplied(lines: str, read: Callable[[str], str | None]) -> list[str]:
    """List the declarations whose pattern occurs nowhere in its file.

    Returns:
        one `<file>::<name>` per stale or malformed line, in file order; a file `read` cannot give
        (None) is reported as unreadable.

    """
    found: list[str] = []
    for raw in lines.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|")
        if len(parts) != _FIELDS:
            found.append(f"{line[:60]}::malformed")
            continue
        file, name, pattern = parts[0], parts[1], parts[2]
        source = read(file)
        if source is None:
            found.append(f"{file}::{name}::unreadable")
        elif re.search(pattern, source, re.MULTILINE) is None:
            found.append(f"{file}::{name}")
    return found
