# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.pycodemod.exit`: the exit census, the catcher census, and the interlock.

⚑⚑ THE GUARD CASES ARE PAIRED: `!=` beside `==`, the guard's `else` beside its body — the two
misreads the origin made, each asserted against the reading it must not collapse into.
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from mikemol.pycodemod import exit as ex

if TYPE_CHECKING:
    from pathlib import Path

_LIB = """import os
import sys

def helper():
    sys.exit(2)

def entry():
    helper()

def unreached():
    raise SystemExit(1)

def hard():
    os._exit(3)

if __name__ != "__main__":
    sys.exit(4)
if __name__ == "__main__":
    sys.exit(0)
else:
    quit()
"""

_APP = """import lib

def run():
    try:
        lib.entry()
    except Exception:
        pass
    try:
        lib.unrelated()
    except Exception:
        pass
    try:
        lib.entry()
    except Exception:
        raise
"""

_CATCH = """def f():
    try:
        pass
    except:
        pass
    try:
        pass
    except BaseException:
        log()
    try:
        pass
    except (ValueError, SystemExit):
        "doc"
        return
    try:
        pass
    except BaseException:
        raise
    try:
        pass
    except ValueError:
        pass
    for _ in []:
        try:
            pass
        except BaseException:
            continue
    try:
        pass
    except BaseException:
        return 1
    try:
        pass
    except BaseException:
        pass
        pass
"""

_REACH_SELF = "from lib import own\nimport lib\nlib.self_read\n"
_REACH_ALIAS = "import lib as L\nL.entry\nx.other\n"
_REACH_STAR = "from lib import *\nfrom .lib import rel\nfrom pkg.s import f\n"


def _write(tmp_path: Path, name: str, text: str) -> str:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def _tree(src: str) -> ast.Module:
    return ast.parse(src)


def test_parse_all_names_every_file_it_could_not_read(tmp_path: Path) -> None:
    """⚑⚑ Unreadable, undecodable and unparseable are each a SKIP with its reason."""
    good = _write(tmp_path, "good.py", "x = 1\n")
    bad = _write(tmp_path, "bad.py", "def (:\n")
    latin = tmp_path / "latin.py"
    latin.write_bytes(b"x = '\xe9'\n")
    missing = str(tmp_path / "absent.py")
    trees, skipped = ex.parse_all([good, bad, str(latin), missing])
    assert list(trees) == [good]
    assert skipped == [
        ex.Skip(bad, "unparseable", "SyntaxError"),
        ex.Skip(str(latin), "undecodable", "UnicodeDecodeError"),
        ex.Skip(missing, "unreadable", "FileNotFoundError"),
    ]


def test_every_census_returns_its_own_skips(tmp_path: Path) -> None:
    """⚑⚑ Skips do not accumulate across calls: the origin's list grew for ever."""
    bad = _write(tmp_path, "bad.py", "def (:\n")
    for _ in range(2):
        assert ex.exits([bad]).skipped == [ex.Skip(bad, "unparseable", "SyntaxError")]
    assert ex.catchers([bad]).skipped == [ex.Skip(bad, "unparseable", "SyntaxError")]
    assert ex.interlock([bad]).skipped == [ex.Skip(bad, "unparseable", "SyntaxError")]


def test_module_name_is_the_flat_stem() -> None:
    """A `.py` file is its stem; anything else has no module name."""
    assert ex.module_name("/a/b/lib.py") == "lib"
    assert ex.module_name("/a/b/notes.txt") is None


def test_the_main_guard_is_equality_in_either_quote() -> None:
    """⚑⚑ `!=` is not the guard; `==` is, in either quote style."""
    guards = [
        "if __name__ == '__main__':\n    pass\n",
        'if __name__ == "__main__":\n    pass\n',
    ]
    for src in guards:
        node = _tree(src).body[0]
        assert isinstance(node, ast.If)
        assert ex.is_main_guard(node)
    node = _tree('if __name__ != "__main__":\n    pass\n').body[0]
    assert isinstance(node, ast.If)
    assert not ex.is_main_guard(node)


def test_exit_sites_find_every_spelling_with_its_owner() -> None:
    """⚑ `raise SystemExit` is an exit; only the guard's BODY is guarded, not its else."""
    tree = _tree(_LIB)
    got = ex.exit_sites(tree, ex.owners(tree))
    assert [(s.line, s.spelling, s.defname, s.under_main) for s in got] == [
        (5, "sys.exit", "helper", False),
        (11, "raise SystemExit", "unreached", False),
        (14, "os._exit", "hard", False),
        (17, "sys.exit", None, False),
        (19, "sys.exit", None, True),
        (21, "builtin-exit", None, False),
    ]


def test_non_exits_are_not_sites() -> None:
    """A raise of another class, a bare re-raise, and calls through expressions are not exits."""
    src = (
        "import sys\n"
        "raise ValueError()\n"
        "raise\n"
        "raise SystemExit\n"
        "fns[0]()\n"
        "a.sys.exit()\n"
        "getattr(sys, 'exit')(1)\n"
        "exit(1)\n"
    )
    tree = _tree(src)
    got = ex.exit_sites(tree, ex.owners(tree))
    assert [(s.line, s.spelling) for s in got] == [(4, "raise SystemExit"), (8, "builtin-exit")]


