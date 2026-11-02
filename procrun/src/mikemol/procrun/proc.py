# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The one place a child process is started, so a caller never spells the subprocess rules itself.

Ported from `mikemol.treeio.proc` (mtools:W873), which was ported from the `subprocess.run` calls in
paperkit's `tools/edit_snapshot.py` (paperkit:W142). paperkit waived the subprocess rules at each
call site; here the call lives in this module, whose one responsibility it is, and every other
module reaches a child through `capture`. It is a leaf of its own, standard library only, so a
caller that only needs to start a child does not inherit treeio's native git dependency.

Every argv is a sequence built by the caller: never a shell.
"""

import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path

# The exception `capture` raises for a child that outlasts its timeout, re-exported so a
# caller can name it without importing the subprocess module itself.
TimeoutExpired = subprocess.TimeoutExpired
# What `capture` returns, named here so a caller can annotate its own result without importing
# the subprocess module itself.
Completed = subprocess.CompletedProcess[str]
# What `capture_bytes` returns, for the same reason.
CompletedBytes = subprocess.CompletedProcess[bytes]


def capture(
    argv: Sequence[str],
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
    timeout: float | None = None,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run `argv` to completion with its output captured as text; a non-zero status is not raised.

    Args:
        argv: The program and its arguments; never interpreted by a shell.
        cwd: The directory to run in; the caller's when omitted.
        env: The child's whole environment; the caller's when omitted.
        timeout: Seconds to wait before giving up on the child; no limit when omitted, so a
            caller that bounds a long gate need not re-implement the seam (mtools:W872).
        input_text: Text written to the child's standard input (mtools:W2231, nemik:W1175); the
            child's stdin is the caller's when omitted, exactly as before.

    Returns:
        The finished process, with its return code, stdout and stderr.

    """
    return subprocess.run(
        list(argv),
        cwd=cwd,
        env=env,
        input=input_text,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )


def capture_bytes(
    argv: Sequence[str],
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
    timeout: float | None = None,
    input_bytes: bytes | None = None,
) -> CompletedBytes:
    """Run `argv` to completion with its output captured as BYTES; a non-zero status is not raised.

    The same seam as `capture` for a child whose output is not text (a rendered file, a protobuf) or
    whose input is bytes; nothing is decoded, so no byte can be mangled or refused on the way.

    Args:
        argv: The program and its arguments; never interpreted by a shell.
        cwd: The directory to run in; the caller's when omitted.
        env: The child's whole environment; the caller's when omitted.
        timeout: Seconds to wait before giving up on the child; no limit when omitted.
        input_bytes: Bytes written to the child's standard input; the caller's stdin when omitted.

    Returns:
        The finished process, with its return code and its stdout and stderr as bytes.

    """
    return subprocess.run(
        list(argv),
        cwd=cwd,
        env=env,
        input=input_bytes,
        capture_output=True,
        check=False,
        timeout=timeout,
    )
