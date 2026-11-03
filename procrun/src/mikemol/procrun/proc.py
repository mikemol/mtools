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
from types import TracebackType
from typing import Literal, Self

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


def capture_stdout(
    argv: Sequence[str],
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
    timeout: float | None = None,
) -> CompletedBytes:
    """Run `argv` to completion capturing only its STDOUT, as bytes; stderr is the caller's.

    ⚑ A CHILD THAT TALKS TO A PERSON THROUGH STDERR (mtools:W2242, gmailstruct W382):
    age-plugin-yubikey asks for the PIN and says to touch the key on age's stderr, so capturing
    it hides the prompt and the run fails naming no cause. Its stdout, which carries the secret,
    is captured and never printed.

    Args:
        argv: The program and its arguments; never interpreted by a shell.
        cwd: The directory to run in; the caller's when omitted.
        env: The child's whole environment; the caller's when omitted.
        timeout: Seconds to wait before giving up on the child; no limit when omitted.

    Returns:
        The finished process, with its return code and its stdout as bytes; its stderr went to the
        caller's, so it is not in the result.

    """
    return subprocess.run(
        list(argv),
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=None,
        check=False,
        timeout=timeout,
    )


# Where a spawned child's stdin or output goes: the caller's own, or nowhere.
Stream = Literal["inherit", "discard"]


class Child:
    """A running child process, held by a caller that must signal it, poll it or wait on it.

    ⚑ THE LIVE-HANDLE SEAM (mtools:W2241): `capture` runs a child to completion, which a test that
    signals a sleeper, races two lockers or probes a browser while it runs cannot use. This class
    owns the one `Popen` so those callers name no subprocess type and need no exemption of their
    own. Used as a context manager it kills and reaps the child on exit, so a test cannot leak one.
    """

    def __init__(self, popen: subprocess.Popen[bytes]) -> None:
        """Wrap the `Popen` this seam started."""
        self._popen = popen

    @property
    def pid(self) -> int:
        """The child's process id."""
        return self._popen.pid

    def poll(self) -> int | None:
        """Say whether the child has finished, without waiting.

        Returns:
            The exit status once it has finished, None while it runs.

        """
        return self._popen.poll()

    def wait(self, timeout: float | None = None) -> int:
        """Wait for the child to finish.

        Args:
            timeout: Seconds to wait; no limit when omitted.

        Returns:
            The child's exit status.

        """
        return self._popen.wait(timeout=timeout)

    def kill(self) -> None:
        """Send the child SIGKILL."""
        self._popen.kill()

    def terminate(self) -> None:
        """Send the child SIGTERM."""
        self._popen.terminate()

    def send_signal(self, sig: int) -> None:
        """Send the child the signal numbered `sig`."""
        self._popen.send_signal(sig)

    def __enter__(self) -> Self:
        """Enter the context: the child is already running.

        Returns:
            This child.

        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Kill the child if it still runs, and reap it."""
        if self._popen.poll() is None:
            self._popen.kill()
        self._popen.wait()


def spawn(
    argv: Sequence[str],
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
    stdin: Stream = "inherit",
    output: Stream = "inherit",
) -> Child:
    """Start `argv` and hand back the live child without waiting for it.

    Args:
        argv: The program and its arguments; never interpreted by a shell.
        cwd: The directory to run in; the caller's when omitted.
        env: The child's whole environment; the caller's when omitted.
        stdin: `inherit` leaves the caller's stdin, `discard` gives the child an empty one.
        output: `inherit` leaves the caller's stdout and stderr, `discard` drops both.

    Returns:
        The running child.

    """
    sink = subprocess.DEVNULL
    return Child(
        subprocess.Popen(
            list(argv),
            cwd=cwd,
            env=env,
            stdin=sink if stdin == "discard" else None,
            stdout=sink if output == "discard" else None,
            stderr=sink if output == "discard" else None,
        )
    )
