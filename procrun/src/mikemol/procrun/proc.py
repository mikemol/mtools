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

import os
import select
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import TracebackType
from typing import BinaryIO, Literal, Self

# The exception `capture` raises for a child that outlasts its timeout, re-exported so a
# caller can name it without importing the subprocess module itself.
TimeoutExpired = subprocess.TimeoutExpired
# What `capture` returns, named here so a caller can annotate its own result without importing
# the subprocess module itself.
Completed = subprocess.CompletedProcess[str]
# What `capture_bytes` returns, for the same reason.
CompletedBytes = subprocess.CompletedProcess[bytes]
# Milliseconds in the second `poll` counts in.
_MS = 1000


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

    def __init__(self, popen: subprocess.Popen[bytes], reader: int | None = None) -> None:
        """Wrap the `Popen` this seam started, and the read end of its output pipe if any."""
        self._popen = popen
        self._reader = reader

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

    def first_line(self, idle: float) -> str:
        """Read the first line the child writes to its piped output.

        ⚑ THE BOUND IS SILENCE, NOT A CLOCK: `idle` is the longest the child may go without
        writing a byte, and every byte that arrives starts the count again. A child that is
        slow but still writing is never cut off; one that has gone quiet is, and the
        `TimeoutExpired` it raises is the one `capture` raises.

        Args:
            idle: Seconds without any output before giving up.

        Returns:
            The line without its newline; whatever was written if the output ended first.

        Raises:
            ValueError: when the child was not started by `spawn_piped`.

        """
        fd = self._reader
        if fd is None:
            message = "first_line needs a child started by spawn_piped"
            raise ValueError(message)
        poller = select.poll()
        poller.register(fd, select.POLLIN)
        written = bytearray()
        while True:
            if not poller.poll(idle * _MS):
                raise TimeoutExpired(self._popen.args, idle)
            byte = os.read(fd, 1)
            if not byte or byte == b"\n":
                return written.decode("utf-8", errors="replace")
            written.extend(byte)

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Kill the child if it still runs, reap it, and close its piped output."""
        if self._popen.poll() is None:
            self._popen.kill()
        self._popen.wait()
        if self._reader is not None:
            os.close(self._reader)


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


def spawn_piped(
    argv: Sequence[str],
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
    stderr: Stream | BinaryIO = "inherit",
) -> Child:
    """Start `argv` with its stdout piped to the caller and hand back the live child (W2277).

    ⚑ A SEPARATE FUNCTION BECAUSE `spawn` TAKES FIVE ARGUMENTS ALREADY: the child's first stdout
    line (`Child.first_line`) is how a caller learns a server is up and which port it took. The
    pipe is made here and its read end kept on the `Child`, so the caller names no subprocess
    type. The caller's stdin is left alone.

    Args:
        argv: The program and its arguments; never interpreted by a shell.
        cwd: The directory to run in; the caller's when omitted.
        env: The child's whole environment; the caller's when omitted.
        stderr: `inherit` leaves the caller's stderr, `discard` drops it, and a binary file
            object the caller opened receives it, so the caller can read what the child
            complained of after it has gone.

    Returns:
        The running child; its read end is closed when the context manager exits.

    Raises:
        OSError: when the program cannot be started; the pipe is closed first, as in `Popen`.

    """
    reader, writer = os.pipe()
    errors: int | BinaryIO | None = None
    if isinstance(stderr, str):
        if stderr == "discard":
            errors = subprocess.DEVNULL
    else:
        errors = stderr
    try:
        popen = subprocess.Popen(list(argv), cwd=cwd, env=env, stdout=writer, stderr=errors)
    except OSError:
        os.close(reader)
        raise
    finally:
        os.close(writer)
    return Child(popen, reader)
