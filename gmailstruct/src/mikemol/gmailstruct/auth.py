# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The refresh token, decrypted from its age file into memory only (W351).

⚑⚑ THE TOKEN NEVER TOUCHES A FILE IN THE CLEAR. It lives on disk only as an age file to the
YubiKey PIV recipient (age-plugin-yubikey); `decrypt` asks `age` for it on stdout, a pipe the
runner reads, and returns it. Nothing here writes, caches or logs it.

⚑ THE RUNNER IS AN ARGUMENT, NOT A DEFAULT. This module starts no process: the CLI (W289) passes
the runner that executes `age`, and the tests pass a fake one. So the record layer stays free of
subprocess, and the path from ciphertext to token is testable without a key.

⚑ A FAILURE CARRIES NO SECRET. When `age` fails, its stdout is dropped unread and the error names
only the file and the exit status, so a partial or garbage plaintext cannot reach a traceback.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

# argv -> (exit status, stdout, stderr). The CLI supplies one that runs the command; tests fake it.
type Runner = Callable[[list[str]], tuple[int, bytes, bytes]]


class DecryptError(Exception):
    """The token could not be decrypted; the message holds no plaintext."""


def decrypt(path: Path, identity: Path, runner: Runner) -> str:
    """Decrypt the refresh token at `path` with the YubiKey identity stub at `identity`.

    Returns:
        the token, stripped of surrounding whitespace.

    Raises:
        DecryptError: when age fails, or yields no token. The message names the file only.

    """
    status, out, _err = runner(["age", "--decrypt", "--identity", str(identity), str(path)])
    if status != 0:
        msg = f"age could not decrypt {path} (exit {status})"
        raise DecryptError(msg)
    try:
        token = out.decode("utf-8").strip()
    except UnicodeDecodeError:
        msg = f"age decrypted {path} to bytes that are not UTF-8"
        raise DecryptError(msg) from None
    if not token:
        msg = f"age decrypted {path} to nothing"
        raise DecryptError(msg)
    return token
