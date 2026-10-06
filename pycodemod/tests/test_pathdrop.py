# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `pathdrop`: a named `sys.path` mutation goes, and the `sys` it leaves idle."""

from __future__ import annotations

import re

from mikemol.pycodemod import pathdrop

_ENGINE = re.compile(r"paperkit|ENGINE")


def test_a_matching_mutation_and_the_idle_sys_import_are_removed() -> None:
    """⚑ The only use of `sys` was the mutation, so both lines go and the rest is untouched."""
    src = (
        'import sys\nfrom pathlib import Path\n\nsys.path.insert(0, str(Path("paperkit")))\nX = 1\n'
    )
    got = pathdrop.retire(src, _ENGINE)
    assert got.text == "from pathlib import Path\n\nX = 1\n"
    assert got.lines == [4]


def test_a_mutation_the_pattern_does_not_name_stays() -> None:
    """⚑⚑ A sibling-directory insert exists for another reason and is not guessed away."""
    src = "import sys\n\nsys.path.insert(0, HERE)\n"
    got = pathdrop.retire(src, _ENGINE)
    assert got.text == src
    assert got.lines == []


def test_sys_stays_when_it_is_read_elsewhere() -> None:
    """⚑ `import sys` is removed only when every reference was inside a removed statement."""
    src = "import sys\n\nsys.path.append(ENGINE)\nprint(sys.argv)\n"
    got = pathdrop.retire(src, _ENGINE)
    assert got.text == "import sys\n\nprint(sys.argv)\n"


def test_a_mutation_with_a_comment_line_stays() -> None:
    """⚑ Commentary is not tidied away: a commented mutation is kept, and so is its `sys`."""
    src = "import sys\n\n# the engine\nsys.path.insert(0, ENGINE)\n"
    got = pathdrop.retire(src, _ENGINE)
    assert got.text == src


def test_a_mutation_inside_a_block_stays() -> None:
    """⚑ Only a module-level statement is removed: an emptied block would not parse."""
    src = "import sys\n\nif X:\n    sys.path.insert(0, ENGINE)\n"
    got = pathdrop.retire(src, _ENGINE)
    assert got.text == src


def test_the_other_names_of_a_combined_import_are_kept() -> None:
    """⚑ `import os, sys` loses only `sys`, and the line ends without a dangling comma."""
    src = "import os, sys\n\nsys.path.insert(0, ENGINE)\nos.getcwd()\n"
    got = pathdrop.retire(src, _ENGINE)
    assert got.text == "import os\n\nos.getcwd()\n"
