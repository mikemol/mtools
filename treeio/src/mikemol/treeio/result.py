# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The verdict a read returns: a presence, the raw bytes, and the cause when the read broke.

Ported from paperkit's `tools/vfs.py`. A read RETURNS a verdict rather than raising, because ABSENT
is a normal answer that callers branch on. BROKEN carries its cause in `error`, and `require`
turns either non-answer into a raise for callers that want the exception.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mikemol.treeio.presence import Presence

if TYPE_CHECKING:
    from pathlib import Path

    from mikemol.treeio.sources import Source


@dataclass(slots=True, eq=False, repr=False)
class Result:
    """What a read found: presence, data, error, path and source. Truthy only when PRESENT."""

    presence: Presence
    data: bytes | None = None
    error: BaseException | None = None
    path: str | Path | None = None
    source: Source | None = None

    def __bool__(self) -> bool:
        """Say whether the read found a blob.

        Returns:
            True only for PRESENT, so an empty file is truthy as a read and ABSENT is falsy.

        """
        return self.presence is Presence.PRESENT

    def __repr__(self) -> str:
        """Render the presence, the byte count and the path.

        Returns:
            Text of the form Result(PRESENT, 5 bytes, 'a.txt'), with a dash for no data.

        """
        size = len(self.data) if self.data is not None else "-"
        return f"Result({self.presence}, {size} bytes, {self.path!r})"

    def require(self) -> bytes:
        """Return the bytes, or RAISE: for callers that want an exception rather than a branch.

        ABSENT and BROKEN raise DIFFERENT types, so an except clause for FileNotFoundError cannot
        accidentally swallow a bad revision: the distinction survives the conversion.

        Returns:
            The raw bytes of a PRESENT read.

        Raises:
            FileNotFoundError: when the read is ABSENT.
            RuntimeError: when a PRESENT result carries no data.

        """
        if self.presence is Presence.PRESENT:
            if self.data is None:
                msg = f"{self.path}: a PRESENT result with no data"
                raise RuntimeError(msg)
            return self.data
        if self.presence is Presence.ABSENT:
            msg = f"{self.path}: not present at {self.source}"
            raise FileNotFoundError(msg)
        raise self.error or RuntimeError(f"{self.path}: broken with no recorded cause")

    def text(self, errors: str = "strict") -> str:
        """Decode as UTF-8. A decode failure is BROKEN, not empty and not absent.

        Choosing errors="replace" is the CALLER's decision to make, never this layer's default.

        Returns:
            The decoded text of a PRESENT read.

        """
        return self.require().decode("utf-8", errors)
