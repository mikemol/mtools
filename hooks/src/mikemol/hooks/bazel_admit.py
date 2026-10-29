# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W836: bazel admits or waits on the host's resources itself, before every heavy command.

A note told each session to read the zram fact before heavy bazel work, and a session that skipped
it filled zram1, which remounted /var/tmp read-only and killed every shell command (the 2026-10-05
outage). A rule that depends on being remembered is the manual step again (operator, 2026-10-06):
the check belongs in bazel's own path. Bazel runs a workspace's `tools/bazel` wrapper before every
client command, naming the real client in BAZEL_REAL; `mikemol-bazel-admit --install` writes that
wrapper, and the wrapper runs this.

⚑ THE WAIT IS MEMBUDGET'S (W837, operator 2026-10-06: "the point of using membudget for the zram
case is that we can have membudget wait until zram is within a safe range again, not because we
want it to take out a specific lease"). A light verb (`info`, `query`, `version`, `shutdown`, ...)
runs at once. A heavy verb (`build`, `test`, `run`, `coverage`, `fetch`) runs under
`mikemol-membudget hold`, with `MEMBUDGET_ZRAM_MAX` set to the host's refusal fraction and
`MEMBUDGET_TIMEOUT` to the wait bound: membudget's own admission loop then holds the start while
zram is at or above the ceiling (no separate poll loop here), refuses it with its own exit 3 once
the bound is spent, and takes its place in the same ledger as every other holder. The lease's MB is
incidental: a nominal weight, not a claim about what bazel will use.

⚑ `hold`, NOT `run`: `run` caps the command's cgroup at its lease, and the bazel client that starts
the server daemon would put the daemon, which outlives the command and does the real work, inside
that cap for good (measured: `run 4096` printed MemoryMax=4096M). `hold` is accounting only.

⚑ A GATE THAT IS NOT THERE IS SAID, NEVER ASSUMED: an older membudget ignores an environment
variable it does not know, so the ceiling set against one would run the start ungated in silence.
The found membudget is asked for its `capabilities` first, and one that does not list `zram-gate`
is treated as absent.

⚑ WHAT CANNOT BE FOUND BLOCKS NOTHING, AND SAYS SO: a missing or too-old `mikemol-membudget` runs
bazel with a note and no zram gate (the gate lives in membudget). `BAZEL_ADMIT=0` bypasses it,
stated on stderr. A value the caller already set for either variable is theirs and is kept.

⚑ THE WRAPPER FAILS OPEN WHEN THIS TOOL IS NOT BUILT: building this tool needs bazel, which would
need the wrapper, which needs the tool.

