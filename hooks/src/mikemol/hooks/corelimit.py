# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-core-limit PID`: report a process whose core-file limit is above zero (W1770).

luthen-observability:W1456 reads the core limit of the agent slices; this is the second reader, at
the consumer that actually crashed: a bazel server in a crash loop wrote core files until the disk
was full, and a limit of zero on its own process is what would have prevented it. The standing rule
(operator 2026-09-23) is a core size of 0 for everything a gate starts.

    mikemol-core-limit <pid>      reads /proc/<pid>/limits, prints one line

Exit 0: both the soft and the hard limit are 0. Exit 4 (`EXIT_FINDINGS`): either is above zero or
`unlimited`, and the line says which. Exit 7 (`EXIT_UNREADABLE`, the exit table's CANNOT_RUN): the
process is gone or its limits cannot be read, which is not a pass. Exit 2: a usage error.

⚑ A REPORT, NEVER A GATE: the pre-commit calls it after the bazel run and prints what it says; its
exit status does not change a verdict, because a limit is a host fact and the gate's tree is not
what set it.
"""

import re
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

EXIT_FINDINGS = 4
EXIT_UNREADABLE = 7
EXIT_USAGE = 2
ARGUMENTS = 1
UNLIMITED = "unlimited"
ABOVE = " (above zero: a crash loop writes cores until the disk is full)"
_CORE = re.compile(r"^Max core file size\s+(?P<soft>\S+)\s+(?P<hard>\S+)", re.MULTILINE)

Read = Callable[[int], str | None]


def limits_of(text: str) -> tuple[str, str] | None:
    """Read the soft and hard core-file limits out of a `/proc/<pid>/limits` text.

    Returns:
        (soft, hard) as written (`0`, a byte count or `unlimited`), or None without the line.

    """
    found = _CORE.search(text)
    return (found.group("soft"), found.group("hard")) if found else None


def above_zero(value: str) -> bool:
    """Say whether a limit allows any core file.

    Returns:
        True for `unlimited` and for a positive byte count; False for 0.

    """
    return value == UNLIMITED or (value.isdecimal() and int(value) > 0)


def report(pid: int, text: str) -> tuple[int, str]:
    """Judge a process's core limits.

    Returns:
        the exit status and the line to print.

    """
    limits = limits_of(text)
    if limits is None:
        return EXIT_UNREADABLE, f"core limit of pid {pid}: no `Max core file size` line"
    soft, hard = limits
    line = f"core limit of pid {pid}: soft {soft}, hard {hard}"
    if above_zero(soft) or above_zero(hard):
        return EXIT_FINDINGS, line + ABOVE
    return 0, line


def read_proc(pid: int) -> str | None:
    """Read a process's limits file.

    Returns:
        its text, or None when the process is gone or the file is unreadable.

    """
    try:
        return Path(f"/proc/{pid}/limits").read_text(encoding="utf-8")
    except OSError:
        return None


def main(argv: Sequence[str] | None = None, read: Read = read_proc) -> int:
    """Print one process's core-limit report.

    Returns:
        0, `EXIT_FINDINGS`, `EXIT_UNREADABLE` or `EXIT_USAGE`.

    """
    args = sys.argv[1:] if argv is None else list(argv)
    if len(args) != ARGUMENTS or not args[0].isdecimal():
        sys.stderr.write("usage: mikemol-core-limit PID\n")
        return EXIT_USAGE
    pid = int(args[0])
    text = read(pid)
    if text is None:
        sys.stderr.write(f"core limit of pid {pid}: not readable (the process is gone?)\n")
        return EXIT_UNREADABLE
    status, line = report(pid, text)
    sys.stdout.write(line + "\n")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
