# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""One pin of one repo and how it stands against the target (mtools:W979, W1138).

⚑ THE ROW LIVES IN ITS OWN MODULE SO THE CENSUS AND ITS TEXTFILE CAN BOTH NAME IT. `repin_cli`
builds rows and `repin_metrics` renders them; with the row defined in the first, the second could
only name it under a `TYPE_CHECKING` guard to avoid a circular import, and a guard is what the
Codon target (mtools:W1319) cannot have. Both import it from here, and `repin_cli.Row` resolves.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Row:
    """One pin in one repo and how it stands against the target.

    `missing` is the must-have fixes a vendored pin lacks by commit ancestry (W1138): None when it
    was not measured (no par, or the pin is not a commit in the mtools history), an empty tuple
    when it has them all. `where` is the file and line the pin was read from (W966), appended as the
    last column so a parser that splits the first five still works.
    """

    repo: str
    dist: str
    form: str
    pinned: str
    status: str
    missing: tuple[str, ...] | None = None
    where: str = ""

    def line(self) -> str:
        """Render the row as one tab-separated line.

        Returns:
            the line, without a newline.

        """
        head = f"{self.repo}\t{self.dist}\t{self.form}\t{self.pinned}\t{self.status}"
        return f"{head}\t{self.where}" if self.where else head
