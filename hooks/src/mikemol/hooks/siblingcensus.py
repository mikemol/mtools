# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Find the places a repo's tracked files reach into ANOTHER checkout (W1709, of W1707).

The operator's ruling (2026-10-19, transcript 695f3e0a line 84035): repos should stop being aware
that sibling paths exist. This is the census that gives each repo its number, the baseline a ratchet
(W1708) takes down to 0.

⚑ A REACH IS A PATH THAT RESOLVES INTO ANOTHER CHECKOUT, NOT ANY PATH THAT LOOKS LIKE ONE. mtools'
own distributions are siblings inside the one checkout (`pycodemod` depends on `../pathwalk`), and a
path that names the repo itself (`~/github/mtools/...` in mtools) leaves nothing. So each `../`
chain is resolved against the directory of the file that holds it and counted only when it lands
in `<github root>/<other repo>`, and each `~/github/<name>`, `$HOME/github/<name>` or
`/home/<user>/github/<name>` is counted only when `<name>` is not this repo.

⚑ A READING, NOT A VERDICT ABOUT INTENT: a docstring that mentions such a path counts the same as
code that opens one, because the ruling is that no tracked file should name it; the first
measurement is the baseline, and a mention that is later reworded leaves the count honestly.
"""

import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import cast

DOTDOT = re.compile(r"(?<![\w.])((?:\.\./)+)([A-Za-z][\w.-]*)")
HOME_FORMS = re.compile(
    r"(?:~|\$\{?HOME\}?|/home/[A-Za-z0-9_-]+|/Users/[A-Za-z0-9_-]+)/github/([A-Za-z][\w.-]*)"
)


@dataclass(frozen=True, slots=True)
class Reach:
    """One line of one file that names a path into another checkout."""

    file: str
    line: int
    target: str


def _lands_in(root: PurePosixPath, file: str, ups: int) -> PurePosixPath | None:
    # Where `ups` parent steps from the file's directory arrive, or None past the filesystem root.
    landing = root / PurePosixPath(file).parent
    if ups > len(landing.parts) - 1:
        return None
    for _ in range(ups):
        landing = landing.parent
    return landing


def _line_reaches(root: PurePosixPath, file: str, line: str) -> Iterator[str]:
    # The other checkouts one line names, by repo name.
    for match in DOTDOT.finditer(line):
        chain, name = cast("str", match.group(1)), cast("str", match.group(2))
        if _lands_in(root, file, chain.count("../")) == root.parent and name != root.name:
            yield name
    for home in HOME_FORMS.finditer(line):
        named = cast("str", home.group(1))
        if named != root.name:
            yield named


def reaches(root: Path, files: Mapping[str, str]) -> list[Reach]:
    """List the lines of `files` (path under `root` to text) that name another checkout.

    Returns:
        every reach in file and line order; a path into the repo itself is not one.

    """
    base = PurePosixPath(root.as_posix())
    return [
        Reach(name, number, other)
        for name in sorted(files)
        for number, line in enumerate(files[name].splitlines(), 1)
        for other in _line_reaches(base, name, line)
    ]
