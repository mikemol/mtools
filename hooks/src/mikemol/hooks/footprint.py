# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The footprint audit: what a test really opens, against the inputs its target declares.

W1504. A narrow `data` declaration is only as good as its enforcement, and paperkit's footdeps
enforces its own by tracing what each check opens. This is the same audit for a hooks test: run the
test's command under `strace -f -e trace=openat`, reduce the successful opens to repo-relative
files, and compare them to the files the target declares.

    MISSING <path>   the test opened a repo file its declaration omits (it fails in a sandbox)
    UNUSED <path>    the declaration names a file the test never opened (a wider cone than needed)

⚑ A DEGRADED TRACE IS NEVER A CLEAN ONE. With no `strace` on the host, `audit` says so and returns
`DEGRADED` and no findings: a caller reads that as unknown, not as a pass, the way paperkit records
the over-declaring sentinel rather than an under-declaration.

⚑ ONLY A SUCCESSFUL OPEN COUNTS. A probe for a file that is not there (`= -1 ENOENT`) reads
nothing, and counting it would demand a declaration for a file that does not exist.
"""

import re
import shutil
import tempfile
from collections.abc import Callable, Collection, Sequence
from pathlib import Path

from mikemol.hooks.runproc import run_process

DEGRADED = "DEGRADED"
STRACE = "strace"
_OPENAT = re.compile(r'openat\([^,]+, "([^"]+)"[^)]*\) = (\d+)')

type Runner = Callable[[Sequence[str], Path], tuple[int, str]]
type Which = Callable[[str], str | None]


def opened(trace: str) -> set[str]:
    """Name the paths a trace opened successfully.

    Returns:
        the path argument of every `openat` line whose result is a file descriptor.

    """
    return {m.group(1) for m in map(_OPENAT.search, trace.splitlines()) if m}


def within(paths: Collection[str], root: Path) -> set[str]:
    """Reduce paths to the repo-relative files that exist under `root`.

    Returns:
        the relative names of the regular files among `paths` that sit inside `root`.

    """
    base = root.resolve()
    out: set[str] = set()
    for raw in paths:
        path = Path(raw) if Path(raw).is_absolute() else base / raw
        try:
            relative = path.resolve().relative_to(base)
        except ValueError:
            continue
        if path.is_file():
            out.add(relative.as_posix())
    return out


def findings(declared: Collection[str], seen: Collection[str]) -> list[str]:
    """Compare a declaration with what the trace saw.

    Returns:
        a `MISSING` line for each seen file not declared, then an `UNUSED` line for each declared
        file not seen, each group sorted.

    """
    want, got = set(declared), set(seen)
    missing = [f"MISSING {p}" for p in sorted(got - want)]
    return missing + [f"UNUSED {p}" for p in sorted(want - got)]


def trace_argv(out: Path, command: Sequence[str]) -> list[str]:
    """Build the argv that runs `command` under strace, writing the opens to `out`.

    Returns:
        the strace invocation.

    """
    return [STRACE, "-f", "-e", "trace=openat", "-o", str(out), *command]


def audit(
    command: Sequence[str],
    root: Path,
    declared: Collection[str],
    run: Runner = run_process,
    which: Which = shutil.which,
) -> list[str]:
    """Trace one test command and compare its opens with its declaration.

    Returns:
        the findings, `[DEGRADED]` when strace is absent, so the caller cannot read it as a pass.

    """
    if which(STRACE) is None:
        return [DEGRADED]
    with tempfile.TemporaryDirectory() as scratch:
        out = Path(scratch) / "trace.txt"
        run(trace_argv(out, command), root)
        text = out.read_text(encoding="utf-8") if out.is_file() else ""
    return findings(declared, within(opened(text), root))
