# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.corpus.suite_discovery`: substrate's suite arms, ported.

The live-population arm read substrate's own tree through `corpus.ROOT`; it becomes a synthetic
tree with known suites. A git-ignore arm is added, against a DECOY repository in tmp_path with
every GIT_* variable removed, since git's ignore is the walk's one owner of exclusions.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import TYPE_CHECKING

from mikemol.corpus import suite_discovery

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_MAIN_GUARD = 'if __name__ == "__main__":\n    sys.exit(_selftest())\n'
_ARGV_GUARD = 'if "--selftest" in sys.argv:\n    sys.exit(_selftest())\n'
_FLAG_IN_GUARD = ('if __name__ == "__main__":\n'
                  '    sys.exit(0 if "--selftest" in sys.argv else 1)\n')
_BODY = "def _selftest():\n    return 0\n\n"
_PLAIN_CLI = 'if __name__ == "__main__":\n    sys.exit(main(sys.argv))\n'


def _write(path: Path, text: str) -> None:
    """Write `text` to `path`, creating its directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_both_live_dispatch_idioms_are_admitted() -> None:
    """A __main__ guard, a bare argv dispatch, and a flag-naming guard with no body are suites.

    ⚑ Requiring the flag alone or the body alone erases one of the other two: both measured live.
    """
    assert suite_discovery.is_suite(_BODY + _MAIN_GUARD)
    assert suite_discovery.is_suite(_BODY + _ARGV_GUARD)
    assert suite_discovery.is_suite(_FLAG_IN_GUARD)


def test_neither_half_alone_is_a_suite() -> None:
    """A body with no dispatch is not a suite, and neither is a plain CLI entry point.

    ⚑ The entry point alone admits every CLI in the tree; the body alone admits implementation
    halves that report SILENT while their cases pass under a parent.
    """
    assert not suite_discovery.is_suite(_BODY)
    assert not suite_discovery.is_suite(_PLAIN_CLI)


def test_vendored_and_snapshot_subtrees_are_walked_past(tmp_path: Path) -> None:
    """Copies under .venv, .edit-snapshots and __pycache__ are not suites; the real one is."""
    _write(tmp_path / "tools" / "real.py", _BODY + _MAIN_GUARD)
    for skipped in (".venv", ".edit-snapshots", "__pycache__"):
        _write(tmp_path / "tools" / skipped / "copy.py", _BODY + _MAIN_GUARD)
    assert {label for label, _p in suite_discovery.discover(tmp_path)} == {"tools/real.py"}


def test_roots_are_discovered_not_frozen(tmp_path: Path) -> None:
    """A new directory is a root, a tracked suiteless one is too, and a dot-directory is not.

    ⚑ `agda` is admitted deliberately: the name roster that skipped it was deleted by ruling, and
    a test pinning it would have kept a deleted mechanism alive through its test.
    """
    for name in ("brand_new", "agda", ".hidden"):
        (tmp_path / name).mkdir()
    got = suite_discovery.roots(tmp_path)
    assert "brand_new" in got
    assert "agda" in got
    assert ".hidden" not in got


def test_the_walk_finds_the_suites_a_tree_holds(tmp_path: Path) -> None:
    """A tree with known suites yields exactly those: the positive control.

    ⚑ Zero suites is what a broken walk returns AND what a correct walk returns over an empty
    tree; only naming files that must be found separates them.
    """
    _write(tmp_path / "pkg" / "a_selftest.py", _BODY + _MAIN_GUARD)
    _write(tmp_path / "pkg" / "b.py", _FLAG_IN_GUARD)
    _write(tmp_path / "pkg" / "cli.py", _PLAIN_CLI)
    found = {label for label, _p in suite_discovery.discover(tmp_path)}
    assert found == {"pkg/a_selftest.py", "pkg/b.py"}


def test_a_git_ignored_tree_is_not_walked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A top-level tree git ignores is not a root: git's ignore is the one owner of exclusions.

    ⚑ Measured in substrate: a walker that never asked git kept counting `build/lib/`'s stale
    copy of every package module, twice, after `build/` was already fixed in git's view.
    """
    for name in [name for name in os.environ if name.startswith("GIT_")]:
        monkeypatch.delenv(name)
    git = shutil.which("git")
    assert git is not None
    subprocess.run([git, "init", "--quiet", str(tmp_path)], check=True)
    _write(tmp_path / ".gitignore", "build/\n")
    _write(tmp_path / "build" / "lib" / "copy_selftest.py", _BODY + _MAIN_GUARD)
    _write(tmp_path / "src" / "real_selftest.py", _BODY + _MAIN_GUARD)
    assert suite_discovery.roots(tmp_path) == ("src",)
    assert {label for label, _p in suite_discovery.discover(tmp_path)} == {
        "src/real_selftest.py",
    }
