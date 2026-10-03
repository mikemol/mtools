# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The argv contract of a `mikemol-hook-*` command: no argument but a declared mode (W526).

A harness hook reads one PreToolUse payload on stdin and is invoked with no arguments. el-openglo
measured (el-openglo:W99) that every installed hook IGNORED argv: `mikemol-hook-structural-query
--help` and `--routes` each read an empty stdin, allowed it, and exited 0 with no output. A
mistyped invocation then reads as one that ran, the silent pass every check in this package
refuses.

⚑ SO ANY ARGUMENT IS REFUSED, NAMED, WITH EXIT 2, unless the hook declares it as a mode. A bare
positional is refused too: unlike `flag_contract.check_flags`, a hook has no operands, so a word
on its command line can only be a mistake. Running with no arguments is unchanged, which is how
`hooks/bin/*` and every adopter's settings.json invoke it.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

EXIT_REFUSED = 2


def mode(prog: str, argv: Sequence[str], modes: Sequence[str] = ()) -> str | int | None:
    """Read a hook's argv: no arguments, exactly one declared mode, or a refusal.

    Returns:
        None for no arguments (run as a hook), the mode when argv is exactly one declared mode,
        or EXIT_REFUSED after writing the refusal to stderr.

    """
    extra = list(argv[1:])
    if not extra:
        return None
    if len(extra) == 1 and extra[0] in modes:
        return extra[0]
    offered = f"; its modes are {', '.join(modes)}" if modes else ""
    sys.stderr.write(
        f"{prog}: refusing argument(s) {' '.join(extra)!r}. A hook takes no arguments: it reads "
        f"one PreToolUse payload on stdin{offered}.\n"
    )
    return EXIT_REFUSED
