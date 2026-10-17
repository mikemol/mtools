# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Ship each REFUSED line of the writer as one OTLP log record, without ever blocking it (W1248).

⚑⚑ A REFUSAL IS DATA ABOUT HOW THE TOOL IS USED (operator, 2026-10-15: top rule, repeat caller,
time to first correct use are queries over these records). Every usage refusal the writer prints
passes `main`; there it also hands one record to `mikemol-otlp log`, which posts it to the declared
logs endpoint. luthen's receiver, record shape and stream key are in luthen-observability
docs/prr/otlp.md (read 2026-10-17); a user-level producer posts OTLP directly and does not use the
root-only mikemol-vlog spool.

⚑ THE WRITER STAYS DEPENDENCY-FREE AND NEVER WAITS. The child is `mikemol-otlp`, found by
`MIKEMOL_OTLP_BIN`, then PATH, then the fleet root's mtools checkout; the endpoint is
`MIKEMOL_OTLP_LOGS_URL`. With either absent this does nothing, so tests, offline hosts and every
peer repo that has not set a URL are unchanged. The child is started detached and not awaited: a
slow or dead endpoint must not slow the refusal the caller is reading, and a failure to start it
is swallowed because the refusal itself is the product.

⚑ THE RECORD CARRIES SHAPES, NEVER VALUES: the rule text has its quoted values replaced, and the
argv is its flag names only, so a path or a token typed after a flag is never shipped.
"""

import os
import re
import shutil
import subprocess
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from mikemol.pathsforward import foreign

BIN_ENV = "MIKEMOL_OTLP_BIN"
URL_ENV = "MIKEMOL_OTLP_LOGS_URL"
ENDPOINTS_ENV = "MIKEMOL_ENDPOINTS"
CALLER_ENV = "MIKEMOL_CALLER"
SERVICE = "mikemol-paths-forward"
_QUOTED = re.compile(r"'[^']*'|\"[^\"]*\"")
# An absolute path wherever it stands, quoted or not: the first real record carried the whole
# --state path in its text, a local filesystem layout the store has no use for.
_PATH = re.compile(r"/[^\s'\":]+")
_REFUSED = re.compile(r"^REFUSED:\s*")

Spawn = Callable[[Sequence[str], str], None]


def rule_of(message: str) -> str:
    """Reduce a refusal to its rule text: the prefix dropped, every quoted value replaced.

    Returns:
        the text with `<value>` where a quoted value stood and `<path>` where an absolute path did.

    """
    bare = _QUOTED.sub("<value>", _REFUSED.sub("", message))
    return _PATH.sub("<path>", bare).strip()


def flags_of(args: Sequence[str]) -> str:
    """Name the flags of an invocation without their values.

    Returns:
        the flags, in order, space-separated.

    """
    return " ".join(arg.split("=", 1)[0] for arg in args if arg.startswith("--"))


def binary(env: Mapping[str, str], root: Path) -> str | None:
    """Find `mikemol-otlp`: the named binary, PATH, then the fleet root's mtools checkout.

    Returns:
        its path, or None when none exists.

    """
    named = env.get(BIN_ENV)
    if named:
        return named
    on_path = shutil.which("mikemol-otlp")
    if on_path:
        return on_path
    checkout = root / "mtools" / "otlp" / ".venv" / "bin" / "mikemol-otlp"
    return str(checkout) if checkout.is_file() else None


def spawn(argv: Sequence[str], line: str) -> None:
    """Start the child detached, give it the line on stdin and do not wait for it."""
    # An OS pipe, not Popen's stdin object: the line is a few hundred bytes, far below the pipe
    # buffer, so writing it before the child reads can never block this process.
    read_end, write_end = os.pipe()
    try:
        subprocess.Popen(
            list(argv),
            stdin=read_end,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        os.write(write_end, (line + "\n").encode("utf-8"))
    finally:
        os.close(read_end)
        os.close(write_end)


def emit(
    message: str,
    args: Sequence[str],
    state: Path,
    env: Mapping[str, str] | None = None,
    start: Spawn | None = None,
) -> bool:
    """Hand one refusal record to `mikemol-otlp log`, when a binary and a URL exist.

    Returns:
        True when a child was started, False when there was nothing to start or it could not be.

    """
    where = os.environ if env is None else env
    url = where.get(URL_ENV)
    program = binary(where, foreign.default_root())
    # ⚑ ENDPOINT BY NAME IS THE ROUTE LUTHEN PREFERS (an address in an environment is an address
    # literal in their tree): with only MIKEMOL_ENDPOINTS set, the child resolves the name itself,
    # so no --url is passed. Neither variable set means nothing is configured: a silent no-op.
    if (not url and not where.get(ENDPOINTS_ENV)) or program is None:
        return False
    repo = state.parent.parent.name
    argv = [
        program,
        "log",
        *(["--url", url] if url else []),
        "--service",
        SERVICE,
        "--namespace",
        repo,
        "--severity",
        "WARN",
        "--field",
        "verdict=REFUSED",
        "--field",
        f"flags={flags_of(args)}",
        "--field",
        f"caller={where.get(CALLER_ENV, '')}",
    ]
    try:
        (spawn if start is None else start)(argv, rule_of(message))
    except OSError:
        return False
    return True
