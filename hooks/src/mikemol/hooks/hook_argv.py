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

import sys
from collections.abc import Sequence

EXIT_BLOCK = 2
# ⚑ THE HARNESS FIXES THIS VALUE: Claude Code reads a hook's exit 2 as BLOCK, so a hook entry point
# cannot move it to the fleet's REFUSE (W1300, corpus/exit-table.json). The old name stays as an
# alias for the callers and tests that read it, and is judged as no constant by the census.
EXIT_REFUSED = EXIT_BLOCK


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