CONSUMED BY: the `mikemol-bazel-admit` console script.
"""

import os
import re
import shutil
import socket
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import TextIO

from mikemol.hooks import host_facts, tool_path

# W2124: the remote services a build uses when the workspace's .bazelrc names them. The endpoint is
# READ from the .bazelrc, never written here, so a moved service needs no change in this module.
_BES_FLAG = re.compile(
    r"^build\s+--bes_backend=grpc://(?P<host>[^:\s/]+):(?P<port>\d+)\s*$", re.MULTILINE
)
SERVICE_VERBS = frozenset({"build", "test", "coverage", "run"})
CONNECT_TIMEOUT_S = 3
OFF_FLAGS = ("--remote_cache=", "--bes_backend=", "--bes_results_url=")
Reach = Callable[[str, int], bool]


def service_address(directory: Path) -> tuple[str, int] | None:
    """Read the remote-service endpoint the nearest workspace `.bazelrc` names.

    Returns:
        `(host, port)` of its `build --bes_backend=grpc://...` line, or None when no `.bazelrc`
        above `directory` names one.

    """
    for candidate in (directory, *directory.parents):
        rc = candidate / ".bazelrc"
        if rc.is_file():
            try:
                found = _BES_FLAG.search(rc.read_text(encoding="utf-8"))
            except OSError:
                return None
            return (found["host"], int(found["port"])) if found else None
    return None


def can_connect(host: str, port: int) -> bool:
    """Say whether a TCP connection to the endpoint is accepted now.

    Returns:
        True when it connects within CONNECT_TIMEOUT_S, False on any socket error.

    """
    try:
        with socket.create_connection((host, port), timeout=CONNECT_TIMEOUT_S):
            return True
    except OSError:
        return False


def degrade(
    args: Sequence[str], directory: Path, reachable: Reach | None = None
) -> tuple[list[str], str | None]:
    """Switch the remote cache and the BEP upload off for one command when their endpoint is down.

    ⚑ AN OUTAGE OF TELEMETRY AND A CACHE MUST NOT FAIL A BUILD THAT PASSES (host retro, 2026-10-29:
    BuildBuddy's endpoint refused connections after a reboot, bazel failed every test action on its
    remote-cache capability query and exited 34 on a passing build for the failed BEP upload).
    ⚑ WHEN THE ENDPOINT IS UP NOTHING CHANGES: the cache and the BES stream stay on, so cache hits
    and the results link are as before. The flags go right after the verb, so a flag the caller put
    later on the command line still wins, and `.bazelrc` is read as it always was.

    Returns:
        the arguments (the off-flags inserted after the verb when the endpoint refuses), and a
        note saying so; unchanged arguments and None for a light verb, a workspace that names no
        endpoint, or an endpoint that accepts.

    """
    verb = verb_of(args)
    address = service_address(directory) if verb in SERVICE_VERBS else None
    if address is None or (reachable or can_connect)(*address):
        return list(args), None
    at = list(args).index(str(verb)) + 1
    note = (
        f"bazel-admit: {address[0]}:{address[1]} refuses connections; this `{verb}` runs with the "
        "remote cache and the BEP upload off"
    )
    return [*args[:at], *OFF_FLAGS, *args[at:]], note


HEAVY_MB = {"build": 4096, "test": 4096, "coverage": 4096, "run": 2048, "fetch": 1024}
MEMBUDGET = "mikemol-membudget"
MEMBUDGET_ENV = "MEMBUDGET_BIN"
CAPABILITY = "zram-gate"
PROBE_TIMEOUT_S = 10
LABEL = "bazel"
ZRAM_MAX_ENV = "MEMBUDGET_ZRAM_MAX"
TIMEOUT_ENV = "MEMBUDGET_TIMEOUT"
BYPASS_ENV = "BAZEL_ADMIT"
MAX_WAIT_ENV = "BAZEL_ADMIT_MAX_WAIT_S"
TRACE_ENV = "BAZEL_ADMIT_TRACE"
EXIT_DEFERRED = 3
EXIT_USAGE = 2
SEPARATOR = "--"
INSTALL_FLAG = "--install"
ARGC_WITH_VALUE = 2
WRAPPER_PATH = Path("tools") / "bazel"
WRAPPER = """#!/bin/sh
# Generated by `mikemol-bazel-admit --install` (mtools:W836). Bazel runs this before every client
# command, with the real client in BAZEL_REAL. Heavy commands (build, test, run, coverage, fetch)
# wait for host resources first; the rest run untouched. The tool is looked for in this repo's venv,
# then in mtools' built venv, then in the REAL checkout's venv (MIKEMOL_REAL_ROOT, which a gate
# exports into its frozen snapshot, W2145), then on PATH, and when it is not built (the bootstrap
# build needs
# this wrapper) bazel runs untouched.
here="$(cd "$(dirname "$0")/.." && pwd -P)"
for admit in \\
    "$here/.venv/bin/mikemol-bazel-admit" \\
    "$here/bazel-bin/hooks/.venv/bin/mikemol-bazel-admit" \\
    "${MIKEMOL_REAL_ROOT:-/nonexistent}/.venv/bin/mikemol-bazel-admit"; do
    if [ -x "$admit" ]; then
        exec "$admit" -- "$BAZEL_REAL" "$@"
    fi
done
# W2124: a frozen snapshot tree has neither venv, but it carries this tool's own source (stdlib
# only), which is exactly what was frozen: run that, so a gate reads nothing outside its snapshot.
if [ -f "$here/hooks/src/mikemol/hooks/bazel_admit.py" ] && command -v python3 >/dev/null 2>&1; then
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$here/hooks/src" \\
        exec python3 -m mikemol.hooks.bazel_admit -- "$BAZEL_REAL" "$@"
