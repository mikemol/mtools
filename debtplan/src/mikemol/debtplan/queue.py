# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""One repository's paths-forward queue, written only through `mikemol-paths-forward`.

⚑⚑ THE STATE FILE HAS ONE WRITER. `mikemol.pathsforward.ops` mutates a state in memory, but the
command's `main` is what also appends the ledger line, regenerates the mirror and holds the flock.
Calling `ops` directly would rewrite those effects here and drift from them; calling `main` in this
process is the same writer without a child process. It is a parameter (`runner`), so a witness can
hand in a recorder and a real queue can be exercised end to end.

⚑ THE WRITER'S OUTPUT IS CAPTURED, NOT PRINTED. A refusal is a return code and the words that came
with it, handed back to the caller, who decides what a refused card means.
"""

from __future__ import annotations

import contextlib
import io
from dataclasses import dataclass
from typing import TYPE_CHECKING

from mikemol.pathsforward.cli import main as pf_main
from mikemol.pathsforward.model import text
from mikemol.pathsforward.store import load

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

type Runner = Callable[[list[str]], int]

EXIT_REFUSED = 2
"""The code a writer that exited without one is read as: refused."""


@dataclass(frozen=True, slots=True)
class Card:
    """A queue card the plan keys by file: its symbol and its status."""

    symbol: str
    status: str


class Queue:
    """A state file, and the one writer that may change it."""

    def __init__(self, state: Path, runner: Runner = pf_main) -> None:
        """Bind the state file and the writer's entry point."""
        self.state = state
        self.runner = runner

    def run(self, *args: str) -> tuple[int, str]:
        """Run the writer on this queue's state file.

        Returns:
            The writer's exit code and everything it printed, standard output and error together.
            A writer that exits through `SystemExit` without an integer code is read as refused.

        """
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            try:
                code = self.runner(["--state", str(self.state), *args])
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else EXIT_REFUSED
        return code, out.getvalue()

    def cards(self, prefix: str) -> dict[str, Card]:
        """Read the cards whose title starts with `prefix`, keyed by the file the title names.

        A title is `<prefix><file> (<n> findings)`; the file is what lies between the prefix and the
        first ` (`.

        Returns:
            Each keyed file and its card, in the queue's order.

        """
        found: dict[str, Card] = {}
        for record in load(self.state).waypoints:
            title = text(record, "title")
            if title.startswith(prefix):
                key = title.removeprefix(prefix).split(" (")[0]
                found[key] = Card(text(record, "symbol"), text(record, "status"))
        return found
