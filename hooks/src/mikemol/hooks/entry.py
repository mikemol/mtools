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
    after_compaction,
    build_failure,
    hook_argv,
    inbound_asks,
    nemik_check,
    no_chaining,
    no_verify,
    pycheck,
    pycheck_advise,
    read_guard,
    routing_table,
    shellcheck,
    structural_query,
    tick_gate,
    tick_release,
    tick_stop,
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


def pycheck_advise_main() -> int:
    """Run `mikemol-hook-pycheck-advise` behind the argv contract (W818).

    Returns:
        the exit code.

    """
    return _guarded("mikemol-hook-pycheck-advise", pycheck_advise.main)


def build_failure_main() -> int:
    """Run `mikemol-hook-build-failure` behind the argv contract (W829).

    Returns:
        the exit code.

    """
    return _guarded("mikemol-hook-build-failure", build_failure.main)


def inbound_asks_main() -> int:
    """Run `mikemol-hook-inbound-asks`, or its `--check` report, behind the argv contract.

    Returns:
        the exit code.

    """
    prog = "mikemol-hook-inbound-asks"
    got = hook_argv.mode(prog, sys.argv, (inbound_asks.CHECK_MODE,))
    if got == inbound_asks.CHECK_MODE:
        return inbound_asks.check_main()
    if isinstance(got, int):
        return got
    return inbound_asks.main()


def nemik_check_main() -> int:
    """Run `mikemol-hook-nemik-check` behind the argv contract.

    Returns:
        the exit code.

    """
    return _guarded("mikemol-hook-nemik-check", nemik_check.main)


def tick_stop_main() -> int:
    """Run `mikemol-hook-tick-stop` behind the argv contract (W811).

    Returns:
        the exit code.

    """
    return _guarded("mikemol-hook-tick-stop", tick_stop.main)


def tick_gate_main() -> int:
    """Run `mikemol-hook-tick-gate` behind the argv contract (W812).

    Returns:
        the exit code.

    """
    return _guarded("mikemol-hook-tick-gate", tick_gate.main)


def after_compaction_main() -> int:
    """Run `mikemol-hook-after-compaction` behind the argv contract (W813).

    Returns:
        the exit code.

    """
    return _guarded("mikemol-hook-after-compaction", after_compaction.main)


def tick_release_main() -> int:
    """Run `mikemol-hook-tick-release` behind the argv contract (W815).

    Returns:
        the exit code.

    """
    return _guarded("mikemol-hook-tick-release", tick_release.main)


def read_guard_main() -> int:
    """Run `mikemol-hook-read-guard` behind the argv contract (W814).

    Returns:
        the exit code.

    """
    return _guarded("mikemol-hook-read-guard", read_guard.main)
