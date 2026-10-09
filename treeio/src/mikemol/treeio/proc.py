# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The one place a child process is started, so a caller never spells the subprocess rules itself.

Ported from the `subprocess.run` calls in paperkit's `tools/edit_snapshot.py` (paperkit:W142).
paperkit waived the subprocess rules at each call site; here the call lives in this module, whose
one responsibility it is, and every other module reaches a child through `capture`.

Every argv is a sequence built by the caller: never a shell.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path


def capture(
    argv: Sequence[str],
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run `argv` to completion with its output captured as text; a non-zero status is not raised.

    Args:
        argv: The program and its arguments; never interpreted by a shell.
        cwd: The directory to run in; the caller's when omitted.
        env: The child's whole environment; the caller's when omitted.
        timeout: Seconds to wait before giving up on the child; no limit when omitted
            (mtools:W872, so a caller that bounds a long gate need not re-implement the seam).

    Returns:
        The finished process, with its return code, stdout and stderr.

    """
    return subprocess.run(
        list(argv), cwd=cwd, env=env, capture_output=True, text=True, check=False, timeout=timeout
    )
