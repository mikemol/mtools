# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Say when this venv's copy of `mikemol.endpoints` is not the checkout's (mtools:W1532).

⚑ THE CHILD'S VENV HOLDS A COPY, NOT A LINK (luthen-observability-d9, 2026-10-18): `mikemol-otlp`
installs `mikemol-endpoints` from a path, so a change to the resolver reached the sender but not
the child, which kept the old resolver and failed SILENT for three minutes of a measurement: no
`mikemol.*` series, no log line. The failure is silent by design (a metric must never stop a
commit), so this is the one place it can speak: on start, if the checkout's `endpoints/` source
sits above this module and its `resolve.py` differs byte for byte from the installed one, one
line on stderr names both files and the command that refreshes the copy.

⚑ SILENT WHEN IT CANNOT BE A CHECKOUT: a wheel installed elsewhere has no `endpoints/` source
above it, so nothing is compared and nothing is said. It reads two small files and writes none.
CONSUMED BY: `mikemol.otlp.cli.main`.
"""

from pathlib import Path

from mikemol.endpoints import resolve

_SOURCE = Path("endpoints") / "src" / "mikemol" / "endpoints" / "resolve.py"
_FIX = "uv sync --frozen --reinstall-package mikemol-endpoints (in the otlp directory)"


def notice() -> str | None:
    """Judge this process's own installed resolver against the checkout above this module.

    Returns:
        the one-line warning, or None when nothing is stale or no checkout is above.

    """
    return stale(Path(resolve.__file__), Path(__file__))


def checkout_copy(start: Path) -> Path | None:
    """Find the checkout's resolver above a path.

    Returns:
        the first `endpoints/src/mikemol/endpoints/resolve.py` found in a parent of `start`, or
        None when no parent holds one.

    """
    for parent in start.resolve().parents:
        candidate = parent / _SOURCE
        if candidate.is_file():
            return candidate
    return None


def stale(installed: Path, start: Path) -> str | None:
    """Say, in one line, that the installed resolver differs from the checkout's.

    Returns:
        the line, or None when there is no checkout above `start`, the installed file is absent,
        or the two are byte-identical.

    """
    source = checkout_copy(start)
    if source is None or not installed.is_file():
        return None
    if installed.read_bytes() == source.read_bytes():
        return None
    return (
        f"mikemol-otlp: its mikemol-endpoints ({installed}) differs from the checkout's "
        f"({source}), so it may resolve differently than the sender; refresh it with: {_FIX}"
    )