fi
exec "$BAZEL_REAL" "$@"
"""

Execute = Callable[[Sequence[str], Mapping[str, str]], int]
Probe = Callable[[Sequence[str]], str | None]


def verb_of(args: Sequence[str]) -> str | None:
    """Name the bazel command in `args`: the first word that is not a startup option.

    Returns:
        the verb, or None when there is none (a bare `bazel`).

    """
    return next((word for word in args if not word.startswith("-")), None)


def estimate_mb(verb: str | None) -> int | None:
    """Estimate the memory a bazel command needs.

    Returns:
        the MB for a heavy verb, or None for a light one that needs no admission.

    """
    return HEAVY_MB.get(verb) if verb is not None else None


def run_probe(argv: Sequence[str]) -> str | None:
    """Run a short query command and return its stdout.

    Returns:
        stdout when it exited 0, None when it could not run, timed out or exited non-zero.

    """
    try:
        done = subprocess.run(
            list(argv),
            capture_output=True,
            text=True,
            check=False,
            timeout=PROBE_TIMEOUT_S,
        )
    except Exception as caught:
        if not isinstance(caught, (OSError, subprocess.TimeoutExpired)):
            raise
        return None
    return done.stdout if done.returncode == 0 else None


def plan(
    real: str, args: Sequence[str], mb: int, env: Mapping[str, str], probe: Probe = run_probe
) -> tuple[list[str], dict[str, str], str | None]:
    """Build the command, its environment and a note, for an admitted heavy verb.

    Returns:
        the argv (under a membudget hold when a membudget with the zram gate is found), the
        environment to run it in (the zram ceiling added unless the caller set it, and a wait
        bound only when the caller names one), and a note to say when no usable membudget was
        found.

    """
    budget = tool_path.find(MEMBUDGET, MEMBUDGET_ENV, Path.cwd(), env)
    if budget is None:
        note = f"bazel-admit: {MEMBUDGET} not found; running without admission or a zram gate"
        return [real, *args], dict(env), note
    if CAPABILITY not in (probe([str(budget), "capabilities"]) or "").split():
        note = f"bazel-admit: {budget} has no {CAPABILITY} (too old); running without a zram gate"
        return [real, *args], dict(env), note
    gated = {ZRAM_MAX_ENV: str(host_facts.REFUSE_FRACTION), **env}
    if env.get(MAX_WAIT_ENV):
        gated.setdefault(TIMEOUT_ENV, f"{float(env[MAX_WAIT_ENV]):.0f}")
    return [str(budget), "hold", str(mb), LABEL, SEPARATOR, real, *args], gated, None


def admit(
    argv: Sequence[str],
    env: Mapping[str, str],
    execute: Execute,
    err: TextIO,
    probe: Probe = run_probe,
) -> int:
    """Run `argv` (the real bazel and its arguments) after admitting it.

    Returns:
        what `execute` returns for the command that ran.

    """
    real, args = argv[0], list(argv[1:])
    verb = verb_of(args)
    mb = estimate_mb(verb)
    if env.get(BYPASS_ENV) == "0":
        err.write("bazel-admit: BAZEL_ADMIT=0, running without admission\n")
        return execute([real, *args], env)
    if mb is None:
        if env.get(TRACE_ENV):
            err.write(f"bazel-admit: `{verb}` is light; running untouched\n")
        return execute([real, *args], env)
    args, down = degrade(args, Path.cwd())
    if down:
        err.write(f"{down}\n")
    command, gated, note = plan(real, args, mb, env, probe)
    if note:
        err.write(f"{note}\n")
    if env.get(TRACE_ENV):
        err.write(f"bazel-admit: admitting `{verb}` ({mb} MB nominal): {' '.join(command)}\n")
    return execute(command, gated)


def install(repo: Path) -> Path:
    """Write the repository's `tools/bazel` wrapper.

    Returns:
        the wrapper's path, executable.

    """
    target = repo / WRAPPER_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(WRAPPER, encoding="utf-8")
    target.chmod(0o755)
    return target


def _exec(argv: Sequence[str], env: Mapping[str, str]) -> int:
    """Replace this process with `argv`; it does not return unless the program is missing.

    Returns:
        127 when the program could not be started.

    """
    program = shutil.which(argv[0]) or argv[0]
    try:
        os.execve(program, list(argv), dict(env))
    except OSError as problem:
        sys.stderr.write(f"bazel-admit: cannot run {argv[0]}: {problem}\n")
        return 127


def main(argv: Sequence[str] | None = None) -> int:
    """Run `mikemol-bazel-admit -- <real bazel> <args>`, or `--install DIR`.

    Returns:
        the command's exit code (membudget's 3 when its wait is spent), or EXIT_USAGE.

    """
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) == ARGC_WITH_VALUE and args[0] == INSTALL_FLAG:
        sys.stdout.write(f"{install(Path(args[1]))}\n")
        return 0
    if len(args) >= ARGC_WITH_VALUE and args[0] == SEPARATOR:
        return admit(args[1:], dict(os.environ), _exec, sys.stderr)
    sys.stderr.write("usage: mikemol-bazel-admit -- <bazel> [args...] | --install DIR\n")
    return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
