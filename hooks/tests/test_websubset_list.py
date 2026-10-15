# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the portable-module list reader (mtools:W1256).

⚑ THE CONTROLS ARE THE FILES THAT MUST NOT READ AS "NOTHING IS PORTABLE": a missing file and every
malformed entry raise, each naming its line, while a list of only comments is an honest empty list.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.hooks import websubset_list

if TYPE_CHECKING:
    from pathlib import Path


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / websubset_list.LIST_NAME
    path.write_text(text, encoding="utf-8")
    return path


def test_entries_are_read_in_order_and_comments_and_blanks_are_ignored(tmp_path: Path) -> None:
    """Paths come back as written; `#` starts a comment, also after a path; blanks vanish."""
    path = _write(tmp_path, "# header\n\na/b.py\n  c/d.py  # why\n")
    assert websubset_list.portable(path) == ["a/b.py", "c/d.py"]


def test_a_list_of_only_comments_is_an_honest_empty_list(tmp_path: Path) -> None:
    """Nothing opted in yet is a valid state: the gate is declared before anything is in it."""
    assert websubset_list.portable(_write(tmp_path, "# nothing yet\n")) == []


def test_a_missing_file_raises_and_is_never_an_empty_list(tmp_path: Path) -> None:
    """A vanished list must not read as nothing-is-portable."""
    with pytest.raises(websubset_list.PortableListError, match="cannot be read"):
        websubset_list.portable(tmp_path / "absent.txt")


@pytest.mark.parametrize(
    ("text", "fragment"),
    [
        ("/etc/x.py\n", ":1: '/etc/x.py' is not a repo-relative .py path"),
        ("a/../b.py\n", ":1: 'a/../b.py' is not a repo-relative .py path"),
        ("# ok\nnotpython.txt\n", ":2: 'notpython.txt' is not a repo-relative .py path"),
        ("a.py\nb.py\na.py\n", ":3: a.py is listed twice"),
    ],
)
def test_each_malformed_entry_raises_naming_its_line(
    tmp_path: Path, text: str, fragment: str
) -> None:
    """Absolute, parent-escaping, non-Python and repeated entries each raise with the line."""
    with pytest.raises(websubset_list.PortableListError) as caught:
        websubset_list.portable(_write(tmp_path, text))
    assert fragment in str(caught.value)
