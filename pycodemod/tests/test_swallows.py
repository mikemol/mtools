# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.pycodemod.swallows`: the silent handlers, what they catch, what they lose.

⚑⚑ THE HANDLERS AT :19 AND :24 ARE THE ARMS. For :19 the origin counted `g` (read on the RIGHT of
`y = g()`) as changed, so the later `g()` call made the handler read as feeding a verdict; for :24
it searched the whole FILE, so `z` read in the unrelated `h()` did the same. Both must be False.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.pycodemod import swallows as sw

if TYPE_CHECKING:
    from pathlib import Path

_CORPUS = """def f(paths):
    out = []
    for p in paths:
        try:
            out.append(p)
        except OSError:
            continue
    try:
        print(p)
    except Exception:
        pass
    try:
        x = g()
    except (Exception, OSError):
        return None
    try:
        y = g()
        use(y)
    except builtins.BaseException:
        return
    while True:
        try:
            z = g()
        except:
            break
    return x
def h():
    z = 1
    return z
try:
    w()
except ValueError:
    log()
    pass
"""

# The module-level handler whose body logs before passing: an accounting, not a swallow.
_ACCOUNTED_LINE = 32


def _write(tmp_path: Path, name: str, text: str) -> str:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def _rows(tmp_path: Path) -> list[tuple[int, str, str, bool]]:
    got = sw.swallows([_write(tmp_path, "m.py", _CORPUS)])
    return [(r.line, r.kind, r.exit, r.feeds) for r in got.rows]


def test_every_kind_and_every_silent_exit_is_found(tmp_path: Path) -> None:
    """⚑⚑ A tuple holding `Exception` is broad; a dotted BaseException is base; five exits."""
    assert [(line, kind, exit_) for line, kind, exit_, _ in _rows(tmp_path)] == [
        (6, "narrow", "continue"),
        (10, "broad", "pass"),
        (14, "broad", "return"),
        (19, "base", "return"),
        (24, "bare-except", "break"),
    ]


def test_feeds_is_a_later_read_in_the_same_scope(tmp_path: Path) -> None:
    """⚑⚑ An accumulator and a later-read target feed; output, scaffolding, other scopes do not."""
    assert [(line, feeds) for line, _, _, feeds in _rows(tmp_path)] == [
        (6, True),
        (10, False),
        (14, True),
        (19, False),
        (24, False),
    ]


def test_a_handler_that_does_anything_else_is_not_a_swallow(tmp_path: Path) -> None:
    """`log(); pass` accounts for the failure: that module-level handler is not reported."""
    lines = [line for line, _, _, _ in _rows(tmp_path)]
    assert _ACCOUNTED_LINE not in lines


def test_an_except_star_handler_is_read(tmp_path: Path) -> None:
    """An exception-group handler discards as silently as a plain one."""
    path = _write(tmp_path, "g.py", "try:\n    pass\nexcept* ValueError:\n    pass\n")
    got = sw.swallows([path])
    assert [(r.line, r.kind, r.exit) for r in got.rows] == [(3, "narrow", "pass")]


def test_the_census_reports_every_file_it_could_not_read(tmp_path: Path) -> None:
    """⚑⚑⚑ The census of silent swallows must not swallow: undecodable, unparseable, unreadable."""
    latin = tmp_path / "latin.py"
    latin.write_bytes(b"x = '\xe9'\n")
    bad = _write(tmp_path, "bad.py", "def (:\n")
    missing = str(tmp_path / "absent.py")
    got = sw.swallows([str(latin), bad, missing])
    assert [(s.path, s.why) for s in got.skipped] == [
        (str(latin), "undecodable"),
        (bad, "unparseable"),
        (missing, "unreadable"),
    ]
    assert got.rows == []
