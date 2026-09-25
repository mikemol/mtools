# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.pycodemod.strings`: string keys by use, and string values by role.

⚑⚑ LINES 2, 5 AND 6 OF `_KEYS` ARE THE ARMS: the origin missed the dict-display declaration and
reported the write and the delete as READS.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.pycodemod import strings

if TYPE_CHECKING:
    from pathlib import Path

_KEYS = '''SCHEMA = ("title", "link")
DEFAULTS = {"link": None}
def use(d):
    x = d["link"]
    d["link"] = 1
    del d["link"]
    if "link" not in d:
        d.get("link")
    return x
class K:
    async def m(self, d):
        """Docstring mentions link."""
        return d.pop("link")
'''

_LITERALS = '''"""Module about sqlite."""
KINDS = ("sqlite", "postgres")
def pick(back):
    if back == "sqlite":
        return dialect("sqlite3")
    url = f"sqlite:///{back}"
    return url
async def later():
    """Async doc: sqlite."""
    return "x-sqlite"
'''

# The accented letter e-acute, and the six characters that spell it as an escape in source.
_ACCENTED = chr(0xE9)
_ESCAPED = chr(92) + "u00e9"


def _write(tmp_path: Path, name: str, text: str) -> str:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_a_key_is_read_written_deleted_or_declared(tmp_path: Path) -> None:
    """⚑⚑ Each use by kind: a write and a delete are not reads; a dict display declares."""
    path = _write(tmp_path, "k.py", _KEYS)
    got = strings.key_reads([path], "link")
    assert [(r.line, r.kind, r.context) for r in got.rows] == [
        (1, "decl", "<module>"),
        (2, "decl", "<module>"),
        (4, "read", "use"),
        (5, "write", "use"),
        (6, "delete", "use"),
        (7, "read", "use"),
        (8, "read", "use"),
        (13, "read", "K.m"),
    ]


def test_a_key_spelled_with_an_escape_is_found(tmp_path: Path) -> None:
    """⚑ The prefilter must not reject a file whose literal spells the key with an escape."""
    path = _write(tmp_path, "e.py", 'd["' + _ESCAPED + '"]\n')
    got = strings.key_reads([path], _ACCENTED)
    assert [(r.line, r.kind) for r in got.rows] == [(1, "read")]


def test_may_hold_rejects_only_what_cannot_be_there() -> None:
    """A plain value must appear verbatim; any other value might be escaped, so is not rejected."""
    assert not strings.may_hold("abc", "x")
    assert strings.may_hold("axb", "x")
    assert strings.may_hold("abc", _ACCENTED)


def test_a_literal_is_classified_by_the_role_it_plays(tmp_path: Path) -> None:
    """⚑⚑ f-string text and an async def's docstring are seen; each role is the enclosing one."""
    path = _write(tmp_path, "l.py", _LITERALS)
    got = strings.literal_sites([path], "sqlite")
    assert [(r.line, r.role, r.context, r.value) for r in got.rows] == [
        (1, "doc", "<module>", "Module about sqlite."),
        (2, "decl", "<module>", "sqlite"),
        (4, "compare", "pick", "sqlite"),
        (5, "arg", "pick", "sqlite3"),
        (6, "fstring", "pick", "sqlite:///"),
        (9, "doc", "later", "Async doc: sqlite."),
        (10, "other", "later", "x-sqlite"),
    ]


def test_both_readers_report_every_file_they_could_not_read(tmp_path: Path) -> None:
    """⚑⚑ The origin's bare `except Exception: continue` dropped these; each is now a skip."""
    latin = tmp_path / "latin.py"
    latin.write_bytes(b"x = '\xe9'\n")
    bad = _write(tmp_path, "bad.py", "def (:\n")
    missing = str(tmp_path / "absent.py")
    paths = [str(latin), bad, missing]
    by_key = strings.key_reads(paths, "k").skipped
    by_literal = strings.literal_sites(paths, "k").skipped
    for skipped in (by_key, by_literal):
        assert [(s.path, s.why) for s in skipped] == [
            (str(latin), "undecodable"),
            (bad, "unparseable"),
            (missing, "unreadable"),
        ]
