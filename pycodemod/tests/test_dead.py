# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.pycodemod.dead`: what is dead, what is excused and why, what was unread.

⚑⚑ `ghost` AND `ghost2` ARE THE ARMS: the origin excused a def whenever its quoted name appeared
anywhere in the file — here, only in a docstring and a comment. Both must read DEAD.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.pycodemod import dead as dd
from mikemol.pycodemod import sites

if TYPE_CHECKING:
    from pathlib import Path

_CORPUS = '''"""Module doc mentioning "ghost"."""
# comment "ghost2"
def ghost():
    pass
def ghost2():
    pass
def live():
    pass
def cb():
    pass
def dispatched():
    pass
def __init__():
    pass
def __private():
    pass
def main():
    pass
def visit_Call():
    pass
def on_():
    pass
live()
register(callbacks=[cb])
MODES = {'dispatched': 1}
'''


def _scan(tmp_path: Path, *extra: str) -> sites.Sites:
    path = tmp_path / "m.py"
    path.write_text(_CORPUS, encoding="utf-8")
    return sites.scan([str(path), *extra])


def test_a_prose_mention_does_not_excuse_a_dead_def(tmp_path: Path) -> None:
    """⚑⚑ A name quoted in a docstring or comment is not a dispatch: `ghost`, `ghost2` are dead."""
    got = dd.dead(_scan(tmp_path))
    assert [d.name for d in got.dead] == ["__private", "ghost", "ghost2", "on_"]


def test_every_exemption_is_reported_with_its_reason(tmp_path: Path) -> None:
    """⚑⚑⚑ An excused def is a visible row naming its rule — a single-quoted dispatch included."""
    got = dd.dead(_scan(tmp_path))
    assert [(e.name, e.why) for e in got.exempt] == [
        ("__init__", "dunder — invoked by the runtime"),
        ("dispatched", "dispatch — named by a string constant"),
        ("main", "entry point by convention"),
        ("visit_Call", "libcst/ast visitor — dispatched off the node type"),
    ]


def test_a_call_or_a_use_as_value_is_a_use(tmp_path: Path) -> None:
    """`live()` is a call and `callbacks=[cb]` a use as a value: neither def is dead or exempt."""
    got = dd.dead(_scan(tmp_path))
    named = {d.name for d in got.dead} | {e.name for e in got.exempt}
    assert {"live", "cb"}.isdisjoint(named)


def test_a_narrowed_scan_is_refused(tmp_path: Path) -> None:
    """⚑⚑ "No caller in this population" over one name reads live code as dead."""
    path = tmp_path / "m.py"
    path.write_text(_CORPUS, encoding="utf-8")
    with pytest.raises(ValueError, match="unnarrowed"):
        dd.dead(sites.scan([str(path)], "ghost"))


def test_an_unread_file_is_reported_once(tmp_path: Path) -> None:
    """A file both readers refuse is one skip, not two."""
    bad = tmp_path / "bad.py"
    bad.write_text("def (:\n", encoding="utf-8")
    got = dd.dead(_scan(tmp_path, str(bad)))
    assert [(s.path, s.why) for s in got.skipped] == [(str(bad), "unparseable")]


def test_string_constants_exclude_docstrings_and_report_unread(tmp_path: Path) -> None:
    """Code strings are collected; docstrings are prose; an unreadable file is a skip."""
    path = tmp_path / "s.py"
    path.write_text('"""doc"""\nclass K:\n    """kdoc"""\nx = "code"\n', encoding="utf-8")
    missing = str(tmp_path / "absent.py")
    found, skipped = dd.string_constants([str(path), missing])
    assert found == {"code"}
    assert [(s.path, s.why) for s in skipped] == [(missing, "unreadable")]


def test_a_framework_prefix_needs_a_name_after_it() -> None:
    """`visit_Call` satisfies the libcst contract; a bare `on_` satisfies nothing."""
    assert dd.framework_dispatch("test_x") == "pytest — collected by prefix"
    assert dd.framework_dispatch("on_") is None
    assert dd.framework_dispatch("helper") is None
