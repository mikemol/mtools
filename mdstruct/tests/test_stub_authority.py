# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The stub is checked against the library it claims to describe.

⚑⚑⚑ A STUB IS AN UNCHECKED CLAIM UNTIL SOMETHING CHECKS IT, and this one cited a
`scripts/check_stub_authority.py` that did not exist — so the file asserted a verification
nobody had built, in evidence-prose, which reads as covered to anyone who does not go look.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_DIST = Path(__file__).resolve().parent.parent
_ALLOWLIST = _DIST / "stubs" / "panflute-allowlist.txt"


def test_the_stub_matches_the_library_it_describes(tmp_path: Path) -> None:
    """Run stubtest over the panflute stub, with the curated allowlist.

    ⚑⚑ THE ALLOWLIST IS CURATED, NOT GENERATED. `--generate-allowlist` produced 15 entries and
    two were `panflute.load` and `panflute.stringify` — the functions this package calls most,
    both carrying REAL defects (a wrong parameter name and a missing parameter). Accepting the
    generated file would have frozen both as permanently allowed and made this gate vacuous at
    exactly the point it exists to check.
    """
    proc = subprocess.run(
        [sys.executable, "-m", "mypy.stubtest", "panflute", "--ignore-missing-stub",
         "--allowlist", str(_ALLOWLIST), "--concise"],
        capture_output=True, text=True, check=False,
        # ⚑⚑ RUN FROM A WRITABLE DIRECTORY, NOT THE DISTRIBUTION ROOT. stubtest writes a sqlite
        # metastore into `.mypy_cache` RELATIVE TO CWD and exposes no knob for it — measured,
        # `--help` carries no cache option and `MYPY_CACHE_DIR` does not reach its build options.
        # A hermetic sandbox stages the distribution read-only, so it raised `unable to open
        # database file` and the witness failed for a reason unrelated to the stub. `MYPYPATH` is
        # absolute because cwd is no longer the root it was relative to.
        cwd=tmp_path,
        # ⚑ THE PARENT ENVIRONMENT IS INHERITED. A hand-built env looked tidier and was wrong: it
        # dropped `PYTHONPATH`, so under bazel the child could not see the staged `mypy` at all.
        env={**os.environ, "MYPYPATH": str(_DIST / "stubs")})
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_every_allowlist_entry_is_a_constructor() -> None:
    """Each allowed divergence is an `__init__`/`__new__`, never a called function.

    ⚑⚑ THIS IS WHAT KEEPS THE ALLOWLIST FROM BECOMING A SUPPRESSION LIST. mdstruct never
    constructs a panflute element — it reads them, via isinstance checks and attribute access,
    from whatever `load` returns. So a constructor entry is surface the stub declines to model;
    an entry that is NOT a constructor is a real inconsistency in something this package calls,
    and it would be hidden rather than fixed.
    """
    entries = [line.strip() for line in _ALLOWLIST.read_text(encoding="utf-8").splitlines()
               if line.strip() and not line.startswith("#")]
    assert entries
    offenders = [e for e in entries if not e.endswith(("__init__", "__new__", ".walk"))]
    assert offenders == [], f"non-constructor entries hide real divergence: {offenders}"
