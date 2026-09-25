# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The reader guard must ADMIT a runnable reader and SKIP a present-but-dead one — both arms.

⚑⚑⚑ A GUARD THAT ALWAYS SKIPS IS INDISTINGUISHABLE FROM ONE THAT WORKS, on a host where the
reader is dead. Tick 20 measured the skip arm on this host (three arms skipped with a stated
reason where they had failed); this module supplies the ADMIT arm, which the host cannot, by
building a reader whose shebang resolves and one whose shebang does not, and asking the same
predicate about each.

⚑⚑ THE DEAD READER IS BUILT, NOT FOUND. Pointing at `mdstruct/.venv/bin/mdstruct` would make
this arm's verdict depend on which host it runs on — the exact coupling the guard exists to
survive. A script whose first line names an interpreter path that does not exist is the same
object as a venv whose root was removed, and it is constructible anywhere.
"""

from __future__ import annotations

import os
import stat
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def _script(path: Path, shebang: str) -> Path:
    """Write a two-line script under `shebang`, mode 775 — the corpse's exact shape.

    Returns:
        the path written, for chaining into the predicate.

    """
    path.write_text(f"#!{shebang}\nexit 0\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def _runs(reader: Path) -> bool:
    """Restate the guard's predicate, so this module tests the SHAPE and not the symbol.

    Returns:
        True when `reader` is a file AND `execve` accepts it; False for absent or dead.

    """
    if not reader.is_file():
        return False
    try:
        subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] — the reader is the subject
            [str(reader), "--help"],
            capture_output=True,
            check=False,
            timeout=30,
        )
    except OSError:
        return False
    return True


def test_a_reader_whose_shebang_resolves_is_admitted(tmp_path: Path) -> None:
    """The ADMIT arm. Without it the guard could skip everything and never be caught."""
    live = _script(tmp_path / "live", "/bin/sh")
    assert live.is_file(), "the control script was not written — nothing below is measured"
    assert _runs(live), "a script whose shebang resolves must be ADMITTED, and was skipped"


def test_a_present_reader_with_a_dead_shebang_is_skipped(tmp_path: Path) -> None:
    """The SKIP arm, on a constructed corpse rather than whichever one this host happens to have.

    ⚑ `is_file()` IS TRUE HERE, which is the whole point: the old guard would have admitted this,
    and the arm behind it would then have failed with `FileNotFoundError` naming a file that is
    present and mode 775. The errno names the script; the fault is the interpreter.
    """
    dead = _script(tmp_path / "dead", str(tmp_path / "no-such-interpreter" / "python3"))
    assert dead.is_file(), "the corpse was not written — nothing below is measured"
    assert os.access(dead, os.X_OK), "the corpse must be mode +x, or this tests absence not death"
    assert not _runs(dead), (
        "a present, executable script whose shebang interpreter does not exist must be SKIPPED — "
        "this is the shape that failed three arms on 2026-09-19 with ENOENT against a present file"
    )


def test_an_absent_reader_is_skipped_too(tmp_path: Path) -> None:
    """The ORIGINAL case still holds — presence is necessary for admission, not sufficient."""
    assert not _runs(tmp_path / "absent"), "a reader that does not exist must be skipped"