def test_the_innermost_def_owns_and_async_defs_count() -> None:
    """A nested def owns its exit over its parent; an async def is a def."""
    src = (
        "import sys\n"
        "def outer():\n"
        "    def inner():\n"
        "        sys.exit(1)\n"
        "async def a():\n"
        "    sys.exit(2)\n"
    )
    tree = _tree(src)
    got = ex.exit_sites(tree, ex.owners(tree))
    assert [(s.line, s.defname) for s in got] == [(4, "inner"), (6, "a")]


def test_reached_names_are_what_other_files_spell(tmp_path: Path) -> None:
    """⚑⚑⚑ `import m` reaches only what is then SPELLED; `from m import` and aliases count."""
    paths = [
        _write(tmp_path, "lib.py", _REACH_SELF),
        _write(tmp_path, "a.py", _REACH_ALIAS),
        _write(tmp_path, "b.py", _REACH_STAR),
    ]
    trees, _ = ex.parse_all(paths)
    assert ex.reached_names(trees) == {"lib": {"entry", "*"}, "pkg": {"f"}}


def test_imported_modules_record_first_segments(tmp_path: Path) -> None:
    """A dotted import is recorded under its first segment; a relative one is not recorded."""
    a = _write(tmp_path, "a.py", "import pkg.sub\nfrom lib import x\nfrom . import y\n")
    trees, _ = ex.parse_all([a])
    assert ex.imported_modules(trees) == {"pkg": {a}, "lib": {a}}


def test_callee_is_the_bare_name_or_none() -> None:
    """`f()` and `x.f()` both name `f`; a call through an expression names nothing."""
    calls = [n for n in ast.walk(_tree("f()\nx.f()\nfns[0]()\n")) if isinstance(n, ast.Call)]
    assert sorted(str(ex.callee(c)) for c in calls) == ["None", "f", "f"]


def test_exits_classify_every_site_by_reach(tmp_path: Path) -> None:
    """⚑⚑⚑ A def another file reaches is LIBRARY, two hops down included; the rest are not."""
    lib = _write(tmp_path, "lib.py", _LIB)
    _write(tmp_path, "app.py", _APP)
    got = ex.exits([lib, str(tmp_path / "app.py")])
    assert [(r.line, r.verdict) for r in got.rows] == [
        (5, "LIBRARY"),
        (11, "dispatch"),
        (14, "hard"),
        (17, "LIBRARY"),
        (19, "main-only"),
        (21, "LIBRARY"),
    ]
    assert got.rows[0].why == "in def helper(), NAMED by another file; 1 import lib"
    assert got.rows[1].why == "in def unreached(); no importer names or reaches it (1)"
    assert got.rows[3].why == "module level in a module 1 file(s) import"
    assert got.skipped == []


def test_a_self_import_is_not_an_importer(tmp_path: Path) -> None:
    """A module-level exit in a file only IT imports is its own process: main-only."""
    solo = _write(tmp_path, "solo.py", "import solo\nimport sys\nsys.exit(1)\n")
    got = ex.exits([solo])
    assert [(r.verdict, r.why) for r in got.rows] == [
        ("main-only", "module level, nothing imports this module"),
    ]


def test_catchers_are_found_by_type_with_silence_and_reraise(tmp_path: Path) -> None:
    """⚑⚑⚑ The handler's TYPE decides; `silent` is a bare discard; a re-raise is never silent."""
    path = _write(tmp_path, "c.py", _CATCH)
    got = ex.catchers([path])
    assert [(r.line, r.kind, r.defname, r.silent, r.reraises) for r in got.rows] == [
        (4, "bare-except", "f", True, False),
        (8, "base", "f", False, False),
        (12, "named", "f", True, False),
        (17, "base", "f", False, True),
        (26, "base", "f", True, False),
        (30, "base", "f", False, False),
        (34, "base", "f", False, False),
    ]


def test_interlock_finds_the_defended_looking_site(tmp_path: Path) -> None:
    """⚑⚑⚑ `except Exception` around an exiting call; not an unrelated call, not a re-raise."""
    lib = _write(tmp_path, "lib.py", _LIB)
    app = _write(tmp_path, "app.py", _APP)
    got = ex.interlock([lib, app])
    assert got.rows == [ex.Interlock(app, 4, "run", "entry")]


def test_interlock_sees_an_exit_within_its_own_module(tmp_path: Path) -> None:
    """A same-module exiting def is visible without any import; a guarded exit makes no def exit."""
    src = (
        "import sys\n"
        "def bail():\n"
        "    sys.exit(1)\n"
        "def safe():\n"
        "    if __name__ == '__main__':\n"
        "        sys.exit(0)\n"
        "try:\n"
        "    safe()\n"
        "except Exception:\n"
        "    pass\n"
        "try:\n"
        "    bail()\n"
        "except (Exception):\n"
        "    pass\n"
    )
    path = _write(tmp_path, "m.py", src)
    assert ex.interlock([path]).rows == [ex.Interlock(path, 11, None, "bail")]


def test_known_misses_are_declared() -> None:
    """The census states its blind spots rather than reading a zero as a fact."""
    assert any("ALIAS" in m for m in ex.KNOWN_MISSES)
