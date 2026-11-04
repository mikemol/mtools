# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The result of one command the gate tools run, as a value this package owns (W2265).

⚑ THE SEAMS RETURN THIS, NOT `subprocess.CompletedProcess`. A seam typed with the standard
library's process record makes every test that fakes a command name `subprocess` types, and so
every such test needs the subprocess exemptions. A three-field record the seams fill from whatever
actually ran has no such name: the real adapters (`rungate.capture_output`,
`rungate.run_passthrough`, `hook_index.git_status`) are the only code that touches `subprocess`,
and the tests build this.

⚑ NO DEPENDENCY: this package is vendored by other repositories, so the record is local rather than
another distribution's result type.
"""

from dataclasses import dataclass


class CommandFailedError(Exception):
    """A command the caller required to succeed exited non-zero."""

    def __init__(self, returncode: int, stderr: str = "") -> None:
        """Remember the exit status and what the command said on stderr."""
        super().__init__(f"command exited {returncode}")
        self.returncode = returncode
        self.stderr = stderr


@dataclass(frozen=True)
class Outcome:
    """What a command exited with and printed."""

    returncode: int
    stdout: str = ""
    stderr: str = ""

    def check(self) -> None:
        """Refuse a failed command.

        Raises:
            CommandFailedError: when the exit status is not zero.

        """
        if self.returncode != 0:
            raise CommandFailedError(self.returncode, self.stderr)
