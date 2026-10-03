# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The `mikemol-hook-*` console scripts: each hook's `main` behind the argv contract (W526).

⚑ ONE PLACE FOR THE CONTRACT, NOT FIVE. Every installed hook ignored argv (el-openglo:W99): a
`--help` read an empty stdin, allowed it and exited 0. The console scripts point here, so each
hook refuses an argument through `hook_argv.mode` before its own `main` reads stdin. The hook
modules are unchanged, and their tests still call `main` directly.

⚑ `--routes` IS structural-query's ONE MODE: it prints the routing table this repo's hook reads,
which substrate's script offered and adopters otherwise re-derived by importing `routes`.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from mikemol.hooks import (
    hook_argv,
    no_chaining,
    no_verify,
    pycheck,
    routing_table,
    shellcheck,
    structural_query,
)

if TYPE_CHECKING:
    from collections.abc import Callable

_ROUTES = "--routes"


def _guarded(prog: str, run: Callable[[], int]) -> int:
    """Refuse any argument, then run the hook.

    Returns:
        the refusal's exit code, or the hook's.

    """
    got = hook_argv.mode(prog, sys.argv)
    if isinstance(got, int):
        return got
    return run()


def print_routes(prog: str) -> int:
    """Print the routing table the invoking repo's hook reads, one `artifact<TAB>tool` per line.

    Returns:
        0 with the rows printed, or 1 when this repo has no table (stated, never a blank pass).

    """
    rows = routing_table.routes()
    if not rows:
        sys.stderr.write(f"{prog}: no routing table found under {routing_table.project_dir()}\n")
        return 1
    sys.stdout.write("".join(f"{artifact}\t{tool}\n" for artifact, tool in rows))
    return 0


def structural_query_main() -> int:
    """Run `mikemol-hook-structural-query`, or print its routing table under `--routes`.

    Returns:
        the exit code.

    """
    prog = "mikemol-hook-structural-query"
    got = hook_argv.mode(prog, sys.argv, (_ROUTES,))
    if got == _ROUTES:
        return print_routes(prog)
    if isinstance(got, int):
        return got
    return structural_query.main()


def no_chaining_main() -> int:
    """Run `mikemol-hook-no-chaining` behind the argv contract.

    Returns:
        the exit code.

    """
    return _guarded("mikemol-hook-no-chaining", no_chaining.main)


def no_verify_main() -> int:
    """Run `mikemol-hook-no-verify` behind the argv contract.

    Returns:
        the exit code.

    """
    return _guarded("mikemol-hook-no-verify", no_verify.main)


def shellcheck_main() -> int:
    """Run `mikemol-hook-shellcheck` behind the argv contract.

    Returns:
        the exit code.

    """
    return _guarded("mikemol-hook-shellcheck", shellcheck.main)


def pycheck_main() -> int:
    """Run `mikemol-hook-pycheck` behind the argv contract.

    Returns:
        the exit code.

    """
    return _guarded("mikemol-hook-pycheck", pycheck.main)
